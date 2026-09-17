import os
import shutil
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple

from vault_linker.constants import METADATA_PLACEHOLDER
from vault_linker.link import compile_link_phrases, line_number_at, process_single_file, read_files
from vault_linker.metadata import build_link_phrases, extract_metadata, note_canonical_title
from vault_linker.models import LinkChange, LinkPhrase
from vault_linker.parallel import map_parallel, resolve_worker_count
from vault_linker.protect import protect_regions, restore_regions
from vault_linker.wikilinks import WIKILINK_PATTERN, build_managed_link_keys, parse_wikilink_inner


@dataclass
class BrokenLink:
    file: str
    line: int
    target: str
    wikilink: str


@dataclass
class AuditResult:
    warnings: List[str] = field(default_factory=list)
    broken_links: List[BrokenLink] = field(default_factory=list)
    zero_backlink_notes: List[str] = field(default_factory=list)
    link_target_counts: List[Tuple[str, int]] = field(default_factory=list)
    pending_link_count: int = 0
    pending_file_count: int = 0
    pending_changes: List[LinkChange] = field(default_factory=list)


@dataclass
class UnlinkChange:
    file: str
    line: int
    wikilink: str
    restored_text: str


@dataclass
class UnlinkResult:
    edited_files: Set[str] = field(default_factory=set)
    total_links_removed: int = 0
    changes: List[UnlinkChange] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


def known_note_titles(markdown_files: List[str]) -> Set[str]:
    return {note_canonical_title(path).casefold() for path in markdown_files}


def scan_wikilinks(
    file: str,
    content: str,
    *,
    skip_headings: bool,
) -> List[Tuple[int, str, str, str]]:
    working, code_block_map, inline_code_map, embed_map, md_link_map, heading_map = protect_regions(
        content, skip_headings=skip_headings
    )
    metadata, working = extract_metadata(working)
    if metadata:
        working = METADATA_PLACEHOLDER + working

    found = []
    for match in WIKILINK_PATTERN.finditer(working):
        inner = match.group(1)
        target, display = parse_wikilink_inner(inner)
        line = line_number_at(working, match.start())
        found.append((line, match.group(0), target, display))
    return found


def audit_vault(
    markdown_files: List[str],
    *,
    no_self_links: bool = False,
    use_aliases: bool = True,
    use_headings: bool = False,
    skip_headings: bool = True,
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
    show_progress: bool = False,
    jobs: int = 1,
    case_sensitive: bool = False,
    first_link_per_phrase: bool = False,
) -> AuditResult:
    worker_count = resolve_worker_count(jobs)
    file_contents = read_files(markdown_files, show_progress=show_progress, jobs=worker_count)
    link_phrases, warnings = build_link_phrases(
        markdown_files,
        file_contents,
        use_aliases=use_aliases,
        use_headings=use_headings,
        ignore_phrases=ignore_phrases,
        min_title_length=min_title_length,
    )
    compiled = compile_link_phrases(link_phrases, case_sensitive=case_sensitive)
    known_titles = known_note_titles(markdown_files)

    result = AuditResult(warnings=list(warnings))
    backlink_counts: Counter = Counter()

    work_items = list(file_contents.items())

    def pending_worker(item: Tuple[str, str]):
        file, content = item
        return process_single_file(
            file,
            content,
            compiled,
            no_self_links=no_self_links,
            skip_headings=skip_headings,
            case_sensitive=case_sensitive,
            first_link_per_phrase=first_link_per_phrase,
        )

    for process_result in map_parallel(
        work_items,
        pending_worker,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Scanning pending links",
    ):
        result.pending_changes.extend(process_result.changes)
        result.pending_link_count += process_result.links_added
        if process_result.links_added > 0:
            result.pending_file_count += 1

    for file, content in file_contents.items():
        for line, wikilink, target, _display in scan_wikilinks(
            file, content, skip_headings=skip_headings
        ):
            if target.casefold() not in known_titles:
                result.broken_links.append(
                    BrokenLink(file=file, line=line, target=target, wikilink=wikilink)
                )
            backlink_counts[target.casefold()] += 1

    title_by_lower = {
        note_canonical_title(path).casefold(): note_canonical_title(path)
        for path in markdown_files
    }
    all_titles = sorted(title_by_lower.values())
    result.zero_backlink_notes = [
        title for title in all_titles if backlink_counts[title.casefold()] == 0
    ]
    result.link_target_counts = [
        (title_by_lower.get(key, key), count) for key, count in backlink_counts.most_common()
    ]
    return result


