from typing import Tuple

from obsidian_linker.constants import (
    CODE_BLOCK_PATTERN,
    CODE_BLOCK_PLACEHOLDER,
    EMBED_PATTERN,
    EMBED_PLACEHOLDER,
    HEADING_LINE_PATTERN,
    HEADING_LINE_PLACEHOLDER,
    INLINE_CODE_PATTERN,
    INLINE_CODE_PLACEHOLDER,
    MARKDOWN_LINK_PATTERN,
    MARKDOWN_LINK_PLACEHOLDER,
    METADATA_PLACEHOLDER,
)
from obsidian_linker.metadata import extract_metadata


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


def finalize_modified_content(
    content,
    metadata,
    inline_code_map,
    code_block_map,
    embed_map,
    md_link_map,
    heading_map,
):
    content = restore_regions(content, code_block_map, inline_code_map, embed_map, md_link_map, heading_map)
    if metadata:
        content = content.replace(METADATA_PLACEHOLDER, metadata)
    return content
