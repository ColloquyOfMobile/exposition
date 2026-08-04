from colloquy.base import Base


class Increment(Base):
    def __init__(self, owner, multiplier):
        super().__init__(owner=owner)
        self._multiplier = multiplier
        self._name = f"*{multiplier}"
        self._value = 0

    def __call__(self, request):
        if request == "+":
            self.owner.value += self.multiplier

        elif request == "-":
            self.owner.value -= self.multiplier

        else:
            raise NotImplementedError(request)

        # self.owner.neopixel.update()

    @property
    def name(self):
        return self._name

    @property
    def multiplier(self):
        return self._multiplier

    def html(self):
        doc, tag, text = CustomDoc().tagtext()

        klass = "int-button"
        style1 = "display:flex;"

        with tag("div", style=style1):
            # - button
            with tag("div", klass=klass):
                with tag(
                    "a",
                    href=f"/{self.path.as_posix()}/-",
                    style="text-decoration: none; color: black;",
                ):
                    text(f"- {self._multiplier}")

            # + button
            with tag("div", klass=klass):
                with tag(
                    "a",
                    href=f"/{self.path.as_posix()}/+",
                    style="text-decoration: none; color: black;",
                ):
                    text(f"+ {self._multiplier}")

            # with tag("div", style="display:flex; place-content: center; margin-left: 1ch;"):
            # text(self._multiplier)#

        return doc.getvalue()
