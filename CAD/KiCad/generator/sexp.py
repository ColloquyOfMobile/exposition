"""Tiny S-expression reader/writer for KiCad files."""
import re

_TOK = re.compile(r'\(|\)|"(?:[^"\\]|\\.)*"|[^\s()"]+')


class Sym(str):
    """Unquoted atom."""


def loads(text):
    stack = [[]]
    for m in _TOK.finditer(text):
        t = m.group(0)
        if t == '(':
            stack.append([])
        elif t == ')':
            node = stack.pop()
            stack[-1].append(node)
        elif t.startswith('"'):
            stack[-1].append(t[1:-1].replace('\\"', '"').replace('\\\\', '\\'))
        else:
            stack[-1].append(Sym(t))
    return stack[0][0]


def _atom(x):
    if isinstance(x, Sym):
        return str(x)
    if isinstance(x, bool):
        return 'yes' if x else 'no'
    if isinstance(x, (int,)):
        return str(x)
    if isinstance(x, float):
        s = ('%.6f' % x).rstrip('0').rstrip('.')
        return '0' if s in ('-0', '') else s
    s = str(x).replace('\\', '\\\\').replace('"', '\\"')
    return '"%s"' % s


def dumps(node, indent=0):
    if not isinstance(node, list):
        return _atom(node)
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(_atom(c) for c in node) + ')'
    out = '(' + ' '.join(_atom(c) for c in node if not isinstance(c, list))
    # keep leading atoms, then children
    head = []
    rest = []
    seen_list = False
    for c in node:
        if isinstance(c, list):
            seen_list = True
        (rest if seen_list else head).append(c)
    out = '(' + ' '.join(_atom(c) for c in head)
    pad = '\t' * (indent + 1)
    for c in rest:
        if isinstance(c, list):
            out += '\n' + pad + dumps(c, indent + 1)
        else:
            out += ' ' + _atom(c)
    out += '\n' + '\t' * indent + ')'
    return out


def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]


def first(node, key):
    for c in node:
        if isinstance(c, list) and c and c[0] == key:
            return c
    return None
