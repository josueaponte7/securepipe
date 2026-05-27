# SecurePipe — DevSecOps Pipeline Auditor

Un agente que analiza repositorios reales y detecta vulnerabilidades de seguridad, dependencias comprometidas, secretos expuestos y misconfigurations de infraestructura.

## El problema que resuelve

La mayoría de repos no tienen ninguna línea de seguridad automatizada en su pipeline. Nadie escanea dependencias, nadie detecta secretos commiteados, nadie valida la configuración de Docker. SecurePipe mete todo eso en una sola llamada HTTP.

## Stack

- **FastAPI** — Orquestador central
- **Semgrep** — Análisis estático del código fuente (SAST)
- **Trivy** — Dependencias con CVEs conocidos (SCA)
- **Gitleaks** — Detección de secretos en el repositorio
- **Checkov** — Seguridad en IaC (Dockerfile, GitHub Actions, OpenAPI)
- **Claude API** — Priorización e interpretación con IA (Semana 3)

## Arquitectura

POST /scan → FastAPI → [Semgrep + Trivy + Gitleaks + Checkov] → JSON unificado
## Cómo usarlo

```bash
docker compose up
```

```bash
curl -X POST http://localhost:8001/scan \
  -H "Content-Type: application/json" \
  -d '{"repo_path": "nombre-del-repo"}'
```

## Roadmap

- [x] Semana 1 — Núcleo scanner: 4 herramientas en paralelo via FastAPI
- [ ] Semana 2 — GitHub Actions: comentario automático en cada PR
- [ ] Semana 3 — Claude API: priorización e interpretación con IA
- [ ] Semana 4 — Dashboard React + lanzamiento público

## Hallazgos reales

En el primer scan contra un proyecto Laravel 11 con Symfony encontró:
- 27 vulnerabilidades en dependencias (5 HIGH en urllib3, CVEs en Symfony)
- 48 issues de configuración en Dockerfiles e IaC
- 0 secretos expuestos
- 0 hallazgos SAST (código fuente limpio)