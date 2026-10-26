#!/usr/bin/env python3
"""Build and verify a checksum-manifested Zenodo release candidate.

This builds an archival snapshot; it does not publish a Zenodo version.
Frozen scientific results are never recalculated or modified.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PREFIX = "genai-trust-reddit-analysis/"
CONCEPT_DOI = "10.5281/zenodo.23653961"
OUTPUT_NAME = "genai-trust-reddit-analysis_release-candidate.zip"
ROOT_FILES = (
    "README.md", "reproduce.md", "CITATION.cff",
    "LICENSE", "LICENSE-CC-BY-4.0.md", "LICENSE-SCOPE.md",
    "environment.yml", "data/README.md",
)
DIRS = ("scripts", "tests", "results", "figures", "provenance")
OMIT_DIRS = {"__pycache__", ".pytest_cache", ".mypy_cache"}
OMIT_SUFFIXES = {".pyc", ".pyo", ".swp", ".tmp"}


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def revision() -> str:
    if os.getenv("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True,
            stderr=subprocess.DEVNULL).strip()
    except (OSError, subprocess.CalledProcessError):
        return "unavailable"


def contents() -> dict[str, bytes]:
    selected: dict[str, bytes] = {}
    for relative in ROOT_FILES:
        path = ROOT / relative
        if not path.is_file() or path.is_symlink():
            raise ValueError(f"Missing required or unsafe file: {relative}")
        selected[relative] = path.read_bytes()
    for dirname in DIRS:
        directory = ROOT / dirname
        if not directory.is_dir():
            raise ValueError(f"Missing required directory: {dirname}")
        for path in sorted(directory.rglob("*")):
            if path.is_symlink():
                raise ValueError(f"Symlink cannot be archived: {path}")
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            if any(part.startswith(".") or part in OMIT_DIRS for part in path.relative_to(ROOT).parts):
                continue
            if path.suffix.lower() in OMIT_SUFFIXES:
                continue
            selected[rel] = path.read_bytes()

    # A candidate cannot know its future version DOI or publication date.
    # Its embedded citation therefore uses the already-issued concept DOI.
    cff = selected["CITATION.cff"].decode("utf-8")
    cff = re.sub(r'(?m)^(version|date-released|doi|url):[^\n]*\n', '', cff)
    cff = re.sub(
        r'(?m)^message:[^\n]*',
        'message: "For the published release, cite its Zenodo version DOI; this candidate uses the concept DOI."',
        cff, count=1)
    cff = cff.rstrip() + (
        f'\ndoi: "{CONCEPT_DOI}"\n'
        f'url: "https://doi.org/{CONCEPT_DOI}"\n'
    )
    selected["CITATION.cff"] = cff.encode("utf-8")
    return selected


def zip_entry(zf: zipfile.ZipFile, name: str, payload: bytes) -> None:
    # Fixed entry timestamps and permissions make same-content archives stable.
    entry = zipfile.ZipInfo(PREFIX + name, (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o100644 << 16
    zf.writestr(entry, payload, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)


def verify(path: Path) -> int:
    with zipfile.ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)):
            raise ValueError("Duplicate paths in ZIP")
        if archive.testzip() is not None:
            raise ValueError("Corrupt ZIP entry")
        manifest_path = PREFIX + "ARCHIVE_MANIFEST.json"
        manifest = json.loads(archive.read(manifest_path))
        if manifest.get("concept_doi") != CONCEPT_DOI:
            raise ValueError("Incorrect concept DOI")
        files = manifest["files"]
        expected = {PREFIX + rel for rel in files} | {manifest_path}
        if set(names) != expected:
            raise ValueError(f"ZIP inventory mismatch: {set(names) ^ expected}")
        for rel, info in files.items():
            actual = archive.read(PREFIX + rel)
            if len(actual) != info["bytes"] or digest(actual) != info["sha256"]:
                raise ValueError(f"Checksum mismatch: {rel}")
        cff = archive.read(PREFIX + "CITATION.cff").decode("utf-8")
        if f'doi: "{CONCEPT_DOI}"' not in cff or re.search(r'(?m)^version:', cff):
            raise ValueError("Citation metadata asserts an unassigned version")
        for necessary in ("README.md", "reproduce.md", "LICENSE",
                          "LICENSE-CC-BY-4.0.md", "LICENSE-SCOPE.md",
                          "scripts/verify_package.py"):
            if necessary not in files:
                raise ValueError(f"Required archive item missing: {necessary}")
    print(f"PASS: {len(files)} archived files verified against SHA-256 manifest")
    return len(files)


def build(path: Path) -> None:
    files = contents()
    manifest = {
        "schema_version": 1,
        "release_status": "candidate_not_published",
        "source_commit": revision(),
        "concept_doi": CONCEPT_DOI,
        "prior_v2_doi": "10.5281/zenodo.23655847",
        "prior_v3_doi": "10.5281/zenodo.23666151",
        "note": ("This is a validated repository snapshot, not a new scientific "
                 "analysis or a published Zenodo version. See LICENSE-SCOPE.md "
                 "for file-level rights."),
        "files": {name: {"sha256": digest(payload), "bytes": len(payload)}
                  for name, payload in sorted(files.items())},
    }
    archive_manifest = (json.dumps(manifest, indent=2, ensure_ascii=False)
                        + "\n").encode("utf-8")
    with zipfile.ZipFile(path, "w") as archive:
        for name, payload in sorted(files.items()):
            zip_entry(archive, name, payload)
        zip_entry(archive, "ARCHIVE_MANIFEST.json", archive_manifest)
    verify(path)
    print(f"Candidate: {path.name}; SHA-256: {digest(path.read_bytes())}")


if __name__ == "__main__":
    if len(sys.argv) == 3 and sys.argv[1] == "--verify":
        verify(Path(sys.argv[2]))
    elif len(sys.argv) == 1:
        build(ROOT / OUTPUT_NAME)
    else:
        raise SystemExit("Usage: build_zenodo_release.py [--verify archive.zip]")
