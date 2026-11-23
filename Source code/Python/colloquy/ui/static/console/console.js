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
  let busy = false;

  async function update(url, options, pressed) {
    if (busy) return;
    busy = true;
    controls.setAttribute("aria-busy", "true");
    const notice = document.getElementById("command-result");
    notice.replaceChildren();
    try {
      const response = await fetch(url, options);
      const next = new DOMParser().parseFromString(await response.text(), "text/html");
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

      const top = pressed.getBoundingClientRect().top;
      const x = scrollX, y = scrollY;
      const link = pressed.closest("a");
      const href = link?.href;
      const wasFocused = pressed.contains(document.activeElement);
      const action = pressed.form?.action;
      const forms = Array.from(fresh.querySelectorAll("form"));
      for (const old of controls.querySelectorAll("form")) {
        const match = forms.find(form => form.getAttribute("action") === old.getAttribute("action"));
        if (match && old.action !== action && old.querySelector("textarea")) match.replaceWith(old);
      }
      const nextMonitor = fresh.querySelector(".monitor");
      if (monitor && nextMonitor) nextMonitor.replaceWith(monitor);
      if (monitor && !nextMonitor) { stopMonitor(); monitor = null; }
      controls.replaceChildren(...fresh.childNodes);
      if (!monitor && nextMonitor) {
        monitor = nextMonitor;
        stopMonitor = connectMonitor(monitor);
      }
      document.dispatchEvent(new Event("tree-updated"));
      const links = Array.from(controls.querySelectorAll("a"));
      const inverse = href?.replace(/\/(open|close)$/, (_, end) => end === "open" ? "/close" : "/open");
      const anchor = links.find(a => a.href === href) || links.find(a => a.href === inverse)
        || Array.from(controls.querySelectorAll("button")).find(b => action && b.form?.action === action);
      if (anchor && wasFocused) anchor.focus({preventScroll:true});
      if (anchor) window.scrollBy(0, anchor.getBoundingClientRect().top - top);
      else window.scrollTo(x, y);
    } catch {
      notice.textContent = "Connection lost. Refresh values to check the result.";
    } finally {
      busy = false;
      controls.removeAttribute("aria-busy");
    }
  }

  document.addEventListener("click", event => {
    const link = event.target.closest("a");
    if (!link || event.defaultPrevented || event.button || event.ctrlKey || event.metaKey ||
        event.shiftKey || event.altKey || link.origin !== location.origin) return;
    if (!(controls.contains(link) && link.pathname.split("/").includes("call")) &&
        !link.matches(".reload")) return;
    event.preventDefault();
    update(link.href, {cache:"no-store"}, link);
  });
  controls.addEventListener("submit", event => {
    const form = event.target;
    if (!form.matches('form[method="post"]') || !form.querySelector("textarea[name=content]")) return;
    event.preventDefault();
    update(form.action, {method:"POST", body:new URLSearchParams(new FormData(form))},
      event.submitter || form);
  });
})();
