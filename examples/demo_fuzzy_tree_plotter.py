#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Giustino C. Miglionico
License: MIT

This demo exercises the public API end to end:
- rule loading from Python lists
- rule loading from TXT, CSV, and JSON files
- validation, duplicate detection, and conflict detection
- graph styling profiles and custom outcome colors
- rendering with and without Graphviz source cleanup
"""

import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fuzzy_tree_plotter import FuzzyTreePlotter


BASE_RULES = [
    "if F2 is L and F8 is L and F7 is L then 3",
    "if F2 is L and F8 is L and F7 is M then 3",
    "if F2 is L and F8 is L and F7 is H then 1",
    "if F2 is L and F8 is M and F7 is L then 2",
    "if F2 is L and F8 is M and F7 is M then 1",
    "if F2 is L and F8 is M and F7 is H then 3",
    "if F2 is M and F8 is L and F7 is L then 2",
    "if F2 is M and F8 is L and F7 is M then 3",
    "if F2 is M and F8 is L and F7 is H then 1",
    "if F2 is M and F8 is M and F7 is L then 3",
    "if F2 is M and F8 is M and F7 is M then 1",
    "if F2 is M and F8 is M and F7 is H then 2",
    "if F2 is H and F8 is L and F7 is L then 3",
    "if F2 is H and F8 is L and F7 is M then 2",
    "if F2 is H and F8 is L and F7 is H then 1",
    "if F2 is H and F8 is M and F7 is L then 1",
    "if F2 is H and F8 is M and F7 is M then 2",
    "if F2 is H and F8 is M and F7 is H then 3",
    "if F2 is H and F8 is H and F7 is L then 2",
    "if F2 is H and F8 is H and F7 is M then 3",
    "if F2 is H and F8 is H and F7 is H then 1",
]


def print_section(title):
    """Print a clear divider so each demo block is easy to scan."""
    print("\n" + "=" * 88)
    print(title)
    print("=" * 88)


def write_text_rules_file(folder, rules):
    """Create a TXT file with comments and blank lines to exercise text loading."""
    path = folder / "rules_sample.txt"
    content = ["# Example rules file", "", *rules]
    path.write_text("\n".join(content), encoding="utf-8")
    return path


def write_csv_rules_file(folder, rules):
    """Create a CSV file where the first column contains the rule text."""
    path = folder / "rules_sample.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["rule"])
        for rule in rules:
            writer.writerow([rule])
    return path


def write_json_rules_file(folder, rules):
    """Create a JSON file using the supported {\"rules\": [...]} structure."""
    path = folder / "rules_sample.json"
    payload = {
        "rules": rules,
        "meta": {
            "source": "demo",
            "format": "json",
        },
    }
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return path


def show_validation_and_conflicts():
    """Demonstrate validation, duplicate detection, and conflict detection."""
    print_section("Validation, duplicates, and conflicts")

    rules_with_duplicates = [
        "if F1 is A then 1",
        "if F1 is A then 1",
        "if F1 is A then 2",
        "if F2 is B then 3",
    ]

    plotter = FuzzyTreePlotter(rules_with_duplicates, aggregate=True)
    print(json.dumps(plotter.validate_rules(), indent=2))
    print("Conflicts:")
    print(json.dumps(plotter.detect_conflicts(), indent=2))


def show_invalid_syntax_handling():
    """Demonstrate that invalid syntax is rejected with a clear error."""
    print_section("Invalid syntax handling")

    invalid_rules = [
        "if F1 is A then 1",
        "if F2 equals B then 2",
    ]

    try:
        FuzzyTreePlotter(invalid_rules)
    except ValueError as exc:
        print("Caught expected validation error:")
        print(exc)


def render_from_list(output_folder):
    """Render a tree from an in-memory list using a presentation theme."""
    print_section("Rendering from a Python list")

    plotter = FuzzyTreePlotter(
        BASE_RULES,
        aggregate=True,
        text_size=20,
        line_width=2,
        edge_text_size=18,
        theme="presentation",
        outcome_colors={"1": "#FAD7A0", "2": "#AED6F1", "3": "#A9DFBF"},
    )

    print(json.dumps(plotter.summary(), indent=2))
    print("Conflicts in base rules:", json.dumps(plotter.detect_conflicts(), indent=2))
    plotter.render(output_folder / "fuzzy_tree_from_list", format="png", view=False, cleanup_source=False)


def render_from_text_file(output_folder):
    """Render a tree from a TXT file and keep the default source cleanup behavior."""
    print_section("Rendering from a TXT file")

    text_path = write_text_rules_file(output_folder, BASE_RULES)
    plotter = FuzzyTreePlotter(text_path, aggregate=True, theme="balanced")

    print(json.dumps(plotter.summary(), indent=2))
    plotter.render(output_folder / "fuzzy_tree_from_text", format="png", view=False)


def render_from_csv_file(output_folder):
    """Render a tree from a CSV file."""
    print_section("Rendering from a CSV file")

    csv_path = write_csv_rules_file(output_folder, BASE_RULES)
    plotter = FuzzyTreePlotter(csv_path, aggregate=True, theme="compact")

    print(json.dumps(plotter.summary(), indent=2))
    plotter.render(output_folder / "fuzzy_tree_from_csv", format="png", view=False)


def render_from_json_file(output_folder):
    """Render a tree from a JSON file."""
    print_section("Rendering from a JSON file")

    json_path = write_json_rules_file(output_folder, BASE_RULES)
    plotter = FuzzyTreePlotter(json_path, aggregate=True, theme="balanced")

    print(json.dumps(plotter.summary(), indent=2))
    plotter.render(output_folder / "fuzzy_tree_from_json", format="png", view=False)


def main():
    """Run all demo scenarios and keep the generated files locally."""
    output_folder = Path(__file__).resolve().parent / "demo_outputs"
    output_folder.mkdir(exist_ok=True)

    # Exercise validation before rendering so the output shows how the parser
    # handles duplicates, conflicts, and syntax errors.
    show_validation_and_conflicts()
    show_invalid_syntax_handling()

    # Exercise all supported sources with the same logical rule set.
    # The generated files remain in demo_outputs/ so the user can inspect them
    # after the script ends.
    render_from_list(output_folder)
    render_from_text_file(output_folder)
    render_from_csv_file(output_folder)
    render_from_json_file(output_folder)

    # This message makes it obvious that the demo finished successfully.
    print_section("Demo completed")
    print(f"Generated files were kept in: {output_folder}")


if __name__ == "__main__":
    main()
