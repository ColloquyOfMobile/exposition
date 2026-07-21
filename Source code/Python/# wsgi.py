 
import json
from urllib.parse import unquote
from pathlib import Path
from colloquy.utils import remove_folder_and_subfolders, pprint4, export_style, get_value
from colloquy.base import Base
from build_html import build_html, build_iframe
from build_html.build_restart import build_restart
# from build_html2 import build_html2, build_iframe2


def make_wsgi(app, shutdown_event, restart_event):
    
    handle = build_handler(
        app=app, 
        shutdown_event=shutdown_event,
        restart_event=restart_event,
    )

    def wsgi(environ, start_response):
        try:
            args = parse_path(environ)
            status, headers, content = handle(*args,)                
            start_response(status, headers,)
            yield content
        except Exception:
            shutdown_event.set()
            app["shutdown"]()
            raise
            
    return wsgi

def parse_path(environ):
    """Parse the path."""
    request_path=environ["PATH_INFO"]
    request_path = unquote(request_path)
    request_path = request_path.strip("/")
    request_path = request_path.encode("iso-8859-1").decode("utf-8")
    return Path(request_path).parts

def build_handler(app, shutdown_event, restart_event):
    
    def handle(*args, ):
        app_href = Path("app")  
        iframe_href = Path("iframe")  
        
        str_args = ", ".join(args)
        print(f"handle({str_args})")
        
        app_handler = handle_app(
            app=app, 
            app_href=app_href, 
            iframe_href=iframe_href,          
            base_href = app_href,
        )
        
        handlers = {
            "shutdown": handle_shutdown(event=shutdown_event, app=app),
            "restart": handle_restart(
                events=(
                    shutdown_event,
                    restart_event,
                ),
                app=app,
            ),
            "app": app_handler,
            "iframe": handle_iframe(
                app=app, 
                app_href=app_href, 
                iframe_href=iframe_href,    
            ),
            "ui2": handle_ui2(
                app=app, 
                app_href=app_href, 
                iframe_href=iframe_href,
            ),
        }
        
        if args:  
            key, *leftovers = args
            if key in handlers:
                status, headers, content = handlers[key](*leftovers)
            else:
                content_type = 'text/text'
                status = '404 Not found'
                headers = [("Content-Type", content_type)]     
                content = b""
        else:
            status, headers, content = app_handler()
            
        return status, headers, content
        
    return handle

def handle_shutdown(event, app):
    def handler():
        app["shutdown"]()
        event.set()
        content_type = 'text/text'
        status = '200 OK'
        headers = [("Content-Type", content_type)]     
        content = b"Goodbye. You can close this tab"
        return status, headers, content
    return handler

def handle_restart(events, app):
    def handler():
        app["shutdown"]()
        for event in events:
            event.set()
        content_type = 'text/html'
        status = '200 OK'
        headers = [("Content-Type", content_type)]     
        content = build_restart()
        return status, headers, content
    return handler

def handle_app(app, app_href, iframe_href, build_html=build_html, **kwargs):
    def handler(*args):
        content_type = 'text/html'
        status = '200 OK'
        headers = [("Content-Type", content_type)]
        ui=app["func"](*args)
        content = build_html(
            ui=ui, 
            app_href=app_href, 
            iframe_href=iframe_href,
            **kwargs,
            )
        return status, headers, content
    return handler

def handle_iframe(app, app_href, iframe_href, build_iframe=build_iframe):
    def handler(*args):
        content_type = 'text/html'
        status = '200 OK'
        headers = [("Content-Type", content_type)]
        ui=app["func"](*args)        
        content = build_iframe(ui=ui, app_href=app_href, iframe_href=iframe_href)
        return status, headers, content
    return handler

def handle_ui2(app, app_href, iframe_href):
    app_href = "ui2" / app_href
    iframe_href = "ui2" / iframe_href
    def handler(*args):
        raise NotImplementedError
        handlers = {
            "app": handle_app(
                app=app, 
                app_href=app_href, 
                iframe_href=iframe_href,                
                base_href = app_href,
                build_html=build_html2,
            ),
            "iframe": handle_iframe(
                app=app, 
                app_href=app_href, 
                iframe_href=iframe_href, 
                build_iframe=build_iframe2
            ),
        }
        if args: 
            key, *leftovers = args
            status, headers, content = handlers[key](*leftovers)
        else:
            status, headers, content = handlers["app"]["func"]()
            
        return status, headers, content
        
    return handler
    
    
  