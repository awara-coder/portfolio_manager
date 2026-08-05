#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ModuleRule:
    name: str
    path: Path
    import_prefix: str
    may_import: frozenset[str]


def load_rules(root: Path) -> dict[str, ModuleRule]:
    config_path = root / "architecture.toml"
    with config_path.open("rb") as config_file:
        config = tomllib.load(config_file)

    if config.get("version") != 1:
        raise ValueError("architecture.toml must declare version = 1")

    modules = config.get("modules")
    if not isinstance(modules, dict) or not modules:
        raise ValueError("architecture.toml must define at least one module")

    rules: dict[str, ModuleRule] = {}
    paths: set[Path] = set()
    prefixes: set[str] = set()
    for name, raw_rule in modules.items():
        path = Path(raw_rule["path"])
        prefix = raw_rule["import_prefix"]
        dependencies = frozenset(raw_rule.get("may_import", []))
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"module {name!r} has an unsafe path")
        if path in paths:
            raise ValueError(f"module path {path} is declared more than once")
        if prefix in prefixes:
            raise ValueError(f"import prefix {prefix!r} is declared more than once")
        paths.add(path)
        prefixes.add(prefix)
        rules[name] = ModuleRule(name, path, prefix, dependencies)

    for rule in rules.values():
        unknown = rule.may_import - rules.keys()
        if unknown:
            raise ValueError(f"module {rule.name!r} references unknown modules: {sorted(unknown)}")
        if rule.name in rule.may_import:
            raise ValueError(f"module {rule.name!r} cannot list itself in may_import")

    detect_cycles(rules)
    return rules


def detect_cycles(rules: dict[str, ModuleRule]) -> None:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(name: str, chain: tuple[str, ...]) -> None:
        if name in visiting:
            cycle = " -> ".join((*chain, name))
            raise ValueError(f"architecture dependency cycle detected: {cycle}")
        if name in visited:
            return
        visiting.add(name)
        for dependency in rules[name].may_import:
            visit(dependency, (*chain, name))
        visiting.remove(name)
        visited.add(name)

    for module_name in rules:
        visit(module_name, ())


def imported_modules(source: str, path: Path) -> set[str]:
    tree = ast.parse(source, filename=str(path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module)
    return imports


def match_module(import_name: str, rules: dict[str, ModuleRule]) -> str | None:
    matches = [
        rule
        for rule in rules.values()
        if import_name == rule.import_prefix or import_name.startswith(f"{rule.import_prefix}.")
    ]
    if not matches:
        return None
    return max(matches, key=lambda rule: len(rule.import_prefix)).name


def check_imports(root: Path, rules: dict[str, ModuleRule]) -> list[str]:
    violations: list[str] = []
    for source_rule in rules.values():
        module_root = root / source_rule.path
        if not module_root.exists():
            continue
        for path in sorted(module_root.rglob("*.py")):
            try:
                imports = imported_modules(path.read_text(encoding="utf-8"), path)
            except (OSError, SyntaxError, UnicodeError) as error:
                violations.append(f"{path.relative_to(root)}: cannot inspect: {error}")
                continue
            for imported in sorted(imports):
                target = match_module(imported, rules)
                if target is None or target == source_rule.name:
                    continue
                if target not in source_rule.may_import:
                    violations.append(
                        f"{path.relative_to(root)}: {source_rule.name} may not import "
                        f"{target} ({imported})"
                    )
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description="Enforce architecture boundaries")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    args = parser.parse_args()
    root = args.root.resolve()

    try:
        rules = load_rules(root)
        violations = check_imports(root, rules)
    except (KeyError, OSError, TypeError, ValueError, tomllib.TOMLDecodeError) as error:
        print(f"architecture policy error: {error}", file=sys.stderr)
        return 2

    if violations:
        print("architecture boundary violations:", file=sys.stderr)
        for violation in violations:
            print(f"- {violation}", file=sys.stderr)
        return 1

    print(f"architecture boundaries valid ({len(rules)} modules)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
