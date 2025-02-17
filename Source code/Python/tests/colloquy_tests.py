from pathlib import Path
import csv
import time
import traceback
from datetime import datetime, timedelta
from time import sleep
from colloquy_driver import ColloquyDriver
from parameters import Parameters

PARAMETERS = Parameters().as_dict()
# PARAMETERS.pop("dynamixel network")

class ColloquyTests:
    def __init__(self):
        self.colloquy_driver = None

    def open(self):
        self.colloquy_driver = ColloquyMock(PARAMETERS)

    def close(self):
        self.colloquy_driver.stop()
        self.colloquy_driver = None


    def run(self, **kwargs):
        with self.colloquy_driver:
            # self.test_dxls()
            self.test_neopixels()
            # self.test_speakers()

    def test_speakers(self, **kwargs):
        yield (f"| Testing the speakers...")
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            elements = colloquy.elements
            females = colloquy.females
            males = colloquy.males
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                for element in (*females, *males):
                    yield f"|| Turning on {element.name}' speaker..."
                    element.turn_on_speaker()
                    sleep(1)
                    element.turn_off_speaker()
                    yield (f"|| Turned off {element.name}' speaker...")
                    sleep(0.5)

    def test_neopixels(self, **kwargs):
        yield (f"| Testing the neopixel...")
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            elements = colloquy.elements
            females = colloquy.females
            males = colloquy.males
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                yield (f"|| Turning on females' Neopixels...")
                colloquy.turn_on_neopixel(elements=females)
                sleep(2)

                yield (f"|| Turning off females' Neopixels...")
                colloquy.turn_off_neopixel(elements=females)
                sleep(2)

                yield (f"|| Turning off males' Neopixels...")
                colloquy.turn_on_neopixel(elements=males)
                sleep(2)

                yield (f"|| Turning off males' Neopixels...")
                colloquy.turn_off_neopixel(elements=males)
                sleep(2)

    def test_dxls(self, **kwargs):
        yield (f"| Testing the dynamixels...")
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            elements = colloquy.elements
            females = colloquy.females
            males = colloquy.males
            mirrors = colloquy.mirrors

            yield (f"| Turning everything to orgin...")
            colloquy.turn_to_origin_position(elements)
            colloquy.wait_until_everything_is_still()

            for iteration in range(iterations):
                yield (f"| {iteration=}")
                yield (f"|| Turning females left...")
                colloquy.turn_to_max_position(elements=females)

                colloquy.wait_until_everything_is_still()

                yield (f"|| Turning females right...")
                colloquy.turn_to_min_position(elements=females)

                colloquy.wait_until_everything_is_still()

                yield (f"|| Turning mirrors up...")
                colloquy.turn_to_max_position(elements=mirrors)

                colloquy.wait_until_everything_is_still()

                yield (f"|| Turning mirrors down...")
                colloquy.turn_to_min_position(elements=mirrors)

                colloquy.wait_until_everything_is_still()

                yield (f"|| Turning males left...")
                colloquy.turn_to_max_position(elements=males)

                colloquy.wait_until_everything_is_still()

                yield (f"|| Turning males right...")
                colloquy.turn_to_min_position(elements=males)

                colloquy.wait_until_everything_is_still()



    def play_pacman(self, **kwargs):
        yield "Playing pacman..."
        colloquy = self.colloquy_driver
        with colloquy:
            colloquy.play_pacman()

    def play_pinkpanther(self, **kwargs):
        yield "Playing pinkpanther..."
        colloquy = self.colloquy_driver
        with colloquy:
            colloquy.play_pinkpanther()


    def test_fem1_speaker(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                yield (f"|| Turning on speak female1...")
                colloquy.female1.turn_on_speaker()
                sleep(1)
                colloquy.female1.turn_off_speaker()
                yield (f"|| Turned off speak...")
                sleep(0.5)

    def test_fem2_speaker(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            for iteration in range(iterations):
                yield (f"|{iteration=}")
                yield (f"|| Turning on speak female2...")
                colloquy.female2.turn_on_speaker()
                sleep(1)
                colloquy.female2.turn_off_speaker()
                yield (f"|| Turned off speak...")
                sleep(0.5)

    def test_fem3_speaker(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            for iteration in range(iterations):
                yield (f"|{iteration=}")
                yield (f"|| Turning on speak female3...")
                colloquy.female3.turn_on_speaker()
                sleep(1)
                colloquy.female3.turn_off_speaker()
                yield (f"|| Turned off speak...")
                sleep(0.5)

    def test_male1_speaker(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                yield (f"|| Turning on speak male1...")
                colloquy.male1.turn_on_speaker()
                sleep(1)
                colloquy.male1.turn_off_speaker()
                yield (f"|| Turned off speak...")
                sleep(0.5)

    def test_male2_speaker(self, **kwargs):
        iterations = int(kwargs.get("iterations", [1])[0])
        with self.colloquy_driver:
            colloquy = self.colloquy_driver
            for iteration in range(iterations):
                yield (f"| {iteration=}")
                yield (f"|| Turning on speak male1...")
                colloquy.male2.turn_on_speaker()
                sleep(1)
                colloquy.male2.turn_off_speaker()
                yield (f"|| Turned off speak...")
                sleep(0.5)


if __name__=="__main__":
    ColloquyTests().run()