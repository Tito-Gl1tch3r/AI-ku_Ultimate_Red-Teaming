# ----------------------------------------------------------------- #
# Here is an example script to create your own plugin for the tool. #
# ----------------------------------------------------------------- #

from Config.Utils import * # Imports all elements defined in Config.Utils, making them directly accessible in the current module.

def Register(): # Main plugin execution function. (Required)
    return {
        "name"       : "%NAME%",        # Name displayed in the menu.
        "description": "%DESCRIPTION%", # Description displayed in the menu.
        "function"   : Run,             # Function executed when the tool is called.
        "arguments"  : {                # CLI arguments automatically handled by argparse. (Leave blank if needed)
            
            # Required argument examples for correct functioning:
            # ----------------------------------------------------------------------------------------
            # * Option      : "required": True / False
            # * Description : Makes the argument required or not.
            # ----------------------------------------------------------------------------------------
            # * Option      : "type": int / float / str
            # * Description : Automatically converts the value to the specified type.
            # ----------------------------------------------------------------------------------------
            # * Option      : "help": "%TEXT%"
            # * Description : Text displayed in CLI help to explain the argument.
            # ----------------------------------------------------------------------------------------

            # Optional argument examples:
            # ----------------------------------------------------------------------------------------
            # * Option      : "nargs": 1
            # * Description : The argument must contain exactly 1 value.
            # ----------------------------------------------------------------------------------------
            # * Option      : "nargs": "+"
            # * Description : The argument must contain at least 1 value.
            # ----------------------------------------------------------------------------------------
            # * Option      : "nargs": "?"
            # * Description : The argument can contain 0 or 1 value.
            # ----------------------------------------------------------------------------------------
            # * Option      : "nargs": "*"
            # * Description : The argument can contain 0, 1, or multiple values.
            # ----------------------------------------------------------------------------------------
            # * Option      : "choices": ["%CHOICE_1%", "%CHOICE_2%", "%CHOICE_3%"]
            # * Description : Restricts allowed values to a predefined list.
            # ----------------------------------------------------------------------------------------
            # * Option      : "default": "%VALUE%"
            # * Description : Sets a default value if the argument is not provided.
            # ----------------------------------------------------------------------------------------
            # * Option      : "action": "store_true"
            # * Description : Converts the argument into a boolean. (True if present, False otherwise)

            # Example:
            "url"    : {"required": True,  "type": str,   "help": "Target: <url>"},
            "method" : {"required": False, "type": str,   "help": "HTTP method: GET / POST / HEAD", "default": "GET", "choices": ["GET", "POST", "HEAD"]},
            "timeout": {"required": False, "type": float, "help": "timeout in seconds: <timeout>",  "default": 5},
        }
    }

def Run(url=None, method=None, timeout=None): # Function used to execute the plugin.
    Title("%NAME%") # Add a title to the command window.

    # The arguments must also be accessible through interactive inputs so the script can be executed without using the command line.
    # Example:
    if not url    : url     = input("URL -> ")
    if not method : method  = input("Method -> ")
    if not timeout: timeout = float(input("Timeout -> "))

    pass # Your script..
