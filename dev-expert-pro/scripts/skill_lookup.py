#!/usr/bin/env python3
"""Resolve integrated topics to real local paths and source-section line ranges.

Read-only. No network, credentials, external tools, or execution of helpers.
"""
import argparse
import json
from pathlib import Path, PurePosixPath
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "references/integration-map.json"


def resolve(topic, root=ROOT):
    root = Path(root).absolute()
    registry = json.loads((root / "references/integration-map.json").read_text())
    key = (topic[1:] if topic.startswith("@") else topic).strip()
    entry = registry["topics"].get(key)
    if entry is None:
        raise ValueError("Unknown topic; use --list to see packaged names")
    if not isinstance(entry, dict) or not isinstance(entry.get("path"), str):
        raise ValueError("Invalid topic mapping")
    path = PurePosixPath(entry["path"])
    if path.is_absolute() or ".." in path.parts or "\\" in entry["path"]:
        raise ValueError("Unsafe registry path")
    target = root.joinpath(*path.parts)
    for parent in [target, *target.parents]:
        if parent == root.parent:
            break
        if parent.is_symlink():
            raise ValueError("Linked bundle input is unsupported")
    if not target.is_file():
        raise ValueError("Mapped reference is missing; check the installed bundle")
    lines = target.read_text(encoding="utf-8").splitlines()
    anchor = entry.get("anchor")
    if anchor is not None and not isinstance(anchor, str):
        raise ValueError("Invalid source anchor")
    first, last = 1, len(lines)
    if anchor:
        marker = '<a id="' + anchor + '"></a>'
        positions = [i for i, line in enumerate(lines) if line.strip() == marker]
        if len(positions) != 1:
            raise ValueError("Mapped source anchor is absent or ambiguous")
        start = positions[0]
        first = start + 1
        for i in range(start + 1, len(lines)):
            if re.fullmatch(r'<a id="source-[0-9a-f]+"></a>', lines[i].strip()):
                last = i
                break
    return {"topic": key, "path": str(target.absolute()), "relative_path": path.as_posix(),
            "anchor": anchor, "start_line": first, "end_line": last,
            "line_count": last - first + 1, "operation": "read_reference"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic", nargs="?", help="Topic name, @alias or CloudBase source ID")
    parser.add_argument("--list", action="store_true", help="List all package topic IDs")
    args = parser.parse_args()
    try:
        if args.list:
            value = json.loads(REGISTRY.read_text())
            output = {"topics": sorted(value["topics"]), "operation": "list_references"}
        elif args.topic:
            output = resolve(args.topic)
        else:
            parser.error("Provide a topic or --list")
        print(json.dumps(output, ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, json.JSONDecodeError):
        print(json.dumps({"ok": False, "error": "Reference lookup failed; check the topic and installed bundle"}))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
