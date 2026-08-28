import importlib
import importlib.util
import tempfile
from pathlib import Path


module_spec = importlib.util.find_spec(
    "verify_project"
)

assert module_spec is not None, (
    "verify_project.py 尚未实现"
)

verify_project = importlib.import_module(
    "verify_project"
)

discover = getattr(
    verify_project,
    "discover_test_files",
    None
)
compile_sources = getattr(
    verify_project,
    "compile_source_files",
    None
)
run_tests = getattr(
    verify_project,
    "run_test_files",
    None
)

assert discover is not None
assert compile_sources is not None
assert run_tests is not None

with tempfile.TemporaryDirectory() as temp_dir:
    test_dir = Path(temp_dir)

    pass_file = test_dir / "test_pass.py"
    fail_file = test_dir / "test_fail.py"
    helper_file = test_dir / "helper.py"
    invalid_file = test_dir / "invalid.py"

    pass_file.write_text(
        'print("temporary pass")',
        encoding="utf-8"
    )
    fail_file.write_text(
        "raise SystemExit(1)",
        encoding="utf-8"
    )
    helper_file.write_text(
        'print("not a test")',
        encoding="utf-8"
    )
    invalid_file.write_text(
        "if True print('broken')",
        encoding="utf-8"
    )

    discovered = discover(test_dir)

    assert [
        path.name for path in discovered
    ] == [
        "test_fail.py",
        "test_pass.py",
    ]

    assert compile_sources([pass_file]) is True
    assert compile_sources([invalid_file]) is False

    passed, failed = run_tests(discovered)

    assert (passed, failed) == (1, 1)

print("Verification-runner tests passed.")