from pathlib import Path
import socket
from .logger import Logger


class SnapchotError(Exception):
    pass


class Base:
    _all_threads = set()

    def __init__(self, owner):
        self._dict = {}
        self._path = None
        assert owner is not self
        self._owner = owner
        self._owners = None
        assert owner is not self.owners
        self._log = Logger()
        self._is_opened = False

    def __repr__(self):
        return f"{type(self).__name__}({self.path.as_posix()})"

    def __getitem__(self, key):
        try:
            item = self._dict[key]
        except KeyError:
            raise KeyError(f"{key} not in {self=}")

        return item

    def __setitem__(self, key, value):
        self._dict[key] = value

    def __contains__(self, key):
        return key in self._dict

    def __iter__(self):
        yield from self._dict

    @property
    def all_threads(self):
        dead_threads = set()
        # Remove dead threads
        for thread in self._all_threads:
            if thread.is_started:
                continue
            dead_threads.add(thread)
        self._all_threads.difference_update(dead_threads)
        return self._all_threads

    @property
    def log(self):
        return self._log

    @property
    def items(self):
        return self._dict.items

    @property
    def path(self):
        if self._path is not None:
            return self._path

        if self.owner is not None:
            self._path = self.owner.path / self.name
            return self._path

        self._path = Path()
        return self._path

    @property
    def owner(self):
        return self._owner

    @property
    def owners(self):
        if self.owner is None:
            return []
        if self._owners is None:
            self._owners = [self.owner] + self.owner.owners
        return self._owners

    @property
    def events(self):
        return self.owner.events

    @property
    def is_simulated(self):
        if socket.gethostname() == "Colloquy-Laptop":
            return False
        return True

    @property
    def opened(self):
        raise NotImplementedError(self)

    @opened.setter
    def opened(self, value):
        raise NotImplementedError(self)

    def add(self, element):
        self[element.name] = element

    def open(self):
        self._is_opened = True

    def close(self):
        self._is_opened = False

    def _snapshot_base_states(self, path):
        return {
            "path": path,
            "name": self.name,
            "close": self.close,
            "open": self.open,
            "opened": self._is_opened,
        }

    @property
    def snapshot_children(self):
        raise NotImplementedError(
            f"{self=}. Property returning a dictionnary with UI children."
        )

    def _snapshot_if_opened(self, path):
        states = {}
        for k, v in self.snapshot_children.items():
            if callable(v):
                # A plain command (bound method or function) registered as a
                # child rather than a Base node. Pass it straight through,
                # exactly as snapshot() below already does - a function has
                # no snapshot_as_child(), so calling it here crashed the
                # whole page the moment such a node was opened. Several
                # nodes register commands this way (a male's or female's
                # Drives setters); Bar and Neopixel each carry a local
                # work-around for the same crash, from before this was
                # handled here.
                states[k] = v
                continue
            child_path = path + (k,)
            states[k] = v.snapshot_as_child(path=child_path)
        return states

    def snapshot(self, path, focus_path):
        try:
            states = self._snapshot_base_states(path)
            if focus_path == path:
                states.update(self._snapshot_if_opened(path))
                return states

            for k, v in self.snapshot_children.items():
                if not callable(v):
                    child_path = path + (k,)
                    if focus_path[: len(child_path)] == child_path:
                        # child_path is a prefix of (or equal to) focus_path -
                        # still on the way there, keep walking.
                        states[k] = v.snapshot(path=child_path, focus_path=focus_path)
                    else:
                        # Not on the way to the focus - render collapsed
                        # (bounded by _is_opened), exactly like any other
                        # unopened sibling would be. Without this, every
                        # render unconditionally recursed through EVERY
                        # sibling subtree IN FULL regardless of relevance -
                        # harmless for small trees, but turns a single wide
                        # value-setter range (or any large enough subtree)
                        # into an unbounded, multi-million-node walk on
                        # every single page request.
                        states[k] = v.snapshot_as_child(path=child_path)
                    continue
                states[k] = v

        except SnapchotError:
            raise
        except Exception as error:
            raise SnapchotError(f"Error getting snapshot from {self}") from error

        return states

    def snapshot_as_child(self, path):
        states = self._snapshot_base_states(path)
        if self._is_opened:
            states.update(self._snapshot_if_opened(path))

        return states
