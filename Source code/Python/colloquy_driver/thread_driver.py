from time import sleep
from pathlib import Path

class ThreadDriver:

    log_folder = Path("local/logs")
    if not log_folder.is_dir():
        log_folder.mkdir()
    for element in log_folder.iterdir():
        lines = element.read_text().splitlines()
        lines = lines[-1000:]
        lines.extend(
            ("",
            "RESTART",
            "",)
        )
        text = "\n".join(lines[-1000:])
        element.write_text(text)

    def log(self, msg):
        path = self.log_folder / f"{self.name}.log"
        with path.open("a") as file:
            file.write(msg)
            file.write("\n")

    def sleep_min(self):
        sleep(0.05)