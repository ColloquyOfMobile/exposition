from colloquy.base import Base


class White(Base):
    def __init__(self, owner):
        Base.__init__(self, owner)

        self._neopixel = owner

        self._hundreds = Digit(owner=self, multiplier=100)
        self._tens = Digit(owner=self, multiplier=10)
        self._ones = Digit(owner=self, multiplier=1)

        self._digits = [
            self._hundreds,
            self._tens,
            self._ones,
        ]
        for digit in self._digits:
            self[digit.name] = digit


    @property
    def neopixel(self):
        return self._neopixel

    @property
    def name(self):
        return "white"

    @property
    def value(self):
        return self._hundreds.value + self._tens.value + self._ones.value

    @value.setter
    def value(self, value):
        value_as_string = f"{value:03}"

        self._hundreds.value = int(value_as_string[0])
        self._tens.value = int(value_as_string[1])
        self._ones.value = int(value_as_string[2])
        self.neopixel.update()

    def hex_to_rgb(self, hex_value):
        hex_value = hex_value.lstrip("#")  # Retire le #
        if len(hex_value) != 6:
            raise ValueError(
                "La valeur hexadécimale doit contenir exactement 6 caractères."
            )
        r = int(hex_value[0:2], 16)
        g = int(hex_value[2:4], 16)
        b = int(hex_value[4:6], 16)
        return (r, g, b)

    def html(self):
        doc, tag, text = CustomDoc().tagtext()

        with tag("div", style="display:flex; align-items: center;"):
            with tag("div", style="margin-right: 1ch;"):
                text("set white")

            for digit in self._digits:
                doc.asis(digit.html())

        return doc.getvalue()


class Digit(Base):
    def __init__(self, owner, multiplier):
        super().__init__(owner=owner)
        self._multiplier = multiplier
        self._name = f"*{multiplier}"
        self._value = 0

    def __call__(self, request):
        if request == "+":
            new_digit = (self._value + 1) % 10

        elif request == "-":
            new_digit = (self._value - 1) % 10  # wrap 0→9

        else:
            raise NotImplementedError(request)

        self._value = new_digit
        if self.owner.value > 255:
            self.owner.value = 255
            return
        self.owner.neopixel.update()

    @property
    def name(self):
        return self._name

    @property
    def value(self):
        return self._value * self._multiplier

    @value.setter
    def value(self, value):
        self._value = value

    def html(self):
        doc, tag, text = CustomDoc().tagtext()

        klass = "int-button"
        style1 = "display:flex; flex-direction: column; place-content: center; padding: 0 0.1ch;"

        with tag("div", style=style1):
            # + button
            with tag("div", klass=klass):
                with tag(
                    "a",
                    href=f"/{self.path.as_posix()}/+",
                    style="text-decoration: none; color: black;",
                ):
                    text("+")

            # The digit itself
            with tag("div", style="display:flex; place-content: center;"):
                text(self._value)

            # - button
            with tag("div", klass=klass):
                with tag(
                    "a",
                    href=f"/{self.path.as_posix()}/-",
                    style="text-decoration: none; color: black;",
                ):
                    text("-")

        return doc.getvalue()
