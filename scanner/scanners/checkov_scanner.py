import asyncio
import json

EXCLUDED_PATHS = [
    "vendor/",
    "node_modules/",
    ".git/",
]


def _is_excluded(file_path: str) -> bool:
    if not file_path:
        return False
    return any(excluded in file_path for excluded in EXCLUDED_PATHS)


async def run_checkov(repo_path: str) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "checkov",
            "--directory", repo_path,
            "--output", "json",
            "--quiet",
            "--soft-fail",
            "--skip-path", "vendor",
            "--skip-path", "node_modules",
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

            findings = []
            for check in all_failed:
                file_path = check.get("repo_file_path", "")

                if _is_excluded(file_path):
                    continue

                check_detail = check.get("check", {})
                name = (
                    check_detail.get("name")
                    or check.get("check_type")
                    or check.get("check_id")
                )

                findings.append({
                    "check_id": check.get("check_id"),
                    "name": name,
                    "file": file_path,
                    "resource": check.get("resource"),
                    "severity": check.get("severity") or check_detail.get("severity"),
                })

            return {
                "status": "ok",
                "total": len(findings),
                "findings": findings,
            }

        return {"status": "ok", "total": 0, "findings": []}

    except Exception as e:
        return {"status": "error", "message": str(e)}