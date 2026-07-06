"""Entry point for 'python sheet_to_banana <url>' run from the repo root.

pyproject.toml maps the 'sheet_to_banana' package to the source/ subdirectory,
but that mapping only applies to installed packages.  When running the directory
directly ('python sheet_to_banana'), Python just looks for this file.  We wire
up the same mapping at runtime so all imports inside source/ resolve correctly.
"""
import importlib.util
import os
import sys
import types

_here = os.path.dirname(os.path.abspath(__file__))

if 'sheet_to_banana' not in sys.modules:
    _pkg = types.ModuleType('sheet_to_banana')
    _pkg.__path__ = [os.path.join(_here, 'src')]
    sys.modules['sheet_to_banana'] = _pkg

_spec = importlib.util.spec_from_file_location(
    'sheet_to_banana._entry',
    os.path.join(_here, 'src', '__main__.py'),
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = 'sheet_to_banana'
_spec.loader.exec_module(_mod)
_mod.main()
