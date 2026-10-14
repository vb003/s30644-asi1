from __future__ import annotations

import argparse
import importlib.metadata
import json
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / "environment.yml"
DEFAULT_REPORT = ROOT / "env_report.json"

EXPECTED_PYTHON = (3, 11)

# Nazwa pakietu w environment.yml -> moduł używany przy imporcie.
IMPORT_MODULES = {
    "numpy": "numpy",
    "pandas": "pandas",
    "matplotlib": "matplotlib",
    "scikit-learn": "sklearn",
    "ipykernel": "ipykernel",
}

# Te narzędzia nie muszą być importowane, ale powinny być zainstalowane.
TOOL_DISTRIBUTIONS = [
    "pytest",
    "pre-commit",
    "ruff",
    "nbstripout",
]


def run_command(command: list[str], timeout: int = 10) -> subprocess.CompletedProcess[str] | None:
    """Uruchamia komendę bez rzucania wyjątku na zwykły błąd programu."""
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def pinned_versions_from_environment() -> dict[str, str]:
    """Czyta tylko proste przypięcia typu package=1.2.3 z environment.yml."""
    if not ENV_FILE.exists():
        return {}

    pinned: dict[str, str] = {}
    pattern = re.compile(r"^\s*-\s*([A-Za-z0-9_.-]+)=([0-9][^\s#]*)\s*(?:#.*)?$")
    for line in ENV_FILE.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if match:
            pinned[match.group(1)] = match.group(2)
    return pinned


def import_check(module: str, timeout: int = 20) -> tuple[bool, str | None]:
    """Sprawdza import w osobnym procesie, żeby pojedynczy pakiet nie zawiesił całego skryptu."""
    result = run_command([sys.executable, "-c", f"import {module}"], timeout=timeout)
    if result is None:
        return False, "import przekroczył limit czasu albo nie udało się uruchomić Pythona"
    if result.returncode != 0:
        message = (result.stderr or result.stdout).strip().splitlines()
        return False, message[-1] if message else "import zakończył się błędem"
    return True, None


def git_configured(key: str) -> bool:
    result = run_command(["git", "config", "--get", key])
    return bool(result and result.returncode == 0 and result.stdout.strip())


def pre_commit_hook_installed() -> bool:
    git_dir = ROOT / ".git"
    hook = git_dir / "hooks" / "pre-commit"
    return hook.exists() and hook.stat().st_size > 0


def kernel_registered(name: str) -> bool:
    result = run_command(["jupyter", "kernelspec", "list", "--json"], timeout=15)
    if not result or result.returncode != 0:
        return False
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return False
    return name in data.get("kernelspecs", {})


def total_ram_gb() -> float | None:
    """Zwraca przybliżoną ilość RAM bez wymagania psutil."""
    try:
        if sys.platform.startswith(("linux", "darwin")):
            pages = os.sysconf("SC_PHYS_PAGES")
            page_size = os.sysconf("SC_PAGE_SIZE")
            return round((pages * page_size) / (1024**3), 1)
        if sys.platform.startswith("win"):
            import ctypes

            class MemoryStatusEx(ctypes.Structure):
                _fields_ = [
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            status = MemoryStatusEx()
            status.dwLength = ctypes.sizeof(MemoryStatusEx)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status))
            return round(status.ullTotalPhys / (1024**3), 1)
    except (AttributeError, OSError, ValueError):
        pass
    return None


