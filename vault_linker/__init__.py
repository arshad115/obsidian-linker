from vault_linker.link import link_files
from vault_linker.models import LinkChange, LinkPhrase, LinkResult
from vault_linker.scan import find_markdown_files, resolve_exclude_dir_names

__all__ = [
    'find_markdown_files',
    'link_files',
    'resolve_exclude_dir_names',
    'LinkChange',
    'LinkPhrase',
    'LinkResult',
]

__version__ = '0.5.1'
