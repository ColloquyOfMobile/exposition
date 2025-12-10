from server.html_element import HTMLElement
from colloquy.thread_element import ThreadElement
from datetime import datetime
from datetime import time
from time import sleep
from time import time as systime



class Agenda(ThreadElement):

    def __init__(self, owner, params):
        ThreadElement.__init__(self, owner=owner, name="agenda")
        self._days = []
        self._week = {}

        self._is_enabled = params["is_enabled"]
        self._print_origin = None

        for name in ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]:
            day = Day(owner=self, name=name, params=params[name])
            setattr(self, name, day)

    @property
    def is_enabled(self):
        return self._is_enabled

    @property
    def days(self):
        return self._days

    @property
    def week(self):
        return self._week

    # @property
    # def hardware(self):
        # return self.owner.hardware

    def stop(self, **kwargs):
        self.stop_event.set()
        self.hardware.stop()
        self.hardware.join()
        ThreadElement.stop(self, **kwargs)

    def save(self):
        return self.hardware.save()

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        if not self._is_enabled:
            self._write_html_action(
                value="hardware/exposition/agenda/enable",
                label="enable agenda",
                func=self._toggle_enable)
            return

        self._write_html_action(
            value="hardware/exposition/agenda/disable",
            label="disable agenda",
            func=self._toggle_enable)

        with tag("div"):
            for day in self._days:
                day.write_html()

        with tag("div"):
            doc.stag("hr")
            if not self.is_started:
                self._add_html_start()
            else:
                self._add_html_stop()
            doc.stag("hr")

    def _toggle_enable(self, **kwargs):
        self._is_enabled = not self._is_enabled
        self.hardware.params["agenda"]["is_enabled"] = self._is_enabled
        self.save()

    def _add_html_start(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/start"):
                text(f"Start.")
                self.actions["hardware/start"] = self.start
            with tag("button", name="action", value="exposition/close"):
                text(f"Close.")
                self.actions["exposition/close"] = self.owner.exposition.close

    def _add_html_stop(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("button", name="action", value="hardware/stop"):
                text(f"Stop.")
        self.actions["hardware/stop"] = self.stop

    def _setup(self):
        pass

    def _loop(self):
        if self.stop_event.is_set():
            print(f"{self.stop_event.is_set()=}")
            return

        if not self._is_enabled:
            self.stop_event.set()

        if self._print_origin is None:
            self._print_origin = systime()

        now = datetime.now()
        today = now.strftime("%A").lower()

        day = self.week[today]

        if day.state:
            start, end = day.start, day.end
            assert start and end, "Make sure to define start and end working days!"
            current_time = now.time()
            if start <= current_time < end:
                if not self.hardware.is_started:
                    print(f"Hardware is started...")
                    self.hardware.start()

                self._print("Running...")
            else:
                if self.hardware.is_started:
                    print(f"Hardware is stop...")
                    self.hardware.stop()

                self._print("Waiting next slot...")
        else:

            self._print("Waiting next slot...")

        sleep(1)

    def _print(self, msg):
        if systime() - self._print_origin > 10:
            self._print_origin = systime()
            print(msg)


class Day(HTMLElement):

    def __init__(self, owner, name, params):
        HTMLElement.__init__(self, owner)
        owner.days.append(self)
        owner.week[name] = self
        self._name = name
        self._state = params["state"]
        self._start = None
        self._end = None

        if params["start"] is not None:
            self._start = time.fromisoformat(params["start"])
        if params["end"] is not None:
            self._end = time.fromisoformat(params["end"])

    # @property
    # def hardware(self):
        # return self.owner.hardware

    @property
    def name(self):
        return self._name

    @property
    def state(self):
        return self._state

    @property
    def start(self):
        return self._start

    @property
    def end(self):
        return self._end

    def save(self):
        return self.owner.save()

    def _set_end_start(self, **kwargs):
        start = kwargs["start"][0] # gives "17:20"
        end = kwargs["end"][0]  # gives "17:20"

        self._start = time.fromisoformat(start)
        self._end = time.fromisoformat(end)
        self.hardware.params["agenda"][self.name]["start"] = start
        self.hardware.params["agenda"][self.name]["end"] = end
        self.save()

    def _toggle_state(self, **kwargs):
        self._state = not self._state
        self.hardware.params["agenda"][self.name]["state"] = self._state
        self.save()
        # if self._state:
            # self._state = False
            # self.save()
            # return
        # self._state = True
        # self.hardware.params["agenda"][self.name]["state"] = self._state
        # self.save()
        # raise NotImplementedError(f"{kwargs=}")

    def write_html(self):
        doc, tag, text = self.html_doc.tagtext()
        with tag("form", method="post"):
            with tag("label"):
                text(f"{self.name}: ")

            path =f"hardware/{self._name}/toggle"
            self.actions[path] = self._toggle_state
            if not self._state:
                with tag("button", name="action", value=path):
                    text("set on")
                return

            with tag("button", name="action", value=path):
                text("set off")

            path =f"hardware/{self._name}/set"

            kwargs = {}
            if self._start is not None:
                kwargs["value"]=self._start.strftime("%H:%M")
            doc.stag("input", type="time", name="start", **kwargs)


            kwargs = {}
            if self._end is not None:
                kwargs["value"]=self._end.strftime("%H:%M")
            doc.stag("input", type="time", name="end", **kwargs)

            with tag("button", name="action", value=path):
                text("set")
            self.actions[path] = self._set_end_start