# -*- coding: utf-8 -*-
# colloquy/base_thread/thread_error/__init__.py
from colloquy.base import Base
from threading import Lock
from pathlib import Path
from .thread_error import ThreadError


class ThreadErrors(Base):
    def __init__(self, owner):
        super().__init__(owner=owner)
        self._errors = []

    def __bool__(self):
        conditions = {bool(child.thread_errors) for child in self.owner.children}
        conditions.add(bool(self._errors))
        # print(f"{conditions}")
        result = any(conditions)
        return result

    @property
    def colloquy(self):
        return self.owner.colloquy

    @property
    def name(self):
        return "thread errors"

    @property
    def errors(self):
        return self._errors

    @property
    def count(self):
        count = len(self._errors)
        for child in self.owner.children:
            count += child.thread_errors.count
        return count

    def append(self, error):
        thread_error = ThreadError(
            owner=self, name=f"error{len(self._errors)}", origin=self.owner, error=error
        )
        self[thread_error.name] = thread_error
        self._errors.append(thread_error)

    @property
    def snapshot_children(self):
        return {}

    def as_html(self):
        """Every traceback under this node: this thread's own first, then any
        collected by threads it started - so a parent shows which of its
        children died, instead of only reporting that something did."""
        blocks = [error.as_html() for error in self._errors]
        for child in self.owner.children:
            block = child.thread_errors.as_html()
            if block:
                blocks.append(block)
        return "".join(blocks)

    def snapshot(self, path, focus_path=None):
        """One always-expanded HTML leaf, not a node to open.

        BaseThread only asks for this when the thread has actually failed, and
        an error you have to go looking for is an error nobody reads. Takes
        focus_path to keep Base.snapshot()'s signature - it is not used, since
        there is nothing here to navigate into.
        """
        return {
            "path": path,
            "name": self.name,
            "html": self.as_html(),
        }
