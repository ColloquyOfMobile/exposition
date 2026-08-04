from colloquy.base import Base

class ValueSetter(Base):
    def __init__(self, owner, limit, digits=None, prefix=""):
        super().__init__(owner=owner)

        if digits is None:
            digits = len(str(limit - 1))

        self._limit = limit
        self._digits = digits
        self._prefix = prefix
        self._setters = []

        if digits == 0:
            value = int(prefix)
            self._setters.append(self._make_setter(value))
            return

        for i in range(10):
            new_prefix = prefix + str(i)

            # valeur minimale possible avec ce prefix
            value = int(new_prefix + "0" * (digits - 1))
            if value >= limit:
                break

            if digits == 1:
                value = int(new_prefix)
                if value < limit:
                    self._setters.append(Set(owner=self, value=value))
            else:
                self._setters.append(
                    ValueSetter(
                        owner=self, limit=limit, digits=digits - 1, prefix=new_prefix
                    )
                )

    def _make_setter(self, value):
        def wrap():
            self.dxl_origin.set(value)

        return wrap

    @property
    def name(self):
        return self._prefix + "*" * self._digits

    @property
    def set(self):
        return self.owner.set

    @property
    def snapshot_children(self):
        children = {}

        for setter in self._setters:
            children[setter.name] = setter

        return children

class Set(Base):
    def __init__(self, owner, value):
        self._value = value
        super().__init__(owner=owner)

    def __call__(self):
        self.set(self._value)

    @property
    def set(self):
        return self.owner.set

    @property
    def name(self):
        return str(self._value) + " set"
