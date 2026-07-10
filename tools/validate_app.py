"""Fast structural checks that do not require a running Frappe site."""

from __future__ import annotations

import ast
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
APP_ROOT = ROOT / "rent_renewal_tracker"
STANDARD_LINK_TARGETS = {"Country", "Currency", "User"}


def validate_python() -> int:
    files = sorted(APP_ROOT.rglob("*.py"))
    for path in files:
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return len(files)


def validate_doctypes() -> tuple[int, set[str]]:
    files = sorted((APP_ROOT / "rent_renewal_tracker" / "doctype").glob("*/*.json"))
    definitions = [(path, json.loads(path.read_text(encoding="utf-8"))) for path in files]
    names = {definition["name"] for _, definition in definitions}
    assert len(names) == len(definitions), "duplicate DocType name"

    for path, definition in definitions:
        assert definition["doctype"] == "DocType", f"{path}: expected a DocType artifact"
        assert definition["module"] == "Rent Renewal Tracker", f"{path}: unexpected module"
        if not definition.get("istable") and not definition.get("issingle"):
            assert definition.get("sort_field") != "modified", (
                f"{path}: Frappe v16 standard DocTypes should not default-sort by modified"
            )

        expected_slug = definition["name"].lower().replace(" ", "_").replace("-", "_")
        assert path.parent.name == expected_slug, f"{path}: directory does not match DocType name"
        fieldnames = [field["fieldname"] for field in definition.get("fields", [])]
        assert len(fieldnames) == len(set(fieldnames)), f"{path}: duplicate fieldname"
        assert definition.get("field_order") == fieldnames, f"{path}: field_order differs from fields"

        controller = path.with_suffix(".py")
        assert controller.exists(), f"{path}: missing Python controller"

        for field in definition.get("fields", []):
            if field.get("fieldtype") not in {"Link", "Table"}:
                continue
            target = field.get("options")
            assert target in names or target in STANDARD_LINK_TARGETS, (
                f"{path}: {field['fieldname']} links to unknown DocType {target!r}"
            )

        for link in definition.get("links", []):
            assert link["link_doctype"] in names, (
                f"{path}: dashboard link targets unknown DocType {link['link_doctype']!r}"
            )

    return len(files), names


def validate_reports(doctype_names: set[str]) -> tuple[int, set[str]]:
    report_root = APP_ROOT / "rent_renewal_tracker" / "report"
    files = sorted(report_root.glob("*/*.json"))
    names = set()

    for path in files:
        definition = json.loads(path.read_text(encoding="utf-8"))
        assert definition["doctype"] == "Report", f"{path}: expected a Report artifact"
        assert definition["module"] == "Rent Renewal Tracker", f"{path}: unexpected module"
        assert definition["report_type"] == "Script Report", f"{path}: expected Script Report"
        assert definition["is_standard"] == "Yes", f"{path}: report must be standard"
        assert definition["ref_doctype"] in doctype_names, f"{path}: unknown reference DocType"
        assert definition["name"] == definition["report_name"], f"{path}: report names differ"
        assert definition["name"] not in names, f"{path}: duplicate report name"
        names.add(definition["name"])

        expected_slug = definition["name"].lower().replace(" ", "_").replace("-", "_")
        assert path.parent.name == expected_slug, f"{path}: directory does not match report name"
        assert path.with_suffix(".py").exists(), f"{path}: missing report controller"
        assert path.with_suffix(".js").exists(), f"{path}: missing report filters"
        assert definition.get("roles"), f"{path}: report has no permitted roles"

    return len(files), names


def validate_workspaces(doctype_names: set[str], report_names: set[str]) -> int:
    workspace_root = APP_ROOT / "rent_renewal_tracker" / "workspace"
    files = sorted(workspace_root.glob("*/*.json"))

    for path in files:
        definition = json.loads(path.read_text(encoding="utf-8"))
        assert definition["doctype"] == "Workspace", f"{path}: expected a Workspace artifact"
        assert definition["app"] == "rent_renewal_tracker", f"{path}: unexpected app"
        assert definition["module"] == "Rent Renewal Tracker", f"{path}: unexpected module"
        content = json.loads(definition["content"])
        shortcut_labels = {row["label"] for row in definition.get("shortcuts", [])}
        card_labels = {
            row["label"] for row in definition.get("links", []) if row.get("type") == "Card Break"
        }
        for block in content:
            if block["type"] == "shortcut":
                assert block["data"]["shortcut_name"] in shortcut_labels, (
                    f"{path}: content references unknown shortcut"
                )
            if block["type"] == "card":
                assert block["data"]["card_name"] in card_labels, (
                    f"{path}: content references unknown card"
                )

        for link in definition.get("links", []):
            if link.get("type") != "Link":
                continue
            if link["link_type"] == "DocType":
                assert link["link_to"] in doctype_names, f"{path}: unknown DocType link"
            if link["link_type"] == "Report":
                assert link["link_to"] in report_names, f"{path}: unknown Report link"

    return len(files)


def validate_hooks() -> None:
    hooks = (APP_ROOT / "hooks.py").read_text(encoding="utf-8")
    assert 'app_name = "rent_renewal_tracker"' in hooks
    assert 'before_install = "rent_renewal_tracker.install.before_install"' in hooks
    assert 'after_install = "rent_renewal_tracker.install.after_install"' in hooks
    assert "refresh_lease_statuses" in hooks
    assert "refresh_rent_schedule_statuses" in hooks
    assert "process_due_reminders" in hooks
    assert "add_to_apps_screen" in hooks
    assert "rent_renewal_tracker.api.has_app_permission" in hooks
    logo = APP_ROOT / "public" / "images" / "rent-renewal-tracker.svg"
    assert logo.exists(), "Apps screen logo is missing"


def validate_patches() -> int:
    entries = [
        line.strip()
        for line in (APP_ROOT / "patches.txt").read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.startswith("[")
    ]
    for entry in entries:
        relative = Path(*entry.split(".")[1:]).with_suffix(".py")
        assert (APP_ROOT / relative).exists(), f"patch module does not exist: {entry}"
    return len(entries)


def main() -> None:
    python_count = validate_python()
    doctype_count, doctype_names = validate_doctypes()
    report_count, report_names = validate_reports(doctype_names)
    workspace_count = validate_workspaces(doctype_names, report_names)
    validate_hooks()
    patch_count = validate_patches()
    print(
        f"Validated {python_count} Python files, {doctype_count} DocTypes, "
        f"{report_count} reports, {workspace_count} Workspace, and {patch_count} patch."
    )


if __name__ == "__main__":
    main()
