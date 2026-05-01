#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Author: Giustino C. Miglionico
License: MIT
"""

import csv
import json
import os
import re
from collections.abc import Iterable
from pathlib import Path
from graphviz import Digraph

class FuzzyTreePlotter:
    def __init__(self, rules, aggregate=False, text_size=12, line_width=1, edge_text_size=12, theme="balanced", outcome_colors=None):
        """
        Class for building and visualizing a fuzzy decision tree from fuzzy rules.
        Accepts either a list of rules or a path to a .txt file (one rule per line).
        """
        self.rules = self._load_rules(rules)
        self.aggregate = aggregate
        self.text_size = text_size
        self.line_width = line_width
        self.edge_text_size = edge_text_size
        self.theme = theme
        self.outcome_colors = outcome_colors or {}
        self.validation_report = self.validate_rules()
        if self.validation_report["syntax_errors"]:
            messages = [f'line {item["line"]}: {item["error"]} -> {item["rule"]}' for item in self.validation_report["syntax_errors"]]
            raise ValueError("Invalid rules found:\n" + "\n".join(messages))
        if self.validation_report["conflicts"]:
            print(f"[WARNING] Found {len(self.validation_report['conflicts'])} conflicting rule(s).")
        self.tree = self._build_tree()
        self.counter = 0
        self.dot = self._build_graphviz_tree()

    def _load_rules(self, source):
        """Loads rules from an iterable or from a text file."""
        if isinstance(source, os.PathLike):
            source = os.fspath(source)

        if isinstance(source, str) and os.path.isfile(source):
            path = Path(source)
            suffix = path.suffix.lower()

            if suffix == ".json":
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        payload = json.load(f)
                except Exception as e:
                    print(f"[WARNING] Failed to open rules file: {source}\n  → {e}")
                    return []

                if isinstance(payload, dict):
                    for key in ("rules", "data", "items"):
                        if key in payload:
                            payload = payload[key]
                            break

                if not isinstance(payload, list):
                    raise ValueError("JSON rules files must contain a list of rule strings or an object with a 'rules' list.")

                return self._normalize_rule_iterable(payload)

            if suffix == ".csv":
                try:
                    with open(path, "r", encoding="utf-8", newline="") as f:
                        reader = csv.reader(f)
                        lines = []
                        header_skipped = False
                        for row in reader:
                            if not row:
                                continue
                            first_cell = row[0].strip()
                            if not header_skipped and first_cell.lower() in {"rule", "rules"}:
                                header_skipped = True
                                continue
                            if not first_cell or first_cell.startswith("#"):
                                continue
                            lines.append(first_cell)
                except Exception as e:
                    print(f"[WARNING] Failed to open rules file: {source}\n  → {e}")
                    return []

                if not lines:
                    print(f"[WARNING] Rules file '{source}' is empty or contains only blank lines.")

                return lines

            try:
                with open(path, "r", encoding="utf-8") as f:
                    lines = []
                    for line in f:
                        stripped = line.strip()
                        if not stripped or stripped.startswith("#"):
                            continue
                        lines.append(stripped)
            except Exception as e:
                print(f"[WARNING] Failed to open rules file: {source}\n  → {e}")
                return []

            if not lines:
                print(f"[WARNING] Rules file '{source}' is empty or contains only blank lines.")

            return lines

        if isinstance(source, Iterable) and not isinstance(source, (str, bytes)):
            return self._normalize_rule_iterable(source)

        else:
            raise ValueError("The 'rules' parameter must be an iterable of strings or a valid path to a .txt, .csv, or .json file.")

    def _normalize_rule_iterable(self, source):
        """Normalizes an iterable of rule strings."""
        lines = []
        for item in source:
            if not isinstance(item, str):
                raise TypeError("Iterable rules must contain only strings.")
            stripped = item.strip()
            if stripped and not stripped.startswith("#"):
                lines.append(stripped)
        return lines


    def _parse_rule(self, rule):
        """Parses a fuzzy rule and returns a tuple (conditions, outcome)."""
        rule = rule.strip()
        rule = re.sub(r"(?i)^if\s+", "", rule)
        parts = re.split(r"(?i)\s+then\s+", rule)

        if len(parts) != 2:
            raise ValueError("Invalid rule format (missing 'then'): " + rule)

        conditions_part, outcome_part = parts
        outcome = outcome_part.strip()
        raw_conditions = re.split(r"(?i)\s+and\s+", conditions_part.strip())
        conditions = []
        for cond in raw_conditions:
            cond_parts = re.split(r"(?i)\s+is\s+", cond.strip())
            if len(cond_parts) != 2:
                raise ValueError("Malformed condition: " + cond)
            attr, value = cond_parts
            conditions.append((attr.strip(), value.strip()))

        return conditions, outcome

    def _conditions_key(self, conditions):
        """Builds a stable key for a rule's condition set."""
        return tuple(sorted((attr.strip().lower(), value.strip().lower()) for attr, value in conditions))

    def validate_rules(self):
        """Validates rules, collecting syntax issues, duplicates, and conflicts."""
        report = {
            "total_rules": len(self.rules),
            "valid_rules": 0,
            "syntax_errors": [],
            "duplicate_rules": [],
            "conflicts": [],
        }
        seen = {}

        for line_number, rule in enumerate(self.rules, start=1):
            try:
                conditions, outcome = self._parse_rule(rule)
            except ValueError as exc:
                report["syntax_errors"].append({"line": line_number, "rule": rule, "error": str(exc)})
                continue

            report["valid_rules"] += 1
            key = self._conditions_key(conditions)

            if key in seen:
                previous = seen[key]
                if previous["outcome"] == outcome:
                    report["duplicate_rules"].append(
                        {
                            "line": line_number,
                            "rule": rule,
                            "duplicate_of_line": previous["line"],
                        }
                    )
                else:
                    report["conflicts"].append(
                        {
                            "line": line_number,
                            "rule": rule,
                            "conflicts_with_line": previous["line"],
                            "previous_outcome": previous["outcome"],
                            "current_outcome": outcome,
                        }
                    )
            else:
                seen[key] = {"line": line_number, "outcome": outcome, "rule": rule}

        return report

    def detect_conflicts(self):
        """Returns only the conflicting rules detected during validation."""
        return list(self.validation_report["conflicts"])

    def _insert_into_tree(self, tree, conditions, outcome):
        """Inserts a rule into the tree structure."""
        if not conditions:
            tree['_leaf'] = outcome
            return
        attr, value = conditions[0]
        if attr not in tree:
            tree[attr] = {}
        if value not in tree[attr]:
            tree[attr][value] = {}
        self._insert_into_tree(tree[attr][value], conditions[1:], outcome)

    def _build_tree(self):
        """Builds the tree structure from rules."""
        tree = {}
        for rule in self.rules:
            conditions, outcome = self._parse_rule(rule)
            self._insert_into_tree(tree, conditions, outcome)
        return tree

    def _theme_settings(self):
        """Returns graph styling settings for the selected theme."""
        themes = {
            "balanced": {
                "graph": {"rankdir": "TB", "splines": "spline", "nodesep": "0.35", "ranksep": "0.55", "pad": "0.25"},
                "node": {"shape": "ellipse", "style": "filled", "fillcolor": "#EAF2FF", "color": "#4E79A7", "fontname": "Helvetica"},
                "leaf": {"shape": "box", "style": "rounded,filled", "color": "#3E5C76", "fontname": "Helvetica"},
                "edge": {"color": "#6B7280"},
            },
            "compact": {
                "graph": {"rankdir": "TB", "splines": "spline", "nodesep": "0.20", "ranksep": "0.35", "pad": "0.12"},
                "node": {"shape": "ellipse", "style": "filled", "fillcolor": "#F4F7FB", "color": "#607D8B", "fontname": "Helvetica"},
                "leaf": {"shape": "box", "style": "rounded,filled", "color": "#455A64", "fontname": "Helvetica"},
                "edge": {"color": "#607D8B"},
            },
            "presentation": {
                "graph": {"rankdir": "TB", "splines": "spline", "nodesep": "0.55", "ranksep": "0.80", "pad": "0.35"},
                "node": {"shape": "ellipse", "style": "filled", "fillcolor": "#FFF8E8", "color": "#C07A00", "fontname": "Helvetica"},
                "leaf": {"shape": "box", "style": "rounded,filled", "color": "#8A5A00", "fontname": "Helvetica"},
                "edge": {"color": "#B08900"},
            },
        }

        return themes.get(self.theme, themes["balanced"])

    def _outcome_color(self, outcome):
        """Returns the fill color for a leaf outcome."""
        if outcome in self.outcome_colors:
            return self.outcome_colors[outcome]

        palette = [
            "#D9EAF7",
            "#E8F5E9",
            "#FFF3E0",
            "#F3E5F5",
            "#FCE4EC",
            "#E0F7FA",
            "#FFFDE7",
        ]
        index = abs(hash(outcome)) % len(palette)
        return palette[index]

    def summary(self):
        """Returns a compact summary of the generated tree."""
        stats = {
            "rules": len(self.rules),
            "internal_nodes": 0,
            "leaf_nodes": 0,
            "max_depth": 0,
            "attributes": set(),
            "outcomes": set(),
        }

        def walk(node, depth):
            stats["max_depth"] = max(stats["max_depth"], depth)

            if '_leaf' in node and len(node) == 1:
                stats["leaf_nodes"] += 1
                stats["outcomes"].add(node['_leaf'])
                return

            for attr, subtrees in node.items():
                if attr == '_leaf':
                    continue
                stats["internal_nodes"] += 1
                stats["attributes"].add(attr)
                for subtree in subtrees.values():
                    walk(subtree, depth + 1)

        walk(self.tree, 0)
        stats["attributes"] = sorted(stats["attributes"])
        stats["outcomes"] = sorted(stats["outcomes"])
        return stats

    def _traverse_tree(self, dot, tree, parent_id=None, edge_label=""):
        """Creates the Graphviz graph based on the tree structure."""
        leaves = []
        if '_leaf' in tree and len(tree) == 1:
            leaf_id = f"leaf_{self.counter}"
            self.counter += 1
            leaf_style = self._theme_settings()["leaf"].copy()
            leaf_style["fillcolor"] = self._outcome_color(tree['_leaf'])
            dot.node(leaf_id, tree['_leaf'], **leaf_style)
            if parent_id:
                dot.edge(parent_id, leaf_id, label=edge_label)
            return [leaf_id]

        for attr, subtrees in tree.items():
            if attr == '_leaf':
                continue
            node_id = f"node_{self.counter}"
            self.counter += 1
            dot.node(node_id, attr, **self._theme_settings()["node"])
            if parent_id:
                dot.edge(parent_id, node_id, label=edge_label)

            aggregated_leaves = {}
            for val, subtree in subtrees.items():
                if self.aggregate and '_leaf' in subtree and len(subtree) == 1:
                    outcome = subtree['_leaf']
                    if outcome in aggregated_leaves:
                        dot.edge(node_id, aggregated_leaves[outcome], label=val)
                    else:
                        leaf_id = f"leaf_{self.counter}"
                        self.counter += 1
                        dot.node(leaf_id, outcome, shape="box")
                        dot.edge(node_id, leaf_id, label=val)
                        aggregated_leaves[outcome] = leaf_id
                        leaves.append(leaf_id)
                else:
                    child_leaves = self._traverse_tree(dot, subtree, node_id, val)
                    leaves.extend(child_leaves)
        return leaves

    def _build_graphviz_tree(self):
        """Creates the Graphviz graph for fuzzy tree visualization."""
        theme_settings = self._theme_settings()
        dot = Digraph(comment="Fuzzy Decision Tree", graph_attr=theme_settings["graph"])
        dot.node_attr.update(fontsize=str(self.text_size))
        dot.edge_attr.update(penwidth=str(self.line_width), fontsize=str(self.edge_text_size), **theme_settings["edge"])

        self.counter = 0  # Reset counter before traversal
        leaf_ids = self._traverse_tree(dot, self.tree)

        with dot.subgraph() as s:
            s.attr(rank='same')
            for lid in leaf_ids:
                s.node(lid)

        return dot

    def render(self, filename="fuzzy_tree", format="png", view=True, cleanup_source=True):
        """
        Renders the fuzzy tree image and optionally removes the Graphviz source file.
        """
        output_path = self.dot.render(filename, format=format, view=view, cleanup=cleanup_source)

        return output_path
