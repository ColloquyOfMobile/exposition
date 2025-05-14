from .thread_driver import ThreadDriver

class NearbyInteraction(ThreadDriver):

    def __init__(self, owner, male, female):
        ThreadDriver.__init__(self, owner=owner, name=f"interaction {male.name}-{female.name}")
        self._male = male
        self._female = female

    def __iter__(self):
        yield self.male
        yield self.female

    @property
    def male(self):
        return self._male

    @property
    def female(self):
        return self._female

    def busy(self):
        return any(
            element.interaction_event.is_set()
            for element
            in self
            )

    def add_html(self):
        pass