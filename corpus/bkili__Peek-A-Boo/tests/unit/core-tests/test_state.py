import unittest
from core.state import get_current_module, set_current_module


class DummyModule:
    def __init__(self, name):
        self.name = name


class TestState(unittest.TestCase):
    def test_get_and_set_current_module(self):
        dummy = DummyModule("mod_test")
        set_current_module(dummy)
        self.assertEqual(get_current_module(), dummy)
        self.assertEqual(get_current_module().name, "mod_test")

    def test_set_none_as_module(self):
        set_current_module(None)
        self.assertIsNone(get_current_module())


if __name__ == "__main__":
    unittest.main()
