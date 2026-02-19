# @trace SPEC-07
"""Spec file reading, requirement extraction, and token counting.

Reads spec files, counts tokens, extracts [SPEC-XX.YY] IDs, and handles
sharding for specs >150K tokens.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path

from tools.shared.token_count import count_tokens

# Pattern matching [SPEC-XX.YY] style IDs
SPEC_ID_PATTERN = re.compile(r"\[SPEC-(\d+)(?:\.(\d+))?\]")


@dataclass
class SpecFile:
    """A spec file with metadata."""

    path: Path
    content: str
    token_count: int
    spec_ids: list[str] = field(default_factory=list)


@dataclass
class SpecBundle:
    """Collection of spec files for decomposition."""

    files: list[SpecFile]
    total_tokens: int
    all_spec_ids: list[str] = field(default_factory=list)
    needs_sharding: bool = False

    @property
    def combined_text(self) -> str:
        """Combine all spec files into a single text."""
        parts: list[str] = []
        for f in self.files:
            parts.append(f"# File: {f.path.name}")
            parts.append(f.content)
            parts.append("")
        return "\n".join(parts)


def _extract_spec_ids(text: str) -> list[str]:
    """Extract all [SPEC-XX.YY] IDs from text."""
    ids: list[str] = []
    for match in SPEC_ID_PATTERN.finditer(text):
        section = match.group(1)
        paragraph = match.group(2)
        spec_id = f"SPEC-{section}"
        if paragraph:
            spec_id += f".{paragraph}"
        if spec_id not in ids:
            ids.append(spec_id)
    return ids


def read_spec_files(paths: list[Path]) -> SpecBundle:
    """Read and analyze spec files.

    Args:
        paths: List of paths to spec files or directories.

    Returns:
        SpecBundle with all files and metadata.
    """
    files: list[SpecFile] = []
    total_tokens = 0
    all_ids: list[str] = []

    for path in paths:
        if path.is_dir():
            # Glob for markdown files
            for md_file in sorted(path.glob("**/*.md")):
                sf = _read_one(md_file)
                files.append(sf)
                total_tokens += sf.token_count
                for sid in sf.spec_ids:
                    if sid not in all_ids:
                        all_ids.append(sid)
        elif path.is_file():
            sf = _read_one(path)
            files.append(sf)
            total_tokens += sf.token_count
            for sid in sf.spec_ids:
                if sid not in all_ids:
                    all_ids.append(sid)

    return SpecBundle(
        files=files,
        total_tokens=total_tokens,
        all_spec_ids=all_ids,
        needs_sharding=total_tokens > 150_000,
    )


@dataclass
class SpecShard:
    """A shard of a large spec for staged processing."""

    index: int
    content: str
    token_count: int
    is_overview: bool = False


def shard_spec(
    spec_text: str,
    max_tokens: int = 150_000,
) -> list[SpecShard]:
    """Split a large spec into processable shards.

    Strategy:
    1. Overview shard: all headers + first N tokens of each section
    2. Cluster shards: full text of sections, grouped to fit budget

    Args:
        spec_text: Full combined spec text.
        max_tokens: Maximum tokens per shard.

    Returns:
        List of SpecShard. Single-element list if spec fits in one shard.
    """
    total = count_tokens(spec_text)
    if total <= max_tokens:
        return [SpecShard(index=0, content=spec_text, token_count=total)]

    # Split by markdown headers (## level)
    sections: list[tuple[str, str]] = []  # (header, content)
    current_header = ""
    current_lines: list[str] = []

    for line in spec_text.split("\n"):
        if line.startswith("## "):
            if current_lines:
                sections.append((current_header, "\n".join(current_lines)))
            current_header = line
            current_lines = [line]
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_header, "\n".join(current_lines)))

    # Overview shard: headers + first 200 tokens of each section
    overview_parts: list[str] = []
    for header, content in sections:
        lines = content.split("\n")
        # Take header + first 10 lines as overview
        overview_parts.append("\n".join(lines[:10]))
    overview_text = "\n\n".join(overview_parts)
    overview_tokens = count_tokens(overview_text)

    shards: list[SpecShard] = [
        SpecShard(index=0, content=overview_text, token_count=overview_tokens, is_overview=True)
    ]

    # Cluster remaining sections into shards
    current_shard_parts: list[str] = []
    current_shard_tokens = 0
    shard_idx = 1

    for _header, content in sections:
        section_tokens = count_tokens(content)
        if current_shard_tokens + section_tokens > max_tokens and current_shard_parts:
            shard_text = "\n\n".join(current_shard_parts)
            shards.append(SpecShard(
                index=shard_idx,
                content=shard_text,
                token_count=current_shard_tokens,
            ))
            shard_idx += 1
            current_shard_parts = []
            current_shard_tokens = 0

        current_shard_parts.append(content)
        current_shard_tokens += section_tokens

    if current_shard_parts:
        shard_text = "\n\n".join(current_shard_parts)
        shards.append(SpecShard(
            index=shard_idx,
            content=shard_text,
            token_count=current_shard_tokens,
        ))

    return shards


def _read_one(path: Path) -> SpecFile:
    """Read a single spec file."""
    try:
        content = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        content = ""

    return SpecFile(
        path=path,
        content=content,
        token_count=count_tokens(content),
        spec_ids=_extract_spec_ids(content),
    )
