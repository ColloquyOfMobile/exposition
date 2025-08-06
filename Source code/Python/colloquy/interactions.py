from .thread_element import ThreadElement

class Interactions():

    def __init__(self, owner):
        # Defined at for each bar position, which female and male interacts
        self._items = [
            Interaction(owner=owner, male=owner.male1, female=owner.female1, origin=0),
            Interaction(owner=owner, male=owner.male2, female=owner.female3, origin=2200),
            Interaction(owner=owner, male=owner.male1, female=owner.female2, origin=4300),
            Interaction(owner=owner, male=owner.male2, female=owner.female1, origin=6200),
            Interaction(owner=owner, male=owner.male1, female=owner.female3, origin=8400),
            Interaction(owner=owner, male=owner.male2, female=owner.female2, origin=10400),
        ]
        self._store_by_position = {}
        self._store_by_females = {}
        for interaction in self._items:
            self._store_by_position[interaction.position] = interaction
            self._store_by_females.setdefault(interaction.female, []).append(interaction)

        # self.interactions = {
            # e.position: e for e in interactions
        # }

    def __getitem__(self, index):
        return self._items[index]

    @property
    def from_females(self):
        return self._store_by_females

    @property
    def from_positions(self):
        return self._store_by_position


class Interaction(ThreadElement):

    def __init__(self, owner, male, female, origin):
        ThreadElement.__init__(self, owner=owner, name=f"interaction {male.name}-{female.name}")
        self._male = male
        self._female = female
        self._origin = origin
        self.target_drive = tuple()

    def __iter__(self):
        yield self.male
        yield self.female

    def __enter__(self):
        print(f"Interaction {self.female.name}-{self.male.name} Started...")
        self.stop_event.clear()

    def __exit__(self, exc_type, exc_value, traceback_obj):
        # if self.female.conversation.is_started:
            # self.female.conversation.stop()
        return ThreadElement.__exit__(self, exc_type, exc_value, traceback_obj)

    @property
    def origin(self):
        return self._origin

    @property
    def position(self):
        return self._origin + self.colloquy.bar.dxl_origin

    @property
    def male(self):
        return self._male

    @property
    def female(self):
        return self._female

    def move_to_position_and_wait(self):
        self.colloquy.bar.goal_position = self.position
        self.female.turn_to_origin_position()
        self.male.turn_to_origin_position()
        self.colloquy.wait_until_everything_is_still()

    def _loop(self):
        pass

    def add_html(self):
        pass

    def _setup(self, **kwargs):
        self.colloquy.interaction = self
        self.female.drives.stop()
        self.female.conversation.start()