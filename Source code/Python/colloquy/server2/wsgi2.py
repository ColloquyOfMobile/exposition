import json
import re
from yattag import Doc, indent
from urllib.parse import unquote
from pathlib import Path
from colloquy.utils import (
    remove_folder_and_subfolders,
    pprint4,
    export_style,
    get_value,
)
from colloquy.base import Base
from threading import Event
from wsgiref.simple_server import make_server, WSGIRequestHandler

WSGIRequestHandler.log_message = lambda *args, **kwargs: None

# Vendored locally (not a CDN) - this app is meant to run at the
# exhibition, possibly offline. MIT licensed, see vendor/uplot/LICENSE.
_UPLOT_DIR = Path(__file__).parent / "vendor" / "uplot"
UPLOT_JS = (_UPLOT_DIR / "uPlot.iife.min.js").read_text(encoding="utf-8")
UPLOT_CSS = (_UPLOT_DIR / "uPlot.min.css").read_text(encoding="utf-8")

# Zero-dependency pan/zoom for embedded matplotlib SVGs (no CDN - this app
# is meant to run at the exhibition, possibly offline). Manipulates each
# svg's own viewBox rather than the page zoom, so the raw-measurement plot
# can be inspected independently of everything else on the page.
SVG_ZOOM_SCRIPT = """
(function () {
  function initSvgZoom(container) {
    var svg = container.querySelector("svg");
    if (!svg) return;

    var viewBox = svg.getAttribute("viewBox");
    if (!viewBox) {
      var w = parseFloat(svg.getAttribute("width")) || svg.clientWidth;
      var h = parseFloat(svg.getAttribute("height")) || svg.clientHeight;
      viewBox = "0 0 " + w + " " + h;
      svg.setAttribute("viewBox", viewBox);
    }
    var original = viewBox.split(/\\s+/).map(Number);
    var x = original[0], y = original[1], w = original[2], h = original[3];

    function apply() {
      svg.setAttribute("viewBox", x + " " + y + " " + w + " " + h);
    }

    function svgPointAt(evt) {
      var rect = svg.getBoundingClientRect();
      var px = (evt.clientX - rect.left) / rect.width;
      var py = (evt.clientY - rect.top) / rect.height;
      return { sx: x + px * w, sy: y + py * h };
    }

    container.addEventListener("wheel", function (evt) {
      evt.preventDefault();
      var p = svgPointAt(evt);
      var factor = evt.deltaY > 0 ? 1.15 : 1 / 1.15;
      var xOnly = evt.shiftKey;
      var newW = w * factor;
      var newH = xOnly ? h : h * factor;
      x = p.sx - (p.sx - x) * (newW / w);
      y = xOnly ? y : p.sy - (p.sy - y) * (newH / h);
      w = newW;
      h = newH;
      apply();
    }, { passive: false });

    var dragging = false, lastX = 0, lastY = 0;
    container.addEventListener("mousedown", function (evt) {
      dragging = true;
      lastX = evt.clientX;
      lastY = evt.clientY;
      container.style.cursor = "grabbing";
    });
    window.addEventListener("mousemove", function (evt) {
      if (!dragging) return;
      var rect = svg.getBoundingClientRect();
      x -= (evt.clientX - lastX) * (w / rect.width);
      y -= (evt.clientY - lastY) * (h / rect.height);
      lastX = evt.clientX;
      lastY = evt.clientY;
      apply();
    });
    window.addEventListener("mouseup", function () {
      dragging = false;
      container.style.cursor = "grab";
    });

    container.addEventListener("dblclick", function () {
      x = original[0]; y = original[1]; w = original[2]; h = original[3];
      apply();
    });
  }

  document.querySelectorAll("[data-svg-zoom]").forEach(initSvgZoom);
})();
"""

