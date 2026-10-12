import unittest
from core.utils.progress_bar import create_spinner, progress_bar
import time
import itertools
import io
import sys


class TestProgressBarUtils(unittest.TestCase):

    def test_create_spinner_valid_names(self):
        # Ensure known spinner styles return an itertools.cycle
        spinner = create_spinner("braille")
        self.assertTrue(isinstance(spinner, itertools.cycle))
        self.assertEqual(next(spinner), "⠋")

        spinner = create_spinner("dots")
        self.assertTrue(isinstance(spinner, itertools.cycle))

        spinner = create_spinner("classic")
        self.assertTrue(isinstance(spinner, itertools.cycle))

    def test_create_spinner_invalid_fallback(self):
        # Should raise ValueError for unknown spinner style
        with self.assertRaises(ValueError):
            create_spinner("non_existing_style")

    def test_progress_bar_output_format(self):
        # Capture printed output from stdout
        captured_output = io.StringIO()
        sys.stdout = captured_output

        # Simulate progress bar usage
        spinner = itertools.cycle(["#"])
        bar_len = 20
        current = 10
        total = 100
        start_time = time.time() - 5  # simulate 5 seconds elapsed

        progress_bar(bar_len, current, total, start_time, spinner)

        # Restore stdout
        sys.stdout = sys.__stdout__

        # Analyze captured output
        output = captured_output.getvalue()
        self.assertIn("10/100", output)  # check for progress indicator
        self.assertIn("s", output)  # check for elapsed time suffix
        self.assertIn("#", output)  # check for spinner character


if __name__ == "__main__":
    unittest.main()
