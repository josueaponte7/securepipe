#!/usr/bin/env python3
"""CLI de SecurePipe: ejecuta los 4 escáneres y calcula el score sin levantar FastAPI.

Reutiliza exactamente la misma lógica que el endpoint POST /scan:
- run_semgrep / run_trivy / run_gitleaks / run_checkov  (scanner/scanners/*.py)
- build_summary / calculate_score                        (scanner/main.py)
"""
import argparse
import asyncio
import json
import os
import sys

from scanners.semgrep_scanner import run_semgrep
from scanners.trivy_scanner import run_trivy
from scanners.gitleaks_scanner import run_gitleaks
from scanners.checkov_scanner import run_checkov
from main import build_summary, calculate_score

# Orden idéntico al asyncio.gather de /scan (main.py:84-89)
SCANNERS = [
    ("semgrep", run_semgrep),
    ("trivy", run_trivy),
    ("gitleaks", run_gitleaks),
    ("checkov", run_checkov),
]


async def run_scan(repo_path: str) -> dict:
    # Tolerante a fallos: un escáner que muera no aborta a los demás.
    raw = await asyncio.gather(
        *[fn(repo_path) for _, fn in SCANNERS],
        return_exceptions=True,
    )

    results = {}
    errors = []
    for (name, _), outcome in zip(SCANNERS, raw):
        if isinstance(outcome, Exception):
            # (a) excepción no controlada. Reusamos el MISMO shape que el
            # fallo controlado de scanners/*.py: {"status":"error","message":...}
            # (sin "findings"). build_summary lo tolera vía .get("findings", []).
            print(f"[ERROR] Scanner '{name}' lanzó excepción: {outcome!r}", file=sys.stderr)
            errors.append({"scanner": name, "error": repr(outcome)})
            results[name] = {"status": "error", "message": str(outcome)}
        else:
            results[name] = outcome
            # (b) el escáner controló su fallo y devolvió status=error
            if isinstance(outcome, dict) and outcome.get("status") == "error":
                print(f"[ERROR] Scanner '{name}' falló: {outcome.get('message')}", file=sys.stderr)
                errors.append({"scanner": name, "error": repr(outcome.get("message"))})

    # El score se calcula con lo que haya: los caídos aportan 0 findings.
    summary = build_summary(
        results["semgrep"],
        results["trivy"],
        results["gitleaks"],
        results["checkov"],
    )
    score = calculate_score(summary)

    # Mismo shape que POST /scan (main.py:96-106) + clave "errors".
    return {
        "repo": repo_path,
        "score": score,
        "summary": summary,
        "errors": errors,
        "results": results,
    }


def print_report(result: dict) -> None:
    s = result["summary"]
    print(f"=== SecurePipe — {result['repo']} ===")
    print(f"Total findings : {s['total_findings']}")
    print(f"  critical     : {s['critical']}")
    print(f"  high         : {s['high']}")
    print(f"  medium       : {s['medium']}")
    print(f"  low          : {s['low']}")
    print(f"  unknown      : {s['unknown']}")
    if result["errors"]:
        print(f"Scanners con error ({len(result['errors'])}):")
        for e in result["errors"]:
            print(f"  - {e['scanner']}: {e['error']}")
    print(f"Score          : {result['score']}/100")


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="securepipe",
        description="Ejecuta los 4 escáneres de SecurePipe y calcula el score de seguridad.",
    )
    parser.add_argument("path", help="Directorio a escanear")
    parser.add_argument(
        "--json-out",
        metavar="RUTA",
        help="Vuelca el JSON completo (mismo shape que POST /scan) a este archivo",
    )
    args = parser.parse_args()

    if not os.path.exists(args.path):
        # Fallo operativo (no gate de score) -> exit 1.
        print(f"[ERROR] Path no encontrado: {args.path}", file=sys.stderr)
        return 1

    result = asyncio.run(run_scan(args.path))

    print_report(result)

    if args.json_out:
        with open(args.json_out, "w", encoding="utf-8") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"[OK] JSON escrito en {args.json_out}", file=sys.stderr)

    # v1: el estado del escaneo NUNCA rompe el build (sin gate por umbral,
    # ni por escaneo parcial). Los errores quedan visibles arriba y en el JSON.
    return 0


if __name__ == "__main__":
    sys.exit(main())