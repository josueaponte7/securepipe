import asyncio
import json


async def run_gitleaks(repo_path: str) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "gitleaks",
            "detect",
            "--source", repo_path,
            "--report-format", "json",
            "--report-path", "/tmp/gitleaks_report.json",
            "--no-git",
            "--exit-code", "0",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        await process.communicate()

        try:
            with open("/tmp/gitleaks_report.json", "r") as f:
                content = f.read().strip()
                findings_raw = json.loads(content) if content else []
        except FileNotFoundError:
            findings_raw = []

        findings = [
            {
                "rule": leak.get("RuleID"),
                "file": leak.get("File"),
                "line": leak.get("StartLine"),
                "secret": leak.get("Secret", "")[:20] + "...",
                "commit": leak.get("Commit"),
                "description": leak.get("Description"),
            }
            for leak in (findings_raw or [])
        ]

        return {
            "status": "ok",
            "total": len(findings),
            "findings": findings,
        }

    except Exception as e:
        return {"status": "error", "message": str(e)}