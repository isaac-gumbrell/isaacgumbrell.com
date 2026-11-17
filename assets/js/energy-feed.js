// Market Watch pages: client-side filtering, "new" badges and deadline countdowns.
(function () {
  "use strict";

  var DAY = 86400000;
  var NEW_WINDOW = 1.5 * DAY; // feed refreshes every 12h, so "new" = first seen in the last ~36h

  function todayISO() {
    // Dates in the feed are Perth calendar dates (UTC+8, no DST).
    return new Date(Date.now() + 8 * 3600000).toISOString().slice(0, 10);
  }

  function daysBetween(fromISO, toISO) {
    return Math.round((Date.parse(toISO) - Date.parse(fromISO)) / DAY);
  }

  function decorate(root) {
    var today = todayISO();
    root.querySelectorAll(".ef-item").forEach(function (el) {
      var seen = Date.parse(el.dataset.firstSeen || "");
      var badge = el.querySelector(".ef-new");
      if (badge && !isNaN(seen) && Date.now() - seen < NEW_WINDOW) badge.hidden = false;

      var dl = el.querySelector(".ef-deadline");
      if (dl) {
        var left = daysBetween(today, dl.dataset.deadline);
        var cd = dl.querySelector(".ef-countdown");
        if (left < 0) {
          cd.textContent = "(closed)";
          dl.classList.add("ef-deadline--closed");
        } else {
          cd.textContent = left === 0 ? "(today)" : left === 1 ? "(tomorrow)" : "(" + left + " days)";
          if (left <= 7) dl.classList.add("ef-deadline--soon");
        }
      }
      // Opportunity lists drop items whose date passed since the last build.
      if (el.closest("[data-ef-upcoming]") && el.dataset.due && el.dataset.due < today) el.remove();
    });
  }

  function setupFilters(root) {
    var search = root.querySelector(".ef-search");
    var chips = root.querySelectorAll("[data-filter-category]");
    var region = root.querySelector("[data-filter-jurisdiction]");
    var topic = root.querySelector("[data-filter-topic]");
    var submitToggle = root.querySelector("[data-filter-submission]");
    var state = { q: "", category: "", jurisdiction: "", topic: "", submission: false };

    function apply() {
      var shown = 0;
      root.querySelectorAll(".ef-list .ef-item").forEach(function (el) {
        var topics = " " + (el.dataset.topics || "") + " ";
        var ok =
          (!state.category || el.dataset.category === state.category) &&
          (!state.jurisdiction || el.dataset.jurisdiction === state.jurisdiction) &&
          (!state.topic || topics.indexOf(" " + state.topic + " ") !== -1) &&
          (!state.submission || el.dataset.submission === "open") &&
          (!state.q || (el.dataset.search || "").indexOf(state.q) !== -1);
        el.hidden = !ok;
        if (ok) shown++;
      });
      root.querySelectorAll("[data-ef-section]").forEach(function (sec) {
        sec.hidden = !sec.querySelector(".ef-item:not([hidden])");
      });
      var empty = root.querySelector(".ef-empty");
      if (empty) empty.hidden = shown > 0;
      var count = root.querySelector(".ef-count");
      if (count) count.textContent = shown + (shown === 1 ? " item" : " items");
      if (submitToggle) submitToggle.setAttribute("aria-pressed", state.submission ? "true" : "false");
      if (topic) topic.value = state.topic;
    }

    if (search)
      search.addEventListener("input", function () {
        state.q = search.value.trim().toLowerCase();
        apply();
      });
    chips.forEach(function (chip) {
      chip.addEventListener("click", function () {
        state.category = chip.dataset.filterCategory;
        chips.forEach(function (c) {
          c.setAttribute("aria-pressed", c === chip ? "true" : "false");
        });
        apply();
      });
    });
    if (region)
      region.addEventListener("change", function () {
        state.jurisdiction = region.value;
        apply();
      });
    if (topic)
      topic.addEventListener("change", function () {
        state.topic = topic.value;
        apply();
      });
    if (submitToggle)
      submitToggle.addEventListener("click", function () {
        state.submission = !state.submission;
        apply();
      });
    // Tags inside an entry act as shortcuts to the same filters.
    root.addEventListener("click", function (e) {
      var tag = e.target.closest(".ef-tag");
      if (!tag) return;
      if (tag.hasAttribute("data-tag-submission")) state.submission = true;
      else state.topic = state.topic === tag.dataset.tagTopic ? "" : tag.dataset.tagTopic;
      apply();
      root.querySelector(".ef-toolbar").scrollIntoView({ block: "nearest" });
    });
    apply();
  }

  document.addEventListener("DOMContentLoaded", function () {
    var root = document.querySelector("[data-energy-feed]");
    if (!root) return;
    decorate(root);
    setupFilters(root);
  });
})();
