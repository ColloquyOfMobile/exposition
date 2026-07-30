# -*- coding: utf-8 -*-
# project2/my_server/solution1/input/html.py

from colloquy.base_html import BaseHTML
from yattag import Doc, indent


class HTML(BaseHTML):
    def _call_unsafe(self, *args):
        doc, tag, text = Doc().tagtext()
        with tag(
            "div",
            name=self.owner.name,
            style="display: flex; flex:1; flex-direction: column;",
        ):
            with tag("div", style="display: flex; flex:1; flex-direction: row;"):
                with tag("div"):
                    text("value: ")
                with tag("div", style="flex:1;"):
                    text(self.owner.value)

                if self.owner.value != "0":
                    doc.asis(self.owner.erase.html())

                with tag("div"):
                    with tag("a", href=f"/{self.owner.path.as_posix()}/commit"):
                        text("commit")

            style = (
                "flex:1;"
                "border: 1px solid black;"
                "border-radius: 0.2rem;"
                "display: flex;"
                "justify-content: center;"
                "align-items: center;"
                "padding: 0.2ch;"
                "margin-inline: 0.5ch;"
            )
            with tag("div", style="display: flex; flex:1; flex-direction: row;"):
                with tag("a", href=f"/{self.owner.path.as_posix()}/1", style=style):
                    with tag("div"):
                        text("1")

                with tag("a", href=f"/{self.owner.path.as_posix()}/2", style=style):
                    with tag("div"):
                        text("2")

                with tag("a", href=f"/{self.owner.path.as_posix()}/3", style=style):
                    with tag("div"):
                        text("3")

            with tag("div", style="display: flex; flex:1; flex-direction: row;"):
                with tag("a", href=f"/{self.owner.path.as_posix()}/4", style=style):
                    with tag("div"):
                        text("4")

                with tag("a", href=f"/{self.owner.path.as_posix()}/5", style=style):
                    with tag("div"):
                        text("5")

                with tag("a", href=f"/{self.owner.path.as_posix()}/6", style=style):
                    with tag("div"):
                        text("6")

            with tag("div", style="display: flex; flex:1; flex-direction: row;"):
                with tag("a", href=f"/{self.owner.path.as_posix()}/7", style=style):
                    with tag("div"):
                        text("7")

                with tag("a", href=f"/{self.owner.path.as_posix()}/8", style=style):
                    with tag("div"):
                        text("8")

                with tag("a", href=f"/{self.owner.path.as_posix()}/9", style=style):
                    with tag("div"):
                        text("9")

            with tag("div", style="display: flex; flex:1; flex-direction: row;"):
                with tag(
                    "a", href=f"/{self.owner.path.as_posix()}/commit", style=style
                ):
                    with tag("div"):
                        text("commit")

                with tag("a", href=f"/{self.owner.path.as_posix()}/0", style=style):
                    with tag("div"):
                        text("0")

        html = doc.getvalue()
        return indent(html)