# uPlot renders from raw data (not a pre-rendered image), so it can redraw
# proper axis ticks/gridlines for whatever range is currently zoomed to -
# unlike the SVG viewBox crop above, which just magnifies whatever ticks
# were baked in at the original full-range view. Interaction: wheel to
# zoom both axes around the cursor, shift+wheel/alt+wheel to zoom just
# x/y, drag to pan, double-click to reset, and dragging directly on an
# axis rescales just that axis (matplotlib-GUI-like).
UPLOT_INIT_SCRIPT = """
window.__colloquyCharts = {};

function zoomPlugin() {
  var xMin0, xMax0, yMin0, yMax0;

  function zoomBy(u, factor, axis) {
    u.batch(function () {
      if (axis !== "y") {
        var xMin = u.scales.x.min, xMax = u.scales.x.max;
        var xMid = (xMin + xMax) / 2;
        var xHalf = ((xMax - xMin) * factor) / 2;
        u.setScale("x", { min: xMid - xHalf, max: xMid + xHalf });
      }
      if (axis !== "x") {
        var yMin = u.scales.y.min, yMax = u.scales.y.max;
        var yMid = (yMin + yMax) / 2;
        var yHalf = ((yMax - yMin) * factor) / 2;
        u.setScale("y", { min: yMid - yHalf, max: yMid + yHalf });
      }
    });
  }

  function resetView(u) {
    u.batch(function () {
      u.setScale("x", { min: xMin0, max: xMax0 });
      u.setScale("y", { min: yMin0, max: yMax0 });
    });
  }

  function axisDrag(u, el, axisKey, isX) {
    var dragging = false, start = 0, startMin = 0, startMax = 0;
    el.style.cursor = isX ? "ew-resize" : "ns-resize";
    el.addEventListener("mousedown", function (e) {
      dragging = true;
      start = isX ? e.clientX : e.clientY;
      startMin = u.scales[axisKey].min;
      startMax = u.scales[axisKey].max;
      e.stopPropagation();
      e.preventDefault();
    });
    window.addEventListener("mousemove", function (e) {
      if (!dragging) return;
      var cur = isX ? e.clientX : e.clientY;
      var deltaPx = cur - start;
      var range = startMax - startMin;
      var rect = u.over.getBoundingClientRect();
      var size = isX ? rect.width : rect.height;
      var factor = Math.exp(((isX ? -deltaPx : deltaPx) / size) * 3);
      var mid = (startMin + startMax) / 2;
      var half = (range * factor) / 2;
      u.setScale(axisKey, { min: mid - half, max: mid + half });
    });
    window.addEventListener("mouseup", function () {
      dragging = false;
    });
  }

  return {
    hooks: {
      ready: function (u) {
        xMin0 = u.scales.x.min;
        xMax0 = u.scales.x.max;
        yMin0 = u.scales.y.min;
        yMax0 = u.scales.y.max;

        var over = u.over;
        over.style.cursor = "grab";

        over.addEventListener(
          "wheel",
          function (e) {
            e.preventDefault();
            var rect = over.getBoundingClientRect();
            var xVal = u.posToVal(e.clientX - rect.left, "x");
            var yVal = u.posToVal(e.clientY - rect.top, "y");
            var factor = e.deltaY < 0 ? 0.85 : 1 / 0.85;

            var axis;
            if (e.shiftKey) axis = "x";
            else if (e.altKey) axis = "y";

            u.batch(function () {
              if (axis !== "y") {
                var xMin = u.scales.x.min, xMax = u.scales.x.max;
                u.setScale("x", {
                  min: xVal - (xVal - xMin) * factor,
                  max: xVal + (xMax - xVal) * factor,
                });
              }
              if (axis !== "x") {
                var yMin = u.scales.y.min, yMax = u.scales.y.max;
                u.setScale("y", {
                  min: yVal - (yVal - yMin) * factor,
                  max: yVal + (yMax - yVal) * factor,
                });
              }
            });
          },
          { passive: false }
        );

        var dragging = false, startX = 0, startY = 0;
        var startXMin, startXMax, startYMin, startYMax;
        over.addEventListener("mousedown", function (e) {
          dragging = true;
          startX = e.clientX;
          startY = e.clientY;
          startXMin = u.scales.x.min;
          startXMax = u.scales.x.max;
          startYMin = u.scales.y.min;
          startYMax = u.scales.y.max;
          over.style.cursor = "grabbing";
        });
        window.addEventListener("mousemove", function (e) {
          if (!dragging) return;
          var rect = over.getBoundingClientRect();
          var xRange = startXMax - startXMin;
          var yRange = startYMax - startYMin;
          var dxVal = ((e.clientX - startX) / rect.width) * xRange;
          var dyVal = ((e.clientY - startY) / rect.height) * yRange;
          u.batch(function () {
            u.setScale("x", { min: startXMin - dxVal, max: startXMax - dxVal });
            u.setScale("y", { min: startYMin + dyVal, max: startYMax + dyVal });
          });
        });
        window.addEventListener("mouseup", function () {
          dragging = false;
          over.style.cursor = "grab";
        });

        over.addEventListener("dblclick", function () {
          resetView(u);
        });

        var axisEls = u.root.querySelectorAll(".u-axis");
        if (axisEls[0]) axisDrag(u, axisEls[0], "x", true);
        if (axisEls[1]) axisDrag(u, axisEls[1], "y", false);

        // Exposed for the zoom in/out/reset buttons rendered next to the
        // chart - one button, one action each, no modifier keys. axis is
        // "x", "y", or undefined (both).
        u.colloquyZoomBy = function (factor, axis) {
          zoomBy(u, factor, axis);
        };
        u.colloquyReset = function () {
          resetView(u);
        };
      },
    },
  };
}

window.colloquyRenderChart = function (containerId, payload) {
  var container = document.getElementById(containerId);
  if (!container) return;

  var series = [{}];
  for (var i = 0; i < payload.labels.length; i++) {
    series.push({
      label: payload.labels[i],
      stroke: payload.colors[i % payload.colors.length],
      width: 1.5,
    });
  }

  var opts = {
    width: container.clientWidth || 900,
    height: 420,
    series: series,
    scales: { x: { time: false } },
    axes: [{ label: "seconds" }, { label: "value" }],
    plugins: [zoomPlugin()],
  };

  var u = new uPlot(opts, payload.data, container);
  window.__colloquyCharts[containerId] = u;

  window.addEventListener("resize", function () {
    var width = container.clientWidth;
    if (width > 0) u.setSize({ width: width, height: 420 });
  });
};

window.colloquyZoomChart = function (containerId, action) {
  var u = window.__colloquyCharts[containerId];
  if (!u) return;
  if (action === "reset") {
    u.colloquyReset();
    return;
  }
  var factor = action.indexOf("in") === 0 ? 0.75 : 1 / 0.75;
  var axis =
    action.indexOf("-x") !== -1 ? "x" : action.indexOf("-y") !== -1 ? "y" : undefined;
  u.colloquyZoomBy(factor, axis);
};
"""


