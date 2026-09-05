"""Refresh the shipped Python signatures from the public implementation.

Run ``uv run python tools/generate_python_reference.py [--check]``.
"""

from __future__ import annotations

import argparse
import ast
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_TARGET = _ROOT / "src/yoghurt/skills/content/dataframes/README.md"
_START = "<!-- BEGIN GENERATED PYTHON REFERENCE -->"
_END = "<!-- END GENERATED PYTHON REFERENCE -->"


def _render_reference() -> str:
    lines = [
        _START,
        "",
        "Signatures and return types generated from the implementation.",
        "",
    ]
    for filename in ("api.py", "_core.py"):
        tree = ast.parse((_ROOT / "src/yoghurt" / filename).read_text(encoding="utf-8"))
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == "Ticker":
                lines.extend(
                    [
                        "### Ticker methods",
                        "",
                        (
                            "Create `yoghurt.Ticker(symbol)`; "
                            "construction performs no request."
                        ),
                        "",
                    ]
                )
                methods = [
                    item
                    for item in node.body
                    if isinstance(item, ast.FunctionDef)
                    and not item.name.startswith("_")
                ]
                prefix = "Ticker."
            elif (
                isinstance(node, ast.FunctionDef)
                and not node.name.startswith("_")
                and (filename == "api.py" or node.name == "configure")
            ):
                methods = [node]
                prefix = "yoghurt."
            else:
                continue
            for method in methods:
                args = method.args
                args.args = [arg for arg in args.args if arg.arg != "self"]
                signature = f"{prefix}{method.name}({ast.unparse(args)})"
                if method.returns:
                    signature += f" -> {ast.unparse(method.returns)}"
                summary = (
                    (ast.get_docstring(method) or "")
                    .split("\n\n")[0]
                    .replace("\n", " ")
                )
                lines.extend([f"`{signature}`", "", summary, ""])
    return "\n".join([*lines, _END])


def _main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = _TARGET.read_text(encoding="utf-8")
    before, marker, rest = text.partition(_START)
    after = rest.partition(_END)[2] if marker else "\n"
    updated = before + _render_reference() + after
    if args.check:
        if updated != text:
            parser.exit(1, "Python reference is stale; run the generator.\n")
    else:
        _TARGET.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    _main()
