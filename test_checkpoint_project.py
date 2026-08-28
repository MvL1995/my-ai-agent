import importlib
import importlib.util
import tempfile
from pathlib import Path


module_spec = importlib.util.find_spec(
    "checkpoint_project"
)

assert module_spec is not None, (
    "checkpoint_project.py 尚未实现"
)

checkpoint_project = importlib.import_module(
    "checkpoint_project"
)

create_checkpoint = getattr(
    checkpoint_project,
    "create_checkpoint",
    None
)

assert create_checkpoint is not None, (
    "create_checkpoint() 尚未实现"
)

with tempfile.TemporaryDirectory() as temp_dir:
    root = Path(temp_dir)
    project_dir = root / "project"
    backup_root = root / "backups"
    project_dir.mkdir()

    (project_dir / "verify_project.py").write_text(
        "raise SystemExit(0)",
        encoding="utf-8"
    )
    (project_dir / "main.py").write_text(
        'print("main")',
        encoding="utf-8"
    )
    (project_dir / "test_demo.py").write_text(
        'print("test")',
        encoding="utf-8"
    )
    (project_dir / "memory.db").write_bytes(
        b"database"
    )
    (project_dir / "ignored.txt").write_text(
        "ignore",
        encoding="utf-8"
    )

    checkpoint = create_checkpoint(
        project_dir,
        backup_root,
        timestamp="20260827_010203"
    )

    assert checkpoint == (
        backup_root / "checkpoint_20260827_010203"
    )

    assert {
        path.name for path in checkpoint.iterdir()
    } == {
        "verify_project.py",
        "main.py",
        "test_demo.py",
        "memory.db",
    }

    (project_dir / "verify_project.py").write_text(
        "raise SystemExit(1)",
        encoding="utf-8"
    )

    failed_checkpoint = create_checkpoint(
        project_dir,
        backup_root,
        timestamp="20260827_010204"
    )

    assert failed_checkpoint is None
    assert not (
        backup_root / "checkpoint_20260827_010204"
    ).exists()

print("Checkpoint-project tests passed.")