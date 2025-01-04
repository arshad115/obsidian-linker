import os
import tempfile
import unittest
from obsidianlinker import find_markdown_files, link_files

class Tests(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file1_path = os.path.join(self.temp_dir.name, "Object-Oriented Programming.md")
        self.file2_path = os.path.join(self.temp_dir.name, "Functional Programming.md")
        self.file3_path = os.path.join(self.temp_dir.name, "README.md")
        self.file4_path = os.path.join(self.temp_dir.name, "Object.md")

    def tearDown(self):
        self.temp_dir.cleanup()

    def create_file(self, path, content):
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)

    def test_simple_linking(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_keep_original_case(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions Object-Oriented Programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)
        
        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_keep_original_case_1(self):
        self.create_file(self.file1_path, "This is a file about Object-Oriented Programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
        self.assertIn(self.file3_path, edited_files)

    def test_no_links(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README does not mention any programming languages.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertNotIn("[[Object-Oriented Programming]]", content)
            self.assertIn("This [[README]] does not mention any programming languages.", content)
    
    def test_link_pattern(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming, but not object oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertNotIn("[[Object Oriented Programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_wiki_link_pattern(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming, but not object oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertNotIn("[[Object Oriented Programming]]", content)
        self.assertIn(self.file3_path, edited_files)

    def test_complex_linking(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file2_path, "This is a file about functional programming.")
        self.create_file(self.file4_path, "This is a file about objects.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming, functional programming, and object.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("[[functional programming]]", content)
            self.assertIn("[[object]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_multiple_links(self):
        titles = [
            "Link1", "Link2", "Link3", "Link4", "Link5",
            "Link6", "Link7", "Link8", "Link9", "Link10"
        ]
        for title in titles:
            self.create_file(os.path.join(self.temp_dir.name, f"{title}.md"), f"This is a file about {title.lower()}.")
        self.create_file(self.file4_path, "This is a file about objects.")

        content = "This file mentions " + ", ".join(titles) + ", and object."
        self.create_file(self.file3_path, content)

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            for title in titles:
                self.assertIn(f"[[{title}]]", content)
            self.assertIn("[[object]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_exclude_partial_matches(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file4_path, "This is a file about objects.")
        self.create_file(self.file3_path, "This README mentions Object-Oriented programming and objects.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented programming]]", content)
            self.assertNotIn("[[Object]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_exclude_existing_links(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file4_path, "This is a file about objects.")
        self.create_file(self.file3_path, "This README mentions [[Object-Oriented Programming]] and [[Object]].")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content)
            self.assertIn("[[Object]]", content)
            self.assertIn("This [[README]] mentions [[Object-Oriented Programming]] and [[Object]].", content)

    def test_no_links_in_code_blocks(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, """This README mentions Object-Oriented Programming.

        ```
        This is a code block mentioning Object-Oriented Programming.
        ```
        And here is another mention of Object-Oriented Programming outside the code block.
        """)

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content)
            self.assertIn("```\n        This is a code block mentioning Object-Oriented Programming.\n        ```", content)
            self.assertNotIn("[[Object-Oriented Programming]]", content.split("```")[1])  # Ensure no link inside code block
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_metadata_intact(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, """
        ---
        title: Object-Oriented Programming
        ---
        This README is with metadata, mentions object-oriented programming.
        """)
        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("title: Object-Oriented Programming", content)
        self.assertIn(self.file3_path, edited_files)

    def test_multiple_links_multiple_lines(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file2_path, "This is a file about functional programming.")
        self.create_file(self.file3_path, """This README mentions object-oriented programming and Functional Programming.

        This README also mentions Object-Oriented Programming and functional programming.""")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content) and self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("[[Functional Programming]]", content) and self.assertIn("[[functional programming]]", content)
        self.assertIn(self.file3_path, edited_files)

    def test_no_links_in_inline_code(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions `object-oriented programming` in inline code.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("`object-oriented programming`", content)
            self.assertNotIn("[[object-oriented programming]]", content)

    def test_links_outside_inline_code(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions `object-oriented programming` in inline code and object-oriented programming outside.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        edited_files, total_links_added = link_files(markdown_files)  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("`object-oriented programming`", content)
            self.assertIn("[[object-oriented programming]] outside", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

if __name__ == "__main__":
    unittest.main()