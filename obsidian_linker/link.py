import os
import re
import shutil
from typing import Optional, Set

from tqdm import tqdm

from obsidian_linker.constants import EXISTING_LINKS_PATTERN, METADATA_PLACEHOLDER
from obsidian_linker.metadata import build_link_phrases, extract_metadata, format_wikilink
from obsidian_linker.models import LinkChange, LinkResult
from obsidian_linker.protect import finalize_modified_content, protect_regions, restore_regions
from obsidian_linker.state import default_state_path, files_to_process, load_state, save_state


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
    incremental: bool = False,
    state_path: Optional[str] = None,
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
) -> LinkResult:
    if output_dir and dry_run:
        raise ValueError("Cannot use --output together with --dry-run")
    if output_dir and backup:
        raise ValueError("Cannot use --backup together with --output (originals are not modified)")
    if incremental and vault_root is None:
        raise ValueError("vault_root is required when using --incremental")

    state = load_state(state_path or default_state_path(vault_root)) if incremental else {}
    process_only = files_to_process(markdown_files, state, incremental) if incremental else None

    file_contents = read_files(markdown_files, show_progress=show_progress)
    link_phrases, index_warnings = build_link_phrases(
        markdown_files,
        file_contents,
        use_aliases=use_aliases,
        use_headings=use_headings,
        ignore_phrases=ignore_phrases,
        min_title_length=min_title_length,
    )

    result = LinkResult(warnings=list(index_warnings))
    modified_contents = {}

    def process_file(file, content):
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

    files_to_iterate = file_contents.items()
    if show_progress:
        process_pbar = tqdm(total=len(file_contents), desc="Processing files")
    for file, content in files_to_iterate:
        if process_only is not None and os.path.abspath(file) not in process_only:
            if show_progress:
                process_pbar.update(1)
            continue
        process_file(file, content)
        if show_progress:
            process_pbar.update(1)
    if show_progress:
        process_pbar.close()

    if dry_run:
        return result

    if not modified_contents:
        if incremental and vault_root:
            save_state(state_path or default_state_path(vault_root), markdown_files)
        return result

    vault_root_abs = os.path.abspath(vault_root) if vault_root else None

    if show_progress:
        write_pbar = tqdm(total=len(modified_contents), desc="Writing files")
    for file, stored in modified_contents.items():
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

    if incremental and vault_root:
        save_state(state_path or default_state_path(vault_root), markdown_files)

    return result
