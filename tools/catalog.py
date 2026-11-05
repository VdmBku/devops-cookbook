"""Build catalog.json and CATALOG.md from every <category>/<template>/template.yaml.

Each template.yaml is validated against schema/template.schema.json, and its
name and category must match the folders it sits in.

    python tools/catalog.py           write catalog.json and CATALOG.md
    python tools/catalog.py --check   fail if either file is out of date
"""

from __future__ import annotations

import argparse
import difflib
import json
import math
import sys
from collections import Counter
from itertools import groupby
from pathlib import Path

import yaml
from jsonschema import Draft202012Validator

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SCHEMA = REPO_ROOT / "schema" / "template.schema.json"
CATALOG_JSON = "catalog.json"
CATALOG_MD = "CATALOG.md"

# Output key order. It follows the schema, not the order a template.yaml happens to use.
FIELDS = (
    "name",
    "category",
    "title",
    "summary",
    "tags",
    "tools",
    "use_when",
    "avoid_when",
    "variables",
    "practices",
    "checks",
    "backs",
)
ITEM_FIELDS = {
    "tools": ("name", "version"),
    "variables": ("name", "default", "description", "where"),
    "practices": ("id", "rule", "why"),
}


def find_templates(root: Path) -> list[Path]:
    """Every <category>/<template>/template.yaml under root, skipping hidden folders."""
    found = [
        path
        for path in root.glob("*/*/template.yaml")
        if not any(part.startswith(".") for part in path.relative_to(root).parts)
    ]
    return sorted(found, key=lambda path: path.relative_to(root).as_posix())


def load_validator(schema_path: Path) -> Draft202012Validator:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def schema_errors(data: object, validator: Draft202012Validator) -> list[str]:
    errors = []
    for error in validator.iter_errors(data):
        where = ".".join(str(part) for part in error.absolute_path) or "top level"
        message = error.message
        if error.validator == "pattern" and "description" in error.schema:
            # A bare regex is hard to read, so add the rule it stands for.
            message += f" ({error.schema['description']})"
        errors.append(f"{where}: {message}")
    return sorted(errors)


def path_errors(data: dict, template_dir: Path) -> list[str]:
    errors = []
    folder, parent = template_dir.name, template_dir.parent.name
    if "name" in data and data["name"] != folder:
        errors.append(f"name {data['name']!r} does not match the folder {folder!r}")
    if "category" in data and data["category"] != parent:
        errors.append(f"category {data['category']!r} does not match the folder {parent!r}")
    return errors


def layout_errors(template_dir: Path) -> list[str]:
    errors = []
    if not (template_dir / "README.md").is_file():
        errors.append("README.md is missing")
    if not (template_dir / "files").is_dir():
        errors.append("files/ is missing")
    return errors


def where_errors(data: dict, files_dir: Path) -> list[str]:
    """Every variable must point at a real file inside files/."""
    errors = []
    base = files_dir.resolve()
    for index, variable in enumerate(data["variables"]):
        target = (files_dir / variable["where"]).resolve()
        if not (target.is_relative_to(base) and target.is_file()):
            errors.append(f"variables.{index}.where: {variable['where']!r} is not a file in files/")
    return errors


def duplicate_errors(data: dict) -> list[str]:
    errors = []
    for key, field in (("practices", "id"), ("variables", "name")):
        counts = Counter(item[field] for item in data[key])
        errors += [f"{key}: {field} {value!r} is used more than once" for value, n in counts.items() if n > 1]
    return errors


def json_errors(value: object, where: tuple[str, ...] = ()) -> list[str]:
    """YAML can hold values JSON cannot, such as dates. Report them instead of crashing later."""
    location = ".".join(where) or "top level"
    if isinstance(value, dict):
        errors = []
        for key, item in value.items():
            if not isinstance(key, str):
                errors.append(f"{location}: key {key!r} must be a string, quote it")
            errors += json_errors(item, (*where, str(key)))
        return errors
    if isinstance(value, list):
        return [error for index, item in enumerate(value) for error in json_errors(item, (*where, str(index)))]
    if isinstance(value, float) and not math.isfinite(value):
        return [f"{location}: {value} cannot be stored in JSON"]
    if value is None or isinstance(value, (str, int, float)):
        return []
    return [f"{location}: {value} cannot be stored in JSON, quote it"]


