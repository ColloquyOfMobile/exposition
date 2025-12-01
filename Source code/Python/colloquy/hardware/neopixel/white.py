from colloquy.base import Base
from pathlib import Path
from utils import CustomDoc


class White(Base):
    
    def __init__(self, owner):
        Base.__init__(self, owner)
        self._value = 0
        
        self._digits = []
        for mult in (100, 10, 1):
            digit = Digit(owner=self, multiplier=mult)
            self._digits.append(digit)
            self[digit.name] = digit
            
        # self._action = Action(owner=self)
        # self._html = HTML(owner=self)
        
    def __call__(self, request):
        request = Path(request)
        if not request.parts:
            raise NotImplementedError
            
        key, *leftover = request.parts
        
        if key in self:
            self[key](request="/".join(leftover))
            return
            
        raise NotImplementedError(f"{key=}, {leftover=}, in {self=}")

    @property
    def name(self):
        return "white"
    
    @property
    def value(self):
        return self._value
    
    @value.setter
    def value(self, value):
        
        print(f"{value=}")
        self._value = value
        self.owner.update()

    def hex_to_rgb(self, hex_value):
        hex_value = hex_value.lstrip('#')  # Retire le #
        if len(hex_value) != 6:
            raise ValueError("La valeur hexadécimale doit contenir exactement 6 caractères.")
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
            # with tag("div", style=style1):
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*100/+", style="text-decoration: none; color: black;"):
                        # text("+")
                # with tag("div", style="display:flex; place-content: center;"):
                    # text(hundreds)
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*100/-", style="text-decoration: none; color: black;"):
                        # text("-")
                        
            # with tag("div", style=style1):
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*10/+", style="text-decoration: none; color: black;"):
                        # text("+")
                # with tag("div", style="display:flex; place-content: center;"):
                    # text(tens)
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*10/-", style="text-decoration: none; color: black;"):
                        # text("-")
                        
            # with tag("div", style=style1):
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*1/+", style="text-decoration: none; color: black;"):
                        # text("+")
                # with tag("div", style="display:flex; place-content: center;"):
                    # text(units)
                # with tag("div", klass=klass):
                    # with tag("a", href=f"/{self.path.as_posix()}/*1/-", style="text-decoration: none; color: black;"):
                        # text("-")
        
        return doc.getvalue()

class Digit(Base):
    
    def __init__(self, owner, multiplier):
        super().__init__(owner=owner)
        self._multiplier = multiplier
        self._name = f"*{multiplier}"
    
    def __call__(self, request):
        if request == "+":
            new_digit = (self.value + 1) % 10
        
        elif request == "-":
            new_digit = (self.value - 1) % 10  # wrap 0→9
        
        else:
            raise NotImplementedError(request)
        
        # Remove the old digit from the number
        base = self.owner.value - (self.value * self._multiplier)

        # Insert the new digit
        new_value = base + (new_digit * self._multiplier)
        
        if new_value > 255:
            new_value = 255

        # Store it
        self.owner.value = new_value

    @property
    def name(self):
        return self._name
    
    @property
    def value(self):
        result = self.owner.value % (self._multiplier * 10)
        return result // self._multiplier
    
    def html(self):
        doc, tag, text = CustomDoc().tagtext()

        klass = "int-button"
        style1 = "display:flex; flex-direction: column; place-content: center; padding: 0 0.1ch;"

        with tag("div", style=style1):
            # + button
            with tag("div", klass=klass):
                with tag("a", 
                         href=f"/{self.path.as_posix()}/+", 
                         style="text-decoration: none; color: black;"):
                    text("+")

            # The digit itself
            with tag("div", style="display:flex; place-content: center;"):
                text(self.value)

            # - button
            with tag("div", klass=klass):
                with tag("a", 
                         href=f"/{self.path.as_posix()}/-", 
                         style="text-decoration: none; color: black;"):
                    text("-")

        return doc.getvalue()

# class HTML(_HTML):

    # def __call__(self):
        # doc, tag, text = self.doc.tagtext()
        # value = self.owner.owner.white
            
        # with tag("form", method="post", style="display: flex; "):
        
            # with tag("label", style="margin-left: 1ch; margin-right: 1ch;"):
                # text("white")
                
            # doc.stag("input", type="number", name="value", value=value)
        
            # with tag(klass, name="action", value=self.owner.action.value):
                # text("set")
            
    # def rgb_to_hex(self, red, green, blue):
        # for value in (red, green, blue):
            # assert 0 <= value <= 255
        # return '#{:02X}{:02X}{:02X}'.format(red, green, blue)