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
    var original = viewBox.split(/\s+/).map(Number);
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
