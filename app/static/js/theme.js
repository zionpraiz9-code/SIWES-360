(function () {
  const storageKey = "siwes360-theme";
  const root = document.documentElement;

  function getSavedTheme() {
    try {
      const savedTheme = window.localStorage.getItem(storageKey);
      return savedTheme === "dark" || savedTheme === "light"
        ? savedTheme
        : "light";
    } catch (_error) {
      return "light";
    }
  }

  function applyTheme(theme) {
    root.dataset.theme = theme;
  }

  applyTheme(getSavedTheme());

  document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.querySelector("[data-theme-toggle]");
    if (!toggle) {
      return;
    }

    const icon = toggle.querySelector("[data-theme-icon]");

    function updateToggle(theme) {
      const isDark = theme === "dark";
      toggle.setAttribute("aria-pressed", String(isDark));
      toggle.setAttribute(
        "aria-label",
        isDark ? "Switch to light mode" : "Switch to dark mode",
      );
      toggle.setAttribute(
        "title",
        isDark ? "Switch to light mode" : "Switch to dark mode",
      );
      if (icon) {
        icon.textContent = isDark ? "☀" : "☾";
      }
    }

    updateToggle(root.dataset.theme);
    toggle.addEventListener("click", function () {
      const theme = root.dataset.theme === "dark" ? "light" : "dark";
      applyTheme(theme);
      updateToggle(theme);
      try {
        window.localStorage.setItem(storageKey, theme);
      } catch (_error) {
        // The current page still changes theme when storage is unavailable.
      }
    });
  });
})();
