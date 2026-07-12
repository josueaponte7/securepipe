# SecurePipe — Orquestador de escaneo de seguridad

![CI](https://github.com/josueaponte7/securepipe/actions/workflows/securepipe.yml/badge.svg)

SecurePipe **no es un agente ni usa IA**. Es un **orquestador determinista** que corre cuatro escáneres de seguridad en paralelo sobre un directorio y agrega sus resultados en un único JSON, con un **score calculado por fórmula** (sin modelo, sin heurística de IA, reproducible).

## El problema que resuelve

La mayoría de repos no tiene ninguna línea de seguridad automatizada: nadie escanea dependencias, nadie detecta secretos, nadie valida la config de Docker/IaC. SecurePipe reúne cuatro herramientas maduras detrás de una sola entrada (HTTP o CLI) y devuelve un resultado combinado más un score.

## Stack

Solo lo que realmente corre hoy:

- **FastAPI** — orquestador HTTP (servicio en el puerto 8001)
- **Semgrep** — análisis estático de código (SAST)
- **Trivy** — vulnerabilidades en dependencias y filesystem (SCA)
- **Gitleaks** — detección de secretos en el repositorio
- **Checkov** — seguridad de IaC (Dockerfile, GitHub Actions, etc.)

## Arquitectura

Dos entradas comparten exactamente la misma lógica de escaneo y scoring:

```
POST /scan  ─┐
             ├─→ asyncio.gather(Semgrep, Trivy, Gitleaks, Checkov)
CLI cli.py  ─┘        → build_summary → calculate_score → JSON unificado
```

Cada escáner corre como subproceso; los fallos se capturan por escáner (un escáner caído no aborta a los demás) y quedan registrados en la clave `errors` del JSON.

## Cómo usarlo

### 1) Como servicio (HTTP)

```bash
docker compose up scanner
```

El scanner queda en `http://localhost:8001`. Los `repo_path` se resuelven dentro de `/repos` en el contenedor (mapeado desde `./repos`).

```bash
curl -X POST http://localhost:8001/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "nombre-del-repo"}'
```

### 2) Como CLI (sin levantar FastAPI)

Misma lógica que `POST /scan`, sin servidor. Recibe un path a escanear y, opcionalmente, vuelca el mismo JSON a un archivo:

```bash
python scanner/cli.py <path> --json-out report.json
```

- Imprime a stdout el resumen por severidad + el score.
- Exit code **0** siempre para el estado del escaneo (v1 sin gate por umbral; los errores de escáner quedan visibles en `errors[]`).
- Exit code **1** solo por fallo operativo (p. ej. el path no existe).

## El score

Determinista y reproducible, calculado en `scanner/main.py` (`calculate_score`). No interviene ninguna IA:

```
penalty = 20·critical + 8·high + 3·medium + 1·low + 0.5·unknown

score   = 100                                    si penalty == 0
        = round(100 · e^(−0.015 · penalty))      en otro caso   (acotado a [0, 100])
```

El conteo por severidad lo produce `build_summary`. Nota: hoy solo se mapean `critical/high/medium/low`; cualquier otra severidad (incluida la ausencia de severidad) cae en `unknown` (ver Roadmap).

## CI/CD — auto-escaneo

El workflow `.github/workflows/securepipe.yml` hace **self-scan del propio repo en cada push a `main` y en cada PR**:

- Instala las 4 herramientas con los mismos métodos que `scanner/Dockerfile` (paridad CI ↔ contenedor) y cachea la base de datos de Trivy.
- Ejecuta `python scanner/cli.py . --json-out securepipe-report.json`.
- **Sube el reporte como artifact** (`securepipe-report`).

No comenta en el PR ni bloquea el merge — eso **no** está implementado (ver Roadmap).

## Hallazgos reales (self-scan de este repo)

Resultado del último self-scan de SecurePipe sobre sí mismo:

- **Score: 95 / 100**
- **7 hallazgos**, todos sin severidad mapeada (`unknown`) → `penalty = 7 × 0.5 = 3.5` → `round(100·e^(−0.015·3.5)) = 95`. La aritmética cierra con la fórmula real.

Lo valioso es que **el pipeline se detectó a sí mismo**. Checkov marcó, entre otros:

- El **workflow usa tags mutables** de acciones (`actions/checkout@v4`, etc.) en vez de fijar un commit SHA.
- El **contenedor del scanner corre como root**: `scanner/Dockerfile` no declara instrucción `USER`.

Ambos son ciertos contra el código actual del repo. Es "dogfooding": la herramienta se auditó a sí misma y encontró deuda real.

## Roadmap (NO implementado)

Nada de esto existe hoy; está aquí como trabajo futuro:

- [ ] **Interpretación de findings con IA** (p. ej. Claude API) — priorización y explicación. Hoy el scoring es 100% fórmula, sin IA.
- [ ] **Gate por umbral de score** — que el CI falle el build si el score baja de un mínimo. Hoy el escaneo nunca rompe el build (exit 0).
- [ ] **Mapeo de severidad de Semgrep y Checkov** — hoy sus findings caen en `unknown` y pesan solo 0.5 en el score.
- [ ] **Comentario automático en el PR** con el resumen del escaneo.
- [ ] **Dashboard** para visualizar histórico de scores y hallazgos.