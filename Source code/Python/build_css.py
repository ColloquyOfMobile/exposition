


def build_css(style):
    lines = []
    for a, b in style.items():
        lines.append(f"{a}: {b};")
    return " ".join(lines)