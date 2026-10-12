import re
import json
import asyncio
import argparse
import warnings

from concurrent.futures import ThreadPoolExecutor

class AsyncRegexChecker:
    def __init__(self, jsonl_file):
        """Load regex patterns from a JSONL file."""
        self.patterns = self.load_patterns(jsonl_file)
        self.executor = ThreadPoolExecutor() 
    
    def compile_pattern(self, pattern):
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=DeprecationWarning)
            try:
                return re.compile(pattern) 
            except re.error as e:
                print(f"Regex compilation error for pattern: {pattern[:50]}... -> {e}")
            return None 

    def load_patterns(self, jsonl_file):
        """Load all regex patterns from a JSONL file."""
        patterns = []
        with open(jsonl_file, 'r', encoding='utf-8') as file:
            for line in file:
                rule = json.loads(line.strip())
                patterns.append({'name': rule['name'], 'id': rule['id'], 'pattern': self.compile_pattern(rule['pattern'])})  # Precompile regex
        return patterns

    async def check_document(self, document):
        """Check document against regex rules asynchronously."""
        loop = asyncio.get_running_loop()
        tasks = [
            loop.run_in_executor(self.executor, self.match_pattern, rule, document)
            for rule in self.patterns
        ]
        results = await asyncio.gather(*tasks)
        return [match for match in results if match]  

    def match_pattern(self, rule, document):
        """Match a single regex pattern synchronously (runs in a thread pool)."""
        matches = [
            {'rule_name': rule['name'], 'rule_id': rule['id'], 'match': m.group(), 'start': m.start(), 'end': m.end()}
            for m in rule['pattern'].finditer(document)
        ]
        return matches if matches else None


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Scan a document/string for secrets.")
    parser.add_argument("--doc", type=str, required=True, help="The document to be scanned")

    args = parser.parse_args()

    checker = AsyncRegexChecker("./regexRules.jsonl")
    np_secret = asyncio.run(checker.check_document(args.doc))
    print("Scan Results:", np_secret)