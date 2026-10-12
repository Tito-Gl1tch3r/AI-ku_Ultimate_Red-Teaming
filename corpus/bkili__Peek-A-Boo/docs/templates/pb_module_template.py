import logging
from modules.base import BaseModule
from core.utils.formatter import printc


class Module(BaseModule):
    def __init__(self):
        # Initialize shared base functionality (options, logging, etc.)
        super().__init__()

        # The name of the module (used in CLI prompt and logs)
        self.name = "your_module_name"

        # Short description of what this module does
        self.description = "Describe what this module is responsible for."

        # Category of the module, e.g., 'recon', 'privilege_escalation', 'utility'
        self.category = "<Category>"

        # Author information
        self.author = "<Name>"
        self.author_email = "<E-mail>"
        self.url = "<URL>"

        # License and version
        self.license = "<License>"
        self.version = "<Version>"

        # Default options for the module
        self.default_options = {"example_option": "default_value"}

        # List of required options (CLI will show them as Required = yes)
        self.required_options = ["example_option"]

        self.options = self.default_options.copy()

    def requires(self):
        """
        Return a list of module names that must run before this one.
        CLI will automatically run them and pass their output via shared_data.

        Example:
        return ["pb_wayback"]  # This module depends on pb_wayback output
        """
        return []

    def run(self, shared_data):
        """
        Main logic of the module.
        shared_data is used to exchange data with other modules.
        You can read values written by previous modules or store your output.
        """
        printc(f"[{self.name}] Running module...", level="info")
        logging.info(f"[{self.name}] Module started.")

        try:
            # Example: Read from shared_data if previous module exists
            previous_value = shared_data.get("previous_module_output")
            if previous_value:
                printc(
                    f"[{self.name}] Received from previous module: {previous_value}",
                    level="info",
                )

            # Example: Read this module's options
            example_value = self.options.get("example_option")
            printc(f"[{self.name}] example_option = {example_value}", level="module")

            # [DO WORK HERE...]

            # Example: Store result into shared_data for next modules
            shared_data["your_module_output"] = "some_value"
            printc(
                f"[{self.name}] Shared data updated with key 'your_module_output'",
                level="info",
            )

        except Exception as e:
            printc(f"[{self.name}] Error during execution: {e}", level="error")
            logging.error(f"[{self.name}] Exception: {e}")

        logging.info(f"[{self.name}] Module finished.")

    def print_summary(self, summary):
        """
        Optionally override this to pretty print output stored in shared_data.
        Called automatically after module run if summary exists.
        """
        try:
            printc(f"Summary for {self.name}:", level="headline")
            printc(str(summary), level="info")
        except Exception as e:
            printc(f"[{self.name}] Failed to print summary: {e}", level="error")
