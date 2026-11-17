// Merit-order chart on the home page: hovering, focusing or tapping a step names the project.
(function () {
  "use strict";
  document.addEventListener("DOMContentLoaded", function () {
    var fig = document.querySelector("[data-merit-order]");
    if (!fig) return;
    var readout = fig.querySelector("[data-mo-readout]");
    var title = readout.querySelector(".mo-readout-title");
    var meta = readout.querySelector(".mo-readout-meta");
    var steps = fig.querySelectorAll(".mo-step");
    var initial = { title: title.textContent, meta: meta.textContent };
    var touched = false;

    function show(step) {
      steps.forEach(function (s) {
        s.classList.toggle("is-active", s === step);
      });
      title.textContent = step.dataset.title;
      meta.textContent = step.dataset.client + " · " + step.dataset.years + " · " + step.dataset.role;
    }
    function reset() {
      steps.forEach(function (s) {
        s.classList.remove("is-active");
      });
      title.textContent = initial.title;
      meta.textContent = initial.meta;
    }

    steps.forEach(function (step) {
      step.addEventListener("mouseenter", function () {
        show(step);
      });
      step.addEventListener("focus", function () {
        show(step);
      });
      // First tap on a touch screen names the step; a second tap follows the link.
      step.addEventListener("touchend", function (e) {
        if (!step.classList.contains("is-active")) {
          e.preventDefault();
          touched = true;
          show(step);
        }
      });
    });
    fig.addEventListener("mouseleave", function () {
      if (!touched) reset();
    });
    fig.addEventListener("focusout", function (e) {
      if (!fig.contains(e.relatedTarget) && !touched) reset();
    });
  });
})();
