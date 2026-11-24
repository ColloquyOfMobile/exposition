(() => {
  "use strict";
  if (location.pathname.split("/").includes("call")) {
    history.replaceState(null, "", document.body.dataset.canonical);
  }

  function connectMonitor(monitor) {
    const feed = document.getElementById("log-feed");
    const picker = document.getElementById("source");
    const button = document.getElementById("pause");
    const status = document.getElementById("log-status");
    const count = document.getElementById("event-count");
    const threads = document.getElementById("thread-count");

    let source = monitor.dataset.source;
    if (!source) {
      try { source = sessionStorage.getItem("console-log-source") || ""; }
      catch { /* Storage is optional. */ }
    }
    let paused = false;
    let timer;
    let pending;
    let previousEvents;
    let previousChoices;
    let revision;
    function indicate(label, state) {
      if (status.textContent !== label) status.textContent = label;
      status.dataset.state = state;
    }

    function choices(names) {
      const key = JSON.stringify([names, source]);
      if (key === previousChoices) return;
      previousChoices = key;
      const options = [new Option("Recent threads", "")];
      for (const name of names) options.push(new Option(name, name));
      if (source && !names.includes(source)) {
        options.push(new Option(source + " (no output)", source));
      }
      picker.replaceChildren(...options);
      picker.value = source;
    }

    function draw(events) {
      const key = JSON.stringify(events);
      if (key === previousEvents) return;
      const follow = previousEvents === undefined ||
        feed.scrollHeight - feed.scrollTop - feed.clientHeight < 6;
      previousEvents = key;
      const fragment = document.createDocumentFragment();
      if (!events.length) {
        const empty = document.createElement("p");
        empty.className = "empty-log";
        empty.textContent = source ? "Waiting for output from this thread." : "Waiting for thread output.";
        fragment.append(empty);
      }
      for (const [stamp, name, message] of events) {
        const entry = document.createElement("div");
        entry.className = "log-entry";
        const time = document.createElement("time");
        time.textContent = stamp;
        const body = document.createElement("div");
        const origin = document.createElement("span");
        origin.className = "entry-source";
        origin.textContent = name;
        const line = document.createElement("span");
        line.className = "entry-message";
        line.textContent = message;
        body.append(origin, line);
        entry.append(time, body);
        fragment.append(entry);
      }
      feed.replaceChildren(fragment);
      if (follow) feed.scrollTop = feed.scrollHeight;
      count.textContent = events.length + (events.length === 1 ? " line" : " lines");
    }

    async function poll() {
      clearTimeout(timer);
      if (pending) pending.abort();
      if (paused || document.hidden) return;
      const request = new AbortController();
      pending = request;
      const timeout = setTimeout(() => request.abort(), 8000);
      let delay = 1500;
      try {
        const url = new URL("/thread-log", location.origin);
        if (source) url.searchParams.set("source", source);
        const res = await fetch(url, {
          cache: "no-store",
          headers: revision ? { "If-None-Match": revision } : {},
          signal: request.signal
        });
        if (request !== pending || paused || document.hidden) return;
        if (res.status === 304) {
          indicate("Live", "live");
          return;
        }
        if (!res.ok) throw new Error();
        const data = await res.json();
        if (request !== pending || paused || document.hidden) return;
        revision = res.headers.get("ETag");
        choices(data.sources);
        draw(data.events);
        threads.textContent = data.threads + (data.threads === 1 ? " active thread" : " active threads");
        indicate("Live", "live");
      } catch {
        if (request === pending && !paused && !document.hidden) indicate("Reconnecting", "offline");
        delay = 4000;
      } finally {
        clearTimeout(timeout);
        if (request === pending) {
          pending = null;
          if (!paused && !document.hidden) timer = setTimeout(poll, delay);
        }
      }
    }

    picker.addEventListener("change", () => {
      source = picker.value;
      try { sessionStorage.setItem("console-log-source", source); } catch { /* optional */ }
      previousEvents = undefined;
      revision = null;
      feed.replaceChildren();
      count.textContent = "";
      indicate("Connecting", "waiting");
      poll();
    });
    button.addEventListener("click", () => {
      paused = !paused;
      picker.disabled = paused;
      button.textContent = paused ? "Resume" : "Pause";
      indicate(paused ? "Paused" : "Connecting", "waiting");
      poll();
    });
    document.addEventListener("visibilitychange", poll);
    function disconnect() {
      clearTimeout(timer);
      if (pending) pending.abort();
      pending = null;
    }
    window.addEventListener("pagehide", disconnect);
    window.addEventListener("pageshow", poll);
    poll();
    return () => {
      paused = true;
      clearTimeout(timer);
      if (pending) pending.abort();
      document.removeEventListener("visibilitychange", poll);
      window.removeEventListener("pageshow", poll);
      window.removeEventListener("pagehide", disconnect);
    };
  }

  let monitor = document.querySelector(".monitor");
  let stopMonitor = monitor && connectMonitor(monitor);
  const controls = document.querySelector(".controls");
  const liveStatus = document.getElementById("live-status");
  let busy = false;
  // What this page pressed, spinning until its answer arrives; and what
  // the server says is in flight from every page (ui/in_flight.py).
  let pressedHere = null;
  let inFlight = [];
  let inFlightAt = 0;
  // A live tree that arrived while it could not be drawn (a press in
  // flight, text selected, a pointer held down): drawn once it can be.
  let waiting = null;
  let pointerDown = false;

  // "/app/drivers/call/female1/home" -> "drivers/female1/home", the name
  // the server gives a press whichever page it was pressed on.
  function commandOf(address) {
    if (!address) return null;
    let parts;
    try {
      parts = new URL(address, location.origin).pathname.split("/").filter(Boolean)
        .map(part => decodeURIComponent(part));
    } catch { return null; }
    if (!parts.includes("call")) return null;
    return parts.slice(1).filter(part => part !== "call").join("/");
  }

  function pressables() {
    const found = [];
    for (const link of controls.querySelectorAll("a[href]")) {
      found.push([commandOf(link.getAttribute("href")), link]);
    }
    for (const form of controls.querySelectorAll("form[action]")) {
      const button = form.querySelector("button[type=submit]");
      if (button) found.push([commandOf(form.getAttribute("action")), button]);
    }
    return found;
  }

  function markCommands() {
    const states = new Map(inFlight.map(entry => [entry.command, entry]));
    const elapsedNow = (performance.now() - inFlightAt) / 1000;
    for (const [command, element] of pressables()) {
      const entry = command && states.get(command);
      const state = entry ? entry.state : (element === pressedHere ? "queued" : "");
      if (!state) {
        if (element.dataset.command) {
          delete element.dataset.command;
          delete element.dataset.elapsed;
          element.removeAttribute("aria-busy");
        }
        continue;
      }
      if (element.dataset.command !== state) element.dataset.command = state;
      element.setAttribute("aria-busy", "true");
      const seconds = entry ? Math.floor(entry.seconds + elapsedNow) : 0;
      const label = seconds >= 2 ? (state === "queued" ? "waiting " : "") + seconds + "s" : "";
      if (label) element.dataset.elapsed = label;
      else delete element.dataset.elapsed;
    }
  }
  setInterval(() => { if (inFlight.length) markCommands(); }, 1000);

  function indicateLive(label, state, detail) {
    if (!liveStatus) return;
    liveStatus.textContent = label;
    liveStatus.dataset.state = state;
    if (detail) liveStatus.title = detail;
    else liveStatus.removeAttribute("title");
  }

  // Put fresh controls in place of the old ones, keeping what the reader
  // is in the middle of: an editor being typed in, the thread log, a
  // picker's scroll, an open <details>, focus and the scroll position.
  function replaceControls(fresh, revision, {keepEditor, anchorHref, anchorAction, anchorTop} = {}) {
    const x = scrollX, y = scrollY;
    const active = document.activeElement;
    const focusHref = controls.contains(active) ? active.closest("a")?.href : null;
    const pickerOffsets = new Map(Array.from(controls.querySelectorAll("[data-picker-path]"),
      picker => [picker.dataset.pickerPath, picker.scrollTop]));
    const openDetails = new Set(Array.from(controls.querySelectorAll("details[open] > summary"),
      summary => summary.textContent));
    const forms = Array.from(fresh.querySelectorAll("form"));
    for (const old of controls.querySelectorAll("form")) {
      const area = old.querySelector("textarea");
      if (!area || !keepEditor(old, area)) continue;
      const match = forms.find(form => form.getAttribute("action") === old.getAttribute("action"));
      if (match) match.replaceWith(old);
    }
    const nextMonitor = fresh.querySelector(".monitor");
    if (monitor && nextMonitor) nextMonitor.replaceWith(monitor);
    if (monitor && !nextMonitor) { stopMonitor(); monitor = null; }
    controls.replaceChildren(...fresh.childNodes);
    if (revision) controls.dataset.revision = revision;
    for (const picker of controls.querySelectorAll("[data-picker-path]")) {
      picker.scrollTop = pickerOffsets.get(picker.dataset.pickerPath) || 0;
    }
    for (const summary of controls.querySelectorAll("details > summary")) {
      if (openDetails.has(summary.textContent)) summary.parentElement.open = true;
    }
    if (!monitor && nextMonitor) {
      monitor = nextMonitor;
      stopMonitor = connectMonitor(monitor);
    }
    markCommands();
    document.dispatchEvent(new Event("tree-updated"));

    const links = Array.from(controls.querySelectorAll("a"));
    if (anchorHref !== undefined || anchorAction) {
      const inverse = anchorHref?.replace(/\/(open|close)$/, (_, end) => end === "open" ? "/close" : "/open");
      const anchor = links.find(a => a.href === anchorHref) || links.find(a => a.href === inverse)
        || Array.from(controls.querySelectorAll("button")).find(b => anchorAction && b.form?.action === anchorAction);
      if (anchor && focusHref !== null) anchor.focus({preventScroll: true});
      if (anchor) { window.scrollBy(0, anchor.getBoundingClientRect().top - anchorTop); return; }
    } else if (focusHref) {
      links.find(a => a.href === focusHref)?.focus({preventScroll: true});
    }
    window.scrollTo(x, y);
  }

  async function update(url, options, pressed) {
    if (busy) return;
    busy = true;
    pressedHere = pressed;
    markCommands();
    controls.setAttribute("aria-busy", "true");
    const notice = document.getElementById("command-result");
    notice.replaceChildren();
    let answered = false;
    try {
      const response = await fetch(url, options);
      const next = new DOMParser().parseFromString(await response.text(), "text/html");
      answered = true;
      const fresh = next.querySelector(".controls");
      if (!fresh || next.body.dataset.canonical !== document.body.dataset.canonical) {
        if (response.redirected) {
          location.assign(response.url);
          return;
        }
        notice.replaceChildren(...next.body.childNodes);
        if (!notice.textContent.trim()) notice.textContent = "Command returned " + response.status;
        notice.scrollIntoView({block: "nearest"});
        return;
      }
      // The answer is newer than anything the stream sent meanwhile.
      waiting = null;
      const action = pressed.form?.action;
      replaceControls(fresh, fresh.dataset.revision, {
        keepEditor: old => old.action !== action,
        anchorHref: pressed.closest("a")?.href,
        anchorAction: action,
        anchorTop: pressed.getBoundingClientRect().top,
      });
    } catch {
      if (!answered) {
        notice.textContent = "Connection lost before the answer came. " +
          "This page updates itself once the server answers again.";
      }
    } finally {
      busy = false;
      pressedHere = null;
      controls.removeAttribute("aria-busy");
      markCommands();
      drawWaiting();
    }
  }

  // --- the live stream (ui/live.py) -------------------------------------

  function canDraw() {
    if (busy || pointerDown) return false;
    const selection = getSelection();
    if (selection && !selection.isCollapsed && selection.rangeCount &&
        controls.contains(selection.getRangeAt(0).commonAncestorContainer)) return false;
    if (controls.contains(document.activeElement) && document.activeElement.matches("select")) return false;
    return true;
  }

  function drawWaiting() {
    if (!waiting || !canDraw()) return;
    const {html, revision} = waiting;
    waiting = null;
    if (revision && revision === controls.dataset.revision) return;
    const template = document.createElement("template");
    template.innerHTML = html;
    replaceControls(template.content, revision, {
      // An editor is somebody's unsaved work: kept while it is changed
      // or being typed in, and brought up to date otherwise.
      keepEditor: (form, area) => area.value !== area.defaultValue || form.contains(document.activeElement),
    });
  }

  document.addEventListener("pointerdown", () => { pointerDown = true; });
  document.addEventListener("pointerup", () => { pointerDown = false; drawWaiting(); });
  document.addEventListener("pointercancel", () => { pointerDown = false; drawWaiting(); });
  document.addEventListener("selectionchange", drawWaiting);
  controls.addEventListener("focusout", () => setTimeout(drawWaiting));

  let live = null;
  function connectLive() {
    if (live || !window.EventSource) {
      if (!window.EventSource) indicateLive("Not live", "offline", "This browser cannot keep the page current.");
      return;
    }
    const url = new URL("/live" + document.body.dataset.canonical, location.origin);
    url.searchParams.set("revision", controls.dataset.revision || "");
    const source = new EventSource(url);
    live = source;
    source.addEventListener("open", () => indicateLive("Live", "live"));
    source.addEventListener("error", () => {
      if (source.readyState === EventSource.CLOSED) {
        live = null;
        indicateLive("Not live", "offline", "The server refused the live view. Reload the page.");
      } else {
        indicateLive("Reconnecting", "offline");
      }
      // Nothing is known to be in flight once the stream is down.
      inFlight = [];
      markCommands();
    });
    source.addEventListener("commands", event => {
      try { inFlight = JSON.parse(event.data); } catch { inFlight = []; }
      inFlightAt = performance.now();
      markCommands();
    });
    source.addEventListener("tree", event => {
      waiting = {html: event.data, revision: event.lastEventId};
      drawWaiting();
    });
    source.addEventListener("trouble", event => {
      if (event.data) indicateLive("Not updating", "trouble", event.data);
      else indicateLive("Live", "live");
    });
    source.addEventListener("gone", () => {
      // The node is not there any more (or the board is out): the
      // ordinary page says what happened.
      source.close();
      live = null;
      location.reload();
    });
  }
  function disconnectLive() {
    if (live) live.close();
    live = null;
  }
  window.addEventListener("pagehide", disconnectLive);
  window.addEventListener("pageshow", connectLive);
  connectLive();

  document.addEventListener("click", event => {
    const link = event.target.closest("a");
    if (!link || event.defaultPrevented || event.button || event.ctrlKey || event.metaKey ||
        event.shiftKey || event.altKey || link.origin !== location.origin) return;
    if (!(controls.contains(link) && link.pathname.split("/").includes("call"))) return;
    event.preventDefault();
    update(link.href, {cache:"no-store"}, link);
  });
  controls.addEventListener("submit", event => {
    const form = event.target;
    if (!form.matches('form[method="post"]') || !form.querySelector("textarea[name=content]")) return;
    event.preventDefault();
    const button = event.submitter || form.querySelector("button[type=submit]") || form;
    update(form.action, {method:"POST", body:new URLSearchParams(new FormData(form))}, button);
  });
})();
