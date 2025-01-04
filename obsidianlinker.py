import os
import re
import argparse
from tqdm import tqdm

CODE_BLOCK_PLACEHOLDER = "<CODE_BLOCK_{}>"
METADATA_PLACEHOLDER = "<METADATA_SECTION>"
INLINE_CODE_PLACEHOLDER = "<INLINE_CODE_{}>"

def find_markdown_files(directory):
    markdown_files = []
    print(f"Searching for markdown files in directory: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    print(f"Found {len(markdown_files)} markdown files.")
    return markdown_files

def link_files(markdown_files):
    titles = {}
    for file in markdown_files:
        title = os.path.splitext(os.path.basename(file))[0]
        titles[title.lower()] = title

    edited_files = set()
    total_links_added = 0

    def process_file(file, pbar):
        nonlocal total_links_added
        # print(f"Processing file: {file}")
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

        pbar.update(1)

    with tqdm(total=len(markdown_files), desc="Processing files") as pbar:
        for file in markdown_files:
            process_file(file, pbar)

    return edited_files, total_links_added

def main():
    parser = argparse.ArgumentParser(description="Link markdown files in an Obsidian vault.")
    parser.add_argument("directory", help="Path to the Obsidian vault directory")
    args = parser.parse_args()

    directory = os.path.expanduser(args.directory)  # Expand user directory
    markdown_files = find_markdown_files(directory)
    edited_files, total_links_added = link_files(markdown_files)

    print(f"Total links added: {total_links_added}")
    print(f"Total files edited: {len(edited_files)}")

if __name__ == "__main__":
    main()