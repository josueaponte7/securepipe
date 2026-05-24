import asyncio
import json


async def run_semgrep(repo_path: str) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "semgrep",
            "--config", "auto",
            "--json",
            repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            data = json.loads(stdout)
            findings = data.get("results", [])
            return {
                "status": "ok",
                "total": len(findings),
                "findings": [
                    {
                        "rule": f.get("check_id"),
                        "file": f.get("path"),
                        "line": f.get("start", {}).get("line"),
                        "severity": f.get("extra", {}).get("severity"),
                        "message": f.get("extra", {}).get("message"),
                    }
                    for f in findings
                ],
            }

        return {"status": "ok", "total": 0, "findings": []}

    except Exception as e:
        return {"status": "error", "message": str(e)}