class WSGI2(Base):
    def __init__(self, server, environ, start_response, db_path=None):
        super().__init__(owner=server)
        self._server = server
        self._colloquy = server.colloquy
        self._db_path = db_path
        self._environ = environ
        self._start_response = start_response
        self._base_path = None
        self._root = Path("app")
        self._status, self._headers, self._content = self._parse()

    def __iter__(self):
        self._start_response(self._status, self._headers)
        yield self._content

    @property
    def shutdown_event(self):
        return self.owner.shutdown_event

    @property
    def restart_event(self):
        return self.owner.restart_event

    @property
    def colloquy(self):
        return self._colloquy

    @property
    def name(self):
        return "wsgi"

    def get_states(self, *args):
        db_path = self._db_path or Path("testspace/version6.json")
        states = self.colloquy.get_states(*args)
        return states

    def _parse(self):
        args = self._parse_path()
        print(f"{args=}")
        if not args:
            return self._parse_app()

        key, *leftovers = args
        if key == "emergency-stop":
            return self._parse_emergency_stop(*leftovers)

        if key == "shutdown":
            return self._parse_shutdown(*leftovers)

        if key == "restart":
            return self._parse_restart(*leftovers)

        if key == self._root.name:
            return self._parse_app(*leftovers)

        content_type = "text/text; charset=utf-8"
        status = "404 Not found"
        headers = [("Content-Type", content_type)]
        return status, headers, b""

    def _parse_path(self):
        """Parse the path."""
        request_path = self._environ["PATH_INFO"]
        request_path = unquote(request_path)
        request_path = request_path.strip("/")
        request_path = request_path.encode("iso-8859-1").decode("utf-8")
        return Path(request_path).parts

    def _parse_app(self, *args):
        to_render = self.get_states(*args)
        self._base_path = Path(*to_render["path"])

        # pprint4(obj=to_render)
        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        css_style = {
            "height": "100%",
            "display": "flex",
            "flex-direction": "column",
            "font-size": "1rem",
        }

        doc, tag, text = Doc().tagtext()
        doc.asis("<!DOCTYPE html>")
        with tag("html", style=export_style(css_style)):
            with tag("head"):
                with tag("style"):
                    doc.asis(UPLOT_CSS)

            with tag(
                "body",
                style="flex:1; display: flex; flex-direction: column; overflow: auto;",
            ):
                # Must come before _html_recursion()'s output below: it
                # emits inline <script> calls to colloquyRenderChart() for
                # each chart, which needs uPlot and colloquyRenderChart
                # itself to already be defined by the time those run.
                with tag("script"):
                    doc.asis(UPLOT_JS)
                with tag("script"):
                    doc.asis(UPLOT_INIT_SCRIPT)

                with tag(
                    "div", name="server commands", style="display: flex; gap: 1ch;"
                ):
                    with tag("div", style=""):
                        with tag(
                            "a",
                            href="/emergency-stop",
                            style="color: white; background: red; font-weight: bold; padding: 0 1ch;",
                        ):
                            text("EMERGENCY STOP")

                    with tag("div", style=""):
                        with tag("a", href="/shutdown"):
                            text("shutdown")

                    with tag("div", style=""):
                        with tag("a", href="/restart"):
                            text("restart")

                    with tag("div", style=""):
                        path = self._root / self._base_path
                        with tag("a", href=f"/{path.as_posix()}"):
                            text("refresh")

                doc.asis(
                    self._html_navigation(
                        to_render=to_render,
                    )
                )

                with tag("div", name="thread count", style="display: flex;"):
                    text(f"thread count: {len(self.all_threads)}")

                doc.asis(
                    self._html_recursion(
                        obj=to_render,
                    )
                )

                with tag("script"):
                    doc.asis(SVG_ZOOM_SCRIPT)

        html = doc.getvalue()
        html = indent(html)
        content = html.encode()

        return status, headers, content

    def _html_navigation(self, to_render):
        doc, tag, text = Doc().tagtext()
        css_style = {
            "display": "flex",
            "overflow-x": "auto",
            "text-wrap": "nowrap",
        }
        with tag("div", name="navigation", style=export_style(css_style)):
            with tag("div"):
                with tag("a", href=f"/"):
                    text("/home")
            href = self._root
            for name in to_render["path"]:
                href = href / name
                with tag("div"):
                    with tag("a", href=f"/{href.as_posix()}"):
                        text("/" + name)

        html = doc.getvalue()
        return indent(html)

    def _html_keyboard(self, obj):
        doc, tag, text = Doc().tagtext()

        call_path = Path(*obj["path"]).relative_to(self._base_path)
        base_path = self._root / self._base_path / "call" / call_path
        keyboard_path = base_path / f"keyboard"

        with tag(
            "div", name="keyboard", style="display: flex; flex-direction: column; "
        ):
            with tag("div", style="display: flex; gap: 1ch;"):
                with tag("div", name="prompt"):
                    text(">>>")
                with tag("div", name="value", style="flex:1;"):
                    if "keyboard" in obj:
                        text(obj["keyboard"]["value"])
                    else:
                        text("")

                path = keyboard_path / "pop"
                with tag("div", name="pop"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("pop")

                path = keyboard_path / "clear"
                with tag("div", name="clear"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("clear")

                path = base_path
                if "keyboard" in obj:
                    path = base_path / obj["keyboard"]["value"]
                with tag("div", name="commit"):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("call")

            all_char = "abcdefghijklmnopqrstuvwxyz"
            with tag("div", name="line1", style="display: flex;"):
                for char in all_char[:10]:
                    path = keyboard_path / char

                    with tag(
                        "div", style="flex:1; display: flex; justify-content: center;"
                    ):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)

            with tag("div", name="line3", style="display: flex;"):
                for char in all_char[10:21]:
                    path = keyboard_path / char

                    with tag(
                        "div", style="flex:1; display: flex; justify-content: center;"
                    ):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)

            with tag("div", name="line3", style="display: flex;"):
                for char in all_char[21:]:
                    path = keyboard_path / char

                    with tag(
                        "div", style="flex:1; display: flex; justify-content: center;"
                    ):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(char)
                path = keyboard_path / "space"
                with tag(
                    "div", style="flex:3; display: flex; justify-content: center;"
                ):
                    with tag("a", href=f"/{path.as_posix()}"):
                        text("space")

        html = doc.getvalue()
        return indent(html)

    def _html_recursion(self, obj):
        doc, tag, text = Doc().tagtext()

        style = {
            "margin-left": "1ch",
            "padding-left": "0.5ch",
            "border-left": "1px gray dashed",
            "display": "flex",
            "flex-direction": "column",
            "flex": "1",
            "overflow": "auto",
            "min-height": "10rem",
            "justify-content": "space-between",
        }

        with tag("div", name=obj["name"], style=export_style(style)):
            for key, value in obj.items():
                # print(f"{key=}")
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
                    with tag("div"):
                        text(f"value: {value}")
                    continue

                if not isinstance(value, dict):
                    func_path = Path(*obj["path"]) / key
                    call_path = func_path.relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path

                    style = {"flex": "1"}
                    with tag("div", name=key, style=export_style(style)):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{key}()")
                    continue

                if "chart" in value:
                    container_id = "chart-" + re.sub(
                        r"[^a-zA-Z0-9_-]+", "-", "-".join(value["path"])
                    )
                    with tag("div", name=key):
                        with tag(
                            "div",
                            style="font-size: 0.75rem; opacity: 0.7;",
                        ):
                            text(
                                "scroll to zoom - shift+scroll x only - alt+scroll y only - "
                                "drag to pan - drag an axis to rescale it - double-click to reset"
                            )
                        with tag(
                            "div", style="display: flex; gap: 1ch; margin: 0.25rem 0;"
                        ):
                            for label, action in (
                                ("zoom in", "in"),
                                ("zoom out", "out"),
                                ("zoom in x", "in-x"),
                                ("zoom out x", "out-x"),
                                ("zoom in y", "in-y"),
                                ("zoom out y", "out-y"),
                                ("reset zoom", "reset"),
                            ):
                                onclick = f"colloquyZoomChart({json.dumps(container_id)}, {json.dumps(action)})"
                                with tag(
                                    "button", type="button", onclick=onclick
                                ):
                                    text(label)
                        with tag(
                            "div",
                            id=container_id,
                            style="width: 100%; max-width: 900px;",
                        ):
                            pass
                        with tag("script"):
                            doc.asis(
                                f"colloquyRenderChart({json.dumps(container_id)}, {value['chart']});"
                            )
                    continue

                if "svg" in value:
                    style = {
                        "overflow": "hidden",
                        "border": "1px solid #8888",
                        "cursor": "grab",
                        "touch-action": "none",
                    }
                    with tag("div", name=key):
                        with tag(
                            "div",
                            style="font-size: 0.75rem; opacity: 0.7;",
                        ):
                            text(
                                "scroll to zoom - shift+scroll to zoom x-axis only - drag to pan - double-click to reset"
                            )
                        with tag(
                            "div", **{"data-svg-zoom": ""}, style=export_style(style)
                        ):
                            doc.asis(value["svg"])
                    continue

                # print(f"{value=}")
                if value.get("opened", False):
                    if value:
                        doc.asis(self._html_if_opened(obj=value))
                    continue

                name = value["name"]

                # Plain informational leaves (e.g. _snapshot_if_opened
                # entries like "sender"/"matches"/"last match") aren't real
                # openable nodes - they have no "open" handler, so drawing
                # the open-arrow/call-link below would 404/crash on click.
                if "value" in value:
                    with tag("div", name="value"):
                        text(f"{name}: {value['value']}")
                    continue

                value_path = Path(*value["path"])

                style = {"display": "flex", "gap": "1ch", "flex": "1"}

                with tag("div", name="title", style=export_style(style)):
                    with tag("div", name="open"):
                        call_path = value_path.relative_to(self._base_path)
                        path = (
                            self._root / self._base_path / "call" / call_path / "open"
                        )

                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f">")

                    # name = obj["name"]
                    path = self._root / value_path
                    with tag("div", name="name"):
                        with tag("a", href=f"/{path.as_posix()}"):
                            text(f"{name}")

        html = doc.getvalue()
        return indent(html)

    def _html_if_opened(self, obj):
        doc, tag, text = Doc().tagtext()
        name = obj["name"]

        style = {
            "margin-bottom": "0.5rem",
            "flex": "1",
            "overflow": "auto",
            "min-height": "10rem",
        }

        with tag("div", name="opened", style=export_style(style)):
            style = {"display": "flex", "gap": "1ch", "margin-bottom": "0.5rem"}

            with tag("div", name="title", style=export_style(style)):
                with tag("div", name="close"):
                    call_path = Path(*obj["path"]).relative_to(self._base_path)
                    path = self._root / self._base_path / "call" / call_path / "close"

                    with tag("a", href=f"/{path.as_posix()}"):
                        text(f"<")

                with tag("div", name="name"):
                    path = self._root / Path(*obj["path"])
                    with tag("a", href=f"/{path.as_posix()}"):
                        text(f"{name}:")

            doc.asis(self._html_recursion(obj=obj))

        html = doc.getvalue()
        return indent(html)

    def _parse_emergency_stop(self):
        """Disable torque and signal every thread to stop right now - no
        homing, no coordinated move (that's the opposite of an emergency
        stop). Unlike /shutdown, the HTTP server itself is kept alive so
        this page (and /restart) stay reachable; the hardware side is
        inert until a real process restart, since BaseThread._shutdown is
        never cleared once set.
        """
        self.colloquy.emergency_stop()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("strong"):
                text("EMERGENCY STOP: torque disabled, all threads signaled to stop.")
        with tag("div"):
            text(
                "Motion is inert until the process is restarted "
                "(BaseThread._shutdown does not clear on its own)."
            )
        with tag("div"):
            with tag("a", href="/restart"):
                text("restart")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content

    def _parse_shutdown(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.colloquy.shutdown_neopixels()
        self.colloquy.move_to_origin()
        self.colloquy.disable_torque()

        self.shutdown_event.set()

        content_type = "text/plain; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]
        lines = [
            f"thread count: {len(self.all_threads)}",
            "Goodbye!",
        ]
        content = "\n".join(lines).encode()

        return status, headers, content

    def _parse_restart(self):
        self.colloquy.shutdown()
        self.colloquy.join_all()
        self.shutdown_event.set()
        self.restart_event.set()

        content_type = "text/html; charset=utf-8"
        status = "200 OK"
        headers = [("Content-Type", content_type)]

        doc, tag, text = Doc().tagtext()
        with tag("div"):
            with tag("a", href=f"/"):
                text("reload")

        html = doc.getvalue()
        content = html.encode()

        return status, headers, content
