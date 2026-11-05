"""Every module imports against the installed pysepal."""

import importlib
from pathlib import Path

import pytest

import component

ROOT = Path(component.__file__).parent

# Listed from the files rather than pkgutil.walk_packages, which silently skips
# the children of a package whose __init__ fails to import.
MODULES = sorted(
    ".".join(("component",) + p.relative_to(ROOT).with_suffix("").parts).removesuffix(
        ".__init__"
    )
    for p in ROOT.rglob("*.py")
)


@pytest.mark.parametrize("name", MODULES)
def test_module_imports(name):
    importlib.import_module(name)
