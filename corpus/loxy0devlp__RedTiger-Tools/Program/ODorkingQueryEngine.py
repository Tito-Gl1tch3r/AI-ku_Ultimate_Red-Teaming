# Copyright (c) RedTiger by Loxy0devlp
# Licensed under the MIT License.
# See LICENSE file in the project root for full license text.

from Config.Utils import *
import webbrowser
import urllib.parse

output_google = f"""
  {BEFORE}00{AFTER} Launch search
  {BEFORE}01{AFTER}{white} inurl      : Match only inside URL. (path, parameters)
  {BEFORE}02{AFTER}{white} intitle    : Match only inside HTML <title> tag.
  {BEFORE}03{AFTER}{white} site       : Restrict results to a specific domain or subdomain.
  {BEFORE}04{AFTER}{white} ""         : Exact phrase match. (no variation or reordering)
  {BEFORE}05{AFTER}{white} -          : Strictly exclude a keyword or pattern.
  {BEFORE}06{AFTER}{white} filetype   : Filter by indexed file extension.
  {BEFORE}07{AFTER}{white} intext     : Keyword must appear in page content.
  {BEFORE}08{AFTER}{white} OR         : Logical OR operator.
  {BEFORE}09{AFTER}{white} ()         : Logical grouping.
  {BEFORE}10{AFTER}{white} ..         : Numeric range.
  {BEFORE}11{AFTER}{white} AROUND(n)  : Proximity search.
  {BEFORE}12{AFTER}{white} define     : Dictionary definition.
  {BEFORE}13{AFTER}{white} *          : Wildcard.
  {BEFORE}14{AFTER}{white} after      : Date filter (News).
  {BEFORE}15{AFTER}{white} before     : Date filter (News).
"""

output_bing = f"""
  {BEFORE}00{AFTER} Launch search
  {BEFORE}01{AFTER}{white} inurl      : URL keyword match (partial support)
  {BEFORE}02{AFTER}{white} intitle    : Title keyword match (partial support)
  {BEFORE}03{AFTER}{white} site       : Domain restriction
  {BEFORE}04{AFTER}{white} ""         : Exact phrase match
  {BEFORE}05{AFTER}{white} -          : Exclude keyword
  {BEFORE}06{AFTER}{white} filetype   : File type filter
  {BEFORE}07{AFTER}{white} OR         : Logical OR operator
  {BEFORE}08{AFTER}{white} ()         : Grouping
  {BEFORE}09{AFTER}{white} ..         : Numeric range
  {BEFORE}10{AFTER}{white} define     : Dictionary lookup
  {BEFORE}11{AFTER}{white} *          : Wildcard
"""

output_duckduckgo = f"""
  {BEFORE}00{AFTER} Launch search
  {BEFORE}01{AFTER}{white} site       : Domain restriction
  {BEFORE}02{AFTER}{white} ""         : Exact phrase match
  {BEFORE}03{AFTER}{white} -          : Exclude keyword
  {BEFORE}04{AFTER}{white} OR         : Logical OR operator
  {BEFORE}05{AFTER}{white} ()         : Grouping
  {BEFORE}06{AFTER}{white} define     : Dictionary lookup
  {BEFORE}07{AFTER}{white} *          : Wildcard
"""

url_google     = "https://www.google.com/search?q="
url_bing       = "https://www.bing.com/search?q="
url_duckduckgo = "https://duckduckgo.com/?q="

def AddDataBase(request):
    if not isinstance(request, str) or not request.strip():
        Error("Invalid request.")
        return
    database.append(request.strip())
    Info("Query added.")

def InputClean(text):
    value = Input(text).strip()
    return " ".join(value.split())

