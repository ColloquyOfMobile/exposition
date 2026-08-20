# -*- coding: utf-8 -*-
# project2/my_server/utils.py

def export_style(style):
    lines = []
    for a, b in style.items():
        lines.append(f"{a}: {b};")
    return " ".join(lines)


def timelap_to_string(seconds_elapsed):
    seconds_elapsed = round(seconds_elapsed)
    if seconds_elapsed > 60:
        minutes = seconds_elapsed // 60
        seconds = seconds_elapsed % 60
        tokens = [f"{minutes}min"]
        if seconds != 0:
            tokens.append(f"{seconds}s")
        seconds_elapsed_as_string = " ".join(tokens)
    else:
        seconds_elapsed_as_string = f"{seconds_elapsed}s"

    return seconds_elapsed_as_string


def write_text(file_path, content):
    """Write what a textarea posted back, without gaining a carriage
    return per line every time.

    A browser posts a textarea's line breaks as CRLF. `write_text` opens
    in text mode, where Python translates "\n" to os.linesep - which on
    Windows turns each posted "\r\n" into "\r\r\n". Saving a document
    unchanged from the page grew it by 497 bytes and put a stray CR on
    every line; saving again would do it again. Found by saving the code
    documentation back byte-for-byte and diffing.

    So: line endings are normalised to "\n" here and written through
    untranslated. Git stores LF either way, and the working copy is
    whatever autocrlf makes of it - what matters is that a save is
    idempotent.
    """
    normalised = content.replace("\r\n", "\n").replace("\r", "\n")
    file_path.write_text(normalised, encoding="utf-8", newline="\n")

