from pathlib import Path

file_path = Path()


def read():
    if file_path.is_file():
        return file_path.read_text()


def write(text):
    if file_path.is_file():
        return file_path.write_text(text)


if __name__ == "__main__":
    data = read()

    write()
