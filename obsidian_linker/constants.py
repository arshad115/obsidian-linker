import re

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
