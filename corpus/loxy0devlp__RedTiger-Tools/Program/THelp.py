# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *

def Help(options_list, options_hidden_list=None):
    Title("Tools")

    def ColorSymbols(text):
        symbols = ["[", "]", " / ", "<", ">", "*"]
        for symbol in symbols:
            text = text.replace(symbol, f"{light_red}{symbol}{white}")
        return text
    
    def AddOptionToCategory(option, categories):
        name, description, category, function, arguments = option
        if function is None: return
        option_name = name.lower().replace(" ", "-")
        short_option = ''.join([p[0] for p in option_name.split('-') if p])
        categories[category].append((False, f"--{option_name}", f"-{short_option}", description))

        for arg, params in arguments.items():
            required = params.get("required", False)
            help_text = params.get("help", "")
            short_arg = (lambda x: x[0].lower() if len(x) == 1 else "".join(c.upper() for c in x))([p[0] for p in arg.split("-") if p])
            categories[category].append((required, f"  --{arg}", f"-{short_arg}", help_text))        

    categories = collections.defaultdict(list)

    for _, option in (options_hidden_list or {}).items(): AddOptionToCategory(option, categories)
    for _, option in options_list.items(): AddOptionToCategory(option, categories)
    if not categories: return

    for category, items in categories.items():
        Slow(f"\n  {yellow + category}:{red}")
        max_short = max(len(short) for _, _, short, _ in items)
        for required, long, short, description in items:
            star = f"{light_red}  * {red}" if required else "  "
            name = long.lstrip() if required else long
            max_long = max((len(long.lstrip()) - 2 if star.strip() else len(long.lstrip())) for _, long, _, _ in items)
            Slow(f"  {star}{name:<{max_long}} {light_red}/{red} {short:<{max_short}} : {white}{ColorSymbols(description)}{red}")

    Slow(f"""
  {yellow}Notations:
    {light_red}/ {red} : {white}Or
    {light_red}[]{red} : {white}Optional
    {light_red}<>{red} : {white}Value
    {light_red}* {red} : {white}Required""")

    if version_interface and not has_cli_args: print()
    Continue()
    Reset()


