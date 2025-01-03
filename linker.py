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

    # Create links
    for file, content in tqdm(file_contents.items(), desc="Linking files"):
        original_content = content
        for title, linked_file in file_titles.items():
            pattern = re.compile(rf'\b{re.escape(title)}\b', re.IGNORECASE)
            content = pattern.sub(f"[{title}]({os.path.relpath(linked_file, os.path.dirname(file))})", content)
        if content != original_content:
            edited_files.append(file)
            file_contents[file] = content

    # Write the updated contents back to the files
    for file in tqdm(edited_files, desc="Writing files"):
        with open(file, 'w', encoding='utf-8') as f:
            f.write(file_contents[file])

    print(f"Edited {len(edited_files)} files.")
    if edited_files:
        print("Modified files:")
        for file in edited_files:
            print(file)

    # Print summary
    print("\nSummary:")
    print(f"Total markdown files found: {len(markdown_files)}")
    print(f"Total files edited: {len(edited_files)}")

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