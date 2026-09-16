import argparse
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from tqdm import tqdm

CODE_BLOCK_PLACEHOLDER = "<CODE_BLOCK_{}>"
METADATA_PLACEHOLDER = "<METADATA_SECTION>"
INLINE_CODE_PLACEHOLDER = "<INLINE_CODE_{}>"
EMBED_PLACEHOLDER = "<EMBED_{}>"
MARKDOWN_LINK_PLACEHOLDER = "<MD_LINK_{}>"
HEADING_LINE_PLACEHOLDER = "<HEADING_LINE_{}>"

CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.DOTALL | re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r'`[^`]*`')
EMBED_PATTERN = re.compile(r'!\[\[(?:[^\]|]+\|)?[^\]]+\]\]')
MARKDOWN_LINK_PATTERN = re.compile(r'\[[^\]]+\]\([^)]+\)')
EXISTING_LINKS_PATTERN = re.compile(r'(?<!!)\[\[(?:[^\]|]+\|)?[^\]]+\]\]')
METADATA_PATTERN = re.compile(r'---\s*\n([\s\S]*?)\n\s*---', re.MULTILINE)
HEADING_LINE_PATTERN = re.compile(r'^(\s{0,3}#{1,6}\s.+)$', re.MULTILINE)
FIRST_H1_PATTERN = re.compile(r'^#\s+(.+?)\s*$', re.MULTILINE)

DEFAULT_EXCLUDE_DIR_NAMES = frozenset({
    '.obsidian',
    '.git',
    '.trash',
    'node_modules',
    'attachments',
    'Attachments',
    'assets',
    'Assets',
    'files',
    'images',
    'img',
    'media',
    'resources',
})


@dataclass
class NoteTarget:
    canonical: str
    source_file: str


@dataclass
class LinkPhrase:
    phrase: str
    canonical: str
    source_file: str

    @property
    def phrase_lower(self) -> str:
        return self.phrase.lower()


@dataclass
class LinkChange:
    file: str
    line: int
    matched_text: str
    wikilink: str


@dataclass
class LinkResult:
    edited_files: Set[str] = field(default_factory=set)
    total_links_added: int = 0
    changes: list = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def resolve_exclude_dir_names(
    use_default_excludes: bool,
    extra_excludes: Optional[Iterable[str]] = None,
) -> Set[str]:
    names: Set[str] = set()
    if use_default_excludes:
        names.update(DEFAULT_EXCLUDE_DIR_NAMES)
    if extra_excludes:
        names.update(extra_excludes)
    return names


def find_markdown_files(
    directory: str,
    *,
    exclude_dir_names: Optional[Set[str]] = None,
    use_default_excludes: bool = True,
    extra_excludes: Optional[Iterable[str]] = None,
) -> list:
    if exclude_dir_names is None:
        exclude_dir_names = resolve_exclude_dir_names(use_default_excludes, extra_excludes)

    markdown_files = []
    print(f"Searching for markdown files in directory: {directory}")
    for root, dirs, files in os.walk(directory):
        dirs[:] = [d for d in dirs if d not in exclude_dir_names]
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    print(f"Found {len(markdown_files)} markdown files.")
    return markdown_files


def read_files(markdown_files, show_progress: bool = True):
    file_contents = {}
    if show_progress:
        read_pbar = tqdm(total=len(markdown_files), desc="Reading files")
    for file in markdown_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                file_contents[file] = f.read()
        except UnicodeDecodeError:
            print(f"Error reading file {file} with UTF-8 encoding.")
        if show_progress:
            read_pbar.update(1)
    if show_progress:
        read_pbar.close()
    return file_contents


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


def register_phrase(
    phrase_map: Dict[str, LinkPhrase],
    warnings: List[str],
    phrase: str,
    canonical: str,
    source_file: str,
) -> None:
    if not phrase.strip():
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
) -> Tuple[List[LinkPhrase], List[str]]:
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
            register_phrase(phrase_map, warnings, canonical, canonical, file)

        metadata_match = METADATA_PATTERN.search(file_contents[file])
        metadata = metadata_match.group(0) if metadata_match else ''
        body = file_contents[file]
        if metadata:
            body = body.replace(metadata, '', 1)

        if use_aliases:
            for alias in parse_aliases_from_front_matter(metadata):
                register_phrase(phrase_map, warnings, alias, canonical, file)

        if use_headings:
            heading = parse_first_h1(body)
            if heading:
                register_phrase(phrase_map, warnings, heading, canonical, file)

    phrases = sorted(phrase_map.values(), key=lambda item: len(item.phrase_lower), reverse=True)
    return phrases, warnings


