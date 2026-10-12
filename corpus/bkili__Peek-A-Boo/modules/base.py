# modules/base_plugin.py


class BaseModule:
    def __init__(self):
        self.name = "base"
        self.description = "Base module class"
        self.category = "core"
        self.author = "022NN"
        self.author_email = "<EMAIL>"
        self.url = "<URL>"
        self.license = "<LICENSE>"
        self.version = "<VERSION>"
        self.options = {}
        self.default_options = {}
        self.required_options = []

    def set_option(self, key, value):
        """
        Allows CLI to update a module option.
        Called with: set <key> <value>
        """
        if key in self.options:
            self.options[key] = value.strip()

    def options_reload(self):
        """
        Reset all options to their default values.
        Called with: reload
        """
        self.options = self.default_options.copy()

    def requires(self):
        """
        List dependent module names to be run beforehand.
        Override this method in subclass if needed.
        """
        return []

    def print_summary(self, summary):
        for k, v in summary.items():
            print(f"{k}: {v}")
