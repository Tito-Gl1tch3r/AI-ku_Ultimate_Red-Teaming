import threading
import queue
import time
import asyncio

class AnalyzeNetwork:
    def __init__(self, env, ai):
        self.env = env
        self.AI = ai

    def writer_thread(self, line_queue, output_file, lock):
        while True:
            try:
                line = line_queue.get(timeout=3)  # wait max 3 seconds for a line

            except queue.Empty:
                # No more lines and no termination signal yet, loop continue
                continue

            if line is None:
                # Sentinel received, exit thread
                line_queue.task_done()
                break

            with lock:
                with open(output_file, 'a+') as f:
                    f.write(line)

            time.sleep(1)  # wait for 1 second before next line
            line_queue.task_done()

    def analyze_network(self, input_file='network.log', output_file='network-analyze.log', num_threads=10):
        # Clear / create output file at start
        open(output_file, 'w').close()
        line_queue = queue.Queue()
        lock = threading.Lock()
        threads = []
        
        try:
            # Start writer threads
            for _ in range(num_threads):
                t = threading.Thread(target=self.writer_thread, args=(line_queue, output_file, lock))
                t.start()
                threads.append(t)

            # Read lines and put in queue
            with open(input_file, 'r') as f:
                for line in f:
                    flag = self.AI.helpAI(line) #help with AI
                    result = f"{flag} # {line}"
                    line_queue.put(result)

            # Wait until all lines have been processed
            line_queue.join()

        except KeyboardInterrupt:
            print("\nShutdown signal received. Stopping threads...")

        finally:
            # Send sentinel None to each thread to unblock and stop
            for _ in range(num_threads):
                line_queue.put(None)

            # Wait for all threads to exit
            for t in threads:
                t.join()

            print("All threads stopped. Exiting.")
