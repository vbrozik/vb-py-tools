#!/usr/bin/env python3

"""Extract SecureCRT sessions from a given XML file, write them as a CSV file.

Parses SecureCRT XML session definitions and outputs a CSV with columns:
name,address,port,protocol.
"""

# /// script
# requires-python = ">=3.10"
# dependencies = []
# [tool.ruff]
# line-length = 100
# ///

from __future__ import annotations

import argparse
import csv
import sys
import xml.etree.ElementTree as ET
from typing import Any, Iterator


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        argparse.Namespace: Parsed arguments with input and output file paths.
    """
    parser = argparse.ArgumentParser(
        description="Extract SecureCRT sessions from XML and write to CSV."
    )
    parser.add_argument(
        "xml_file",
        nargs="?",
        default="-",
        help="Input SecureCRT XML file (default: stdin, use '-' for stdin)",
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default="-",
        help="Output CSV file (default: stdout, use '-' for stdout)",
    )
    return parser.parse_args()


def find_sessions_root(root: ET.Element) -> ET.Element | None:
    """Find the <key name="Sessions"> element in the XML tree.

    Args:
        root (ET.Element): Root element of the XML tree.

    Returns:
        ET.Element | None: The Sessions element or None if not found.
    """
    for key in root.findall(".//key"):
        if key.attrib.get("name") == "Sessions":
            return key
    return None


def iter_sessions(
    node: ET.Element, path: list[str]
) -> Iterator[dict[str, Any]]:
    """Recursively traverse session nodes and yield session info dicts.

    Args:
        node (ET.Element): Current XML node.
        path (list[str]): List of key names leading to this node.

    Yields:
        dict[str, Any]: Session info with name, address, port, protocol.
    """
    # If this node has children <key>, recurse
    keys = [child for child in node.findall("key")]
    if keys:
        for child in keys:
            child_name = child.attrib.get("name", "")
            yield from iter_sessions(child, path + [child_name])
    else:
        # Only consider nodes that have Hostname or Protocol Name
        hostname = None
        port = None
        protocol = None
        for child in node:
            if child.tag == "string" and child.attrib.get("name") == "Hostname":
                hostname = child.text or ""
            elif child.tag == "dword" and child.attrib.get("name") == "[SSH2] Port":
                port = child.text or ""
            elif child.tag == "string" and child.attrib.get("name") == "Protocol Name":
                protocol = child.text or ""
        if hostname:
            session_name = "/".join(path)
            yield {
                "name": session_name,
                "address": hostname,
                "port": port or "22",
                "protocol": protocol or "SSH2",
            }


def main() -> None:
    """Main entry point for the script."""
    args = parse_args()
    # Unified XML input handling
    xml_source = sys.stdin if args.xml_file == "-" else args.xml_file
    try:
        tree = ET.parse(xml_source)
    except Exception as exc:
        src = "stdin" if args.xml_file == "-" else args.xml_file
        print(f"Error parsing XML from {src}: {exc}", file=sys.stderr)
        sys.exit(1)
    root = tree.getroot()
    sessions_root = find_sessions_root(root)
    if sessions_root is None:
        print("Could not find Sessions node in XML.", file=sys.stderr)
        sys.exit(1)
    sessions = list(iter_sessions(sessions_root, []))
    # Write CSV output
    csv_dest = (
            sys.stdout if args.csv_file == "-"
            else open(args.csv_file, "w", newline="", encoding="utf-8"))
    try:
        writer = csv.DictWriter(csv_dest, fieldnames=["name", "address", "port", "protocol"])
        writer.writeheader()
        for session in sessions:
            writer.writerow(session)
    finally:
        if csv_dest is not sys.stdout:
            csv_dest.close()


if __name__ == "__main__":
    main()
