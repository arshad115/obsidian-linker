# Obsidian Linker

[![Run Tests](https://github.com/arshad115/obsidian-linker/actions/workflows/run-tests.yml/badge.svg)](https://github.com/arshad115/obsidian-linker/actions/workflows/run-tests.yml)

## Overview

Obsidian Linker is a tool designed to help you manage and link your notes in Obsidian. It provides various features to enhance your note-taking experience.

## Linking

<p float="left">
  <img src="images/before.png" alt="Before" width="45%" />
  <img src="images/after.png" alt="After" width="45%" />
</p>

## Features

- Automatic linking of notes
- Uses Wikilink format
- Skip links in metadata
- Skip links in codeblocks, inline code

## Linking Process

1. **Scan Files**: The tool scans all the markdown files in your Obsidian vault.
2. **Extract Filenames**: It extracts the filenames from the scanned files.
3. **Match Filenames**: It matches the filenames with the content in other files, ignoring the case.
4. **Insert Links**: When a match is found, it inserts a Wikilink in the content, preserving the original case of the filename in the link.
5. **Skip Metadata and Code**: The tool skips adding links in metadata sections and code blocks to avoid unwanted linking.

### Examples

- **Simple Linking**: If a file named `Object-Oriented Programming.md` exists and another file mentions "object-oriented programming", the tool will link it as `[[object-oriented programming]]`.
- **Preserve Case**: If the mention is "Object-Oriented Programming", the link will be `[[Object-Oriented Programming]]`.
- **No Links in Code Blocks**: Mentions inside code blocks are ignored.
- **No Links in Metadata**: Mentions inside metadata sections are ignored.
- **Multiple Links**: If multiple files are mentioned, each will be linked appropriately.
- **Partial Matches**: If a file named `Object.md` exists, mentions of "object" will be linked as `[[object]]`, but "objects" will not be linked.
- **Complex Linking**: If files named `Object-Oriented Programming.md`, `Functional Programming.md`, and `Object.md` exist, and another file mentions "object-oriented programming", "functional programming", and "object", each will be linked as `[[object-oriented programming]]`, `[[functional programming]]`, and `[[object]]` respectively. Note "object" will not be added inside "object-oriented programming".

## Installation

To install Obsidian Linker, follow these steps:

1. Clone the repository:
    ```sh
    git clone https://github.com/your-username/obsidian-linker.git
    ```
2. Navigate to the project directory:
    ```sh
    cd obsidian-linker
    ```
3. Install the required dependencies:
    ```sh
    pip install -r requirements.txt
    ```

## Usage

![Usage Image](images/usage.png)

To use Obsidian Linker, run the following command:
```sh
python obsidianlinker.py /path/to/vault/
```

Make sure to back up your vault before using this tool, as it can make irreversible edits.
## Running Tests

To run tests for Obsidian Linker, use the following command:
```sh
pytest
```

This will execute all the tests and provide you with a summary of the results. Make sure you have all the necessary dependencies installed before running the tests.

## TODO

- [ ] Add support for alias links
- [ ] Multithreading
- [ ] Write additional tests for edge cases
- [ ] Make it into a plugin for Obsidian

## Contributors

- [Arshad Mehmood](https://github.com/arshad115)

## Contributing

We welcome contributions to Obsidian Linker! If you have an idea for a new feature or have found a bug, please open an issue or submit a pull request.

### Steps to Contribute

1. Fork the repository.
2. Create a new branch for your feature or bugfix:
    ```sh
    git checkout -b feature-name
    ```
3. Make your changes and commit them:
    ```sh
    git commit -m "Description of your changes"
    ```
4. Push your changes to your fork:
    ```sh
    git push origin feature-name
    ```
5. Open a pull request on the main repository.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for more details. © Arshad Mehmood


