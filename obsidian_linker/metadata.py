import os
import re
from typing import Dict, List, Optional, Set, Tuple

from obsidian_linker.constants import FIRST_H1_PATTERN, METADATA_PATTERN
from obsidian_linker.models import LinkPhrase


def strip_yaml_scalar(value: str) -> str:
    value = value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in ('"', "'"):
        return value[1:-1]
    return value


def front_matter_inner(metadata: str) -> str:
    inner = metadata.strip()
    if inner.startswith('---'):
        inner = inner[3:]
    if inner.endswith('---'):
        inner = inner[:-3]
    return inner.strip('\n')


def parse_aliases_from_front_matter(metadata: str) -> List[str]:
    if not metadata:
        return []

    aliases: List[str] = []
    lines = front_matter_inner(metadata).splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        alias_match = re.match(r'^alias:\s*(.+)$', line)
        if alias_match:
            aliases.append(strip_yaml_scalar(alias_match.group(1)))
            i += 1
            continue

        inline_match = re.match(r'^aliases:\s*\[(.*)\]\s*$', line)
        if inline_match:
            for part in inline_match.group(1).split(','):
                if part.strip():
                    aliases.append(strip_yaml_scalar(part))
            i += 1
            continue

        if re.match(r'^aliases:\s*$', line):
            i += 1
            while i < len(lines) and re.match(r'^\s+-\s+', lines[i]):
                aliases.append(strip_yaml_scalar(lines[i].split('-', 1)[1]))
                i += 1
            continue

        i += 1

    return aliases


def parse_first_h1(content: str) -> Optional[str]:
    match = FIRST_H1_PATTERN.search(content)
    return match.group(1).strip() if match else None


def note_canonical_title(file_path: str) -> str:
    return os.path.splitext(os.path.basename(file_path))[0]


def format_wikilink(canonical: str, matched: str) -> str:
    if matched.casefold() == canonical.casefold():
        return f'[[{matched}]]'
    return f'[[{canonical}|{matched}]]'


def phrase_is_ignored(phrase: str, ignore_phrases: Set[str], min_title_length: int) -> bool:
    if not phrase.strip():
        return True
    if len(phrase.strip()) < min_title_length:
        return True
    return phrase.strip().lower() in ignore_phrases


def register_phrase(
    phrase_map: Dict[str, LinkPhrase],
    warnings: List[str],
    phrase: str,
    canonical: str,
    source_file: str,
    *,
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
) -> None:
    ignore_phrases = ignore_phrases or set()
    if phrase_is_ignored(phrase, ignore_phrases, min_title_length):
        return

    key = phrase.lower()
    new_entry = LinkPhrase(phrase=phrase, canonical=canonical, source_file=source_file)
    existing = phrase_map.get(key)
    if existing is None:
        phrase_map[key] = new_entry
        return

    if existing.source_file == source_file and existing.canonical == canonical:
        return

    warnings.append(
        f"Duplicate link phrase '{phrase}' for notes "
        f"'{existing.canonical}' ({existing.source_file}) and "
        f"'{canonical}' ({source_file}); using '{canonical}'."
    )
    if len(source_file) >= len(existing.source_file):
        phrase_map[key] = new_entry


def build_link_phrases(
    markdown_files: List[str],
    file_contents: Dict[str, str],
    *,
    use_aliases: bool = True,
    use_headings: bool = False,
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
) -> Tuple[List[LinkPhrase], List[str]]:
    ignore_phrases = ignore_phrases or set()
    warnings: List[str] = []
    phrase_map: Dict[str, LinkPhrase] = {}

    by_title_lower: Dict[str, List[str]] = {}
    for file in markdown_files:
        title_lower = note_canonical_title(file).lower()
        by_title_lower.setdefault(title_lower, []).append(file)

    basename_winners: Dict[str, str] = {}
    for title_lower, paths in by_title_lower.items():
        winner = max(paths, key=len)
        basename_winners[title_lower] = winner
        if len(paths) > 1:
            paths_display = ', '.join(sorted(paths))
            warnings.append(
                f"Duplicate note title '{note_canonical_title(winner)}': {paths_display}; "
                f"using '{winner}' as the link target."
            )

    for file in markdown_files:
        canonical = note_canonical_title(file)
        title_lower = canonical.lower()
        if basename_winners.get(title_lower) == file:
            register_phrase(
                phrase_map,
                warnings,
                canonical,
                canonical,
                file,
                ignore_phrases=ignore_phrases,
                min_title_length=min_title_length,
            )

        metadata_match = METADATA_PATTERN.search(file_contents[file])
        metadata = metadata_match.group(0) if metadata_match else ''
        body = file_contents[file]
        if metadata:
            body = body.replace(metadata, '', 1)

        if use_aliases:
            for alias in parse_aliases_from_front_matter(metadata):
                register_phrase(
                    phrase_map,
                    warnings,
                    alias,
                    canonical,
                    file,
                    ignore_phrases=ignore_phrases,
                    min_title_length=min_title_length,
                )

        if use_headings:
            heading = parse_first_h1(body)
            if heading:
                register_phrase(
                    phrase_map,
                    warnings,
                    heading,
                    canonical,
                    file,
                    ignore_phrases=ignore_phrases,
                    min_title_length=min_title_length,
                )

    phrases = sorted(phrase_map.values(), key=lambda item: len(item.phrase_lower), reverse=True)
    return phrases, warnings


def extract_metadata(content: str):
    metadata_match = METADATA_PATTERN.search(content)
    if metadata_match:
        metadata = metadata_match.group(0)
        content = content.replace(metadata, '', 1)
        return metadata, content
    return '', content
