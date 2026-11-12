"""Make the app importable and keep every test away from real data."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import app as app_module  # noqa: E402
from modules import database  # noqa: E402


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(database, "DATABASE_FILE", tmp_path / "test.db")
    monkeypatch.setattr(app_module, "OUTPUT_DIR", tmp_path / "output")
    app_module.app.config.update(TESTING=True)
    return app_module.app.test_client()