def print_audit_report(audit: AuditResult, *, verbose: bool = False) -> None:
    print("=== Vault Linker audit ===")
    print(f"Pending links (would add): {audit.pending_link_count} in {audit.pending_file_count} files")

    print(f"\nBroken wikilinks: {len(audit.broken_links)}")
    limit = None if verbose else 50
    for broken in audit.broken_links[:limit]:
        print(f"  {broken.file}:{broken.line}: {broken.wikilink} (no note titled '{broken.target}')")
    if not verbose and len(audit.broken_links) > 50:
        print(f"  ... and {len(audit.broken_links) - 50} more (use -v)")

    print(f"\nNotes with zero incoming links: {len(audit.zero_backlink_notes)}")
    title_limit = None if verbose else 30
    for title in audit.zero_backlink_notes[:title_limit]:
        print(f"  {title}")
    if not verbose and len(audit.zero_backlink_notes) > 30:
        print(f"  ... and {len(audit.zero_backlink_notes) - 30} more (use -v)")

    if audit.link_target_counts:
        print("\nMost linked note titles:")
        for title_key, count in audit.link_target_counts[:10]:
            print(f"  {title_key} ({count})")

    if verbose and audit.pending_changes:
        print("\nPending link details:")
        for change in audit.pending_changes:
            print(f"  {change.file}:{change.line}: {change.matched_text} -> {change.wikilink}")


def unlink_single_file(
    file: str,
    content: str,
    managed_keys: Dict[Tuple[str, str], LinkPhrase],
    *,
    no_self_links: bool,
    skip_headings: bool,
) -> Tuple[str, List[UnlinkChange], int]:
    original = content
    working, code_block_map, inline_code_map, embed_map, md_link_map, heading_map = protect_regions(
        content, skip_headings=skip_headings
    )
    metadata, working = extract_metadata(working)
    if metadata:
        working = METADATA_PLACEHOLDER + working

    changes: List[UnlinkChange] = []
    removed = 0

    def replace_wikilink(match):
        nonlocal removed
        inner = match.group(1)
        target, display = parse_wikilink_inner(inner)
        key = (target.casefold(), display.casefold())
        entry = managed_keys.get(key)
        if entry is None:
            return match.group(0)
        if no_self_links and entry.source_file == file:
            return match.group(0)
        removed += 1
        line = line_number_at(working, match.start())
        changes.append(
            UnlinkChange(
                file=file,
                line=line,
                wikilink=match.group(0),
                restored_text=display,
            )
        )
        return display

    working = WIKILINK_PATTERN.sub(replace_wikilink, working)
    working = restore_regions(working, code_block_map, inline_code_map, embed_map, md_link_map, heading_map)

    if metadata:
        working = working.replace(METADATA_PLACEHOLDER, metadata)

    if removed == 0:
        return original, changes, removed
    return working, changes, removed


def unlink_files(
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
    ignore_phrases: Optional[Set[str]] = None,
    min_title_length: int = 1,
    jobs: int = 1,
) -> UnlinkResult:
    if output_dir and dry_run:
        raise ValueError("Cannot use --output together with --dry-run")
    if output_dir and backup:
        raise ValueError("Cannot use --backup together with --output (originals are not modified)")

    worker_count = resolve_worker_count(jobs)
    file_contents = read_files(markdown_files, show_progress=show_progress, jobs=worker_count)
    link_phrases, warnings = build_link_phrases(
        markdown_files,
        file_contents,
        use_aliases=use_aliases,
        use_headings=use_headings,
        ignore_phrases=ignore_phrases,
        min_title_length=min_title_length,
    )
    managed_keys = build_managed_link_keys(link_phrases)
    result = UnlinkResult(warnings=list(warnings))
    modified_contents: Dict[str, str] = {}

    def unlink_worker(item: Tuple[str, str]):
        file, content = item
        new_content, changes, removed = unlink_single_file(
            file,
            content,
            managed_keys,
            no_self_links=no_self_links,
            skip_headings=skip_headings,
        )
        return file, new_content, changes, removed

    for file, new_content, changes, removed in map_parallel(
        list(file_contents.items()),
        unlink_worker,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Removing links",
    ):
        result.changes.extend(changes)
        result.total_links_removed += removed
        if removed > 0:
            result.edited_files.add(file)
            modified_contents[file] = new_content

    if dry_run:
        return result

    if not modified_contents:
        return result

    vault_root_abs = os.path.abspath(vault_root) if vault_root else None

    def write_worker(item: Tuple[str, str]):
        file, content = item
        try:
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

    for message in map_parallel(
        list(modified_contents.items()),
        write_worker,
        jobs=worker_count,
        show_progress=show_progress,
        desc="Writing files",
    ):
        if message:
            print(message)

    return result


def print_unlink_report(changes: List[UnlinkChange]) -> None:
    for change in changes:
        print(f"{change.file}:{change.line}: {change.wikilink} -> {change.restored_text}")
