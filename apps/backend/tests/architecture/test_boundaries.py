from pathlib import Path

from scripts.check_boundaries import scan_file, scan_tree

REPOSITORY_ROOT = Path(__file__).parents[4]
BACKEND_ROOT = REPOSITORY_ROOT / "apps" / "backend" / "src" / "lep"


def test_backend_modules_use_the_standard_structure_and_have_no_violations() -> None:
    violations = scan_tree(BACKEND_ROOT)

    assert violations == []
    module_root = BACKEND_ROOT / "modules"
    expected_parts = {
        "api",
        "application",
        "domain",
        "infrastructure",
        "events",
        "permissions",
        "tests",
    }
    modules = [
        path for path in module_root.iterdir() if path.is_dir() and not path.name.startswith("_")
    ]
    assert modules
    for module in modules:
        assert (module / "public.py").is_file()
        assert expected_parts.issubset(
            {path.name for path in module.iterdir() if path.is_dir()}
        )


def test_boundary_checker_rejects_cross_module_internal_imports() -> None:
    fixture_root = REPOSITORY_ROOT / "apps" / "backend" / "tests" / "architecture" / "fixtures"
    module_root = fixture_root / "lep" / "modules"
    source = module_root / "alpha" / "domain" / "entities.py"

    violations = scan_file(source, module_root)

    assert any("cross-module internal import" in violation.message for violation in violations)


def test_boundary_checker_rejects_relative_cross_module_internal_imports(tmp_path: Path) -> None:
    module_root = tmp_path / "modules"
    source = module_root / "alpha" / "domain" / "entities.py"
    source.parent.mkdir(parents=True)
    source.write_text(
        "from ...beta.domain.entities import BetaEntity\n",
        encoding="utf-8",
    )

    violations = scan_file(source, module_root)

    assert any("cross-module internal import" in violation.message for violation in violations)


def test_boundary_checker_rejects_framework_imports_from_domain() -> None:
    fixture_root = REPOSITORY_ROOT / "apps" / "backend" / "tests" / "architecture" / "fixtures"
    module_root = fixture_root / "lep" / "modules"
    source = module_root / "alpha" / "domain" / "external.py"

    violations = scan_file(source, module_root)

    assert any(
        "domain layer imports infrastructure framework" in violation.message
        for violation in violations
    )
