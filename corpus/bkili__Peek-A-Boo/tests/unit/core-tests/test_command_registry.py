import unittest
from core.registry import COMMAND_HANDLERS


class TestCommandRegistration(unittest.TestCase):
    def test_essential_commands_are_registered(self):
        """Test that all essential commands are properly registered"""
        essential_commands = {
            "use",
            "help",
            # Add other essential commands here
        }
        registered_commands = set(COMMAND_HANDLERS.keys())

        for cmd in essential_commands:
            self.assertIn(
                cmd,
                registered_commands,
                f"Essential command '{cmd}' is not registered in COMMAND_HANDLERS",
            )

    def test_command_handlers_are_callable(self):
        """Test that registered handlers are actually callable"""
        for cmd, handler in COMMAND_HANDLERS.items():
            self.assertTrue(
                callable(handler), f"Handler for command '{cmd}' is not callable"
            )
