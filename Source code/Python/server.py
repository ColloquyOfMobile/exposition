
import sys, os
import json
from yattag import Doc, indent
from urllib.parse import unquote
from pathlib import Path
from colloquy.utils import remove_folder_and_subfolders
from colloquy.base import Base
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler
from wsgi import make_wsgi
WSGIRequestHandler.log_message = lambda *args, **kwargs: None

shutdown_event = Event()
restart_event = Event()

def server(colloquy):
        
    port=8000
    hostname = "localhost" # socket.gethostname()
    wsgi = make_wsgi(colloquy=colloquy, shutdown_event=shutdown_event, restart_event=restart_event)
    with make_server("localhost", port, wsgi) as httpd:
        WSGIRequestHandler.log_message = lambda *args, **kwargs: None
        print(f"Accessible at http://{hostname}:{port}/")

        while True:
            httpd.handle_request()

            if shutdown_event.is_set():
                print(f"Shutdown event!")
                break
                
        print("Out from server loop.")
    print("Out from server context.")
    
    if restart_event.is_set():
        restart_process()

def restart_process():
    python = sys.executable
    args = ["main.py", "colloquy2"]
    # args.append()
    os.execl(python, python, *args)