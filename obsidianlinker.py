import os
import re
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

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
            content = content.replace(section, '')

        # Exclude existing links
        content_without_links = re.sub(r'\[\[.*?\]\]', '', content)

        for title_lower, title in titles.items():
            if title_lower in content_without_links.lower():
                pattern = re.compile(rf'(?<!\[\[)\b{re.escape(title)}\b(?!\]\])', re.IGNORECASE)
                content = pattern.sub(lambda match: f'[[{match.group(0)}]]', content)

        # Restore metadata sections
        for section in metadata_sections:
            content = section + content

        if content != original_content:
            with open(file, 'w', encoding='utf-8') as f:
                f.write(content)
            edited_files.add(file)
            total_links_added += content.count('[[') - original_content.count('[[')

    with ThreadPoolExecutor() as executor:
        list(tqdm(executor.map(process_file, markdown_files), total=len(markdown_files), desc="Linking files"))

    print(f"Total links added: {total_links_added}")
    print(f"Total files edited: {len(edited_files)}")

    return edited_files
