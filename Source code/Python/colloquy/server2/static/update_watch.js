// update_watch.js
//
// Keeps the update banner true on a page that is just sitting open, and
// loads the page again once the server has restarted under it.
//
// The banner itself is drawn by the server (server2/updates.py), so a
// page loaded during an update says so without any of this. What this
// adds is the page that was already open: on the installation's laptop
// the repository pulls by itself and the server restarts onto what it
// pulled, and nobody pressed anything to make that happen.
//
// It asks /update-status, which answers without going near the tree's
// command lock. `boot` in the answer names the process that gave it; the
// page holds the one it was drawn under, and a different one means the
// server has been restarted since - by an update, by somebody pressing
// restart in another tab, it does not matter which.
(function () {
  "use strict";

  var box = document.getElementById("update-notice");
  if (!box || !window.fetch) {
    return;
  }

  var boot = box.getAttribute("data-boot");
  var back = box.getAttribute("data-back") || "/";
  // A page that is itself the announcement of a restart (the one
  // /mount-main-pcb answers with) keeps its own sentence until a new
  // process answers: the old one is on its way down and has nothing
  // further to say about it.
  var sticky = box.hasAttribute("data-sticky");
  // Was a restart announced? Then silence from the server is the restart
  // and not a fault, and is said differently.
  var announced = sticky || box.getAttribute("data-phase") === "restarting";

  var QUIET = 5000; // nothing going on
  var BUSY = 2000; // an update is under way
  var DOWN = 1000; // waiting for the server to come back

  function show(phase, text) {
    box.setAttribute("data-phase", phase);
    box.textContent = text;
    box.hidden = !phase;
  }

  function comeBack() {
    // A page with a text box on it may hold something unsaved, and the
    // save still works after a restart - so that page is told, not
    // reloaded from under whoever is typing into it.
    if (document.querySelector("textarea")) {
      show(
        "updated",
        "The server has been restarted. Save what you are writing, " +
          "then reload this page."
      );
      return;
    }
    window.location.replace(back);
  }

  function ask() {
    fetch("/update-status", { cache: "no-store" })
      .then(function (response) {
        return response.json();
      })
      .then(function (said) {
        if (said.boot !== boot) {
          comeBack();
          return;
        }
        if (sticky) {
          window.setTimeout(ask, DOWN);
          return;
        }
        announced = said.phase === "restarting";
        show(said.phase, said.text);
        window.setTimeout(ask, said.phase ? BUSY : QUIET);
      })
      .catch(function () {
        if (!sticky) {
          show(
            announced ? "restarting" : "down",
            announced
              ? "Restarting to run the update. This page comes back by itself."
              : "The server is not answering. This page comes back by " +
                  "itself when it does."
          );
        }
        window.setTimeout(ask, DOWN);
      });
  }

  window.setTimeout(ask, announced ? DOWN : BUSY);
})();
