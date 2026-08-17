// Keeps the virtual-hardware panel up to date without reloading the page.
//
// Reloading is not an option here: the address bar routinely holds a
// /call/... path, and re-issuing it would run the command again - clicking
// "start" twice by refreshing is not something this UI should make
// possible. So only the panel is re-fetched, from a route that renders
// value leaves and skips every callable.
//
// The simulation changes constantly (a blinking ring changes ten times per
// pattern), so a second is about right: fast enough to watch a pattern
// play out, slow enough not to crowd a single-threaded dev server that is
// also serving whatever the user is clicking.
(function () {
  var INTERVAL_MS = 1000;
  // A restart takes the server away for a few seconds and every poll in
  // that window fails. Backing off and carrying on means the panel comes
  // back by itself afterwards; giving up on the first error would leave a
  // frozen panel that still looks live, which is worse than a blank one.
  var RETRY_MS = 5000;

  var target = document.getElementById("virtual-state");
  if (!target) {
    return;
  }

  var failing = false;

  function schedule(delay) {
    setTimeout(refresh, delay);
  }

  function refresh() {
    // Pause while the tab is hidden: nobody is watching, and this server
    // handles one request at a time.
    if (document.hidden) {
      schedule(INTERVAL_MS);
      return;
    }

    fetch("/virtual-state", { cache: "no-store" })
      .then(function (response) {
        if (!response.ok) {
          throw new Error("HTTP " + response.status);
        }
        return response.text();
      })
      .then(function (html) {
        target.innerHTML = html;
        if (failing) {
          failing = false;
          console.log("[virtual-state] polling again");
        }
        schedule(INTERVAL_MS);
      })
      .catch(function (error) {
        if (!failing) {
          // Once per outage, not once per second.
          failing = true;
          console.log("[virtual-state] paused, retrying: " + error);
        }
        schedule(RETRY_MS);
      });
  }

  schedule(INTERVAL_MS);
})();
