from colloquy.base import Base
from colloquy.ui import leaves

class ValueSetter(Base):
    def __init__(self, owner, limit, get_func, digits=None, prefix=""):
        super().__init__(owner=owner)

        if digits is None:
            digits = len(str(limit - 1))

        self._limit = limit
        self._get_func = get_func
        self._digits = digits
        self._prefix = prefix
        # Built lazily on first snapshot_children access - see the
        # identical fix/comment on value_setter2.ValueSetter2.
        self._setters = None

    def _build_setters(self):
        setters = []

        if self._digits == 0:
            value = int(self._prefix)
            setters.append(self._make_setter(value))
            return setters

        for i in range(10):
            new_prefix = self._prefix + str(i)

            # valeur minimale possible avec ce prefix
            value = int(new_prefix + "0" * (self._digits - 1))
            if value >= self._limit:
                break

            if self._digits == 1:
                value = int(new_prefix)
                if value < self._limit:
                    setters.append(Set(owner=self, value=value))
            else:
                setters.append(
                    ValueSetter(
                        owner=self,
                        limit=self._limit,
                        get_func=self._get_func,
                        digits=self._digits - 1,
                        prefix=new_prefix,
                    )
                )
                # One-click shortcut to the round value this digit choice
                # implies - see the identical addition/comment on
                # value_setter2.ValueSetter2._build_setters.
                setters.append(Set(owner=self, value=value))

        return setters

    def _make_setter(self, value):
        def wrap():
            self.dxl_origin.set(value)

        return wrap

    @property
    def name(self):
        low = int(self._prefix + "0" * self._digits)
        high = min(int(self._prefix + "9" * self._digits), self._limit - 1)
        return f"{low} to {high}"

    @property
    def set(self):
        return self.owner.set

    @property
    def snapshot_children(self):
        if self._setters is None:
            self._setters = self._build_setters()

        children = {}
        for setter in self._setters:
            children[setter.name] = setter

        return children

    def _snapshot_if_opened(self, path):
        # See the identical fix/comment on value_setter2.ValueSetter2.
        states = {}
        for k, v in self.snapshot_children.items():
            if callable(v):
                states[k] = v
            else:
                states[k] = v.snapshot_as_child(path=path + (k,))

        states["current value"] = leaves.value(path, "current value", self._get_func())
        return states

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

    @property
    def snapshot_children(self):
        # See the identical fix/comment on value_setter2.Set.
        return {}
