# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/__init__.py

"""What the web UI and the object tree agree on.

Every node in the tree describes itself to the page by returning a dict
from `snapshot()` / `_snapshot_if_opened()`, and `server2/wsgi2.py`
renders whatever it finds in there. That dict is the whole contract
between the two halves of this app, and until this package existed it had
no definition anywhere: 33 files hand-built the shapes and the renderer
worked out what each one was by looking at which key happened to be
present.

`leaves.py` holds the vocabulary - one constructor per kind of thing the
page can draw. Nothing here imports from the rest of colloquy: these are
plain dicts, so a node can describe itself without dragging in a server
and the renderer can be exercised on hand-written dicts without a
hardware tree.
"""
