"""Build and exercise the Evidence Lab wheel outside its source checkout."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATE_AUDIT_FIXTURE = ROOT / "labels" / "readerB" / "serock-1890-death-1.json"


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="backslashreplace",
        check=False,
    )
    if result.returncode != 0:
        rendered = " ".join(command)
        raise RuntimeError(
            f"command failed ({result.returncode}): {rendered}\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _json_command(
    python: Path,
    arguments: list[str],
    *,
    cwd: Path,
    env: dict[str, str],
) -> dict[str, Any]:
    result = _run([str(python), "-m", "aktreader", *arguments], cwd=cwd, env=env)
    payload = json.loads(result.stdout)
    if not isinstance(payload, dict):
        raise RuntimeError(f"command returned a non-object JSON payload: {arguments}")
    return payload


def _venv_python(environment: Path) -> Path:
    if os.name == "nt":
        return environment / "Scripts" / "python.exe"
    return environment / "bin" / "python"


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="aktreader-lab-wheel-") as raw_temp:
        temp = Path(raw_temp)
        wheel_dir = temp / "wheel"
        wheel_dir.mkdir()
        clean_env = os.environ.copy()
        clean_env.pop("PYTHONPATH", None)

        _run(
            [
                sys.executable,
                "-m",
                "pip",
                "wheel",
                "--disable-pip-version-check",
                "--no-deps",
                "--wheel-dir",
                str(wheel_dir),
                str(ROOT),
            ],
            cwd=temp,
            env=clean_env,
        )
        wheels = list(wheel_dir.glob("aktreader_research-*.whl"))
        if len(wheels) != 1:
            raise RuntimeError(f"expected one Evidence Lab wheel, found {len(wheels)}")
        wheel = wheels[0]

        environment = temp / "venv"
        _run([sys.executable, "-m", "venv", str(environment)], cwd=temp, env=clean_env)
        python = _venv_python(environment)
        _run(
            [
                str(python),
                "-m",
                "pip",
                "install",
                "--disable-pip-version-check",
                str(wheel),
            ],
            cwd=temp,
            env=clean_env,
        )

        import_result = _run(
            [
                str(python),
                "-c",
                (
                    "import json, aktreader; "
                    "print(json.dumps({'module_path': aktreader.__file__}))"
                ),
            ],
            cwd=temp,
            env=clean_env,
        )
        installed_module = Path(json.loads(import_result.stdout)["module_path"]).resolve()
        if environment.resolve() not in installed_module.parents:
            raise RuntimeError(f"wheel smoke imported outside its fresh venv: {installed_module}")
        if ROOT.resolve() in installed_module.parents:
            raise RuntimeError(f"wheel smoke imported the source checkout: {installed_module}")

        doctor = _json_command(python, ["doctor", "--json"], cwd=temp, env=clean_env)
        if doctor.get("runtime_mode") != "installed-distribution":
            raise RuntimeError(f"doctor did not recognize the wheel install: {doctor}")
        if doctor.get("available_runtime_asset_count") != 9:
            raise RuntimeError(f"doctor did not find all packaged runtime assets: {doctor}")
        if doctor.get("standalone_distribution_ready") is not True:
            raise RuntimeError(f"doctor did not mark the wheel ready: {doctor}")

        variants = _json_command(
            python,
            ["variant-propose", "Goldsztejn", "--kind", "surname", "--no-phonetic"],
            cwd=temp,
            env=clean_env,
        )
        if variants.get("status") != "PROPOSAL_ONLY" or not variants.get("proposals"):
            raise RuntimeError(f"packaged variant lexicons produced no proposals: {variants}")

        audit = _json_command(
            python,
            ["date-audit", str(DATE_AUDIT_FIXTURE)],
            cwd=temp,
            env=clean_env,
        )
        if audit.get("status") != "PASS" or audit.get("file_count") != 1:
            raise RuntimeError(f"installed date audit did not validate its fixture: {audit}")

        print(
            json.dumps(
                {
                    "status": "PASS",
                    "wheel": wheel.name,
                    "installed_module": str(installed_module),
                    "runtime_assets": "9/9",
                    "variant_proposals": len(variants["proposals"]),
                    "date_audit_files": audit["file_count"],
                },
                ensure_ascii=False,
                sort_keys=True,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
