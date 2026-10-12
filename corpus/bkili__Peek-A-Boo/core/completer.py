from pathlib import Path
from prompt_toolkit.completion import Completer, NestedCompleter, PathCompleter
from core.utils.listing import list_modules, list_plugins, list_exploits
from core.state import get_current_module
from core.config_ops import load_global_config
from prompt_toolkit.document import Document

global_config = load_global_config()


def get_config_path_completions(text, complete_event):
    config_path = Path("configs") / text  # start from configs/
    completer = PathCompleter(
        get_paths=lambda: [config_path],
        expanduser=True,
        only_directories=False,
    )
    return completer.get_completions(Document(text), complete_event)


class SmartCompleter(Completer):
    def __init__(self):
        self.path_completer = PathCompleter(expanduser=True, only_directories=False)
        self.update_nested()

    def update_nested(self):
        current = get_current_module()
        self.base_completer = NestedCompleter.from_nested_dict(
            {
                "exit": None,
                "help": None,
                "use": {
                    mod: None
                    for mod in list_modules() + list_plugins() + list_exploits()
                },
                "info": {
                    mod: None
                    for mod in list_modules() + list_plugins() + list_exploits()
                },
                "list": {"modules": None, "plugins": None, "exploits": None},
                "search": None,
                "run": None,
                "reload": None,
                "save": {"config": None},
                "load": {"config": None, "module": None},
                "show": {"options": None, "summary": None},
                "set": {opt: None for opt in current.options} if current else {},
                "history": None,
                "clear": {"history": None},
            }
        )

    def get_completions(self, document, complete_event):
        words = document.text.strip().split()

        if len(words) >= 2 and words[0] == "load" and words[1] == "config":
            # Show completions from configs/ instead of current dir
            partial = document.text.partition("config")[2].strip()
            return get_config_path_completions(partial, complete_event)

        return self.base_completer.get_completions(document, complete_event)
