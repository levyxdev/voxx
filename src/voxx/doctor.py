"""`voxx doctor`: what an agent checks before narrating. Reports, never fails, and caches nothing."""

import os
import platform
import shutil
import subprocess

from voxx.models import is_installed, models, voxx_home

# Test-only: "<system> <machine>[ rosetta]" stands in for the real platform.
PLATFORM_ENV = "VOXX_TEST_PLATFORM"


def doctor():
    home = voxx_home()
    disk = next(p for p in (home, *home.parents) if p.exists())
    listed = models()
    return {
        "platform": _platform(),
        "home": str(home),
        "disk": {"path": str(disk), "free_bytes": shutil.disk_usage(disk).free},
        "models": {"installed": [m.id for m in listed if is_installed(m)],
                   "not_installed": [{"model": m.id, "size_bytes": m.size_bytes} for m in listed if not is_installed(m)]},
    }


def _platform():
    if PLATFORM_ENV in os.environ:
        system, machine, *rest = os.environ[PLATFORM_ENV].split()
        translated = rest == ["rosetta"]
    else:
        system, machine = platform.system(), platform.machine()
        translated = system == "Darwin" and _sysctl("sysctl.proc_translated") == "1"
    reported = {"system": system, "machine": machine}
    if system == "Darwin" and machine == "arm64":
        return {**reported, "apple_silicon": True, "supported": True}
    if translated:
        return {**reported, "apple_silicon": True, "supported": False,
                "reason": "This Mac has Apple Silicon, but Python runs as x86_64 under Rosetta. Use an arm64 Python."}
    return {**reported, "apple_silicon": False, "supported": False,
            "reason": "voxx v0.1 runs only on Apple Silicon Macs (M1 or later)."}


def _sysctl(name):
    try:
        return subprocess.run(["sysctl", "-n", name], capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return ""
