"""What a release ships: the skill pinned to the package version, a wheel and an sdist, a README that names every Model."""

import json
import os
import re
import shutil
import subprocess
import tarfile
import tomllib
import zipfile
from pathlib import Path

from conftest import VOXX

ROOT = Path(__file__).parent.parent
VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]


def test_the_skill_launcher_pins_the_version_being_released():
    launcher = (ROOT / "skills/voxx/scripts/voxx").read_text(encoding="utf-8")

    assert re.findall(r"uvx voxx@(\S+)\}", launcher) == [VERSION]
    assert os.access(ROOT / "skills/voxx/scripts/voxx", os.X_OK)


def test_the_plugin_has_the_version_being_released():
    plugin = json.loads((ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8"))

    assert plugin["version"] == VERSION


def test_the_build_makes_a_wheel_and_an_sdist(tmp_path):
    uv = shutil.which("uv")
    assert uv, "uv builds the release"
    subprocess.run([uv, "build", "--out-dir", str(tmp_path), str(ROOT)], check=True, capture_output=True, timeout=300)

    wheel = tmp_path / f"voxx-{VERSION}-py3-none-any.whl"
    sdist = tmp_path / f"voxx-{VERSION}.tar.gz"
    assert sorted(p.name for p in tmp_path.glob("voxx-*")) == sorted([wheel.name, sdist.name])
    with zipfile.ZipFile(wheel) as w:
        names = set(w.namelist())
        info = f"voxx-{VERSION}.dist-info"
        assert {"voxx/cli.py", "voxx/worker/__main__.py", f"{info}/licenses/LICENSE", f"{info}/licenses/NOTICE"} <= names
        # PyPI shows the README, disclaimer included.
        assert "## Disclaimer" in w.read(f"{info}/METADATA").decode()
    with tarfile.open(sdist) as s:
        names = {n.split("/", 1)[1] for n in s.getnames() if "/" in n}
    assert {"skills/voxx/SKILL.md", "skills/voxx/scripts/voxx", "README.md", "LICENSE", "NOTICE", "tests/conftest.py"} <= names
    assert not any(n.startswith((".agents/", ".claude/")) for n in names)


def test_the_readme_names_every_registered_model_and_its_license():
    process = subprocess.run([str(VOXX), "models"], capture_output=True, encoding="utf-8", timeout=60,
                             env={k: v for k, v in os.environ.items() if not k.startswith("VOXX_TEST_")})
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    models = json.loads(process.stdout)["data"]["models"]
    assert models
    for model in models:
        row = next(line for line in readme.splitlines() if line.startswith(f"| `{model['id']}` |"))
        assert f"[{model['weights_license']['id']}]({model['weights_license']['url']})" in row