def BuildRequest(choice, engine):
    if engine == "Google":
        mapping = {
            '1':  lambda: f"inurl:{InputClean('Keyword -> ')}",
            '2':  lambda: f"intitle:{InputClean('Keyword -> ')}",
            '3':  lambda: f"site:{InputClean('Domain -> ')}",
            '4':  lambda: f"\"{InputClean('Exact keyword -> ')}\"",
            '5':  lambda: f"-{InputClean('Exclude keyword -> ')}",
            '6':  lambda: f"filetype:{InputClean('Extension -> ')}",
            '7':  lambda: f"intext:{InputClean('Keyword -> ')}",
            '8':  lambda: " OR ".join([k.strip() for k in InputClean('Keywords -> ').split(",") if k.strip()]),
            '9':  lambda: f"({InputClean('Group -> ')})",
            '10': lambda: f"{InputClean('Min -> ')}..{InputClean('Max -> ')}",
            '11': lambda: f"({InputClean('Left -> ')}) AROUND({InputClean('Distance -> ')}) ({InputClean('Right -> ')})",
            '12': lambda: f"define:{InputClean('Word -> ')}",
            '13': lambda: f"* {InputClean('Keyword -> ')} *",
            '14': lambda: f"after:{InputClean('YYYY-MM-DD -> ')}",
            '15': lambda: f"before:{InputClean('YYYY-MM-DD -> ')}",
        }

    elif engine == "Bing":
        mapping = {
            '1':  lambda: f"inurl:{InputClean('Keyword -> ')}",
            '2':  lambda: f"intitle:{InputClean('Keyword -> ')}",
            '3':  lambda: f"site:{InputClean('Domain -> ')}",
            '4':  lambda: f"\"{InputClean('Exact keyword -> ')}\"",
            '5':  lambda: f"-{InputClean('Exclude keyword -> ')}",
            '6':  lambda: f"filetype:{InputClean('Extension -> ')}",
            '7':  lambda: " OR ".join([k.strip() for k in InputClean('Keywords -> ').split(",") if k.strip()]),
            '8':  lambda: f"({InputClean('Group -> ')})",
            '9':  lambda: f"{InputClean('Min -> ')}..{InputClean('Max -> ')}",
            '10': lambda: f"define:{InputClean('Word -> ')}",
            '11': lambda: f"* {InputClean('Keyword -> ')} *",
        }
    
    elif engine == "Duckduckgo":
        mapping = {
            '1':  lambda: f"site:{InputClean('Domain -> ')}",
            '2':  lambda: f"\"{InputClean('Exact keyword -> ')}\"",
            '3':  lambda: f"-{InputClean('Exclude keyword -> ')}",
            '4':  lambda: " OR ".join([k.strip() for k in InputClean('Keywords -> ').split(",") if k.strip()]),
            '5':  lambda: f"({InputClean('Group -> ')})",
            '6':  lambda: f"{InputClean('Word -> ')} definition",
            '7':  lambda: InputClean('Keyword -> '),
        }

    return mapping.get(choice)

def DorkingQueryEngine(engine=None):
    Title("Dorking Query Engine")

    global database
    database = []

    engine_output = {
        "Google"     : output_google,
        "Bing"       : output_bing,
        "Duckduckgo" : output_duckduckgo
    }
    
    engine_url = {
        "Google"     : url_google,
        "Bing"       : url_bing,
        "Duckduckgo" : url_duckduckgo
    }
    
    if not engine:
        Info("Search engine:")
        Slow(f"""
  {BEFORE}01{AFTER}{white} Google
  {BEFORE}02{AFTER}{white} Bing
  {BEFORE}03{AFTER}{white} Duckduckgo
""")
        engine = Input("Engine [-e] -> ").strip().lower()

    try:
        if   int(engine) == 1: engine = "Google"
        elif int(engine) == 2: engine = "Bing"
        elif int(engine) == 3: engine = "Duckduckgo"
        else: ErrorChoice()
    except (ValueError, TypeError):
        if   engine == "google"    : engine = "Google"
        elif engine == "bing"      : engine = "Bing"
        elif engine == "duckduckgo": engine = "Duckduckgo"
        else: ErrorChoice()
    
    output = engine_output.get(engine)
    if output: 
        Info(f"Operators for {engine}:")
        Slow(output)
    else: ErrorChoice()

    Info("Multiple operators allowed. \"00\" to execute.")

    while True:
        choice = Input(f"Method -> {reset}").zfill(2)
        if choice == '00': break

        builder = BuildRequest(choice.lstrip('0'), engine)
        if builder:
            try:
                request = builder().strip()
                if request: AddDataBase(request)
                else: Error("Empty input.")
            except Exception as e: Error(f"Build error: {white}{e}")
        else: Error("Invalid choice.")

    if not database:
        Error("No query.")
        Continue()
        Reset()
        return

    total_request = " ".join(database)
    encoded_query = urllib.parse.quote(total_request)
    final_url     = engine_url[engine] + encoded_query

    Info(f"Preview: {white + total_request}")
    Info(f"Url: {white + final_url}")
    confirm = Input("Confirm (y/n) -> ").lower()
    if confirm in affirmative:
        try:
            webbrowser.open(final_url)
            Info("Browser launched.")
        except Exception as e: Error(f"Browser error: {white}{e}")
    else: Info("Cancelled.")

    Continue()
    Reset()