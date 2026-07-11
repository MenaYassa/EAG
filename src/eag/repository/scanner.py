import contextlib
import hashlib
import os
from datetime import UTC, datetime
from pathlib import Path

from eag.repository.errors import RepositoryNotFoundError, ScanFailedError
from eag.repository.ignore import IgnoreEngine
from eag.repository.models import (
    LanguageSummary,
    RepositoryCapabilities,
    RepositoryFact,
    RepositoryIdentity,
    RepositoryMetadata,
    RepositoryProfile,
    RepositoryStatistics,
)
from eag.repository.state import (
    ProjectLayout,
    RepositoryHealth,
    RepositoryKind,
)


class RepositoryScanner:
    def __init__(self, ignore_engine: IgnoreEngine) -> None:
        self._ignore = ignore_engine

    def scan(self, root: Path) -> RepositoryProfile:
        if not root.exists() or not root.is_dir():
            raise RepositoryNotFoundError(f"Repository directory not found: {root}")

        try:
            identity = self._create_identity(root)
            statistics, metadata, capabilities, facts = self._discover(root)
            health = self._determine_health(metadata, capabilities)
            kind = self._determine_kind(root)
            layout = self._determine_layout(root)

            return RepositoryProfile(
                identity=identity,
                statistics=statistics,
                metadata=metadata,
                health=health,
                kind=kind,
                layout=layout,
                capabilities=capabilities,
                facts=facts,
                fingerprint=self._generate_fingerprint(root, statistics),
                generated_at=datetime.now(UTC),
            )
        except Exception as e:
            raise ScanFailedError(f"Failed to scan repository {root}: {e}") from e

    def _create_identity(self, root: Path) -> RepositoryIdentity:
        return RepositoryIdentity(
            name=root.name,
            root=root.resolve(),
            discovered_at=datetime.now(UTC),
        )

    def _discover(
        self, root: Path
    ) -> tuple[
        RepositoryStatistics,
        RepositoryMetadata,
        RepositoryCapabilities,
        list[RepositoryFact],
    ]:
        files = 0
        dirs = 0
        packages = 0
        tests = 0
        docs = 0
        bytes_total = 0
        py_files = 0
        md_files = 0
        cfg_files = 0

        has_readme = False
        has_license = False
        has_pyproject = False
        has_dockerfile = False
        has_docker_compose = False
        has_tests_dir = False

        facts: list[RepositoryFact] = []

        for dirpath, dirnames, filenames in os.walk(root, topdown=True):
            kept_dirs = []
            for d in dirnames:
                p = Path(dirpath) / d
                if not self._ignore.should_ignore(p):
                    kept_dirs.append(d)
                if p.name in ["tests", "test"]:
                    has_tests_dir = True
                if (p / "__init__.py").exists():
                    packages += 1
            dirnames[:] = kept_dirs

            if Path(dirpath) != root:
                dirs += 1

            for f in filenames:
                p = Path(dirpath) / f
                if self._ignore.should_ignore(p):
                    continue

                files += 1
                with contextlib.suppress(OSError):
                    bytes_total += p.stat().st_size

                name_lower = f.lower()
                rel_path = p.relative_to(root)

                if name_lower == "readme.md" or name_lower.startswith("readme."):
                    has_readme = True
                    docs += 1
                elif name_lower.startswith("license"):
                    has_license = True
                    docs += 1
                elif name_lower == "pyproject.toml":
                    has_pyproject = True
                    cfg_files += 1
                elif name_lower == "dockerfile":
                    has_dockerfile = True
                    cfg_files += 1
                elif name_lower in ["docker-compose.yml", "docker-compose.yaml"]:
                    has_docker_compose = True
                    cfg_files += 1
                elif name_lower.endswith(".py"):
                    py_files += 1
                    if "test" in name_lower or "tests" in str(rel_path).lower():
                        tests += 1
                elif name_lower.endswith(".md"):
                    md_files += 1
                    docs += 1
                elif name_lower in [
                    "requirements.txt",
                    "uv.lock",
                    "setup.py",
                    "setup.cfg",
                    "tox.ini",
                    "makefile",
                    ".gitignore",
                ]:
                    cfg_files += 1

        git_dir = root / ".git"

        ci_path = None
        if (root / ".github" / "workflows").exists():
            ci_path = root / ".github" / "workflows"
        elif (root / ".gitlab-ci.yml").exists():
            ci_path = root / ".gitlab-ci.yml"

        pkg_mgr = None
        if (root / "uv.lock").exists():
            pkg_mgr = "uv"
        elif (root / "poetry.lock").exists():
            pkg_mgr = "poetry"
        elif (root / "Pipfile.lock").exists():
            pkg_mgr = "pipenv"
        elif (root / "requirements.txt").exists():
            pkg_mgr = "pip"

        metadata = RepositoryMetadata(
            git_repository=git_dir.exists(),
            readme=(root / "README.md") if has_readme else None,
            license=(root / "LICENSE") if has_license else None,
            pyproject=(root / "pyproject.toml") if has_pyproject else None,
            docker=(
                (root / "docker-compose.yml")
                if has_docker_compose
                else (root / "Dockerfile")
                if has_dockerfile
                else None
            ),
            ci=ci_path,
            package_manager=pkg_mgr,
        )

        pyproject_content = ""
        if has_pyproject:
            with contextlib.suppress(Exception):
                pyproject_content = (root / "pyproject.toml").read_text()

        capabilities = RepositoryCapabilities(
            git=metadata.git_repository,
            docker=bool(metadata.docker),
            tests=has_tests_dir or tests > 0,
            ci=bool(metadata.ci),
            package_manager=bool(metadata.package_manager),
            virtual_env=(root / ".venv").exists(),
            type_checking="mypy" in pyproject_content,
            formatting="ruff" in pyproject_content,
            linting="ruff" in pyproject_content,
        )

        facts.append(
            RepositoryFact(
                kind="project_type",
                value="Python",
                confidence=1.0 if has_pyproject else 0.5,
            )
        )

        if metadata.git_repository:
            facts.append(RepositoryFact(kind="vcs", value="Git", confidence=1.0))
        if capabilities.tests:
            facts.append(RepositoryFact(kind="testing", value="Present", confidence=1.0))
        if metadata.package_manager:
            facts.append(
                RepositoryFact(
                    kind="package_manager",
                    value=metadata.package_manager,
                    confidence=1.0,
                )
            )

        langs = []
        if files > 0:
            if py_files > 0:
                langs.append(
                    LanguageSummary(
                        language="Python",
                        file_count=py_files,
                        line_count=0,
                        percentage=(py_files / files) * 100,
                    )
                )
            if md_files > 0:
                langs.append(
                    LanguageSummary(
                        language="Markdown",
                        file_count=md_files,
                        line_count=0,
                        percentage=(md_files / files) * 100,
                    )
                )

        stats = RepositoryStatistics(
            files=files,
            directories=dirs,
            packages=packages,
            tests=tests,
            documentation=docs,
            total_bytes=bytes_total,
            python_files=py_files,
            markdown_files=md_files,
            config_files=cfg_files,
            languages=langs,
        )

        return stats, metadata, capabilities, facts

    def _determine_health(
        self, metadata: RepositoryMetadata, capabilities: RepositoryCapabilities
    ) -> RepositoryHealth:
        if not metadata.git_repository and not metadata.pyproject:
            return RepositoryHealth.ERROR
        if not metadata.readme or not metadata.pyproject:
            return RepositoryHealth.WARNING
        return RepositoryHealth.HEALTHY

    def _determine_kind(self, root: Path) -> RepositoryKind:
        if (root / "pyproject.toml").exists():
            return RepositoryKind.PYTHON
        if (root / "package.json").exists():
            return RepositoryKind.NODE
        if (root / "Cargo.toml").exists():
            return RepositoryKind.RUST
        if (root / "go.mod").exists():
            return RepositoryKind.GO
        if (root / "pom.xml").exists():
            return RepositoryKind.JAVA
        return RepositoryKind.UNKNOWN

    def _determine_layout(self, root: Path) -> ProjectLayout:
        if (root / "src").is_dir():
            return ProjectLayout.SRC_LAYOUT
        if (root / "packages").is_dir():
            return ProjectLayout.MONOREPO
        if any(f.suffix == ".py" for f in root.iterdir() if f.is_file()):
            return ProjectLayout.FLAT
        return ProjectLayout.UNKNOWN

    def _generate_fingerprint(self, root: Path, stats: RepositoryStatistics) -> str:
        h = hashlib.sha256()
        h.update(str(root).encode())
        h.update(str(stats.files).encode())
        h.update(str(datetime.now(UTC).isoformat()).encode())
        return h.hexdigest()
