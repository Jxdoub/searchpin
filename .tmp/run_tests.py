"""Throwaway stdlib runner for tests/test_backends.py (pytest unavailable)."""

import importlib.util
import inspect
import sys
import types
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

# Register a bare `searchpin` package so importing searchpin.config /
# searchpin.backends skips __init__.py (which pulls in fastembed).
_pkg = types.ModuleType("searchpin")
_pkg.__path__ = [str(ROOT / "searchpin")]
sys.modules["searchpin"] = _pkg

spec = importlib.util.spec_from_file_location("test_backends", ROOT / "tests" / "test_backends.py")
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class MonkeyPatchShim:
    """Minimal pytest monkeypatch fixture: setattr/getattr/delitem with undo."""

    def __init__(self):
        self._undo = []

    def setattr(self, target, name, value):
        old = getattr(target, name)
        setattr(target, name, value)
        self._undo.append(lambda: setattr(target, name, old))

    def undo(self):
        for f in reversed(self._undo):
            f()
        self._undo.clear()


passed, failed = [], []
for cls_name in dir(mod):
    cls = getattr(mod, cls_name)
    if not isinstance(cls, type) or cls_name.startswith("_"):
        continue
    for meth_name in dir(cls):
        if not meth_name.startswith("test_"):
            continue
        inst = cls()
        meth = getattr(inst, meth_name)
        kwargs = {}
        mp = None
        if "monkeypatch" in inspect.signature(meth).parameters:
            mp = MonkeyPatchShim()
            kwargs["monkeypatch"] = mp
        full = f"{cls_name}::{meth_name}"
        try:
            meth(**kwargs)
            passed.append(full)
        except Exception as e:
            failed.append((full, f"{type(e).__name__}: {e}"))
        finally:
            if mp:
                mp.undo()

print(f"\nPASSED {len(passed)}  FAILED {len(failed)}")
for name, err in failed:
    print(f"  FAIL {name}\n       {err}")
sys.exit(1 if failed else 0)
