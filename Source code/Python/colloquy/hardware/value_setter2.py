from colloquy.base import Base

class ValueSetter2(Base):
    def __init__(
        self,
        owner,
        min_value,
        max_value,
        set_func,
        get_func,
        digits=None,
        prefix="",
        sign=1,
        _is_root=True,
    ):
        super().__init__(owner=owner)

        # --- DETERMINE DIGITS ---
        if digits is None:
            digits = len(str(max_value - 1)) if max_value > 0 else 1

        self._digits = digits

        self._min = min_value
        self._max = max_value
        self._prefix = prefix
        self._sign = sign
        self._set_func = set_func
        self._get_func = get_func
        self._is_root = _is_root

        # Children (both the root's negative/positive split and every
        # digit level's 10-way branch) used to be built eagerly here,
        # recursively, all the way down to every leaf Set - for a wide
        # range (e.g. -20000..20000) that's tens of thousands of Base
        # instances constructed regardless of whether the tree is ever
        # navigated, adding tens of seconds to Colloquy() startup once
        # more than a couple of these exist (confirmed: colloquy/
        # params_browser's params tab alone added ~25s). Build lazily
        # instead - only the one level actually being rendered/navigated
        # pays this cost, memoized so repeated access within one request
        # doesn't rebuild it.
        self._setters = None

    def _build_setters(self):
        setters = []

        # --- ROOT LEVEL: split into negative / positive ---
        if self._is_root and self._prefix == "":
            if self._min < 0:
                setters.append(
                    ValueSetter2(
                        owner=self,
                        min_value=0,
                        max_value=abs(self._min),
                        set_func=self._set_func,
                        get_func=self._get_func,
                        digits=len(str(abs(self._min) - 1)),
                        prefix="",
                        sign=-1,
                        _is_root=False,
                    )
                )

            if self._max > 0:
                setters.append(
                    ValueSetter2(
                        owner=self,
                        min_value=0,
                        max_value=self._max,
                        set_func=self._set_func,
                        get_func=self._get_func,
                        digits=len(str(self._max - 1)) if self._max > 0 else 1,
                        prefix="",
                        sign=1,
                        _is_root=False,
                    )
                )
            return setters

        # --- LEAF ---
        # self._min is always 0 here (both root-split branches are
        # constructed with min_value=0 - see _build_setters' ROOT LEVEL
        # branch above - the negative branch's own self._max is the
        # *magnitude* bound abs(original min_value)), so bounds checks
        # below compare the unsigned magnitude against self._max, then
        # apply self._sign exactly once to get the real value. Comparing
        # a signed value against these magnitude-scoped bounds directly
        # would be wrong for the negative branch.
        if self._digits == 0:
            magnitude = int(self._prefix)
            if magnitude < self._max:
                setters.append(Set(owner=self, value=self._sign * magnitude))
            return setters

        # --- BUILD ONE LEVEL (children built lazily by each child in turn) ---
        for i in range(10):
            new_prefix = self._prefix + str(i)
            magnitude = int(new_prefix + "0" * (self._digits - 1))
            value = self._sign * magnitude

            if magnitude >= self._max:
                break

            if self._digits == 1:
                setters.append(Set(owner=self, value=value))
            else:
                setters.append(
                    ValueSetter2(
                        owner=self,
                        min_value=self._min,
                        max_value=self._max,
                        set_func=self._set_func,
                        get_func=self._get_func,
                        digits=self._digits - 1,
                        prefix=new_prefix,
                        sign=self._sign,
                        _is_root=False,
                    )
                )
                # One-click shortcut to the round value this digit choice
                # implies (e.g. picking "8" at the thousands level offers
                # both "drill into 8xxx" and "set to 8000" right here),
                # so common round targets don't need full-depth digit-by-
                # digit navigation. Reuses the same Set leaf shape/naming
                # ("N set") a fully-drilled-down leaf would have.
                setters.append(Set(owner=self, value=value))

        return setters

    @property
    def name(self):
        if self._is_root and self._prefix == "":
            return "choose value"

        sign_str = "-" if self._sign == -1 else ""
        low = int(self._prefix + "0" * self._digits)
        high = min(int(self._prefix + "9" * self._digits), self._max - 1)
        return f"{sign_str}{low} to {sign_str}{high}"

    @property
    def set(self):
        return self._set_func

    @property
    def snapshot_children(self):
        if self._setters is None:
            self._setters = self._build_setters()

        children = {}
        for setter in self._setters:
            children[setter.name] = setter

        return children

    def _snapshot_if_opened(self, path):
        # Base._snapshot_if_opened's default always wraps every child via
        # .snapshot_as_child() (a dict), even a callable Set leaf - which
        # means update() (colloquy/__init__.py) can never actually reach
        # `focus(*args)` for a Set leaf: recursing through nested dicts
        # never bottoms out at a raw callable, so clicking a "N set" leaf
        # silently does nothing (no error, just never calls Set.__call__,
        # so the value is never written). Mirror Base.snapshot()'s own
        # non-focus-branch behavior instead: expose callable children
        # (Set leaves) raw, so they're invokable, while still wrapping
        # non-callable children (nested ValueSetter2 branches) normally
        # so they stay browsable/collapsible.
        states = {}
        for k, v in self.snapshot_children.items():
            if callable(v):
                states[k] = v
            else:
                states[k] = v.snapshot_as_child(path=path + (k,))

        states["current value"] = {
            "path": path + ("current value",),
            "name": "current value",
            "value": self._get_func(),
        }
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
        # A genuine leaf. Without this, Base.snapshot_children's default
        # raises NotImplementedError the instant this node's "open" link
        # is clicked (Base._snapshot_if_opened walks snapshot_children
        # unconditionally once _is_opened is True) - crashing the whole
        # server via Server2.wsgi()'s catch-all emergency-stop safety net.
        return {}
