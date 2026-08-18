# -*- coding: utf-8 -*-
# project2/my_server/utils.py

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
