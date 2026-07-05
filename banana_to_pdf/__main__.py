"""Entry point for 'python banana_to_pdf <url>' run from the repo root.

pyproject.toml maps the 'banana_to_pdf' package to the source/ subdirectory,
but that mapping only applies to installed packages.  When running the directory
directly ('python banana_to_pdf'), Python just looks for this file.  We wire
up the same mapping at runtime so all imports inside source/ resolve correctly.
"""
import importlib.util
import os
import sys
import types

_here = os.path.dirname(os.path.abspath(__file__))

if 'banana_to_pdf' not in sys.modules:
    _pkg = types.ModuleType('banana_to_pdf')
    _pkg.__path__ = [os.path.join(_here, 'src')]
    sys.modules['banana_to_pdf'] = _pkg

_spec = importlib.util.spec_from_file_location(
    'banana_to_pdf._entry',
    os.path.join(_here, 'src', '__main__.py'),
)
_mod = importlib.util.module_from_spec(_spec)
_mod.__package__ = 'banana_to_pdf'
_spec.loader.exec_module(_mod)
_mod.main()
