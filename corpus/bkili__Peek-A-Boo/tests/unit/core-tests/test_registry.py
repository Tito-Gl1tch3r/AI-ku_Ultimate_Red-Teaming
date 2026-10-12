import unittest
from core.registry import COMMAND_HANDLERS, register_command


class TestRegistry(unittest.TestCase):
    def setUp(self):
        # Her testten önce temizle
        COMMAND_HANDLERS.clear()

    def test_register_command_adds_function_to_dict(self):
        @register_command("hello")
        def dummy_command(args, shared_data):
            return "hi"

        self.assertIn("hello", COMMAND_HANDLERS)
        self.assertEqual(COMMAND_HANDLERS["hello"].__name__, "dummy_command")

    def test_register_multiple_commands(self):
        @register_command("cmd1")
        def one(args, shared_data):
            pass

        @register_command("cmd2")
        def two(args, shared_data):
            pass

        self.assertIn("cmd1", COMMAND_HANDLERS)
        self.assertIn("cmd2", COMMAND_HANDLERS)

    def test_overwriting_existing_command(self):
        @register_command("same")
        def first(args, shared_data):
            return "first"

        @register_command("same")
        def second(args, shared_data):
            return "second"

        self.assertEqual(COMMAND_HANDLERS["same"]([], {}), "second")


if __name__ == "__main__":
    unittest.main()
