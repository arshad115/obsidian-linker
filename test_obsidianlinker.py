import os
import tempfile
import unittest
from obsidianlinker import find_markdown_files, link_files
from obsidian_linker.scan import path_matches_globs
from obsidian_linker.parallel import resolve_worker_count
from obsidian_linker.state import default_state_path, files_to_process

class Tests(unittest.TestCase):

    def run_link(self, markdown_files, **kwargs):
        return link_files(markdown_files, show_progress=False, **kwargs)

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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_keep_original_case(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions Object-Oriented Programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files
        
        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_keep_original_case_1(self):
        self.create_file(self.file1_path, "This is a file about Object-Oriented Programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
        self.assertIn(self.file3_path, edited_files)

    def test_no_links(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README does not mention any programming languages.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertNotIn("[[Object-Oriented Programming]]", content)
            self.assertIn("This [[README]] does not mention any programming languages.", content)
    
    def test_link_pattern(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming, but not object oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertNotIn("[[Object Oriented Programming]]", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_wiki_link_pattern(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming, but not object oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented programming]]", content)
            self.assertNotIn("[[Object]]", content)
            self.assertIn("objects", content)  # Ensure 'objects' is not linked
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_exclude_existing_links(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file4_path, "This is a file about objects.")
        self.create_file(self.file3_path, "This README mentions [[Object-Oriented Programming]] and [[Object]].")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content)
            self.assertIn("```\n        This is a code block mentioning Object-Oriented Programming.\n        ```", content)
            self.assertNotIn("[[Object-Oriented Programming]]", content.split("```")[1])  # Ensure no link inside code block
            self.assertNotIn("CODE_BLOCK", content)
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
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("title: Object-Oriented Programming", content)
            self.assertNotIn("METADATA_SECTION", content)
        self.assertIn(self.file3_path, edited_files)

    def test_multiple_links_multiple_lines(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file2_path, "This is a file about functional programming.")
        self.create_file(self.file3_path, """This README mentions object-oriented programming and Functional Programming.

        This README also mentions Object-Oriented Programming and functional programming.""")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[Object-Oriented Programming]]", content) and self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("[[Functional Programming]]", content) and self.assertIn("[[functional programming]]", content)
        self.assertIn(self.file3_path, edited_files)

    def test_no_links_in_inline_code(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions `object-oriented programming` in inline code.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("`object-oriented programming`", content)
            self.assertNotIn("[[object-oriented programming]]", content)
            self.assertNotIn("INLINE_CODE", content)

    def test_links_outside_inline_code(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions `object-oriented programming` in inline code and object-oriented programming outside.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)
        edited_files = result.edited_files  # Capture the return value

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("`object-oriented programming`", content)
            self.assertIn("[[object-oriented programming]] outside", content)
            self.assertNotIn("INLINE_CODE", content)
        self.assertIn(self.file3_path, edited_files)  # Verify the file was edited

    def test_excludes_obsidian_directory(self):
        obsidian_dir = os.path.join(self.temp_dir.name, '.obsidian')
        os.makedirs(obsidian_dir)
        self.create_file(os.path.join(obsidian_dir, 'Hidden.md'), 'hidden note')
        self.create_file(self.file3_path, 'visible note')

        markdown_files = find_markdown_files(self.temp_dir.name)
        paths = {os.path.basename(p) for p in markdown_files}
        self.assertIn('README.md', paths)
        self.assertNotIn('Hidden.md', paths)

    def test_dry_run_does_not_modify_files(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        original = "This README mentions object-oriented programming."
        self.create_file(self.file3_path, original)

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files, dry_run=True)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), original)
        self.assertGreater(result.total_links_added, 0)
        self.assertTrue(any(c.file == self.file3_path for c in result.changes))

    def test_no_self_links(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming and README.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files, no_self_links=True)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertIn("README", content)
            self.assertNotIn("[[README]]", content)

    def test_output_mirror_leaves_vault_unchanged(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        original = "This README mentions object-oriented programming."
        self.create_file(self.file3_path, original)
        output_dir = os.path.join(self.temp_dir.name, 'out')

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(
            markdown_files,
            vault_root=self.temp_dir.name,
            output_dir=output_dir,
        )

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), original)

        mirrored = os.path.join(output_dir, 'README.md')
        self.assertTrue(os.path.isfile(mirrored))
        with open(mirrored, 'r', encoding='utf-8') as f:
            self.assertIn("[[object-oriented programming]]", f.read())
        self.assertIn(self.file3_path, result.edited_files)

    def test_backup_before_overwrite(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files, backup=True)

        backup_path = self.file3_path + '.bak'
        self.assertTrue(os.path.isfile(backup_path))
        with open(backup_path, 'r', encoding='utf-8') as f:
            self.assertIn("object-oriented programming", f.read())
            self.assertNotIn("[[object-oriented programming]]", f.read())

    def test_alias_links_to_canonical_note(self):
        self.create_file(
            self.file1_path,
            "---\naliases:\n  - OOP\n---\nNote about OOP.",
        )
        self.create_file(self.file3_path, "This README discusses OOP.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertIn("[[Object-Oriented Programming|OOP]]", f.read())

    def test_no_links_inside_embeds(self):
        self.create_file(self.file1_path, "Note body.")
        self.create_file(
            self.file3_path,
            "See ![[Object-Oriented Programming]] for details.",
        )

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertEqual("See ![[Object-Oriented Programming]] for details.", f.read())

    def test_no_links_inside_markdown_links(self):
        self.create_file(self.file1_path, "Note body.")
        self.create_file(
            self.file3_path,
            "Read [Object-Oriented Programming](https://example.com) here.",
        )

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertEqual(
                "Read [Object-Oriented Programming](https://example.com) here.",
                f.read(),
            )

    def test_skip_heading_lines_by_default(self):
        self.create_file(self.file1_path, "Note body.")
        self.create_file(
            self.file3_path,
            "# Object-Oriented Programming\n\nBody mentions object-oriented programming.",
        )

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("# Object-Oriented Programming\n", content)
            self.assertIn("[[object-oriented programming]]", content)

    def test_include_and_exclude_globs(self):
        notes_dir = os.path.join(self.temp_dir.name, 'notes')
        templates_dir = os.path.join(self.temp_dir.name, 'templates')
        os.makedirs(notes_dir)
        os.makedirs(templates_dir)
        self.create_file(os.path.join(notes_dir, 'Topic.md'), 'topic note')
        self.create_file(os.path.join(templates_dir, 'Topic.md'), 'template topic')
        self.create_file(os.path.join(notes_dir, 'Daily.md'), 'daily note')
        self.create_file(self.file3_path, 'README mentions Topic.')

        markdown_files = find_markdown_files(
            self.temp_dir.name,
            include_globs=['notes/**'],
            exclude_globs=['notes/Daily.md'],
        )
        rel_paths = {
            os.path.relpath(path, self.temp_dir.name).replace(os.sep, '/')
            for path in markdown_files
        }
        self.assertIn('notes/Topic.md', rel_paths)
        self.assertNotIn('notes/Daily.md', rel_paths)
        self.assertNotIn('templates/Topic.md', rel_paths)

    def test_path_matches_globs(self):
        self.assertTrue(path_matches_globs('notes/a.md', ['notes/**'], []))
        self.assertFalse(path_matches_globs('templates/a.md', ['notes/**'], []))
        self.assertFalse(path_matches_globs('notes/a.md', [], ['notes/**']))

    def test_ignore_phrase(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files, ignore_phrases={'readme'})

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[object-oriented programming]]", content)
            self.assertNotIn("[[README]]", content)

    def test_min_title_length(self):
        self.create_file(self.file4_path, "Object note.")
        self.create_file(self.file3_path, "This README mentions object.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files, min_title_length=10)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertNotIn("[[object]]", f.read())

    def test_incremental_skips_unchanged_files(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files, vault_root=self.temp_dir.name, incremental=True)

        state_path = default_state_path(self.temp_dir.name)
        self.assertTrue(os.path.isfile(state_path))

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            linked = f.read()

        result = self.run_link(
            markdown_files,
            vault_root=self.temp_dir.name,
            incremental=True,
        )
        self.assertEqual(result.total_links_added, 0)
        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertEqual(f.read(), linked)

    def test_incremental_reprocesses_all_when_note_added(self):
        self.create_file(self.file1_path, "This is a file about object-oriented programming.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        self.run_link(markdown_files, vault_root=self.temp_dir.name, incremental=True)

        self.create_file(self.file2_path, "Functional programming note.")
        self.create_file(self.file3_path, "This README mentions object-oriented programming and functional programming.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files, vault_root=self.temp_dir.name, incremental=True)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            content = f.read()
            self.assertIn("[[functional programming]]", content)
        self.assertGreater(result.total_links_added, 0)

    def test_files_to_process_detects_changes(self):
        stable = os.path.join(self.temp_dir.name, 'stable.md')
        self.create_file(stable, 'stable')
        stable_mtime = os.path.getmtime(stable)
        state = {
            'version': 1,
            'paths': [os.path.abspath(stable)],
            'files': {os.path.abspath(stable): stable_mtime},
        }
        self.assertEqual(files_to_process([stable], state, True), set())
        self.assertIsNone(
            files_to_process([stable, os.path.join(self.temp_dir.name, 'missing.md')], state, True)
        )

    def create_file_at(self, path, content):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as handle:
            handle.write(content)

    def test_parallel_jobs_matches_sequential(self):
        readme_body = (
            "This README mentions object-oriented programming and functional programming."
        )
        with tempfile.TemporaryDirectory() as seq_dir, tempfile.TemporaryDirectory() as par_dir:
            for base in (seq_dir, par_dir):
                self.create_file_at(
                    os.path.join(base, "Object-Oriented Programming.md"),
                    "This is a file about object-oriented programming.",
                )
                self.create_file_at(
                    os.path.join(base, "Functional Programming.md"),
                    "This is a file about functional programming.",
                )
                self.create_file_at(os.path.join(base, "README.md"), readme_body)

            seq_files = find_markdown_files(seq_dir)
            par_files = find_markdown_files(par_dir)
            self.run_link(seq_files, jobs=1)
            self.run_link(par_files, jobs=4)

            with open(os.path.join(seq_dir, "README.md"), 'r', encoding='utf-8') as handle:
                sequential_content = handle.read()
            with open(os.path.join(par_dir, "README.md"), 'r', encoding='utf-8') as handle:
                parallel_content = handle.read()
            self.assertEqual(sequential_content, parallel_content)

    def test_resolve_worker_count(self):
        self.assertGreaterEqual(resolve_worker_count(0), 1)
        self.assertEqual(resolve_worker_count(3), 3)

    def test_duplicate_basenames_use_longest_path(self):
        short_dir = os.path.join(self.temp_dir.name, 'a')
        long_dir = os.path.join(self.temp_dir.name, 'a', 'nested', 'deep')
        os.makedirs(long_dir)
        self.create_file(os.path.join(short_dir, 'Topic.md'), 'short path note')
        self.create_file(os.path.join(long_dir, 'Topic.md'), 'long path note')
        self.create_file(self.file3_path, "This README mentions Topic.")

        markdown_files = find_markdown_files(self.temp_dir.name)
        result = self.run_link(markdown_files)

        with open(self.file3_path, 'r', encoding='utf-8') as f:
            self.assertIn("[[Topic]]", f.read())
        self.assertTrue(any('Duplicate note title' in w for w in result.warnings))

if __name__ == "__main__":
    unittest.main()