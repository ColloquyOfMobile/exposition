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
