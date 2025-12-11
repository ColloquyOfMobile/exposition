from time import time, sleep
import inspect
from collections import defaultdict
import threading
from pathlib import Path
import shutil
from threading import Lock


class Logger:
    
    _time_origin = time()
    _log_folder = Path("local/logs")
    shutil.rmtree(_log_folder)
    _log_folder.mkdir(parents=True, exist_ok=True)
    
    def __init__(self):
        self._line_counts = {}
        self._lock = Lock()
        

    def __call__(self, msg: str):
        
        msg = self._format(msg=msg)
        
        current = threading.current_thread()
        main_thread = threading.main_thread()
        
        if current == main_thread:
            print(msg)
        
        self._write(msg)        
    
    def _write(self, msg: str):
        """Write log to current thread's file, creating directories if needed."""
        
        thread_name = threading.current_thread().name
        file_path = (self._log_folder / thread_name).with_suffix(".log")
        
        if not file_path.exists():
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.touch()
            
        if file_path not in self._line_counts:
            lines = file_path.read_text().splitlines()
            self._line_counts[file_path] = len(lines)
            text = "\n".join(lines)
            with self._lock:
                file_path.write_text(text)
            
        self._line_counts[file_path] += len(msg.splitlines())
        
        with self._lock:
            with open(file_path, "a", encoding="utf-8") as f:
                msg = msg + "\n"
                f.write(msg)
            
        if self._line_counts[file_path] > 2000:
            lines = file_path.read_text().splitlines()
            lines[-1000:]
            self._line_counts[file_path] = len(lines)
            text = "\n".join(lines)            
            with self._lock:
                file_path.write_text(text)

    def _format(self, msg):
        time_header = f"{round(time()-self._time_origin, 2)}:"
        lines = msg.splitlines()
        if len(lines) == 1:
            return f"{time_header} {msg}"

        new_lines = [f"{time_header}:"]
        for line in lines:
            new_lines.append(f"+ {line}")

        return "\n".join(new_lines)