"""Render tree controls from the same snapshot on the installation and preview."""
from contextlib import nullcontext
from pathlib import Path
from urllib.parse import parse_qs, quote

from yattag import Doc, indent
from colloquy.ui.tree import CommandFailed
from colloquy.ui.console import thread_monitor


class ConsoleTree:
    def _parse_virtual_panel(self, *args):
        """Bookmarks from the side-panel UI now open the simulation branch."""
        if not self.colloquy.is_simulated or not args or args[0] not in ("show", "hide"):
            return self._parse_not_found(("virtual-panel", *args), NotImplementedError("No such panel"))
        back = args[1:]
        # The old hide link carried the node to return to. Only navigate
        # to nodes: a stale bookmark must never redirect to a command.
        if args[0] == "show":
            back = ("app", "simulation")
        elif not back or back[0] != "app" or any(part in ("..", "call") for part in back):
            back = ("app",)
        return "303 See Other", [("Location", quote("/" + "/".join(back)))], b""

    def _parse_post(self, *args):
        """Save from either a focused editor or one expanded beneath the focus."""
        if not args or args[0] != self._root.name or "call" not in args[1:-1]:
            return self._parse_not_found(args, NotImplementedError("Expected an editor command"))
        marker = args.index("call")
        focus = args[1:marker]
        children = focus + args[marker + 1:-1]
        command = args[-1]
        try:
            size = int(self._environ.get("CONTENT_LENGTH") or 0)
            if size < 0:
                raise ValueError("negative form length")
            body = self._environ["wsgi.input"].read(size)
            content = parse_qs(body.decode("utf-8")).get("content", [""])[0]
        except (OSError, ValueError, OverflowError):
            return "400 Bad Request", [("Content-Type", "text/plain")], b"Could not read the editor form."
        hold = getattr(self.colloquy, "hold_commands", None)
        lock = hold() if hold else nullcontext(True)
        with lock as acquired:
            if not acquired:
                return "503 Service Unavailable", [("Content-Type", "text/plain")], b"Command busy. Try saving again."
            node = self.colloquy
            try:
                for key in children:
                    node = node.snapshot_children[key]
                handler = node[command]
            except (KeyError, AttributeError, TypeError):
                return self._parse_not_found(args, NotImplementedError(command))
            if not callable(handler):
                return self._parse_not_found(args, NotImplementedError(command))
            try:
                handler(content)
            except Exception as error:
                return self._parse_command_failed(args[1:], CommandFailed((command,), error))
        location = quote("/" + "/".join((self._root.name, *focus)))
        return "303 See Other", [("Location", location)], b""

    def _html_recursion(self, obj):
        doc, tag, text = Doc().tagtext()

        with tag("div", name=obj["name"], klass="tree-level"):
            node_parts = tuple(obj["path"])
            if node_parts == ("logs",):
                doc.asis(thread_monitor())
            elif node_parts[:1] == ("logs",) and Path(*node_parts) == self._base_path and "content" in obj:
                doc.asis(thread_monitor("/".join(node_parts[1:])))
            for key, value in obj.items():
                if key in (
                    "name",
                    "subject",
                    "id",
                    "path",
                    "focus",
                    "func",
                    "ref",
                    "checked",
                    "keyboard",
                    "close",
                    "open",
                    "opened",
                ):
                    continue

                if key == "value":
                    # Two shapes reach here under the literal key "value":
                    # a bare scalar (obj["value"] set directly), or the
                    # wrapped {"path", "name", "value"} leaf dict used
                    # everywhere else in this function (and by classes
                    # like LightSensor, whose _snapshot_if_opened key
                    # happens to also be "value") - unwrap the latter so
                    # it doesn't print the dict's own repr.
                    display_value = (
                        value["value"]
                        if isinstance(value, dict) and "value" in value
                        else value
                    )
                    with tag("div", name="value"):
                        text(f"value: {display_value}")
                    continue

                if not isinstance(value, dict):
                    func_path = Path(*obj["path"]) / key
                    call_path = func_path.relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path

                    with tag("div", name=key, klass="command"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(key)
                    continue

                # Branches can contain children named editor, image, or pre.
                # Identify the open branch before interpreting a leaf payload.
                if value.get("opened") is True:
                    doc.asis(self._html_if_opened(obj=value))
                    continue

                if "editor" in value:
                    node_path = Path(*value["path"][:-1])
                    call_path = node_path.relative_to(self._base_path)
                    save_path = self._root / self._base_path / "call" / call_path / "save"

                    with tag("div", name=key):
                        with tag(
                            "form", method="post", action=f"/{save_path.as_posix()}"
                        ):
                            with tag("textarea", name="content", **{"aria-label": key}):
                                text(value["editor"])
                            with tag("div"):
                                with tag("button", type="submit"):
                                    text("save")
                    continue

                if "html" in value:
                    with tag("div", name=key, klass="md-content"):
                        doc.asis(value["html"])
                    continue

                if "pre" in value:
                    with tag("div", name=key):
                        if key == "content" and obj["path"][:1] == ("logs",):
                            if Path(*node_parts) != self._base_path:
                                with tag("a", href="/" + "/".join((self._root.name, *node_parts))):
                                    text("Follow this thread")
                            with tag("details", klass="log-archive"):
                                with tag("summary"):
                                    text("Full log at page load")
                                with tag("pre"):
                                    text(value["pre"])
                        else:
                            with tag("pre"):
                                text(value["pre"])
                    continue

                if "svg" in value:
                    with tag("div", name=key):
                        with tag("div"):
                            text(
                                "scroll to zoom - shift+scroll to zoom x-axis only - drag to pan - double-click to reset"
                            )
                        with tag("div", **{"data-svg-zoom": ""}):
                            doc.asis(value["svg"])
                    continue

                # No zoom handle, so svg_zoom.js never binds anything to
                # it - see leaves.image.
                if "image" in value:
                    with tag("div", name=key):
                        doc.asis(value["image"])
                    continue

                # Use the dict key rather than value["name"] for display:
                # a parent can (and does, e.g. TestNeopixels/TestSensors)
                # register the same kind of child multiple times under
                # distinct keys precisely because the child's own .name is
                # a fixed literal shared across every instance of that
                # type ("light sensor", "head", ...) - showing value["name"]
                # here made every such sibling display identical link text
                # even though their hrefs (built from the key) already
                # correctly pointed at different objects.
                name = key

                # Plain informational leaves (e.g. _snapshot_if_opened
                # entries like "sender"/"matches"/"last match") aren't real
                # openable nodes - they have no "open" handler, so drawing
                # the open-arrow/call-link below would 404/crash on click.
                if "value" in value:
                    with tag("div", name="value"):
                        text(f"{name}: {value['value']}")
                    continue

                value_path = Path(*value["path"])

                with tag("div", name="title"):
                    with tag("div", name="open"):
                        call_path = value_path.relative_to(self._base_path)
                        path = (
                            self._root / self._base_path / "call" / call_path / "open"
                        )

                        with tag("a", href=f"/{path.as_posix()}", **{"aria-label": f"Expand {name}"}):
                            text("›")

                    path = self._root / value_path
                    with tag("div", name="name"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{name}")

        html = doc.getvalue()
        return indent(html)

    def _html_if_opened(self, obj):
        doc, tag, text = Doc().tagtext()
        name = obj["path"][-1]

        with tag("div", name="opened"):
            with tag("div", name="title"):
                with tag("div", name="close"):
                    call_path = Path(*obj["path"]).relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path / "close"

                    with tag("a", href=f"/{path.as_posix()}", **{"aria-label": f"Collapse {name}"}):
                        text("⌄")

                with tag("div", name="name"):
                    path = self._root / Path(*obj["path"])
                    with tag("a", href=f"/{path.as_posix()}"):
                        text(name)

            doc.asis(self._html_recursion(obj=obj))

        html = doc.getvalue()
        return indent(html)
