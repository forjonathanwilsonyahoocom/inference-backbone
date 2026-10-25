import unittest
from pathlib import Path
import json
import sys
import os

# Import the main module from the app package
# The script is not a package, so we add the app directory to sys.path
sys.path.append(str(Path(__file__).parent))
from main import main

class TestTextAnalysis(unittest.TestCase):
    def test_no_files(self):
        # Create a temporary directory with no matching files
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            # Run the main function with workdir pointing to the empty dir
            # Capture stdout and stderr
            from io import StringIO
            stdout = StringIO()
            stderr = StringIO()
            old_stdout, old_stderr = sys.stdout, sys.stderr
            sys.stdout, sys.stderr = stdout, stderr
            try:
                main(["--workdir", tmpdir, "--ext", "*.txt"])
            finally:
                sys.stdout, sys.stderr = old_stdout, old_stderr
            # The script should exit with no files found but not raise
            self.assertIn("No files found to analyze.", stderr.getvalue())

    def test_single_file(self):
        # Create a temporary file with some text
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = Path(tmpdir) / "sample.txt"
            file_path.write_text("Hello world! This is a test. Hello again.")
            # Run the main function with workdir and file
            from io import StringIO
            stdout = StringIO()
            stderr = StringError?\n