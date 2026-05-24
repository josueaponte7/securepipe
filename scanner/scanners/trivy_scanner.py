import asyncio
import json


async def run_trivy(repo_path: str) -> dict:
    try:
        process = await asyncio.create_subprocess_exec(
            "trivy",
            "fs",
            "--format", "json",
            "--quiet",
            repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()

        if stdout:
            data = json.loads(stdout)
            results = data.get("Results", [])

            findings = []
            for result in results:
                for vuln in result.get("Vulnerabilities") or []:
                    findings.append({
                        "package": vuln.get("PkgName"),
                        "version": vuln.get("InstalledVersion"),
                        "fixed_version": vuln.get("FixedVersion"),
                        "severity": vuln.get("Severity"),
                        "cve": vuln.get("VulnerabilityID"),
                        "title": vuln.get("Title"),
                    })

            return {
                "status": "ok",
                "total": len(findings),
                "findings": findings,
            }

        return {"status": "ok", "total": 0, "findings": []}

    except Exception as e:
        return {"status": "error", "message": str(e)}