"""Import smoke test: every module under src/ must be importable.

The rest of the suite never imports the frontends, so a broken import path in
one of them (a one-letter typo in `from src.utils.misc import Label`, for
example) stays invisible until someone runs that frontend by hand. This walks
src/ and imports each module in a separate test case.
"""

import importlib
from pathlib import Path

import pytest

import src


def discover_modules():
    root = Path(src.__file__).parent
    modules = []
    for path in sorted(root.rglob('*.py')):
        if '__pycache__' in path.parts:
            continue
        parts = list(path.relative_to(root).with_suffix('').parts)
        if parts[-1] == '__init__':
            parts = parts[:-1]
        if not parts:
            continue
        modules.append('.'.join(['src'] + parts))
    return modules


@pytest.mark.parametrize('module_name', discover_modules())
def test_module_imports(module_name):
    importlib.import_module(module_name)
