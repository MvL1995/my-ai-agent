import py_compile
import subprocess
import sys
from pathlib import Path


SOURCE_FILE_NAMES = (
    "main.py",
    "memory.py",
    "agent_instructions.py",
    "session_manager.py",
    "input_validation.py",
    "search_routing.py",
    "search_service.py",
    "search_cache.py",
    "task_contract.py",
    "task_factory.py",
    "landing_page_package.py",
    "task_router.py",
    "task_executor.py",
    "agent_registry.py",
    "task_pipeline.py",
    "task_entry.py",
    "workflow_contract.py",
    "client_project_workflow.py",
    "workflow_entry.py",
    "workflow_history.py",
    "lead_capture.py",
    "web_app.py",
)


def discover_test_files(directory="."):
    test_directory = Path(directory)

    return sorted(
        test_directory.glob("test_*.py"),
        key=lambda path: path.name
    )


def compile_source_files(files):
    all_passed = True

    for file in files:
        source_file = Path(file)

        try:
            py_compile.compile(
                str(source_file),
                doraise=True
            )
        except (py_compile.PyCompileError, OSError) as error:
            print(f"[FAIL] compile {source_file.name}")
            print(error)
            all_passed = False
        else:
            print(f"[PASS] compile {source_file.name}")

    return all_passed


def run_test_files(files):
    passed = 0
    failed = 0

    for file in files:
        test_file = Path(file).resolve()

        result = subprocess.run(
            [sys.executable, str(test_file)],
            cwd=str(test_file.parent),
            capture_output=True,
            text=True,
            check=False
        )

        if result.returncode == 0:
            print(f"[PASS] {test_file.name}")
            passed += 1
        else:
            print(f"[FAIL] {test_file.name}")

            if result.stdout:
                print(result.stdout)

            if result.stderr:
                print(result.stderr)

            failed += 1

    return passed, failed


def main():
    project_directory = Path(__file__).resolve().parent

    source_files = [
        project_directory / name
        for name in SOURCE_FILE_NAMES
    ]
    test_files = discover_test_files(
        project_directory
    )

    print("Checking source files...")
    sources_passed = compile_source_files(
        source_files
    )

    print("\nRunning tests...")
    passed, failed = run_test_files(test_files)
    total = passed + failed

    print(
        f"\nSummary: {passed}/{total} tests passed."
    )

    if sources_passed and failed == 0:
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
