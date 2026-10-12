#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ultra-Fast Multi-Threaded Proxy Checker
Supports HTTP, HTTPS, SOCKS4, SOCKS5 proxies
Optimized for checking millions of proxies quickly
By: Scav-engeR
"""

import socket
import threading
import time
import sys
import os
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
import argparse
import signal

class UltraFastProxyChecker:
    def __init__(self, threads=500, timeout=3, output_file="working_proxies.txt"):
        self.threads = threads
        self.timeout = timeout
        self.output_file = output_file
        self.proxies = []
        self.working_proxies = []
        self.checked_count = 0
        self.lock = threading.Lock()
        self.stop_event = threading.Event()

        # Statistics
        self.stats = {
            'total': 0,
            'working': 0,
            'failed': 0,
            'start_time': None
        }

        # Setup signal handler for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)

    def signal_handler(self, signum, frame):
        """Handle Ctrl+C gracefully"""
        print(f"\n\n{self.colorize('[!] Stopping proxy checker...', 'yellow')}")
        self.stop_event.set()

    def colorize(self, text, color):
        """Add color to output"""
        colors = {
            'red': '\033[91m',
            'green': '\033[92m',
            'yellow': '\033[93m',
            'blue': '\033[94m',
            'magenta': '\033[95m',
            'cyan': '\033[96m',
            'white': '\033[97m',
            'reset': '\033[0m'
        }
        return f"{colors.get(color, '')}{text}{colors['reset']}"

    def load_proxies(self, filename):
        """Load proxies from file"""
        try:
            with open(filename, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()

            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    # Clean and validate proxy format
                    proxy = line.split()[0]  # Take first part if there are comments
                    if ':' in proxy:
                        self.proxies.append(proxy)

            self.stats['total'] = len(self.proxies)
            print(f"{self.colorize('[+]', 'green')} Loaded {len(self.proxies)} proxies from {filename}")
            return True
        except FileNotFoundError:
            print(f"{self.colorize('[!]', 'red')} File {filename} not found!")
            return False
        except Exception as e:
            print(f"{self.colorize('[!]', 'red')} Error loading proxies: {e}")
            return False

    def test_proxy(self, proxy):
        """Test a single proxy using socket connection"""
        if self.stop_event.is_set():
            return None

        try:
            # Parse proxy
            if '://' in proxy:
                proxy = proxy.split('://', 1)[1]

            host, port = proxy.split(':')
            port = int(port)

            # Create socket
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)

            # Test connection
            start_time = time.time()
            result = sock.connect_ex((host, port))
            end_time = time.time()

            sock.close()

            if result == 0:
                response_time = (end_time - start_time) * 1000
                return {
                    'proxy': proxy,
                    'response_time': response_time,
                    'type': self.detect_proxy_type(port)
                }

        except Exception:
            pass

        return None

    def detect_proxy_type(self, port):
        """Detect proxy type based on port number"""
        port_types = {
            80: 'HTTP',
            8080: 'HTTP',
            3128: 'HTTP',
            8888: 'HTTP',
            1080: 'SOCKS',
            1081: 'SOCKS',
            443: 'HTTPS',
            8443: 'HTTPS'
        }
        return port_types.get(port, 'UNKNOWN')

    def progress_bar(self, current, total, prefix='', suffix='', length=50, fill='█'):
        """Display progress bar"""
        percent = f"{100 * (current / float(total)):.1f}"
        filled_length = int(length * current // total)
        bar = fill * filled_length + '-' * (length - filled_length)

        print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
        if current == total:
            print()

    def check_worker(self, proxies_chunk):
        """Worker function for checking proxies"""
        local_working = []

        for proxy in proxies_chunk:
            if self.stop_event.is_set():
                break

            result = self.test_proxy(proxy)
            if result:
                local_working.append(result)

            with self.lock:
                self.checked_count += 1
                self.stats['working' if result else 'failed'] += 1

                # Update progress every 100 proxies
                if self.checked_count % 100 == 0 or self.checked_count == self.stats['total']:
                    elapsed = time.time() - self.stats['start_time']
                    speed = self.checked_count / elapsed if elapsed > 0 else 0
                    print(f"\r{self.colorize('[PROGRESS]', 'cyan')} "
                          f"Checked: {self.checked_count}/{self.stats['total']} "
                          f"({(self.checked_count/self.stats['total']*100):.1f}%) "
                          f"| Working: {len(self.working_proxies) + len(local_working)} "
                          f"| Speed: {speed:.0f} proxies/sec", end='', flush=True)

        return local_working

    def check_proxies(self):
        """Main proxy checking function"""
        if not self.proxies:
            print(f"{self.colorize('[!]', 'red')} No proxies to check!")
            return False

        print(f"{self.colorize('[+]', 'green')} Starting proxy check with {self.threads} threads...")
        print(f"{self.colorize('[+]', 'green')} Timeout: {self.timeout} seconds")
        print(f"{self.colorize('[+]', 'green')} Total proxies: {len(self.proxies)}")
        print(f"{self.colorize('[*]', 'yellow')} Press Ctrl+C to stop\n")

        self.stats['start_time'] = time.time()
        self.checked_count = 0
        self.stats['working'] = 0
        self.stats['failed'] = 0

        # Split proxies into chunks for threads
        chunk_size = max(1, len(self.proxies) // self.threads)
        proxy_chunks = [self.proxies[i:i + chunk_size] for i in range(0, len(self.proxies), chunk_size)]

        # Use ThreadPoolExecutor for better control
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            # Submit all tasks
            future_to_chunk = {executor.submit(self.check_worker, chunk): chunk for chunk in proxy_chunks}

            # Process completed tasks
            for future in as_completed(future_to_chunk):
                if self.stop_event.is_set():
                    break

                try:
                    working_results = future.result()
                    self.working_proxies.extend(working_results)
                except Exception as e:
                    print(f"{self.colorize('[!]', 'red')} Worker error: {e}")

        return True

    def save_results(self):
        """Save working proxies to file"""
        try:
            # Sort by response time for better proxies first
            sorted_proxies = sorted(self.working_proxies, key=lambda x: x['response_time'])

            with open(self.output_file, 'w') as f:
                for proxy_info in sorted_proxies:
                    f.write(f"{proxy_info['proxy']}\n")

            # Save detailed results
            detailed_file = self.output_file.replace('.txt', '_detailed.txt')
            with open(detailed_file, 'w') as f:
                f.write(f"Proxy Checker Results - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 50 + "\n")
                f.write(f"Total proxies checked: {self.stats['total']}\n")
                f.write(f"Working proxies: {len(self.working_proxies)}\n")
                f.write(f"Success rate: {(len(self.working_proxies)/self.stats['total']*100):.2f}%\n")

                elapsed = time.time() - self.stats['start_time']
                f.write(f"Time taken: {elapsed:.2f} seconds\n")
                f.write(f"Average speed: {self.stats['total']/elapsed:.0f} proxies/sec\n\n")

                f.write("Working proxies (sorted by response time):\n")
                f.write("-" * 30 + "\n")
                for proxy_info in sorted_proxies:
                    f.write(f"{proxy_info['proxy']} | {proxy_info['response_time']:.2f}ms | {proxy_info['type']}\n")

            print(f"\n{self.colorize('[+]', 'green')} Results saved to:")
            print(f"  {self.output_file} ({len(self.working_proxies)} proxies)")
            print(f"  {detailed_file} (detailed results)")

        except Exception as e:
            print(f"{self.colorize('[!]', 'red')} Error saving results: {e}")

    def print_statistics(self):
        """Print final statistics"""
        elapsed = time.time() - self.stats['start_time']
        success_rate = (len(self.working_proxies)/self.stats['total']*100) if self.stats['total'] > 0 else 0

        print(f"\n\n{self.colorize('=== PROXY CHECK COMPLETE ===', 'magenta')}")
        print(f"{self.colorize('Total proxies:', 'white')}     {self.stats['total']}")
        print(f"{self.colorize('Working proxies:', 'green')}   {len(self.working_proxies)}")
        print(f"{self.colorize('Failed proxies:', 'red')}      {self.stats['failed']}")
        print(f"{self.colorize('Success rate:', 'cyan')}       {success_rate:.2f}%")
        print(f"{self.colorize('Time taken:', 'white')}        {elapsed:.2f} seconds")
        print(f"{self.colorize('Average speed:', 'yellow')}    {self.stats['total']/elapsed:.0f} proxies/sec")

        if self.working_proxies:
            fastest = min(self.working_proxies, key=lambda x: x['response_time'])
            slowest = max(self.working_proxies, key=lambda x: x['response_time'])
            avg_time = sum(p['response_time'] for p in self.working_proxies) / len(self.working_proxies)

            print(f"\n{self.colorize('Performance:', 'cyan')}")
            print(f"  Fastest: {fastest['response_time']:.2f}ms ({fastest['proxy']})")
            print(f"  Slowest: {slowest['response_time']:.2f}ms ({slowest['proxy']})")
            print(f"  Average: {avg_time:.2f}ms")

    def run(self, input_file):
        """Main execution function"""
        # Load proxies
        if not self.load_proxies(input_file):
            return False

        # Check proxies
        try:
            self.check_proxies()
        except KeyboardInterrupt:
            print(f"\n{self.colorize('[!]', 'yellow')} Interrupted by user")

        # Print statistics
        if self.stats['start_time']:
            self.print_statistics()

        # Save results
        if self.working_proxies:
            self.save_results()

        return True

def main():
    parser = argparse.ArgumentParser(description='Ultra-Fast Multi-Threaded Proxy Checker')
    parser.add_argument('input_file', help='Input file containing proxies (one per line)')
    parser.add_argument('-t', '--threads', type=int, default=500, help='Number of threads (default: 500)')
    parser.add_argument('-T', '--timeout', type=int, default=3, help='Connection timeout in seconds (default: 3)')
    parser.add_argument('-o', '--output', default='working_proxies.txt', help='Output file for working proxies (default: working_proxies.txt)')

    args = parser.parse_args()

    # Validate input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file '{args.input_file}' not found!")
        sys.exit(1)

    # Create checker instance
    checker = UltraFastProxyChecker(
        threads=args.threads,
        timeout=args.timeout,
        output_file=args.output
    )

    # Run the checker
    checker.run(args.input_file)

if __name__ == '__main__':
    main()