def extract_metadata(content):
    metadata_match = METADATA_PATTERN.search(content)
    if metadata_match:
        metadata = metadata_match.group(0)
        content = content.replace(metadata, '', 1)
        return metadata, content
    return '', content


def protect_regions(content: str, skip_headings: bool) -> Tuple[str, dict, dict, dict, dict, dict]:
    code_blocks = CODE_BLOCK_PATTERN.findall(content)
    code_block_map = {CODE_BLOCK_PLACEHOLDER.format(i): block for i, block in enumerate(code_blocks)}
    for placeholder, block in code_block_map.items():
        content = content.replace(block, placeholder)

    inline_code = INLINE_CODE_PATTERN.findall(content)
    inline_code_map = {INLINE_CODE_PLACEHOLDER.format(i): code for i, code in enumerate(inline_code)}
    for placeholder, code in inline_code_map.items():
        content = content.replace(code, placeholder)

    embeds = EMBED_PATTERN.findall(content)
    embed_map = {EMBED_PLACEHOLDER.format(i): embed for i, embed in enumerate(embeds)}
    for placeholder, embed in embed_map.items():
        content = content.replace(embed, placeholder)

    md_links = MARKDOWN_LINK_PATTERN.findall(content)
    md_link_map = {MARKDOWN_LINK_PLACEHOLDER.format(i): link for i, link in enumerate(md_links)}
    for placeholder, link in md_link_map.items():
        content = content.replace(link, placeholder)

    heading_map = {}
    if skip_headings:
        heading_lines = HEADING_LINE_PATTERN.findall(content)
        heading_map = {HEADING_LINE_PLACEHOLDER.format(i): line for i, line in enumerate(heading_lines)}
        for placeholder, line in heading_map.items():
            content = content.replace(line, placeholder)

    return content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map


def restore_regions(
    content: str,
    code_block_map: dict,
    inline_code_map: dict,
    embed_map: dict,
    md_link_map: dict,
    heading_map: dict,
) -> str:
    for placeholder, code in inline_code_map.items():
        content = content.replace(placeholder, code)
    for placeholder, block in code_block_map.items():
        content = content.replace(placeholder, block)
    for placeholder, embed in embed_map.items():
        content = content.replace(placeholder, embed)
    for placeholder, link in md_link_map.items():
        content = content.replace(placeholder, link)
    for placeholder, line in heading_map.items():
        content = content.replace(placeholder, line)
    return content


def finalize_modified_content(content, metadata, inline_code_map, code_block_map, embed_map, md_link_map, heading_map):
    content = restore_regions(content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map)
    if metadata:
        content = content.replace(METADATA_PLACEHOLDER, metadata)
    return content


def line_number_at(content: str, index: int) -> int:
    return content.count('\n', 0, index) + 1


