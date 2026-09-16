import os
import re
import shutil
from dataclasses import dataclass
from typing import Dict, List, Optional, Set, Tuple

from obsidian_linker.constants import EXISTING_LINKS_PATTERN, METADATA_PLACEHOLDER
from obsidian_linker.metadata import build_link_phrases, extract_metadata, format_wikilink
from obsidian_linker.models import LinkChange, LinkPhrase, LinkResult
from obsidian_linker.parallel import map_parallel, resolve_worker_count
from obsidian_linker.protect import finalize_modified_content, protect_regions, restore_regions
from obsidian_linker.state import default_state_path, files_to_process, load_state, save_state

StoredContent = Tuple[str, str, dict, dict, dict, dict, dict]


@dataclass
class FileProcessResult:
    file: str
    links_added: int
    changes: List[LinkChange]
    stored: Optional[StoredContent]


@dataclass(frozen=True)
class CompiledLinkPhrase:
    entry: LinkPhrase
    pattern: re.Pattern


def compile_link_phrases(link_phrases: List[LinkPhrase]) -> List[CompiledLinkPhrase]:
    compiled = []
    for entry in link_phrases:
        compiled.append(
            CompiledLinkPhrase(
                entry=entry,
                pattern=re.compile(
                    rf'(?<!\[\[)\b{re.escape(entry.phrase)}\b(?!\]\])',
                    re.IGNORECASE,
                ),
            )
        )
    return compiled


def line_number_at(content: str, index: int) -> int:
    return content.count('\n', 0, index) + 1


def process_single_file(
    file: str,
    content: str,
    compiled_phrases: List[CompiledLinkPhrase],
    *,
    no_self_links: bool,
    skip_headings: bool,
) -> FileProcessResult:
    content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map = protect_regions(
        content, skip_headings=skip_headings
    )

    metadata, content = extract_metadata(content)
    if metadata:
        content = METADATA_PLACEHOLDER + content

    content_without_links = EXISTING_LINKS_PATTERN.sub('', content)
    changes: List[LinkChange] = []
    links_added_in_file = 0

    for compiled in compiled_phrases:
        entry = compiled.entry
        if no_self_links and entry.source_file == file:
            continue
        if entry.phrase_lower not in content_without_links.lower():
            continue

        def replace_match(match, _file=file, _entry=entry):
            nonlocal links_added_in_file
            links_added_in_file += 1
            matched = match.group(0)
            wikilink = format_wikilink(_entry.canonical, matched)
            line = line_number_at(content, match.start())
            changes.append(
                LinkChange(file=_file, line=line, matched_text=matched, wikilink=wikilink)
            )
            return wikilink

        content = compiled.pattern.sub(replace_match, content)

    content = restore_regions(content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map)

    stored = None
    if links_added_in_file > 0:
        stored = (
            content,
            metadata,
            inline_code_map,
            code_block_map,
            embed_map,
            md_link_map,
            heading_map,
        )

    return FileProcessResult(
        file=file,
        links_added=links_added_in_file,
        changes=changes,
        stored=stored,
    )


def _read_one(file: str) -> Tuple[str, Optional[str]]:
    try:
        with open(file, 'r', encoding='utf-8') as handle:
            return file, handle.read()
    except UnicodeDecodeError:
        print(f"Error reading file {file} with UTF-8 encoding.")
        return file, None


def read_files(markdown_files, *, show_progress: bool = True, jobs: int = 1):
    worker_count = resolve_worker_count(jobs)
    pairs = map_parallel(
        markdown_files,
        _read_one,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Reading files",
    )
    file_contents: Dict[str, str] = {}
    for file, content in pairs:
        if content is not None:
            file_contents[file] = content
    return file_contents


def _write_one(
    file: str,
    stored: StoredContent,
    *,
    vault_root_abs: Optional[str],
    output_dir: Optional[str],
    backup: bool,
) -> Optional[str]:
    content, metadata, inline_code_map, code_block_map, embed_map, md_link_map, heading_map = stored
    try:
        content = finalize_modified_content(
            content, metadata, inline_code_map, code_block_map, embed_map, md_link_map, heading_map
        )

        if output_dir:
            if vault_root_abs is None:
                raise ValueError("vault_root is required when using --output")
            rel_path = os.path.relpath(file, vault_root_abs)
            dest_path = os.path.join(os.path.abspath(output_dir), rel_path)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            with open(dest_path, 'w', encoding='utf-8') as handle:
                handle.write(content)
        else:
            if backup:
                shutil.copy2(file, file + '.bak')
            with open(file, 'w', encoding='utf-8') as handle:
                handle.write(content)
    except OSError as error:
        return f"Error writing to file {file}: {error}"
    return None


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
    incremental: bool = False,
    state_path: Optional[str] = None,
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
    jobs: int = 1,
) -> LinkResult:
    if output_dir and dry_run:
        raise ValueError("Cannot use --output together with --dry-run")
    if output_dir and backup:
        raise ValueError("Cannot use --backup together with --output (originals are not modified)")
    if incremental and vault_root is None:
        raise ValueError("vault_root is required when using --incremental")

    worker_count = resolve_worker_count(jobs)

    state = load_state(state_path or default_state_path(vault_root)) if incremental else {}
    process_only = files_to_process(markdown_files, state, incremental) if incremental else None

    file_contents = read_files(markdown_files, show_progress=show_progress, jobs=worker_count)
    link_phrases, index_warnings = build_link_phrases(
        markdown_files,
        file_contents,
        use_aliases=use_aliases,
        use_headings=use_headings,
        ignore_phrases=ignore_phrases,
        min_title_length=min_title_length,
    )
    compiled_phrases = compile_link_phrases(link_phrases)

    result = LinkResult(warnings=list(index_warnings))
    modified_contents: Dict[str, StoredContent] = {}

    work_items = []
    for file, content in file_contents.items():
        if process_only is not None and os.path.abspath(file) not in process_only:
            continue
        work_items.append((file, content))

    def process_worker(item: Tuple[str, str]) -> FileProcessResult:
        file, content = item
        return process_single_file(
            file,
            content,
            compiled_phrases,
            no_self_links=no_self_links,
            skip_headings=skip_headings,
        )

    process_results = map_parallel(
        work_items,
        process_worker,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Processing files",
    )

    for process_result in process_results:
        result.changes.extend(process_result.changes)
        result.total_links_added += process_result.links_added
        if process_result.stored is not None:
            modified_contents[process_result.file] = process_result.stored
            result.edited_files.add(process_result.file)

    if dry_run:
        return result

    if not modified_contents:
        if incremental and vault_root:
            save_state(state_path or default_state_path(vault_root), markdown_files)
        return result

    vault_root_abs = os.path.abspath(vault_root) if vault_root else None
    write_items = list(modified_contents.items())

    def write_worker(item: Tuple[str, StoredContent]) -> Optional[str]:
        file, stored = item
        return _write_one(
            file,
            stored,
            vault_root_abs=vault_root_abs,
            output_dir=output_dir,
            backup=backup,
        )

    write_errors = map_parallel(
        write_items,
        write_worker,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Writing files",
    )
    for message in write_errors:
        if message:
            print(message)

    if incremental and vault_root:
        save_state(state_path or default_state_path(vault_root), markdown_files)

    return result
