(function () {
  "use strict";

  var TIME_ZONE = "America/Los_Angeles";
  var EPOCH_DAY = Date.UTC(2025, 0, 1) / 86400000; // day 0 of the cycle shows 1.1
  var MODE_KEY = "gita-mode";

  var verses = [];
  var indexByKey = {};
  var featured = []; // indices into verses
  var mode = "all";
  var current = 0;
  var showingToday = true;

  var $ = function (id) { return document.getElementById(id); };

  function keyOf(v) { return v.chapter + "." + v.verse; }

  function mod(n, m) { return ((n % m) + m) % m; }

  function laDateParts(date) {
    var parts = new Intl.DateTimeFormat("en-US", {
      timeZone: TIME_ZONE, year: "numeric", month: "numeric", day: "numeric"
    }).formatToParts(date);
    var out = {};
    parts.forEach(function (p) { out[p.type] = parseInt(p.value, 10); });
    return out;
  }

  function laDayNumber(date) {
    var p = laDateParts(date || new Date());
    return Date.UTC(p.year, p.month - 1, p.day) / 86400000;
  }

  function list() {
    return mode === "featured" ? featured : null;
  }

  function todayIndex() {
    var n = laDayNumber() - EPOCH_DAY;
    var l = list();
    return l ? l[mod(n, l.length)] : mod(n, verses.length);
  }

  function step(dir) {
    var l = list();
    if (!l) return mod(current + dir, verses.length);
    var pos = l.indexOf(current);
    if (pos !== -1) return l[mod(pos + dir, l.length)];
    // Current verse is outside the featured list: jump to the nearest one in that direction.
    if (dir > 0) {
      for (var i = 0; i < l.length; i++) if (l[i] > current) return l[i];
      return l[0];
    }
    for (var j = l.length - 1; j >= 0; j--) if (l[j] < current) return l[j];
    return l[l.length - 1];
  }

  function randomIndex() {
    var l = list() || null;
    var size = l ? l.length : verses.length;
    if (size < 2) return current;
    var pick;
    do {
      var r = Math.floor(Math.random() * size);
      pick = l ? l[r] : r;
    } while (pick === current);
    return pick;
  }

  function parseHash() {
    var m = /^#?(\d{1,2})[.:](\d{1,3})$/.exec(decodeURIComponent(location.hash));
    if (!m) return null;
    var idx = indexByKey[parseInt(m[1], 10) + "." + parseInt(m[2], 10)];
    return idx === undefined ? null : idx;
  }

  function render() {
    var v = verses[current];
    var key = keyOf(v);
    $("ref").textContent = "Chapter " + v.chapter + " · Verse " + v.verse;
    $("ref-link").setAttribute("href", "#" + key);
    $("chapter-name").textContent = v.chapter_name + (v.chapter_meaning ? " — " + v.chapter_meaning : "");
    $("chapter-name-sa").textContent = v.chapter_name_sa;
    $("sanskrit").textContent = v.sanskrit;
    $("translit").textContent = v.transliteration;
    $("translation").textContent = v.translation;
    $("translator").textContent = v.translator;

    var date = new Intl.DateTimeFormat("en-US", {
      timeZone: TIME_ZONE, weekday: "long", month: "long", day: "numeric"
    }).format(new Date());
    var isToday = current === todayIndex();
    $("day-label").textContent = isToday
      ? (mode === "featured" ? "Featured verse for " : "Verse of the day · ") + date
      : (mode === "featured" ? "Featured verses" : "All " + verses.length + " verses");
    $("today").disabled = isToday && showingToday;

    document.title = "Bhagavad Gita " + key + " · Daily Verse";
    $("verse").hidden = false;
    $("status").textContent = "";
  }

  function go(idx, opts) {
    current = idx;
    showingToday = !!(opts && opts.today);
    var hash = showingToday ? "" : "#" + keyOf(verses[idx]);
    var url = location.pathname + location.search + hash;
    if (location.hash !== hash) {
      history[opts && opts.replace ? "replaceState" : "pushState"](null, "", url);
    }
    render();
  }

  function goToday(replace) {
    go(todayIndex(), { today: true, replace: replace });
  }

  function setMode(m, fromUser) {
    mode = m === "featured" && featured.length ? "featured" : "all";
    try { localStorage.setItem(MODE_KEY, mode); } catch (e) { /* storage unavailable */ }
    Array.prototype.forEach.call(document.querySelectorAll(".mode-btn"), function (b) {
      b.setAttribute("aria-pressed", String(b.getAttribute("data-mode") === mode));
    });
    if (fromUser) goToday();
  }

  function fromLocation() {
    var idx = parseHash();
    if (idx === null) goToday(true);
    else { current = idx; showingToday = false; render(); }
  }

  function bind() {
    $("prev").addEventListener("click", function () { go(step(-1)); });
    $("next").addEventListener("click", function () { go(step(1)); });
    $("random").addEventListener("click", function () { go(randomIndex()); });
    $("today").addEventListener("click", function () { goToday(); });
    Array.prototype.forEach.call(document.querySelectorAll(".mode-btn"), function (b) {
      b.addEventListener("click", function () { setMode(b.getAttribute("data-mode"), true); });
    });
    window.addEventListener("hashchange", fromLocation);
    window.addEventListener("popstate", fromLocation);
    document.addEventListener("keydown", function (e) {
      if (e.altKey || e.ctrlKey || e.metaKey || e.shiftKey) return;
      if (e.target && /^(INPUT|TEXTAREA|SELECT)$/.test(e.target.tagName)) return;
      if (e.key === "ArrowLeft") go(step(-1));
      else if (e.key === "ArrowRight") go(step(1));
      else if (e.key === "r" || e.key === "R") go(randomIndex());
      else if (e.key === "t" || e.key === "T") goToday();
    });

    // Roll over to the new verse at midnight if the page is left open.
    var lastDay = laDayNumber();
    function checkDay() {
      var d = laDayNumber();
      if (d === lastDay) return;
      lastDay = d;
      if (showingToday) goToday(true);
      else render();
    }
    setInterval(checkDay, 60 * 1000);
    document.addEventListener("visibilitychange", function () {
      if (!document.hidden) checkDay();
    });
  }

  function getJSON(path) {
    return fetch(path).then(function (r) {
      if (!r.ok) throw new Error(path + ": HTTP " + r.status);
      return r.json();
    });
  }

  Promise.all([getJSON("data/verses.json"), getJSON("data/featured.json")])
    .then(function (res) {
      verses = res[0].verses;
      verses.forEach(function (v, i) { indexByKey[keyOf(v)] = i; });
      featured = res[1]
        .map(function (k) { return indexByKey[String(k).trim()]; })
        .filter(function (i) { return i !== undefined; });

      var saved = null;
      try { saved = localStorage.getItem(MODE_KEY); } catch (e) { /* storage unavailable */ }
      setMode(saved || "all", false);
      bind();
      fromLocation();
    })
    .catch(function (err) {
      $("status").textContent = "Could not load verses (" + err.message + "). " +
        "If you opened this file directly, serve the folder over HTTP instead, e.g. `python3 -m http.server`.";
      console.error(err);
    });
})();
