import asyncio
import json


async def run_checkov(repo_path: str) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "checkov",
            "--directory", repo_path,
            "--output", "json",
            "--quiet",
            "--soft-fail",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            raw = stdout.decode("utf-8").strip()
            data = json.loads(raw)

            if isinstance(data, list):
                all_failed = []
                for block in data:
                    results = block.get("results", {})
                    all_failed.extend(results.get("failed_checks", []))
            else:
                all_failed = data.get("results", {}).get("failed_checks", [])

            findings = [
                {
                    "check_id": check.get("check_id"),
                    "name": check.get("check.name") or check.get("check", {}).get("name"),
                    "file": check.get("repo_file_path"),
                    "resource": check.get("resource"),
                    "severity": check.get("severity"),
                }
                for check in all_failed
            ]

            return {
                "status": "ok",
                "total": len(findings),
                "findings": findings,
            }

        return {"status": "ok", "total": 0, "findings": []}

    except Exception as e:
        return {"status": "error", "message": str(e)}