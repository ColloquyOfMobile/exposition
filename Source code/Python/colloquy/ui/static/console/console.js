(() => {
  "use strict";
  const monitor = document.querySelector(".monitor");
  const feed = document.getElementById("log-feed");
  const picker = document.getElementById("source");
  const button = document.getElementById("pause");
  const status = document.getElementById("log-status");
  const count = document.getElementById("event-count");
  const threads = document.getElementById("thread-count");

  // Reload, bookmarks and browser history should address the node after a press.
  if (location.pathname.split("/").includes("call")) {
    history.replaceState(null, "", document.body.dataset.canonical);
  }

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
  const workspace = document.querySelector(".workspace");
  const views = document.querySelectorAll(".view-switch button");
  function selectPane(id) {
    workspace.dataset.pane = id;
    for (const view of views) {
      view.setAttribute("aria-pressed", String(view.getAttribute("aria-controls") === id));
    }
  }
  for (const view of views) {
    view.addEventListener("click", () => selectPane(view.getAttribute("aria-controls")));
  }
  selectPane(monitor.dataset.source ? "monitor" : "explorer");

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
  document.querySelectorAll("[data-follow-source]").forEach(link => {
    link.hidden = false;
    link.addEventListener("click", () => {
      source = link.dataset.followSource;
      paused = false;
      picker.disabled = false;
      button.textContent = "Pause";
      previousEvents = undefined;
      revision = null;
      indicate("Connecting", "waiting");
      selectPane("monitor");
      monitor.scrollIntoView({block: "nearest"});
      poll();
    });
  });
  button.addEventListener("click", () => {
    paused = !paused;
    picker.disabled = paused;
    button.textContent = paused ? "Resume" : "Pause";
    indicate(paused ? "Paused" : "Connecting", "waiting");
    poll();
  });
  document.addEventListener("visibilitychange", poll);
  window.addEventListener("pagehide", () => {
    clearTimeout(timer);
    if (pending) pending.abort();
    pending = null;
  });
  window.addEventListener("pageshow", poll);
})();
