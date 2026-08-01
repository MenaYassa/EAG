"""Benchmark fixtures for EAG."""

import shutil
import tempfile
from pathlib import Path

from eag.benchmark.errors import FixtureError
from eag.benchmark.models import Benchmark


class FixtureManager:
    """Manages isolated workspaces for benchmark execution."""

    def prepare(self, benchmark: Benchmark) -> Path:
        """Creates a temporary workspace for the benchmark."""
        try:
            temp_dir = Path(tempfile.mkdtemp(prefix=f"eag_bench_{benchmark.id}_"))
            if benchmark.fixture_path and benchmark.fixture_path.exists():
                shutil.copytree(benchmark.fixture_path, temp_dir, dirs_exist_ok=True)
            return temp_dir
        except Exception as e:
            raise FixtureError(f"Failed to prepare fixture for {benchmark.id}: {e}") from e

    def cleanup(self, workspace: Path) -> None:
        """Removes the temporary workspace."""
        if workspace.exists():
            shutil.rmtree(workspace, ignore_errors=True)
