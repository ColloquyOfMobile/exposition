# -*- coding: utf-8 -*-
# Source code/Python/colloquy/ui/tree.py

"""Walking a tree of nodes for the page: find what is being looked at,
call what has been clicked.

This is what turns a request path into the dict the renderer draws. It
used to live on `Colloquy` itself, which meant the page could only ever
be pointed at the whole installation - hardware, threads, params and all.
It is plain tree walking: it asks nodes for `snapshot_children` and
`snapshot()` and nothing else, so any root that answers those two will do
(`colloquy/ui/mock.py` is one that answers them with nothing behind it).

The "call" segment in a path is what separates navigation from doing
something: everything before it names a node, everything after it names a
command on that node and its arguments.
"""


class CommandFailed(Exception):
    """A command raised, and this says which one.

    The walk knows two things the request layer cannot work out for
    itself once an exception is loose: that what raised was a *command*
    rather than the render around it, and which command it was. Both go in
    here, so a page can name what failed and offer a way back that does
    not run it again.

    Nothing catches it here on purpose. Whether a failed command is worth
    a page or worth stopping the installation is a decision for whoever is
    serving, and the two roots answer it differently.
    """

    def __init__(self, command, error):
        super().__init__(f"{'/'.join(str(part) for part in command)}: {error}")
        self.command = tuple(command)
        self.error = error


def get_focus(root, *args, obj=None, path=None):
    """The node a path points at, as a snapshot, plus whatever is left.

    The leftovers are the "call" tail: empty while the reader is only
    navigating, and the command (with its arguments) once they have
    clicked something.
    """
    if obj is None:
        obj = root
    if path is None:
        path = list()

    if args:
        key, *leftovers = args
        if key != "call":
            path.append(key)
            if key not in obj.snapshot_children:
                raise NotImplementedError(f"{obj.snapshot_children=}, {obj=}")
            obj = obj.snapshot_children[key]
            return get_focus(root, *leftovers, obj=obj, path=path)

        return obj.snapshot(path=tuple(path), focus_path=tuple(path)), leftovers

    return obj.snapshot(path=tuple(path), focus_path=tuple(path)), tuple()


def update(*args, focus):
    """Follow a "call" tail into the snapshot and invoke what it names.

    Commands sit in a snapshot as bare callables, so the walk ends when it
    reaches something that is not a dict - which it then calls with
    whatever arguments are left over.
    """
    if not isinstance(focus, dict):
        return focus(*args)
    if args:
        key, *leftovers = args
        if key not in focus:
            raise NotImplementedError(key, focus["name"])
        return update(*leftovers, focus=focus[key])
    return focus


def get_states(root, *args):
    """The snapshot the page is about to draw, having first done whatever
    the path asked for.

    Snapshotting twice is deliberate: a command may change what it is
    looking at (turning a body, opening a node), so the state that gets
    drawn is read *after* the command rather than before it.
    """
    focus, leftovers = get_focus(root, *args)

    if leftovers:
        try:
            update(*leftovers, focus=focus)
        except NotImplementedError:
            # The routing idiom for "no such key" - `update` raises it on
            # a miss, and the page answers that with a 404. Wrapping it
            # would turn a mistyped link into a report of a hardware
            # fault.
            raise
        except Exception as error:
            raise CommandFailed(leftovers, error) from error
        focus, leftovers = get_focus(root, *args)

    return focus
