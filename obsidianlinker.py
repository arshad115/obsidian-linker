import os
import re
import argparse
from tqdm import tqdm

CODE_BLOCK_PLACEHOLDER = "<CODE_BLOCK_{}>"
METADATA_PLACEHOLDER = "<METADATA_SECTION>"
INLINE_CODE_PLACEHOLDER = "<INLINE_CODE_{}>"

# Compile regex patterns
CODE_BLOCK_PATTERN = re.compile(r'```[\s\S]*?```', re.DOTALL | re.MULTILINE)
INLINE_CODE_PATTERN = re.compile(r'`[^`]*`')
EXISTING_LINKS_PATTERN = re.compile(r'\[\[.*?\]\]')
METADATA_PATTERN = re.compile(r'---\s*\n([\s\S]*?)\n\s*---', re.MULTILINE)

def find_markdown_files(directory):
    markdown_files = []
    print(f"Searching for markdown files in directory: {directory}")
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    print(f"Found {len(markdown_files)} markdown files.")
    return markdown_files

def read_files(markdown_files):
    file_contents = {}
    with tqdm(total=len(markdown_files), desc="Reading files") as read_pbar:
        for file in markdown_files:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    file_contents[file] = f.read()
            except UnicodeDecodeError:
                print(f"Error reading file {file} with UTF-8 encoding.")
            read_pbar.update(1)
    return file_contents

def extract_metadata(content):
    metadata_match = METADATA_PATTERN.search(content)  # Changed from match to search
    if metadata_match:
        metadata = metadata_match.group(0)
        content = content.replace(metadata, '', 1)  # Remove only the first occurrence
        return metadata, content
    return '', content

def link_files(markdown_files):
    titles = {}
    for file in markdown_files:
        title = os.path.splitext(os.path.basename(file))[0]
        titles[title.lower()] = title

    edited_files = set()
    total_links_added = 0
    modified_contents = {}

    def process_file(file, content):
        nonlocal total_links_added

        original_content = content

        # Exclude metadata sections
        metadata, content = extract_metadata(content)
        if metadata:
            content = content.replace(metadata, METADATA_PLACEHOLDER)
        
        # Exclude code blocks
        code_blocks = CODE_BLOCK_PATTERN.findall(content)
        code_block_map = {CODE_BLOCK_PLACEHOLDER.format(i): block for i, block in enumerate(code_blocks)}
        for placeholder, block in code_block_map.items():
            content = content.replace(block, placeholder)

        # Exclude inline code
        inline_code = INLINE_CODE_PATTERN.findall(content)
        inline_code_map = {INLINE_CODE_PLACEHOLDER.format(i): code for i, code in enumerate(inline_code)}
        for placeholder, code in inline_code_map.items():
            content = content.replace(code, placeholder)

        # Exclude existing links
        content_without_links = EXISTING_LINKS_PATTERN.sub('', content)

        for title_lower, title in titles.items():
            if title_lower in content_without_links.lower():
                pattern = re.compile(rf'(?<!\[\[)\b{re.escape(title)}\b(?!\]\])', re.IGNORECASE)
                content = pattern.sub(lambda match: f'[[{match.group(0)}]]', content)

        # Restore inline code, code blocks, and metadata sections
        for placeholder, code in inline_code_map.items():
            content = content.replace(placeholder, code)
        for placeholder, block in code_block_map.items():
            content = content.replace(placeholder, block)
        
        if metadata:
            content = METADATA_PLACEHOLDER + content  # Prepend metadata placeholder

        if content != original_content:
            modified_contents[file] = (content, metadata, inline_code_map, code_block_map)  # Store content, metadata, inline code map, and code block map
            edited_files.add(file)
            total_links_added += 1

    file_contents = read_files(markdown_files)

    with tqdm(total=len(markdown_files), desc="Processing files") as process_pbar:
        for file, content in file_contents.items():
            process_file(file, content)
            process_pbar.update(1)

    with tqdm(total=len(modified_contents), desc="Writing files") as write_pbar:
        for file, (content, metadata, inline_code_map, code_block_map) in modified_contents.items():
            try:
                # Restore inline code and code blocks
                for placeholder, code in inline_code_map.items():
                    content = content.replace(placeholder, code)
                for placeholder, block in code_block_map.items():
                    content = content.replace(placeholder, block)
                    
                # Restore metadata
                if metadata:
                    content = content.replace(METADATA_PLACEHOLDER, metadata)

                with open(file, 'w', encoding='utf-8') as f:
                    f.write(content)  
            except IOError as e:
                print(f"Error writing to file {file}: {e}")
            write_pbar.update(1)

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