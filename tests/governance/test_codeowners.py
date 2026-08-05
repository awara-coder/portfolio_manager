from __future__ import annotations

import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
EXPECTED_OWNER = "@awara-coder"
REQUIRED_PATTERNS = {
    "*",
    "/AGENTS.md",
    "/architecture.toml",
    "/.github/",
    "/.pre-commit-config.yaml",
    "/docs/architecture/",
    "/docs/decisions/",
    "/scripts/check_architecture.py",
    "/tests/governance/",
    "/packages/domain/",
    "/packages/application/",
    "**/migrations/",
    "**/security/",
}


class CodeOwnersTests(unittest.TestCase):
    def test_critical_paths_require_the_designated_human_owner(self) -> None:
        codeowners = REPOSITORY_ROOT / ".github" / "CODEOWNERS"
        entries: dict[str, list[str]] = {}
        for raw_line in codeowners.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            pattern, *owners = line.split()
            entries[pattern] = owners

        self.assertEqual(set(), REQUIRED_PATTERNS - entries.keys())
        for pattern in REQUIRED_PATTERNS:
            self.assertEqual([EXPECTED_OWNER], entries[pattern], pattern)


if __name__ == "__main__":
    unittest.main()
