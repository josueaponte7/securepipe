from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import asyncio
import os

from scanners.semgrep_scanner import run_semgrep
from scanners.trivy_scanner import run_trivy
from scanners.gitleaks_scanner import run_gitleaks
from scanners.checkov_scanner import run_checkov

app = FastAPI(title="SecurePipe", version="0.1.0")


class ScanRequest(BaseModel):
    repo_path: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/scan")
async def scan(request: ScanRequest):
    full_path = f"/repos/{request.repo_path}"

    print(f"[SCAN] Recibida petición para: {full_path}", flush=True)

    if not os.path.exists(full_path):
        raise HTTPException(
            status_code=404,
            detail=f"Repo no encontrado en {full_path}"
        )

    print("[SCAN] Lanzando scanners...", flush=True)

    semgrep, trivy, gitleaks, checkov = await asyncio.gather(
        run_semgrep(full_path),
        run_trivy(full_path),
        run_gitleaks(full_path),
        run_checkov(full_path),
    )

    print("[SCAN] Scanners completados", flush=True)

    return {
        "repo": request.repo_path,
        "results": {
            "semgrep": semgrep,
            "trivy": trivy,
            "gitleaks": gitleaks,
            "checkov": checkov,
        }
    }