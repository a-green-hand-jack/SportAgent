#!/usr/bin/env python3
"""Synthetic smoke test for adopt-existing-repo."""
from __future__ import annotations

import subprocess
import sys
import tempfile
from pathlib import Path


REPO = Path(__file__).resolve().parents[3]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    proc = subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)
    if proc.returncode != 0:
        print("$ " + " ".join(cmd))
        print(proc.stdout)
        print(proc.stderr)
        raise SystemExit(proc.returncode)
    return proc


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_fixture(root: Path) -> Path:
    target = root / "sample-existing"
    target.mkdir()
    run(["git", "init"], target)
    run(["git", "config", "user.email", "adoption@example.test"], target)
    run(["git", "config", "user.name", "Adoption Test"], target)
    write(target / "README.md", "# Sample Existing Repo\n")
    write(
        target / "pyproject.toml",
        "[project]\nname = \"sample-existing\"\nversion = \"0.0.1\"\n",
    )
    write(
        target / "src" / "sample_existing.py",
        "def answer():\n    return 42\n",
    )
    write(
        target / "tests" / "test_sample.py",
        "import sys\n"
        "import unittest\n"
        "from pathlib import Path\n"
        "sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))\n"
        "import sample_existing\n\n"
        "class SampleTest(unittest.TestCase):\n"
        "    def test_answer(self):\n"
        "        self.assertEqual(sample_existing.answer(), 42)\n",
    )
    run(["git", "add", "."], target)
    run(["git", "commit", "-m", "initial"], target)
    return target


def main() -> int:
    with tempfile.TemporaryDirectory(prefix="adoption-smoke-") as tmp:
        target = make_fixture(Path(tmp))
        adopter = REPO / "scripts" / "adopt-existing-repo.py"
        integrity = REPO / "scripts" / "check-adoption-integrity.py"
        cmd = [
            sys.executable,
            str(adopter),
            str(target),
            "--phase",
            "all",
            "--test-command",
            "python -m unittest discover -s tests",
            "--project-name",
            "sample-existing",
        ]
        run(cmd, REPO)
        run([sys.executable, str(integrity), str(target)], REPO)
        imported = target / "lab" / "code" / "imported" / "sample-existing"
        expected = [
            imported / "src" / "sample_existing.py",
            imported / "tests" / "test_sample.py",
            imported / "pyproject.toml",
            target / "human" / "imported" / "adoption-conflicts" / "README.md",
            target / "lab" / "docs" / "audits" / "template-adoption-report.md",
        ]
        missing = [p for p in expected if not p.exists()]
        if missing:
            for path in missing:
                print(f"missing expected path: {path}")
            return 1
        root_names = {p.name for p in target.iterdir()}
        polluted = {"src", "tests", "pyproject.toml"} & root_names
        if polluted:
            print(f"root pollution remained: {sorted(polluted)}")
            return 1
    print("[adoption-smoke] OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
