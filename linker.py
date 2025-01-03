import os
import re
import sys
from tqdm import tqdm

def find_markdown_files(directory):
    markdown_files = []
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith(".md"):
                markdown_files.append(os.path.join(root, file))
    print(f"Found {len(markdown_files)} markdown files.")
    return markdown_files

def extract_title(file_path):
    return os.path.splitext(os.path.basename(file_path))[0]

def link_files(markdown_files):
    file_contents = {}
    file_titles = {}
    edited_files = []

    # Read all files and store their contents
    for file in markdown_files:
        with open(file, 'r', encoding='utf-8') as f:
            content = f.read()
            file_contents[file] = content
            title = extract_title(file)
            if title:
                file_titles[title.lower()] = file

    # Sort titles by length in descending order
    sorted_titles = sorted(file_titles.keys(), key=len, reverse=True)

    # Create links
    for file, content in tqdm(file_contents.items(), desc="Linking files"):
        original_content = content
        in_code_block = False
        new_content_lines = []
        for line in content.split('\n'):
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
            if not in_code_block:
                for title in sorted_titles:
                    pattern = re.compile(rf'\b{re.escape(title)}\b', re.IGNORECASE)
                    line = pattern.sub(lambda m: f"[[{m.group(0)}]]" if f"[[{m.group(0)}]]" not in line and not re.search(r'\[\[.*?\]\]', line) else m.group(0), line)
            new_content_lines.append(line)
        new_content = '\n'.join(new_content_lines)
        if new_content != original_content:
            edited_files.append(file)
            file_contents[file] = new_content

    # Write the updated contents back to the files
    for file in tqdm(set(edited_files), desc="Writing files"):
        with open(file, 'w', encoding='utf-8') as f:
            f.write(file_contents[file])

    print(f"Edited {len(set(edited_files))} files.")
    if edited_files:
        print("Modified files:")
        for file in set(edited_files):
            print(file)

    # Print summary
    print("\nSummary:")
    print(f"Total markdown files found: {len(markdown_files)}")
    print(f"Total files edited: {len(set(edited_files))}")

def main():
    if len(sys.argv) != 2:
        print("Usage: python linker.py '<obsidian_vault_directory>'")
        sys.exit(1)

    vault_directory = os.path.expanduser(sys.argv[1])
    if not os.path.isdir(vault_directory):
        print(f"Error: '{vault_directory}' is not a valid directory.")
        sys.exit(1)

    markdown_files = find_markdown_files(vault_directory)
    link_files(markdown_files)

if __name__ == "__main__":
    main()