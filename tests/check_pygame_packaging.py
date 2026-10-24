"""Exercise the recipe and real pip metadata hooks without an Android SDK.

Run in a virtualenv containing pip>=23:
    python tests/check_pygame_packaging.py /path/to/pygame-ce-2.5.8

The input is an unpacked upstream source archive. All changes and generated
files stay in a temporary copy. SDL/NDK paths are placeholders: metadata
generation does not compile or link native code. This is not an APK test.
Pip installs the recipe's build dependencies into its isolated environment.
"""

import contextlib
import json
import os
from pathlib import Path
import runpy
import shutil
import subprocess
import sys
import tempfile
from types import ModuleType, SimpleNamespace
from unittest.mock import patch


@contextlib.contextmanager
def current_directory(path):
    previous = Path.cwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


def check(source):
    recipe_path = Path(__file__).resolve().parents[1] / "p4a-recipes/pygame-ce/__init__.py"
    with tempfile.TemporaryDirectory(prefix="pygame-packaging-") as scratch:
        root = Path(scratch)
        build_dir = root / "source"
        shutil.copytree(source, build_dir)

        class RecipeBase:
            ctx = SimpleNamespace(bootstrap=SimpleNamespace(build_dir=str(root / "sdl2")))

            def prebuild_arch(self, arch):
                pass

            def get_build_dir(self, arch):
                return str(build_dir)

            def get_recipe(self, name, ctx):
                return SimpleNamespace(
                    get_build_dir=lambda arch: str(root / name),
                    get_include_dirs=lambda arch: [str(root / name / "include")],
                )

        # Only p4a's SDK-dependent context is stubbed. Run the actual recipe's
        # prebuild method and actual setuptools/pip subprocesses below.
        recipe_module = ModuleType("pythonforandroid.recipe")
        recipe_module.CompiledComponentsPythonRecipe = RecipeBase
        toolchain_module = ModuleType("pythonforandroid.toolchain")
        toolchain_module.current_directory = current_directory
        with patch.dict(sys.modules, {
            "pythonforandroid": ModuleType("pythonforandroid"),
            "pythonforandroid.recipe": recipe_module,
            "pythonforandroid.toolchain": toolchain_module,
        }):
            recipe = runpy.run_path(str(recipe_path))["recipe"]

        arch = SimpleNamespace(arch="arm64-v8a", ndk_lib_dir_versioned=str(root / "ndk"))
        recipe.prebuild_arch(arch)
        first = (build_dir / "pyproject.toml").read_bytes()
        recipe.prebuild_arch(arch)
        assert (build_dir / "pyproject.toml").read_bytes() == first, "Prebuild is not idempotent"

        version = subprocess.check_output(
            [sys.executable, "buildconfig/get_version.py"], cwd=build_dir, text=True,
        ).strip()
        assert version == recipe.version, (version, recipe.version)
        report = root / "report.json"
        env = dict(os.environ, PYGAME_ANDROID="TRUE", PYGAME_CROSS_COMPILE="TRUE", USE_SDL2="1")
        # Let pip invoke the PEP 517 backend from its own runner, so the source
        # directory is not implicitly present on sys.path (the CI failure).
        subprocess.run([
            sys.executable, "-m", "pip", "install", ".", "--dry-run",
            "--no-cache-dir", "--no-deps", "--ignore-installed",
            "--disable-pip-version-check", "--report", str(report),
        ], cwd=build_dir, env=env, check=True)
        metadata = json.loads(report.read_text())["install"][0]["metadata"]
        assert metadata["name"] == "pygame-ce", metadata
        assert metadata["version"] == recipe.version, metadata
        print("PASS: recipe preparation, version lookup and pip metadata generation")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    check(Path(sys.argv[1]).resolve())
