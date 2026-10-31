from pathlib import Path


def test_demo_app_is_valid_python():
    source = Path("scripts/demo_app.py").read_text(encoding="utf-8")
    compile(source, "scripts/demo_app.py", "exec")
