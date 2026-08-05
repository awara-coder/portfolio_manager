from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
MODULE_SPEC = importlib.util.spec_from_file_location(
    "check_architecture", REPOSITORY_ROOT / "scripts" / "check_architecture.py"
)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError("unable to load architecture checker")
CHECKER = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_SPEC.name] = CHECKER
MODULE_SPEC.loader.exec_module(CHECKER)


class ArchitecturePolicyTests(unittest.TestCase):
    def test_repository_policy_is_valid(self) -> None:
        rules = CHECKER.load_rules(REPOSITORY_ROOT)

        self.assertEqual([], CHECKER.check_imports(REPOSITORY_ROOT, rules))

    def test_dependency_cycle_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "architecture.toml").write_text(
                """
version = 1
[modules.one]
path = "one"
import_prefix = "example.one"
may_import = ["two"]
[modules.two]
path = "two"
import_prefix = "example.two"
may_import = ["one"]
""".strip(),
                encoding="utf-8",
            )

            with self.assertRaisesRegex(ValueError, "cycle"):
                CHECKER.load_rules(root)

    def test_forbidden_import_is_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "architecture.toml").write_text(
                """
version = 1
[modules.domain]
path = "domain"
import_prefix = "example.domain"
may_import = []
[modules.persistence]
path = "persistence"
import_prefix = "example.persistence"
may_import = ["domain"]
""".strip(),
                encoding="utf-8",
            )
            domain = root / "domain"
            domain.mkdir()
            (domain / "model.py").write_text(
                "import example.persistence\n", encoding="utf-8"
            )
            rules = CHECKER.load_rules(root)

            violations = CHECKER.check_imports(root, rules)

            self.assertEqual(1, len(violations))
            self.assertIn("domain may not import persistence", violations[0])


if __name__ == "__main__":
    unittest.main()
