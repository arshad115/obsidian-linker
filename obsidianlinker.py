import argparse
import os
import re
import shutil
from dataclasses import dataclass, field
from typing import Iterable, Optional, Set

from tqdm import tqdm

CODE_BLOCK_PLACEHOLDER = "<CODE_BLOCK_{}>"
METADATA_PLACEHOLDER = "<METADATA_SECTION>"
INLINE_CODE_PLACEHOLDER = "<INLINE_CODE_{}>"

# Compile regex patterns
CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.DOTALL | re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r'`[^`]*`')
EXISTING_LINKS_PATTERN = re.compile(r'\[\[.*?\]\]')
METADATA_PATTERN = re.compile(r'---\s*\n([\s\S]*?)\n\s*---', re.MULTILINE)

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
class LinkChange:
    file: str
    line: int
    matched_text: str


@dataclass
class LinkResult:
    edited_files: Set[str] = field(default_factory=set)
    total_links_added: int = 0
    changes: list = field(default_factory=list)


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
    iterator = markdown_files
    if show_progress:
        read_pbar = tqdm(total=len(markdown_files), desc="Reading files")
    for file in iterator:
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


def extract_metadata(content):
    metadata_match = METADATA_PATTERN.search(content)
    if metadata_match:
        metadata = metadata_match.group(0)
        content = content.replace(metadata, '', 1)
        return metadata, content
    return '', content


def finalize_modified_content(content, metadata, inline_code_map, code_block_map):
    for placeholder, code in inline_code_map.items():
        content = content.replace(placeholder, code)
    for placeholder, block in code_block_map.items():
        content = content.replace(placeholder, block)
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
    show_progress: bool = True,
) -> LinkResult:
    if output_dir and dry_run:
        raise ValueError("Cannot use --output together with --dry-run")
    if output_dir and backup:
        raise ValueError("Cannot use --backup together with --output (originals are not modified)")

    titles = {}
    for file in markdown_files:
        title = os.path.splitext(os.path.basename(file))[0]
        titles[title.lower()] = title

    sorted_titles = sorted(titles.items(), key=lambda item: len(item[0]), reverse=True)

    result = LinkResult()
    modified_contents = {}

    def process_file(file, content):
        original_content = content
        file_title_lower = os.path.splitext(os.path.basename(file))[0].lower()

        code_blocks = CODE_BLOCK_PATTERN.findall(content)
        code_block_map = {CODE_BLOCK_PLACEHOLDER.format(i): block for i, block in enumerate(code_blocks)}
        for placeholder, block in code_block_map.items():
            content = content.replace(block, placeholder)

        inline_code = INLINE_CODE_PATTERN.findall(content)
        inline_code_map = {INLINE_CODE_PLACEHOLDER.format(i): code for i, code in enumerate(inline_code)}
        for placeholder, code in inline_code_map.items():
            content = content.replace(code, placeholder)

        metadata, content = extract_metadata(content)
        if metadata:
            content = METADATA_PLACEHOLDER + content

        content_without_links = EXISTING_LINKS_PATTERN.sub('', content)

        links_added_in_file = 0
        for title_lower, title in sorted_titles:
            if no_self_links and title_lower == file_title_lower:
                continue
            if title_lower not in content_without_links.lower():
                continue
            pattern = re.compile(rf'(?<!\[\[)\b{re.escape(title)}\b(?!\]\])', re.IGNORECASE)

            def replace_match(match, _file=file):
                nonlocal links_added_in_file
                links_added_in_file += 1
                matched = match.group(0)
                line = line_number_at(content, match.start())
                result.changes.append(LinkChange(file=_file, line=line, matched_text=matched))
                return f'[[{matched}]]'

            content = pattern.sub(replace_match, content)

        for placeholder, code in inline_code_map.items():
            content = content.replace(placeholder, code)
        for placeholder, block in code_block_map.items():
            content = content.replace(placeholder, block)

        if content != original_content:
            modified_contents[file] = (content, metadata, inline_code_map, code_block_map)
            result.edited_files.add(file)
            result.total_links_added += links_added_in_file

    file_contents = read_files(markdown_files, show_progress=show_progress)

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
        content, metadata, inline_code_map, code_block_map = stored
        try:
            content = finalize_modified_content(content, metadata, inline_code_map, code_block_map)

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
        print(f"{change.file}:{change.line}: {change.matched_text} -> [[{change.matched_text}]]")


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
    )

    if args.dry_run and result.changes:
        print_dry_run_report(result.changes)

    print(f"Total links added: {result.total_links_added}")
    print(f"Total files edited: {len(result.edited_files)}")
    if args.dry_run:
        print("(dry run — no files were modified)")


if __name__ == "__main__":
    main()