def check_template(path: Path, validator: Draft202012Validator) -> tuple[object, list[str]]:
    """Load one template.yaml and return its data with every problem found."""
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError) as exc:
        return None, [f"invalid YAML: {' '.join(str(exc).split())}"]

    errors = layout_errors(path.parent)
    structure = schema_errors(data, validator)
    errors += structure
    if not isinstance(data, dict):
        return data, errors
    errors += path_errors(data, path.parent)
    if not structure:
        # These checks rely on the shape the schema guarantees.
        errors += where_errors(data, path.parent / "files")
        errors += duplicate_errors(data)
        errors += json_errors(data)
    return data, errors


def catalog_entry(data: dict, template_dir: Path, root: Path) -> dict:
    entry = {"path": template_dir.relative_to(root).as_posix()}
    for key in FIELDS:
        if key not in data:
            continue
        value = data[key]
        if key in ITEM_FIELDS:
            value = [{field: item[field] for field in ITEM_FIELDS[key]} for item in value]
        entry[key] = value
    return entry


def build(root: Path, validator: Draft202012Validator) -> tuple[list[dict], list[str]]:
    """Return catalog entries sorted by path, and the problems that block the catalog."""
    entries, problems = [], []
    for path in find_templates(root):
        data, errors = check_template(path, validator)
        if errors:
            rel = path.relative_to(root).as_posix()
            problems += [f"{rel}: {error}" for error in errors]
            continue
        entries.append(catalog_entry(data, path.parent, root))
    entries.sort(key=lambda entry: (entry["category"], entry["name"]))
    return entries, problems


def render_json(entries: list[dict]) -> str:
    return json.dumps({"templates": entries}, indent=2, ensure_ascii=False) + "\n"


def cell(text: str) -> str:
    """Make text safe for one Markdown table cell."""
    return " ".join(str(text).split()).replace("|", "\\|")


def render_markdown(entries: list[dict]) -> str:
    lines = [
        "# Catalog",
        "",
        "Every template in this library, grouped by category. Each link opens the template folder and its README.",
        "",
        f"This file is generated by `tools/catalog.py` from each `template.yaml`. Do not edit it by hand."
        f" The same data is in [{CATALOG_JSON}]({CATALOG_JSON}) for scripts and AI assistants.",
    ]
    if not entries:
        lines += ["", "No templates yet."]
    for category, group in groupby(entries, key=lambda entry: entry["category"]):
        lines += [
            "",
            f"## {category}",
            "",
            "| Template | Summary | Tools | Tags |",
            "| --- | --- | --- | --- |",
        ]
        for entry in group:
            tools = ", ".join(f"{tool['name']} {tool['version']}" for tool in entry["tools"])
            tags = ", ".join(entry["tags"])
            link = f"[{cell(entry['title'])}]({entry['path']}/)"
            lines.append(f"| {link} | {cell(entry['summary'])} | {cell(tools)} | {cell(tags)} |")
    return "\n".join(lines) + "\n"


def stale_files(root: Path, outputs: dict[str, str]) -> list[str]:
    """Print a diff for every output that differs from the file on disk, return their names."""
    stale = []
    for filename, expected in outputs.items():
        target = root / filename
        current = target.read_bytes().decode("utf-8", errors="replace") if target.is_file() else ""
        if current == expected:
            continue
        stale.append(filename)
        diff = difflib.unified_diff(
            current.splitlines(keepends=True),
            expected.splitlines(keepends=True),
            fromfile=f"{filename} (committed)",
            tofile=f"{filename} (generated)",
        )
        sys.stderr.writelines(diff)
        print(f"\n{filename} is out of date.", file=sys.stderr)
    return stale


def count(entries: list[dict]) -> str:
    return f"{len(entries)} template" + ("" if len(entries) == 1 else "s")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="tools/catalog.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--check", action="store_true", help="do not write, fail if the files are out of date")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="library root (default: this repository)")
    parser.add_argument("--schema", type=Path, default=DEFAULT_SCHEMA, help="template schema to validate against")
    args = parser.parse_args(argv)

    entries, problems = build(args.root, load_validator(args.schema))
    if problems:
        for problem in problems:
            print(problem, file=sys.stderr)
        print(f"\n{len(problems)} problem(s) found. Nothing was written.", file=sys.stderr)
        return 1

    outputs = {CATALOG_JSON: render_json(entries), CATALOG_MD: render_markdown(entries)}
    if args.check:
        if stale_files(args.root, outputs):
            print("Run: python tools/catalog.py, then commit the result.", file=sys.stderr)
            return 1
        print(f"Catalog is up to date ({count(entries)}).")
        return 0

    for filename, content in outputs.items():
        (args.root / filename).write_bytes(content.encode("utf-8"))
    print(f"Wrote {CATALOG_JSON} and {CATALOG_MD} ({count(entries)}).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
