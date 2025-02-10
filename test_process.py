import time
import subprocess
import threading
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class FileModifiedHandler(FileSystemEventHandler):

    def __init__(self):
        FileSystemEventHandler.__init__(self)
        self.last_call = time.time()
        self.subprocess = None
        self.subprocess_thread = None

    def on_modified(self, event):
        src_path = Path(event.src_path)
        if time.time() - self.last_call < 3:
            return
        self.last_call = time.time()

        if src_path.suffix == ".py":
            print(f"File modified: {src_path}")
            self._strip_lines(src_path)
            self.run()

    def run(self):
        """Kill the existing subprocess and trigger a new one to run the tests"""
        print("Running tests...")

        # Kill the existing server process if it exists
        if self.subprocess and self.subprocess.poll() is None:
            print("Killing previous server process...")
            self.subprocess.kill()

        # Start the server again and display its output
        print("Starting new server process...")
        self.subprocess = subprocess.Popen(
            ["py", "-u", "main.py"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            bufsize=1,  # Line-buffered output
            universal_newlines=True  # Required for text mode and line buffering
            )

        # Start a thread to read the subprocess output
        self.subprocess_thread = threading.Thread(target=self._print_subprocess_output)
        self.subprocess_thread.start()

    def _print_subprocess_output(self):
        """Continuously read the subprocess stdout and print to main console"""
        for line in iter(self.subprocess.stdout.readline, ''):
            print(f"# {line}", end='')
            self.subprocess.stdout.flush()  # Flush the output to ensure real-time display

    def _strip_lines(self, src_path):
        """Strip trailing spaces from each line of the file"""
        lines = src_path.read_text().splitlines()
        new_lines = [line.rstrip() for line in lines]
        src_path.write_text("\n".join(new_lines))


def monitor_folder(folder_to_watch):
    """Monitor folder for file changes and restart server on modification"""
    print("Starting the server...")
    event_handler = FileModifiedHandler()

    # Start the server subprocess
    event_handler.subprocess = subprocess.Popen(
        ["py", "-u", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=1,  # Line-buffered output
        universal_newlines=True  # Required for text mode and line buffering
        )
    event_handler.subprocess_thread = threading.Thread(target=event_handler._print_subprocess_output)
    event_handler.subprocess_thread.start()

    print("Server running...")

    # Set up the observer to monitor the folder
    observer = Observer()
    observer.schedule(event_handler, folder_to_watch, recursive=True)
    observer.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Stopping server and observer...")
        observer.stop()
        # Kill the server process if it's still running
        if event_handler.subprocess and event_handler.subprocess.poll() is None:
            event_handler.subprocess.kill()

    observer.join()


if __name__ == "__main__":
    folder_to_watch = Path.cwd()  # Replace with the path to your folder
    monitor_folder(folder_to_watch)