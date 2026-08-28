import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path


def collect_project_files(project_directory):
    project_directory = Path(project_directory)

    files = list(project_directory.glob("*.py"))
    files.extend(project_directory.glob("*.db"))

    return sorted(
        files,
        key=lambda path: path.name
    )


def run_project_verification(project_directory):
    project_directory = Path(project_directory)

    result = subprocess.run(
        [sys.executable, "verify_project.py"],
        cwd=str(project_directory),
        capture_output=True,
        text=True,
        check=False
    )

    if result.stdout:
        print(result.stdout, end="")

    if result.stderr:
        print(result.stderr, end="")

    return result.returncode == 0


def create_checkpoint(
    project_directory,
    backup_root,
    timestamp=None
):
    project_directory = Path(project_directory)
    backup_root = Path(backup_root)

    if not run_project_verification(
        project_directory
    ):
        print(
            "Checkpoint aborted: "
            "verification failed."
        )
        return None

    if timestamp is None:
        timestamp = datetime.now().strftime(
            "%Y%m%d_%H%M%S"
        )

    checkpoint_directory = (
        backup_root / f"checkpoint_{timestamp}"
    )

    checkpoint_directory.mkdir(
        parents=True,
        exist_ok=False
    )

    for source_file in collect_project_files(
        project_directory
    ):
        shutil.copy2(
            source_file,
            checkpoint_directory / source_file.name
        )

    print(
        "Checkpoint created:",
        checkpoint_directory
    )

    return checkpoint_directory


def main():
    project_directory = (
        Path(__file__).resolve().parent
    )
    backup_root = (
        project_directory / "checkpoints"
    )

    checkpoint = create_checkpoint(
        project_directory,
        backup_root
    )

    if checkpoint is None:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())