import unittest
from core.utils.formatter import printc, colorize, console
from rich.text import Text


class TestFormatterUtils(unittest.TestCase):

    def test_colorize_basic(self):
        text = colorize("Hello World", "green", "bold")
        self.assertIsInstance(text, Text)
        self.assertEqual(str(text), "Hello World")
        self.assertEqual(text.style, "green bold")

    def test_colorize_with_unknown_tag(self):
        text = colorize("[weird] tag", "cyan")
        self.assertIsInstance(text, Text)
        self.assertEqual(str(text), "[weird] tag")

    def test_printc_info_level(self):
        with console.capture() as capture:
            printc("This is info", level="info")
        output = capture.get()
        self.assertIn("This is info", output)

    def test_printc_error_level(self):
        with console.capture() as capture:
            printc("Something failed", level="error")
        output = capture.get()
        self.assertIn("Something failed", output)

    def test_printc_success_level(self):
        with console.capture() as capture:
            printc("Done!", level="success")
        output = capture.get()
        self.assertIn("Done!", output)


if __name__ == "__main__":
    unittest.main()
