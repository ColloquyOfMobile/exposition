from colloquy.base import Base


class ValueSetter2(Base):
    def __init__(self, owner, min_value, max_value, set_func, digits=None, prefix="", sign=1, _is_root=True):
        super().__init__(owner=owner)

        # --- DETERMINE DIGITS ---
        if digits is None:
            digits = len(str(max_value - 1)) if max_value > 0 else 1

        self._digits = digits

        self._min = min_value
        self._max = max_value
        self._prefix = prefix
        self._sign = sign
        self._setters = []
        self._set_func = set_func

        # --- ROOT LEVEL: split into negative / positive ---
        if _is_root:
            if prefix == "":
                if min_value < 0:
                    self._setters.append(
                        ValueSetter2(
                            owner=self,
                            min_value=0,
                            max_value=abs(min_value),
                            set_func = set_func,
                            digits=len(str(abs(min_value) - 1)),
                            prefix="-",
                            sign=-1,
                            _is_root=False,
                        )
                    )

                if max_value > 0:
                    self._setters.append(
                        ValueSetter2(
                            owner=self,
                            min_value=0,
                            max_value=max_value,
                            set_func = set_func,
                            digits=len(str(max_value - 1)) if max_value > 0 else 1,
                            prefix="",
                            sign=1,
                            _is_root=False,
                        )
                    )
                return

        # --- LEAF ---
        if digits == 0:
            value = sign * int(prefix)
            if min_value <= value < max_value:
                self._setters.append(self._make_setter(owner=self, value=value))
            return

        # --- BUILD TREE ---
        for i in range(10):
            new_prefix = prefix + str(i)

            # smallest possible value with this prefix
            try:
                _ = int(new_prefix)
            except ValueError:
                continue

            value = sign * int(new_prefix + "0" * (digits - 1))

            # pruning
            if sign == 1:
                if value >= max_value:
                    break
                    
            else:
                if value < min_value:
                    break

            if digits == 1:
                value = sign * int(new_prefix)
                if min_value <= value < max_value:
                    self._setters.append(Set(owner=self, value=value))
            else:
                self._setters.append(
                    ValueSetter2(
                        owner=self,
                        min_value=min_value,
                        max_value=max_value,
                        set_func = set_func,
                        digits=digits - 1,
                        prefix=new_prefix,
                        sign=sign,
                        _is_root=False,
                    )
                )

    @property
    def name(self):
        return self._prefix + "*" * self._digits

    @property
    def set(self):
        return self._set_func

    def _make_setter(self, value):
        def wrap():
            self._set_func(value)
        return wrap
    
    
    @property
    def snapshot_children(self):
        children = {}

        for setter in self._setters:
            if self._sign == -1:
                children["-" + setter.name] = setter
            else:
                children[setter.name] = setter
                
        return children

    # def snapshot(self, path):
        # states = super().snapshot(path=path)
        # _path = path + (self.name,)

        # for setter in self._setters:
            # if callable(setter):
                # if self._sign == -1:
                    # states["-" + setter.name] = setter
                # else:
                    # states[setter.name] = setter
            # else:
                # states[setter.name] = setter.snapshot(_path)

        # return states


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