def link_files(
    markdown_files,
    *,
    vault_root: Optional[str] = None,
    dry_run: bool = False,
    backup: bool = False,
    output_dir: Optional[str] = None,
    no_self_links: bool = False,
    use_aliases: bool = True,
    use_headings: bool = False,
    skip_headings: bool = True,
    show_progress: bool = True,
) -> LinkResult:
    if output_dir and dry_run:
        raise ValueError("Cannot use --output together with --dry-run")
    if output_dir and backup:
        raise ValueError("Cannot use --backup together with --output (originals are not modified)")

    file_contents = read_files(markdown_files, show_progress=show_progress)
    link_phrases, index_warnings = build_link_phrases(
        markdown_files,
        file_contents,
        use_aliases=use_aliases,
        use_headings=use_headings,
    )

    result = LinkResult(warnings=list(index_warnings))
    modified_contents = {}

    def process_file(file, content):
        original_content = content

        content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map = protect_regions(
            content, skip_headings=skip_headings
        )

        metadata, content = extract_metadata(content)
        if metadata:
            content = METADATA_PLACEHOLDER + content

        content_without_links = EXISTING_LINKS_PATTERN.sub('', content)

        links_added_in_file = 0
        for entry in link_phrases:
            if no_self_links and entry.source_file == file:
                continue
            if entry.phrase_lower not in content_without_links.lower():
                continue

            pattern = re.compile(
                rf'(?<!\[\[)\b{re.escape(entry.phrase)}\b(?!\]\])',
                re.IGNORECASE,
            )

            def replace_match(match, _file=file, _entry=entry):
                nonlocal links_added_in_file
                links_added_in_file += 1
                matched = match.group(0)
                wikilink = format_wikilink(_entry.canonical, matched)
                line = line_number_at(content, match.start())
                result.changes.append(
                    LinkChange(file=_file, line=line, matched_text=matched, wikilink=wikilink)
                )
                return wikilink

            content = pattern.sub(replace_match, content)

        content = restore_regions(content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map)

        if links_added_in_file > 0:
            modified_contents[file] = (
                content,
                metadata,
                inline_code_map,
                code_block_map,
                embed_map,
                md_link_map,
                heading_map,
            )
            result.edited_files.add(file)
            result.total_links_added += links_added_in_file

    if show_progress:
        process_pbar = tqdm(total=len(markdown_files), desc="Processing files")
    for file, content in file_contents.items():
        process_file(file, content)
        if show_progress:
            process_pbar.update(1)
    if show_progress:
        process_pbar.close()

    if dry_run:
        return result

    if not modified_contents:
        return result

    vault_root = os.path.abspath(vault_root) if vault_root else None

    if show_progress:
        write_pbar = tqdm(total=len(modified_contents), desc="Writing files")
    for file, stored in modified_contents.items():
        content, metadata, inline_code_map, code_block_map, embed_map, md_link_map, heading_map = stored
        try:
            content = finalize_modified_content(
                content, metadata, inline_code_map, code_block_map, embed_map, md_link_map, heading_map
            )

            if output_dir:
                if vault_root is None:
                    raise ValueError("vault_root is required when using --output")
                rel_path = os.path.relpath(file, vault_root)
                dest_path = os.path.join(os.path.abspath(output_dir), rel_path)
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                with open(dest_path, 'w', encoding='utf-8') as f:
                    f.write(content)
            else:
                if backup:
                    shutil.copy2(file, file + '.bak')
                with open(file, 'w', encoding='utf-8') as f:
                    f.write(content)
        except OSError as e:
            print(f"Error writing to file {file}: {e}")
        if show_progress:
            write_pbar.update(1)
    if show_progress:
        write_pbar.close()

    return result


def print_dry_run_report(changes: list) -> None:
    for change in changes:
        print(f"{change.file}:{change.line}: {change.matched_text} -> {change.wikilink}")


def print_warnings(warnings: List[str]) -> None:
    for warning in warnings:
        print(f"Warning: {warning}")


def main():
    parser = argparse.ArgumentParser(description="Link markdown files in an Obsidian vault.")
    parser.add_argument("directory", help="Path to the Obsidian vault directory")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report links that would be added without modifying files",
    )
    parser.add_argument(
        "--backup",
        action="store_true",
        help="Before overwriting a file in the vault, save a copy as <file>.bak",
    )
    parser.add_argument(
        "--output",
        metavar="DIR",
        help="Write linked files to DIR, mirroring vault paths (does not modify the vault)",
    )
    parser.add_argument(
        "--no-self-links",
        action="store_true",
        help="Do not link a note's title inside the file that bears that title",
    )
    parser.add_argument(
        "--no-aliases",
        action="store_true",
        help="Do not use YAML alias / aliases fields from front matter",
    )
    parser.add_argument(
        "--use-headings",
        action="store_true",
        help="Also treat each note's first H1 heading as a link phrase",
    )
    parser.add_argument(
        "--link-headings",
        action="store_true",
        help="Add links inside markdown heading lines (skipped by default)",
    )
    parser.add_argument(
        "--exclude",
        action="append",
        default=[],
        metavar="DIRNAME",
        help="Skip directories with this name (repeatable). Combined with default excludes unless --no-default-excludes is set",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Do not skip .obsidian, .git, and other default folders",
    )
    args = parser.parse_args()

    directory = os.path.abspath(os.path.expanduser(args.directory))
    exclude_dir_names = resolve_exclude_dir_names(
        use_default_excludes=not args.no_default_excludes,
        extra_excludes=args.exclude,
    )
    output_dir = os.path.abspath(os.path.expanduser(args.output)) if args.output else None

    markdown_files = find_markdown_files(directory, exclude_dir_names=exclude_dir_names)
    result = link_files(
        markdown_files,
        vault_root=directory,
        dry_run=args.dry_run,
        backup=args.backup,
        output_dir=output_dir,
        no_self_links=args.no_self_links,
        use_aliases=not args.no_aliases,
        use_headings=args.use_headings,
        skip_headings=not args.link_headings,
    )

    if result.warnings:
        print_warnings(result.warnings)

    if args.dry_run and result.changes:
        print_dry_run_report(result.changes)

    print(f"Total links added: {result.total_links_added}")
    print(f"Total files edited: {len(result.edited_files)}")
    if args.dry_run:
        print("(dry run — no files were modified)")


if __name__ == "__main__":
    main()
