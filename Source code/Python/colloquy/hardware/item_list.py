from pathlib import Path
from colloquy.wsgi.root.html_item import HtmlItem
from colloquy.wsgi.root.body.action_item import ActionItem
from colloquy.hardware.item import Item, HTML as _HTML
# from colloquy.wsgi.root.body.workspace.share_commands import Commands



class ItemList(Item):

    def __init__(self, owner, name):
        self._name = name
        Item.__init__(self, owner=owner)
        self._opened = None
        self._html = HTML(owner=self)
        # self._commands = None # Commands(owner=self)

    def __call__(self):
        if not self.is_opened:
            # print(f"{self.is_opened=}")
            self.open()
        # print(f"{self.is_opened=}")
        # print(f"{self.owner=}")
        # print(f"{self.owner.opened=}")

    def __iter__(self):
        raise NotImplementedError

    @property
    def name(self):
        return self._name


class HTML(HtmlItem):

    def _call_unsafe(self):
        doc, tag, text = self.doc.tagtext()
        if not self.owner.is_opened:
            self._call_if_is_not_opened()
            return


        print(f"{self.owner.opened=}")

        if self.owner.opened:
            return self.owner.opened.html()

        with tag("div", style="display: flex; flex-direction: column;"):
            with tag("h2", style="flex: 1;" ):
                text(self.owner.name)
            self.owner.commands.html()

        self._call_body()

    def _call_if_is_not_opened(self):
        doc, tag, text = self.doc.tagtext()
        with tag("form", method="post", style="display: flex; "):
            with tag("button", name="action", value=self.owner.action.value):
                text(self.owner.name)

    def _call_body(self):
        for item in self.owner:
            item.html()

    @property
    def name(self):
        return "HTML"

# class HTML(_HTML):

    # def _call_body(self):
        # for item in self.owner:
            # item.html()
