 
import json
from yattag import Doc, indent
from urllib.parse import unquote
from pathlib import Path
from colloquy.utils import remove_folder_and_subfolders, pprint4, export_style, get_value
from colloquy.base import Base
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler
WSGIRequestHandler.log_message = lambda *args, **kwargs: None     
  
class WSGI2(Base):
    
    def __init__(self, server, environ, start_response, db_path=None):
        super().__init__(owner=server)
        self._server = server
        self._colloquy = server.colloquy
        self._db_path = db_path
        self._environ = environ
        self._start_response = start_response
        self._base_path=None
        self._root = Path("app")
        self._status, self._headers, self._content = self._parse()
    
    def __iter__(self):
        self._start_response(self._status, self._headers)
        yield self._content

    @property
    def shutdown_event(self):
        return self.owner.shutdown_event

    @property
    def restart_event(self):
        return self.owner.restart_event

    @property
    def colloquy(self):
        return self._colloquy
    
    @property
    def name(self):
        return "wsgi"
    
    
    def get_states(self, *args):
        db_path = self._db_path or Path("testspace/version6.json")
        states = self.colloquy.get_states(*args)
        return states
    
    def _parse(self):
        args = self._parse_path()
        print(f"{args=}")
        if not args:
            return self._parse_app()
        
        key, *leftovers = args
        if  key == "shutdown":
            return self._parse_shutdown(*leftovers)
            
        if  key == "restart":
            return self._parse_restart(*leftovers)
        
        if key == self._root.name:
            return self._parse_app(*leftovers)
            
        content_type = 'text/text'
        status = '404 Not found'
        headers = [("Content-Type", content_type)]
        return status, headers, b""
        
    def _parse_path(self):
        """Parse the path."""
        request_path=self._environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        return Path(request_path).parts
        
    def _parse_app(self, *args):
        to_render = self.get_states(*args)
        self._base_path= Path(*to_render['path'])
        
        # pprint4(obj=to_render)
        content_type = 'text/html'
        status = '200 OK'
        headers = [("Content-Type", content_type)]            
        
        css_style = {
            "height": "100%",
            "display": "flex",
            "flex-direction": "column",
            "font-size": "1rem",
        }
            
        doc, tag, text = Doc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html", style=export_style(css_style)):
            with tag("body", style="flex:1; display: flex; flex-direction: column; overflow: auto;"):
                with tag("div", name="server commands", style="display: flex; gap: 1ch;"):
                    with tag("div", style=""):
                        with tag("a", href="/shutdown"):
                            text("shutdown")
                            
                    with tag("div", style=""):
                        with tag("a", href="/restart"):
                            text("restart")
                            
                    with tag("div", style=""):
                        path = self._root / self._base_path
                        with tag("a", href=f"/{path.as_posix()}"):
                            text("refresh")
                
                doc.asis(self._html_navigation(to_render=to_render, ))
                
                                
                with tag("div", name="thread count", style="display: flex;"):
                        text(f"thread count: {len(self.all_threads)}")
                
                doc.asis(self._html_recursion(obj=to_render, ))
                

        html = doc.getvalue()
        html = indent(html)
        content = html.encode()
        
        return status, headers, content
    
    def _html_navigation(self, to_render): 
        doc, tag, text = Doc().tagtext() 
        css_style = {
            "display": "flex",
            "overflow-x": "auto",
            "text-wrap": "nowrap",
        }
        with tag("div", name="navigation", style=export_style(css_style)):
            with tag("div"):
                with tag("a", href=f"/"):
                    text("/home")
            href = self._root
            for name in to_render["path"]:
                href = href / name
                with tag("div"):
                    with tag("a", href=f"/{href.as_posix()}"):
                        text("/" + name)

        html = doc.getvalue()
        return indent(html)
    
    def _html_keyboard(self, obj):        
        doc, tag, text = Doc().tagtext() 
        
        call_path = Path(*obj["path"]).relative_to(self._base_path) 
        base_path = self._root / self._base_path / "call"/ call_path
        keyboard_path = base_path / f"keyboard"
        
        with tag("div", name="keyboard", style="display: flex; flex-direction: column; "):
            with tag("div", style="display: flex; gap: 1ch;"):
                with tag("div", name="prompt"):
                    text(">>>")
                with tag("div", name="value", style="flex:1;"):
                    if "keyboard" in obj:
                        text(obj["keyboard"]["value"])
                    else:
                        text("")
                
                path = keyboard_path / "pop"
                with tag("div", name="pop"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("pop")
                        
                path = keyboard_path / "clear"
                with tag("div", name="clear"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("clear")
                        
                path = base_path
                if "keyboard" in obj:
                    path = base_path / obj["keyboard"]["value"]
                with tag("div", name="commit"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("call")
            
            all_char = "abcdefghijklmnopqrstuvwxyz"
            with tag("div", name="line1", style="display: flex;"):
                for char in all_char[:10]:
                    
                    path = keyboard_path / char
                    
                    with tag("div", style="flex:1; display: flex; justify-content: center;"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)
                            
            with tag("div", name="line3", style="display: flex;"):
                for char in all_char[10:21]:
                    
                    path = keyboard_path / char
                    
                    with tag("div", style="flex:1; display: flex; justify-content: center;"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)
                            
            with tag("div", name="line3", style="display: flex;"):                    
                    
                for char in all_char[21:]:
                    
                    path = keyboard_path / char
                    
                    with tag("div", style="flex:1; display: flex; justify-content: center;"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)
                path = keyboard_path / "space"
                with tag("div", style="flex:3; display: flex; justify-content: center;"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text("space")

        html = doc.getvalue()
        return indent(html)
    
    def _html_recursion(self, obj):
        doc, tag, text = Doc().tagtext()
                
        style={
            "margin-left": "1ch", 
            "padding-left": "0.5ch", 
            "border-left": "1px gray dashed", 
            "display": "flex", 
            "flex-direction": "column", 
            "flex": "1", 
            "overflow": "auto", 
            "min-height": "10rem",
            "justify-content": "space-between",
            }
                
        with tag("div", name=obj["name"], style=export_style(style)): 
            
            for key, value in obj.items():
                # print(f"{key=}")
                if key in ("name", "subject", "id", "path", "focus", "func", "ref", "checked", "keyboard", "close", "open", "opened", ):
                    continue                    
                    
                if key == "value":
                    with tag("div"):
                        text(f"value: {value}")  
                    continue  
            
                if not isinstance(value, dict): 
                    func_path = Path(*obj["path"]) / key
                    call_path = func_path.relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path
                    
                    style={"flex": "1"}
                    with tag("div", name=key, style=export_style(style)):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{key}()")
                    continue
                    
                # print(f"{value=}")
                if value.get("opened", False):
                    if value:
                        doc.asis(self._html_if_opened(obj=value))
                    continue
                
                name = value["name"]
                
                value_path = Path(*value["path"])
    
                style={"display": "flex", "gap": "1ch", "flex": "1"}
                
                with tag("div", name="title", style=export_style(style)):
                    with tag("div", name="open"):               
                        call_path = value_path.relative_to(self._base_path)
                        path = self._root / self._base_path / "call" / call_path / "open"
                        
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f">")
                            
                    # name = obj["name"]
                    path = self._root / value_path
                    if "value" in value:
                        with tag("div", name="value"):
                            with tag("a", href=f"/{path.as_posix()}"):
                                text(f"{name}: {value['value']}")
                        continue
                    
                    with tag("div", name="name"):                
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{name}")                      

        html = doc.getvalue()
        return indent(html) 
        
    
    def _html_if_opened(self, obj):
        doc, tag, text = Doc().tagtext()
        name = obj["name"]  
        
        style={
            "margin-bottom": "0.5rem", 
            "flex": "1",
            "overflow": "auto", 
            "min-height": "10rem",
            }  
        
        with tag("div", name="opened", style=export_style(style)):
        
            style={"display": "flex", "gap": "1ch", "margin-bottom": "0.5rem"}  
            
            with tag("div", name="title", style=export_style(style)):            
                with tag("div", name="close"):               
                    call_path = Path(*obj["path"]).relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path / "close"
                    
                    with tag("a", href=f"/{path.as_posix()}"):
                        text(f"<")
                        
                with tag("div", name="name"):
                    path = self._root / Path(*obj["path"])
                    with tag("a", href=f"/{path.as_posix()}"):
                        text(f"{name}:")
                        
            doc.asis(self._html_recursion(obj=obj))
        
        html = doc.getvalue()
        return indent(html)  
        
        
    def _parse_shutdown(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        
        content_type = 'text/plain'
        status = '200 OK'
        headers = [("Content-Type", content_type)]
        lines = [
            f"thread count: {len(self.all_threads)}",
            "Goodbye!",
            ]
        content = "\n".join(lines).encode()
        
        return status, headers, content
        
        
    def _parse_restart(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()
        
        content_type = 'text/html'
        status = '200 OK'
        headers = [("Content-Type", content_type)]
        
        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("a", href=f"/"):
                text("reload")
        
        html = doc.getvalue()
        content = html.encode()
        
        return status, headers, content