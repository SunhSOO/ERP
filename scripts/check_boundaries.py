"""Static checks for backend module boundaries.

The checker is intentionally dependency-free so it can run before the rest of
the development environment is installed.
"""

from __future__ import annotations

import argparse
import ast
from dataclasses import dataclass
from pathlib import Path

REQUIRED_PARTS = {
    "api",
    "application",
    "domain",
    "infrastructure",
    "events",
    "permissions",
    "tests",
}
FORBIDDEN_DOMAIN_IMPORTS = {"fastapi", "sqlalchemy", "redis", "minio"}


@dataclass(frozen=True)
class Violation:
    path: Path
    line: int
    message: str


def _module_name(path: Path, module_root: Path) -> str | None:
    relative = path.relative_to(module_root)
    if not relative.parts:
        return None
    return relative.parts[0] if len(relative.parts) > 1 else None


def _import_name(node: ast.Import | ast.ImportFrom) -> str:
    if isinstance(node, ast.Import):
        return node.names[0].name
    return node.module or ""


def scan_file(path: Path, module_root: Path) -> list[Violation]:
    """Return violations found in one Python file."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, SyntaxError) as exc:
        return [Violation(path, 1, f"cannot parse file: {exc}")]

    current_module = _module_name(path, module_root)
    violations: list[Violation] = []
    in_domain = "domain" in path.relative_to(module_root).parts
    for node in ast.walk(tree):
        if not isinstance(node, ast.Import | ast.ImportFrom):
            continue
        imported = _import_name(node)
        if in_domain and imported.split(".", 1)[0] in FORBIDDEN_DOMAIN_IMPORTS:
            violations.append(
                Violation(path, node.lineno, "domain layer imports infrastructure framework")
            )
        if not imported.startswith("lep.modules."):
            continue
        parts = imported.split(".")
        if len(parts) < 3 or current_module is None or parts[2] == current_module:
            continue
        if len(parts) >= 4 and parts[3] == "public":
            continue
        violations.append(
            Violation(path, node.lineno, "cross-module internal import")
        )
    return violations


def scan_tree(root: Path) -> list[Violation]:
    """Check module structure and Python imports beneath ``root``."""

    module_root = root / "modules"
    if not module_root.is_dir():
        return [Violation(module_root, 1, "modules directory is missing")]

    violations: list[Violation] = []
    for module in sorted(path for path in module_root.iterdir() if path.is_dir()):
        if module.name.startswith("_"):
            continue
        child_dirs = {child.name for child in module.iterdir() if child.is_dir()}
        missing = sorted(REQUIRED_PARTS - child_dirs)
        if missing:
            violations.append(
                Violation(module, 1, f"missing standard module directories: {', '.join(missing)}")
            )
        if not (module / "public.py").is_file():
            violations.append(Violation(module, 1, "public.py is missing"))
    for path in root.rglob("*.py"):
        if "modules" not in path.relative_to(root).parts:
            continue
        violations.extend(scan_file(path, module_root))
    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path("apps/backend/src/lep"),
        help="backend package root (default: apps/backend/src/lep)",
    )
    args = parser.parse_args()
    violations = scan_tree(args.root)
    for violation in violations:
        print(f"{violation.path}:{violation.line}: {violation.message}")
    if violations:
        print(f"Found {len(violations)} boundary violation(s).")
        return 1
    print(f"Boundary check passed: {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
