import os
import mmap
import re
import gzip
import bz2
import lzma
import zipfile
import argparse
import psutil
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
from tqdm import tqdm

def search_file(file_path, search_string, use_regex=False):
    """Search a file for the given string or regex."""
    matches = []
    try:
        if file_path.endswith('.gz'):
            with gzip.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                matches.extend(search_lines(f, file_path, search_string, use_regex))
        elif file_path.endswith('.bz2'):
            with bz2.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                matches.extend(search_lines(f, file_path, search_string, use_regex))
        elif file_path.endswith('.xz'):
            with lzma.open(file_path, 'rt', encoding='utf-8', errors='ignore') as f:
                matches.extend(search_lines(f, file_path, search_string, use_regex))
        elif file_path.endswith('.zip'):
            with zipfile.ZipFile(file_path, 'r') as z:
                for zip_info in z.infolist():
                    with z.open(zip_info, 'r') as f:
                        lines = (line.decode('utf-8', errors='ignore') for line in f)
                        matches.extend(search_lines(lines, file_path + "::" + zip_info.filename, search_string, use_regex))
        else:
            with open(file_path, 'rb') as f:
                with mmap.mmap(f.fileno(), 0, access=mmap.ACCESS_READ) as mm:
                    file_content = mm.read().decode('utf-8', errors='ignore')
                    matches.extend(search_lines(file_content.splitlines(), file_path, search_string, use_regex))
    except Exception:
        return []
    return matches

def search_lines(lines, file_path, search_string, use_regex=False):
    """Search lines in a file for the given string or regex."""
    matches = []
    for line_num, line in enumerate(lines, 1):
        if use_regex:
            if re.search(search_string, line):
                matches.append(f"Found in {file_path} on line {line_num}: {line.strip()}")
        else:
            if search_string in line:
                matches.append(f"Found in {file_path} on line {line_num}: {line.strip()}")
    return matches

def display_system_info(max_workers, output_file=None):
    """Display system information above the progress bars."""
    cpu_count = psutil.cpu_count(logical=True)
    mem_info = psutil.virtual_memory()
    system_info = (
        "System Information:\n"
        f"  CPUs available: {cpu_count}\n"
        f"  Total Memory: {mem_info.total // (1024 ** 2)} MB\n"
        f"  Number of Workers: {max_workers}\n"
        f"{'=' * 40}\n"
    )
    if output_file:
        output_file.write(system_info)
    else:
        print(system_info)

def display_summary(num_files_scanned, num_matches, max_workers, total_time, output_file=None):
    """Display a summary after scanning and searching are complete."""
    summary = (
        "\nSummary:\n"
        f"{'=' * 40}\n"
        f"  Total files scanned: {num_files_scanned}\n"
        f"  Total matches found: {num_matches}\n"
        f"  Number of Workers: {max_workers}\n"
        f"  Total time taken: {total_time:.2f} seconds\n"
        f"{'=' * 40}\n"
    )
    if output_file:
        output_file.write(summary)
    else:
        print(summary)

def scan_and_search(root_dir, search_string, use_regex=False, max_workers=5):
    """Scan directories and search files concurrently."""
    queue = Queue()
    results = []
    num_files_scanned = 0

    scan_pbar = tqdm(desc="Scanning files", unit="file", position=0, leave=True)
    search_pbar = tqdm(desc="Searching files", unit="file", position=1, leave=True)

    start_time = time.time()

    def producer():
        """Producer thread: Scans directories and adds files to the queue."""
        nonlocal num_files_scanned
        stack = [root_dir]
        while stack:
            current_dir = stack.pop()
            try:
                with os.scandir(current_dir) as it:
                    for entry in it:
                        if entry.is_file(follow_symlinks=False):
                            queue.put(entry.path)
                            num_files_scanned += 1
                            scan_pbar.update(1)
                        elif entry.is_dir(follow_symlinks=False):
                            stack.append(entry.path)
            except PermissionError:
                print(f"Permission denied: {current_dir}")

        queue.put(None)

    def consumer():
        """Consumer thread: Fetches files from the queue and searches them."""
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            while True:
                file_path = queue.get()
                if file_path is None:
                    break
                futures.append(executor.submit(search_file, file_path, search_string, use_regex))

            for future in as_completed(futures):
                result = future.result()
                if result:
                    results.extend(result)
                search_pbar.update(1)

    producer_thread = ThreadPoolExecutor(max_workers=1)
    producer_thread.submit(producer)
    consumer()

    scan_pbar.close()
    search_pbar.close()

    end_time = time.time()
    total_time = end_time - start_time

    return results, num_files_scanned, total_time

def format_output(matches, output_file=None):
    """Format the output for better readability."""
    output = "\nSearch Results:\n" + "=" * 40 + "\n"
    for match in matches:
        output += f"- {match}\n"
    output += "=" * 40 + "\n"

    if output_file:
        output_file.write(output)
    else:
        print(output)

def main():
    parser = argparse.ArgumentParser(description="Search for a string or regex in files within a directory.")
    parser.add_argument("search_string", type=str, help="The string or regex pattern to search for.")
    parser.add_argument("root_dir", type=str, nargs="?", default=os.getcwd(), help="The directory to search in (default is current directory).")
    parser.add_argument("--use-regex", action="store_true", help="Use regex for searching instead of a simple string match.")
    parser.add_argument("--max-workers", type=int, default=5, help="Number of worker threads for file search.")
    parser.add_argument("--output-file", type=str, help="Path to output file (optional)")

    args = parser.parse_args()

    output_file = open(args.output_file, 'w') if args.output_file else None

    display_system_info(args.max_workers, output_file)

    matches, num_files_scanned, total_time = scan_and_search(args.root_dir, args.search_string, args.use_regex, args.max_workers)

    if matches:
        format_output(matches, output_file)
    else:
        if output_file:
            output_file.write("No matches found.\n")
        else:
            print("No matches found.")

    display_summary(num_files_scanned, len(matches), args.max_workers, total_time, output_file)

    if output_file:
        output_file.close()

if __name__ == "__main__":
    main()
