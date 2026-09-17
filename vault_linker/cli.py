import argparse
import os

from vault_linker.audit import audit_vault, print_audit_report, print_unlink_report, unlink_files
from vault_linker.ignore import load_ignore_phrases
from vault_linker.link import link_files
from vault_linker.scan import find_markdown_files, resolve_exclude_dir_names
from vault_linker.state import default_state_path


def print_dry_run_report(changes: list) -> None:
    for change in changes:
        print(f"{change.file}:{change.line}: {change.matched_text} -> {change.wikilink}")


def print_warnings(warnings: list) -> None:
    for warning in warnings:
        print(f"Warning: {warning}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Vault Linker — link note titles in an Obsidian vault.")
    parser.add_argument("directory", help="Path to the Obsidian vault directory")
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Show progress bars and scan details",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report links that would be added without modifying files (also applies to --unlink)",
    )
    parser.add_argument(
        "--audit",
        action="store_true",
        help="Audit vault: pending links, broken wikilinks, notes with zero backlinks",
    )
    parser.add_argument(
        "--unlink",
        action="store_true",
        help="Remove wikilinks that match this tool's title/alias link rules",
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
        "--include-glob",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Only process vault-relative paths matching this glob (repeatable; e.g. 'notes/**')",
    )
    parser.add_argument(
        "--exclude-glob",
        action="append",
        default=[],
        metavar="PATTERN",
        help="Skip vault-relative paths matching this glob (repeatable; e.g. 'templates/**')",
    )
    parser.add_argument(
        "--no-default-excludes",
        action="store_true",
        help="Do not skip .obsidian, .git, and other default folders",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Only process notes changed since the last run (reprocesses all notes when notes are added or removed)",
    )
    parser.add_argument(
        "--state-file",
        metavar="PATH",
        help="Path for incremental state (default: <vault>/.obsidian/vault-linker-state.json)",
    )
    parser.add_argument(
        "--ignore-phrase",
        action="append",
        default=[],
        metavar="TEXT",
        help="Skip linking this phrase (repeatable; case-insensitive)",
    )
    parser.add_argument(
        "--ignore-file",
        metavar="PATH",
        help="File with phrases to skip, one per line (# comments allowed)",
    )
    parser.add_argument(
        "--min-title-length",
        type=int,
        default=1,
        metavar="N",
        help="Do not link phrases shorter than N characters (default: 1)",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=1,
        metavar="N",
        help="Parallel workers for read/process/write (default: 1). Use 0 for automatic (CPU count, max 32)",
    )
    parser.add_argument(
        "--case-sensitive",
        action="store_true",
        help="Match note titles and aliases with exact letter case",
    )
    parser.add_argument(
        "--first-link-per-phrase",
        action="store_true",
        help="Add at most one wikilink per phrase per file (first occurrence only)",
    )
    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.audit and args.unlink:
        parser.error("Use either --audit or --unlink, not both")
    if args.audit and (args.output or args.backup or args.incremental):
        parser.error("--audit does not support --output, --backup, or --incremental")

    directory = os.path.abspath(os.path.expanduser(args.directory))
    exclude_dir_names = resolve_exclude_dir_names(
        use_default_excludes=not args.no_default_excludes,
        extra_excludes=args.exclude,
    )
    output_dir = os.path.abspath(os.path.expanduser(args.output)) if args.output else None
    state_path = (
        os.path.abspath(os.path.expanduser(args.state_file))
        if args.state_file
        else (default_state_path(directory) if args.incremental else None)
    )
    ignore_file = os.path.expanduser(args.ignore_file) if args.ignore_file else None
    ignore_phrases = load_ignore_phrases(args.ignore_phrase, ignore_file)

    markdown_files = find_markdown_files(
        directory,
        exclude_dir_names=exclude_dir_names,
        include_globs=args.include_glob,
        exclude_globs=args.exclude_glob,
        verbose=args.verbose,
    )

    if args.audit:
        audit = audit_vault(
            markdown_files,
            no_self_links=args.no_self_links,
            use_aliases=not args.no_aliases,
            use_headings=args.use_headings,
            skip_headings=not args.link_headings,
            ignore_phrases=ignore_phrases,
            min_title_length=args.min_title_length,
            show_progress=args.verbose,
            jobs=args.jobs,
            case_sensitive=args.case_sensitive,
            first_link_per_phrase=args.first_link_per_phrase,
        )
        if audit.warnings:
            print_warnings(audit.warnings)
        print_audit_report(audit, verbose=args.verbose)
        return 0

    if args.unlink:
        unlink_result = unlink_files(
            markdown_files,
            vault_root=directory,
            dry_run=args.dry_run,
            backup=args.backup,
            output_dir=output_dir,
            no_self_links=args.no_self_links,
            use_aliases=not args.no_aliases,
            use_headings=args.use_headings,
            skip_headings=not args.link_headings,
            show_progress=args.verbose,
            ignore_phrases=ignore_phrases,
            min_title_length=args.min_title_length,
            jobs=args.jobs,
        )
        if unlink_result.warnings:
            print_warnings(unlink_result.warnings)
        if args.dry_run and unlink_result.changes:
            print_unlink_report(unlink_result.changes)
        print(f"Total links removed: {unlink_result.total_links_removed}")
        print(f"Total files edited: {len(unlink_result.edited_files)}")
        if args.dry_run:
            print("(dry run — no files were modified)")
        return 0

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
        show_progress=args.verbose,
        incremental=args.incremental,
        state_path=state_path,
        ignore_phrases=ignore_phrases,
        min_title_length=args.min_title_length,
        jobs=args.jobs,
        case_sensitive=args.case_sensitive,
        first_link_per_phrase=args.first_link_per_phrase,
    )

    if result.warnings:
        print_warnings(result.warnings)

    if args.dry_run and result.changes:
        print_dry_run_report(result.changes)

    print(f"Total links added: {result.total_links_added}")
    print(f"Total files edited: {len(result.edited_files)}")
    if args.dry_run:
        print("(dry run — no files were modified)")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
