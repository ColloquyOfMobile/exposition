# -*- coding: utf-8 -*-
# project2/my_server/utils.py

from pathlib import Path
import shutil


def export_style(style):
    lines = []
    for a, b in style.items():
        lines.append(f"{a}: {b};")
    return " ".join(lines)

def remove_folder_and_subfolders(path):
    assert not path.is_file()
    if path.is_dir():
        shutil.rmtree(path)

def is_pymodule(path):
    if path.is_file():
        return path.suffix == ".py"
    return False

def add_header(lines: list[str], file_path: Path) -> list[str]:
    encoding_line = "# -*- coding: utf-8 -*-"
    file_path_line = f"# {file_path.as_posix()}"

    # Remove any existing encoding comment at top
    while lines and lines[0].startswith("#"):
        lines.pop(0)

    # Remove leading empty lines
    while lines and lines[0].strip() == "":
        lines.pop(0)

    # Build normalized header
    header = [
        encoding_line,
        file_path_line,
        "",
    ]

    return header + lines

def is_pypackage(path):
    # Might want to remove this function, package does't have to have a __init__.py file
    if path.is_dir():
        return True
    return False
    
def _old_is_pypackage(path):
    if path.is_dir():
        return (path/"__init__.py").is_file()
    return False


def empty_dir(path):
    remove_folder_and_subfolders(path=path)
    path.mkdir()

            
def mkdirtree(root_path, specs):
    assert isinstance(specs, dict)
    if not root_path.is_dir():
        assert not root_path.exists()
        root_path.mkdir()
    for name, value in specs.items():    
        subpath = root_path / name
        if isinstance(value, str):
            subpath.write_text(value)
            continue
        mkdirtree(
            root_path=subpath, 
            specs=value,
            )
    
def dir_as_dict(dir_path: Path):
    data = {}

    for path in dir_path.iterdir():
        if path.is_dir():
            data[path.name] = dir_as_dict(path)
            continue
        data[path.name] = path.read_text()

    return data
            
class TestPrint:

    def __init__(self):
        self.calls = []

    def __call__(self, msg):
        self.calls.append(msg)
        
def pprint(obj, depth=None, indent=0, context=None):       
        
    indents = "|"*indent
                
    if indent == 0:
        path = obj.origin.as_posix()
        print(path, ":")
        if obj.value is not None:
            print(f"value={repr(obj.value)}")
    else:
        text_value = f"{obj.name}:"
        if obj.value is not None:
            text_value = f"{obj.name} (={obj.value}):"
        print(*indents, text_value)  
    
    # if context is not None:
        # print(*indents, "|", "context :", context.name,)  
        
        
    elements = list(obj)
    if elements:
        for element in elements:
            pprint(obj=element, indent=indent+1, context=obj)
        
def pprint2(obj): 
    
    lines = pformat_lines(obj)
    print("/".join(lines[0]))
    for tokens in lines[1:]:
        print(*tokens)

def pformat_lines(obj, lines=None, indent=0):    
    
    if lines is None:
        lines = [[]]
        
    lines[0].append(obj["name"])
    
    if "focus" in obj:
        focus = obj["focus"]
        return pformat_lines(obj=obj[focus], lines=lines)
    
    
    if "value" in obj:
        lines[0] += [":", obj['value']]
        return lines
    
    if "children" in obj:
        for child in obj["children"]:
            for tokens in pformat_lines(obj=obj[child]):
                lines.append(["|", *tokens])
                
    return lines


def test_pformat_lines():  
    obj = {
        "name": "test", 
        "focus": "test2", 
        "test2": {
            "name": "test2",
            "test3": {
                "name": "test value", 
                "value": "some value",
            },
            "children": [
                    "test3"
                ]
            },
        "children": [
            "test2"
            ],
        }
    lines = pformat_lines(obj=obj)
    expected = [['test', 'test2'], ['|', 'test value', ':', 'some value']]
    assert expected == lines, f"pformat_lines shouldn't be modified, copy a new version instead!"

test_pformat_lines()
        
def pprint3(obj): 
    lines = pformat_lines2(obj)
    print(*lines[0])
    for tokens in lines[1:]:
        print(*tokens)

def pformat_lines2(obj, lines=None):  
    
    if lines is None:
        lines = [[""]]
        
    lines[0][0] += (f'{obj["name"]}')
    
    if "focus" in obj:
        lines[0][0] += (f'/')        
        focus = obj["focus"]
        return pformat_lines2(obj=obj[focus], lines=lines)
    
    if "opened" not in obj:
        if "value" in obj:
            lines[0][0] +=  ":"
            value = get_value(obj)
            lines[0].append(value)
        return lines
        
    if "opened" in obj:
        lines[0][0] +=  ":"
        
    for key, item in obj.items():
        if key in ("name", "subject", "id", "path"):
            continue
            
        # if isinstance(item, dict):
        for tokens in pformat_lines2(obj=item):
            lines.append(["|", *tokens])
                
    return lines
    

def get_value(obj):
        if not "value" in obj:
            return
        value = set(obj["value"])
        for name in ("name", "delete", "subject", "id", "opened", "path", "open"):
            value.discard(name)
        if not value:
            return None
        
        if len(value)==1:
            return value.pop()
            
        # value = value.pop()
        return sorted(value)
        
        
def pprint4(obj): 
    print("colloquy/", end="")
    print(*obj["path"], sep="/")
    
    lines = pformat_lines3(obj, depth=2)
    for tokens in lines:
        print(*tokens)

def pformat_lines3(obj, depth):
    if depth <= 0:
        return []
    lines = []
    if obj["name"] == "value":
        lines.append(f"{value}")    
    else:        
        for key, value in obj.items():
            tokens = []
            if key in ("name", "subject", "id", "path", "focus", "func", "ref"):
                continue
                
            if key in ("value", "opened",):
                lines.append([f"{key}: {value}"])
                continue
            
            if not isinstance(value, dict):
                lines.append([f"{key}()"])                
                continue
                
            if "opened" in value:
                lines.append([f'{value["name"]}:'])
                lines += pformat_lines3(value, depth=depth-1)
                continue
                
            if "value" in value:
                lines.append([f'{value["name"]}: {value["value"]}'])
                continue
                
            lines.append([f'{value["name"]}'])
    
    return add_indent(lines)

def add_indent(lines):
    return  [["|", *tokens] for tokens in lines]