def docker_info() -> dict[str, Any]:
    installed = shutil.which("docker") is not None
    if not installed:
        return {"installed": False, "running": False}

    result = run_command(["docker", "info"], timeout=5)
    return {
        "installed": True,
        "running": bool(result and result.returncode == 0),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Sprawdza środowisko ASI.")
    parser.add_argument(
        "--expected-env",
        default="asi-ml",
        help="Oczekiwana nazwa aktywnego środowiska conda/mamba (domyślnie: asi-ml).",
    )
    parser.add_argument(
        "--ci",
        action="store_true",
        help="Tryb CI: pomija lokalne wymagania dotyczące Git, kernela i hooka pre-commit.",
    )
    parser.add_argument(
        "--report-path",
        type=Path,
        default=DEFAULT_REPORT,
        help="Gdzie zapisać raport JSON.",
    )
    args = parser.parse_args()

    pinned = pinned_versions_from_environment()
    failures: list[str] = []
    warnings: list[str] = []

    python_ok = sys.version_info[:2] == EXPECTED_PYTHON
    if not python_ok:
        failures.append(
            f"Python ma wersję {platform.python_version()}, a oczekiwana jest linia 3.11.x."
        )

    active_env = os.environ.get("CONDA_DEFAULT_ENV") or os.environ.get("MAMBA_DEFAULT_ENV")
    env_ok = active_env == args.expected_env
    if not env_ok:
        failures.append(
            f"Aktywne środowisko to {active_env or 'brak'}, a oczekiwane jest {args.expected_env}."
        )

    packages: dict[str, Any] = {}
    for distribution, module in IMPORT_MODULES.items():
        installed_version = package_version(distribution)
        expected_version = pinned.get(distribution)
        imported, import_error = import_check(module)
        version_ok = expected_version is None or installed_version == expected_version

        packages[distribution] = {
            "version": installed_version,
            "expected": expected_version,
            "import_ok": imported,
            "version_ok": version_ok,
        }

        if not imported:
            failures.append(f"Nie działa import pakietu {distribution}: {import_error}.")
        if installed_version is None:
            failures.append(f"Pakiet {distribution} nie jest zainstalowany.")
        elif not version_ok:
            failures.append(
                f"Pakiet {distribution} ma wersję {installed_version}, a environment.yml przypina {expected_version}."
            )

    tools: dict[str, Any] = {}
    for distribution in TOOL_DISTRIBUTIONS:
        installed_version = package_version(distribution)
        expected_version = pinned.get(distribution)
        version_ok = expected_version is None or installed_version == expected_version
        tools[distribution] = {
            "version": installed_version,
            "expected": expected_version,
            "version_ok": version_ok,
        }
        if installed_version is None:
            failures.append(f"Narzędzie {distribution} nie jest zainstalowane.")
        elif not version_ok:
            failures.append(
                f"Narzędzie {distribution} ma wersję {installed_version}, a environment.yml przypina {expected_version}."
            )

    git_info = {
        "user_name_configured": git_configured("user.name"),
        "user_email_configured": git_configured("user.email"),
        "pre_commit_hook_installed": pre_commit_hook_installed(),
    }

    kernel_ok = kernel_registered("asi-ml")

    if not args.ci:
        if not git_info["user_name_configured"]:
            failures.append("Git nie ma ustawionego user.name.")
        if not git_info["user_email_configured"]:
            failures.append("Git nie ma ustawionego user.email.")
        if not git_info["pre_commit_hook_installed"]:
            failures.append(
                "Hook pre-commit nie jest zainstalowany. Uruchom: pre-commit install"
            )
        if not kernel_ok:
            failures.append(
                'Kernel Jupyter "asi-ml" nie jest zarejestrowany. Uruchom: '
                'python -m ipykernel install --user --name asi-ml --display-name "Python (asi-ml)"'
            )

    docker = docker_info()
    if not docker["installed"]:
        warnings.append("Docker nie jest zainstalowany. Nie blokuje to pierwszych zajęć.")
    elif not docker["running"]:
        warnings.append("Docker jest zainstalowany, ale daemon nie działa. Nie blokuje to pierwszych zajęć.")

    report = {
        "schema_version": 1,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "ok" if not failures else "error",
        "path": "codespaces" if os.environ.get("CODESPACES") == "true" else "local",
        "python": {
            "version": platform.python_version(),
            "expected": "3.11.x",
            "ok": python_ok,
        },
        "environment": {
            "name": active_env,
            "expected": args.expected_env,
            "ok": env_ok,
        },
        "packages": packages,
        "tools": tools,
        "git": git_info,
        "jupyter": {
            "asi_ml_kernel_registered": kernel_ok,
        },
        "system": {
            "os": platform.system(),
            "architecture": platform.machine(),
            "ram_gb": total_ram_gb(),
            "docker": docker,
        },
        "failures": failures,
        "warnings": warnings,
    }

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print("\nASI — sprawdzenie środowiska")
    print("=" * 31)
    print(f"Python:       {platform.python_version()} {'OK' if python_ok else 'BŁĄD'}")
    print(f"Środowisko:  {active_env or 'brak'} {'OK' if env_ok else 'BŁĄD'}")

    for distribution, info in packages.items():
        state = "OK" if info["import_ok"] and info["version_ok"] else "BŁĄD"
        print(f"{distribution:<13} {info['version'] or 'brak':<12} {state}")

    if not args.ci:
        print(f"Git user.name:  {'OK' if git_info['user_name_configured'] else 'BŁĄD'}")
        print(f"Git user.email: {'OK' if git_info['user_email_configured'] else 'BŁĄD'}")
        print(f"pre-commit:     {'OK' if git_info['pre_commit_hook_installed'] else 'BŁĄD'}")
        print(f"kernel asi-ml:  {'OK' if kernel_ok else 'BŁĄD'}")

    if warnings:
        print("\nInformacyjnie:")
        for warning in warnings:
            print(f"- {warning}")

    if failures:
        print("\nDo poprawy:")
        for failure in failures:
            print(f"- {failure}")
        print(f"\nRaport zapisano w: {args.report_path}")
        return 1

    print("\nŚrodowisko jest gotowe.")
    print(f"Raport zapisano w: {args.report_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
