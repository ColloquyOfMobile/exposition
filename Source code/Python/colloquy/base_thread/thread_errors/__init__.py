# -*- coding: utf-8 -*-
# colloquy/base_thread/thread_error/__init__.py
from colloquy.base import Base
from .html import HTML
from threading import Lock
from pathlib import Path
from .thread_error import ThreadError


class ThreadErrors(Base):

    def __init__(self, owner):        
        super().__init__(owner=owner)
        self._errors = []
        self._html = HTML(owner=self)

        self[self.html.name] = self.html.handle_request
        
    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError

        key, *leftover = request.parts

        if key in self:
            self[key](request="/".join(leftover))
            return

        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")
    
    def __bool__(self):
        conditions = {bool(child.thread_errors) for child in self.owner.children}
        conditions.add(bool(self._errors))
        # print(f"{conditions}")
        result =  any(conditions)
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
    def html(self):
        return self._html

    @property
    def count(self):
        count = len(self._errors)
        for child in self.owner.children:
            count += child.thread_errors.count
        return count
    
    def append(self, error):
        thread_error = ThreadError(owner=self, name=f"error{len(self._errors)}", origin=self.owner, error=error)
        self[thread_error.name] = thread_error
        self._errors.append(thread_error)
            