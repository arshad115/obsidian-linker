import os
import re
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

CODE_BLOCK_PLACEHOLDER = "<CODE_BLOCK_{}>"
METADATA_PLACEHOLDER = "<METADATA_SECTION>"
INLINE_CODE_PLACEHOLDER = "<INLINE_CODE_{}>"

def find_markdown_files(directory):
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    return markdown_files

def link_files(markdown_files):
    titles = {}
    for file in markdown_files:
        title = os.path.splitext(os.path.basename(file))[0]
        titles[title.lower()] = title

    edited_files = set()
    total_links_added = 0

    def process_file(file):
        nonlocal total_links_added
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()

        original_content = content

        # Exclude metadata sections
        metadata_sections = re.findall(r'---([\s\S]*?)---', content, re.DOTALL | re.MULTILINE)
        for section in metadata_sections:
            content = content.replace(section, METADATA_PLACEHOLDER)

        # Exclude code blocks
        code_blocks = re.findall(r'```[\s\S]*?```', content, re.DOTALL | re.MULTILINE)
        for i, block in enumerate(code_blocks):
            content = content.replace(block, CODE_BLOCK_PLACEHOLDER.format(i))

        # Exclude inline code
        inline_code = re.findall(r'`[^`]*`', content)
        for i, code in enumerate(inline_code):
            content = content.replace(code, INLINE_CODE_PLACEHOLDER.format(i))

        # Exclude existing links
        content_without_links = re.sub(r'\[\[.*?\]\]', '', content)

        for title_lower, title in titles.items():
            if title_lower in content_without_links.lower():
                pattern = re.compile(rf'(?<!\[\[)\b{re.escape(title)}\b(?!\]\])', re.IGNORECASE)
                content = pattern.sub(lambda match: f'[[{match.group(0)}]]', content)

        # Restore inline code, code blocks, and metadata sections
        for i, code in enumerate(inline_code):
            content = content.replace(INLINE_CODE_PLACEHOLDER.format(i), code, 1)
        for i, block in enumerate(code_blocks):
            content = content.replace(CODE_BLOCK_PLACEHOLDER.format(i), block, 1)
        for section in metadata_sections:
            content = content.replace(METADATA_PLACEHOLDER, section, 1)

        if content != original_content:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            edited_files.add(file)
            total_links_added += 1

    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, markdown_files), total=len(markdown_files)))

    return edited_files, total_links_added