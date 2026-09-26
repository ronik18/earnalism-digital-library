import importlib.util
from pathlib import Path

path = Path("bridge_fixtures/codex_acceptance_fixture.py")
spec = importlib.util.spec_from_file_location("codex_fixture", path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)

assert module.LABEL == "ready", "fixture label must be ready"
assert module.format_label(module.LABEL) == "READY", "fixture label must be uppercase"
print("codex fixture acceptance passed")
