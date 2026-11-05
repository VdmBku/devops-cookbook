import json
import shutil
from pathlib import Path

import pytest
import yaml
from jsonschema import Draft202012Validator

import catalog

FIXTURES = Path(__file__).parent / "fixtures"


def fixture_root(name, tmp_path):
    """Copy a fixture library into tmp_path so the tool can write next to it."""
    root = tmp_path / "library"
    shutil.copytree(FIXTURES / name, root)
    return root


def empty_root(tmp_path):
    root = tmp_path / "library"
    root.mkdir()
    return root


def add_template(root, category, name, **changes):
    """Copy the valid fixture to <category>/<name>/ and adjust its metadata."""
    target = root / category / name
    shutil.copytree(FIXTURES / "valid" / "ansible" / "demo-role", target)
    meta_path = target / "template.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta.update(name=name, category=category, **changes)
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")
    return target


def reverse_keys(mapping):
    return dict(reversed(list(mapping.items())))


def run(root, *args):
    """Run the tool the way the command line does and return its exit code."""
    return catalog.main(["--root", str(root), *args])


def output(capsys):
    captured = capsys.readouterr()
    return captured.out + captured.err


def read_json(root):
    return json.loads((root / "catalog.json").read_text(encoding="utf-8"))


def read_md(root):
    return (root / "CATALOG.md").read_text(encoding="utf-8")


def test_schema_is_a_valid_draft_2020_12_schema():
    schema = json.loads(catalog.DEFAULT_SCHEMA.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)


def test_empty_library_produces_valid_outputs(tmp_path):
    root = empty_root(tmp_path)

    assert run(root) == 0

    assert read_json(root) == {"templates": []}
    assert "No templates yet." in read_md(root)


def test_valid_template_is_listed_in_both_outputs(tmp_path):
    root = fixture_root("valid", tmp_path)

    assert run(root) == 0

    templates = read_json(root)["templates"]
    assert len(templates) == 1
    entry = templates[0]
    assert entry["path"] == "ansible/demo-role"
    assert entry["name"] == "demo-role"
    assert entry["category"] == "ansible"
    assert entry["tools"] == [{"name": "ansible-core", "version": "2.18.1"}]
    assert entry["variables"][0]["where"] == "defaults/main.yml"
    assert entry["practices"][0]["id"] == "defaults-in-one-file"
    assert entry["backs"] == "Example item"

    md = read_md(root)
    assert "## ansible" in md
    assert "[Demo role](ansible/demo-role/)" in md
    assert "ansible-core 2.18.1" in md


def test_schema_violation_is_reported_and_nothing_is_written(tmp_path, capsys):
    root = fixture_root("schema-violation", tmp_path)

    assert run(root) == 1

    text = output(capsys)
    assert "ansible/demo-role/template.yaml" in text
    assert "'tag' was unexpected" in text
    assert "'tags' is a required property" in text
    assert "tools.0.version: 'latest'" in text
    assert "tools.1.version: 1.2 is not of type 'string'" in text
    assert "practices.0: 'why' is a required property" in text
    assert not (root / "catalog.json").exists()
    assert not (root / "CATALOG.md").exists()


def test_name_must_match_the_template_folder(tmp_path, capsys):
    root = fixture_root("name-mismatch", tmp_path)

    assert run(root) == 1

    text = output(capsys)
    assert "ansible/demo-role/template.yaml" in text
    assert "name 'other-role' does not match the folder 'demo-role'" in text


def test_category_must_match_the_parent_folder(tmp_path, capsys):
    root = empty_root(tmp_path)
    shutil.copytree(FIXTURES / "valid" / "ansible" / "demo-role", root / "terraform" / "demo-role")

    assert run(root) == 1

    assert "category 'ansible' does not match the folder 'terraform'" in output(capsys)


def test_output_is_sorted_grouped_and_identical_on_every_run(tmp_path):
    root = empty_root(tmp_path)
    for category, name in [("terraform", "b-module"), ("ansible", "z-role"), ("ansible", "a-role")]:
        add_template(root, category, name)

    assert run(root) == 0
    first = [(root / f).read_bytes() for f in ("catalog.json", "CATALOG.md")]
    assert run(root) == 0
    second = [(root / f).read_bytes() for f in ("catalog.json", "CATALOG.md")]

    assert first == second
    assert all(b"\r" not in content for content in first)
    paths = [entry["path"] for entry in read_json(root)["templates"]]
    assert paths == ["ansible/a-role", "ansible/z-role", "terraform/b-module"]
    md = read_md(root)
    assert md.count("## ansible") == 1
    assert md.index("## ansible") < md.index("ansible/a-role/") < md.index("ansible/z-role/")
    assert md.index("ansible/z-role/") < md.index("## terraform") < md.index("terraform/b-module/")


def test_key_order_in_template_yaml_does_not_change_the_output(tmp_path):
    root = fixture_root("valid", tmp_path)
    assert run(root) == 0
    expected = (root / "catalog.json").read_bytes()

    meta_path = root / "ansible" / "demo-role" / "template.yaml"
    meta = yaml.safe_load(meta_path.read_text(encoding="utf-8"))
    meta = reverse_keys(meta)
    for key in ("tools", "variables", "practices"):
        meta[key] = [reverse_keys(item) for item in meta[key]]
    meta_path.write_text(yaml.safe_dump(meta, sort_keys=False), encoding="utf-8")

    assert run(root) == 0
    assert (root / "catalog.json").read_bytes() == expected


def test_check_passes_when_the_files_are_current(tmp_path):
    root = fixture_root("valid", tmp_path)
    assert run(root) == 0

    assert run(root, "--check") == 0


def test_check_passes_for_an_empty_library(tmp_path):
    root = empty_root(tmp_path)
    assert run(root) == 0

    assert run(root, "--check") == 0


@pytest.mark.parametrize("filename", ["catalog.json", "CATALOG.md"])
def test_check_fails_when_a_file_was_edited_by_hand(tmp_path, capsys, filename):
    root = fixture_root("valid", tmp_path)
    assert run(root) == 0
    target = root / filename
    target.write_bytes(target.read_bytes().replace(b"Demo role", b"Edited role"))
    capsys.readouterr()

    assert run(root, "--check") == 1

    text = output(capsys)
    assert f"{filename} is out of date" in text
    assert "python tools/catalog.py" in text


@pytest.mark.parametrize("filename", ["catalog.json", "CATALOG.md"])
def test_check_fails_when_a_file_is_missing(tmp_path, capsys, filename):
    root = fixture_root("valid", tmp_path)
    assert run(root) == 0
    (root / filename).unlink()

    assert run(root, "--check") == 1
    assert f"{filename} is out of date" in output(capsys)


def test_check_fails_when_a_template_changed_after_generation(tmp_path):
    root = fixture_root("valid", tmp_path)
    assert run(root) == 0
    meta_path = root / "ansible" / "demo-role" / "template.yaml"
    meta_path.write_text(meta_path.read_text(encoding="utf-8").replace("Demo role", "Renamed role"), encoding="utf-8")

    assert run(root, "--check") == 1


def test_check_never_writes_files(tmp_path):
    root = fixture_root("valid", tmp_path)

    assert run(root, "--check") == 1

    assert not (root / "catalog.json").exists()
    assert not (root / "CATALOG.md").exists()


def test_check_fails_on_an_invalid_template(tmp_path):
    root = fixture_root("schema-violation", tmp_path)

    assert run(root, "--check") == 1


def test_invalid_yaml_is_reported_not_raised(tmp_path, capsys):
    root = empty_root(tmp_path)
    target = add_template(root, "ansible", "demo-role")
    (target / "template.yaml").write_text("name: [demo-role\n", encoding="utf-8")

    assert run(root) == 1

    text = output(capsys)
    assert "ansible/demo-role/template.yaml: invalid YAML" in text


def test_template_needs_a_readme_and_a_files_folder(tmp_path, capsys):
    root = fixture_root("valid", tmp_path)
    template = root / "ansible" / "demo-role"
    (template / "README.md").unlink()
    shutil.rmtree(template / "files")

    assert run(root) == 1

    text = output(capsys)
    assert "ansible/demo-role/template.yaml: README.md is missing" in text
    assert "ansible/demo-role/template.yaml: files/ is missing" in text


@pytest.mark.parametrize("where", ["defaults/missing.yml", "../template.yaml", "defaults"])
def test_variable_where_must_be_a_file_inside_files(tmp_path, capsys, where):
    root = empty_root(tmp_path)
    variable = {"name": "demo_role_port", "default": 8080, "description": "Port.", "where": where}
    add_template(root, "ansible", "demo-role", variables=[variable])

    assert run(root) == 1

    assert f"variables.0.where: {where!r} is not a file in files/" in output(capsys)


def test_practice_ids_and_variable_names_must_be_unique(tmp_path, capsys):
    root = empty_root(tmp_path)
    practice = {"id": "same-id", "rule": "Do it.", "why": "Because."}
    variable = {"name": "demo_role_port", "default": 8080, "description": "Port.", "where": "defaults/main.yml"}
    add_template(root, "ansible", "demo-role", practices=[practice, practice], variables=[variable, variable])

    assert run(root) == 1

    text = output(capsys)
    assert "practices: id 'same-id' is used more than once" in text
    assert "variables: name 'demo_role_port' is used more than once" in text


def test_values_json_cannot_hold_are_reported(tmp_path, capsys):
    root = empty_root(tmp_path)
    target = add_template(root, "ansible", "demo-role")
    meta_path = target / "template.yaml"
    meta_path.write_text(
        meta_path.read_text(encoding="utf-8").replace("default: 8080", "default: 2024-01-31"),
        encoding="utf-8",
    )

    assert run(root) == 1

    assert "variables.0.default: 2024-01-31 cannot be stored in JSON, quote it" in output(capsys)


def test_markdown_cells_escape_pipes_and_line_breaks(tmp_path):
    root = empty_root(tmp_path)
    add_template(root, "ansible", "demo-role", summary="Uses a | b.\n")

    assert run(root) == 0

    assert r"| Uses a \| b. |" in read_md(root)


def test_hidden_folders_are_not_scanned(tmp_path):
    root = empty_root(tmp_path)
    (root / ".github" / "workflows").mkdir(parents=True)
    (root / ".github" / "workflows" / "template.yaml").write_text("not: a template\n", encoding="utf-8")

    assert run(root) == 0
    assert read_json(root) == {"templates": []}


@pytest.mark.parametrize(
    "version, accepted",
    [
        ("2.18.1", True),
        ("v8.30.1", True),
        ("24.04", True),
        ("2.479.3-lts", True),
        ("10.1.34-jdk21-temurin", True),
        ("1.0.0+build.1", True),
        ("latest", False),
        ("stable", False),
        ("^1.2.0", False),
        (">=1.0", False),
        ("~> 1.9", False),
        ("1.x", False),
        ("1.2.*", False),
        ("", False),
    ],
)
def test_tool_versions_must_be_exact(tmp_path, version, accepted):
    root = empty_root(tmp_path)
    add_template(root, "ansible", "demo-role", tools=[{"name": "ansible-core", "version": version}])

    assert (run(root) == 0) is accepted
