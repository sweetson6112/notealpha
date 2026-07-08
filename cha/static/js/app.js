document.addEventListener("DOMContentLoaded", function () {
  const root = document.documentElement;
  const darkBtn = document.getElementById("darkModeToggle");
  const saved = localStorage.getItem("cha-theme");
  if (saved) root.setAttribute("data-bs-theme", saved);

  if (darkBtn) {
    darkBtn.addEventListener("click", function () {
      const current = root.getAttribute("data-bs-theme");
      const next = current === "dark" ? "light" : "dark";
      root.setAttribute("data-bs-theme", next);
      localStorage.setItem("cha-theme", next);
    });
  }

  const sidebarToggle = document.getElementById("sidebarToggle");
  const sidebar = document.querySelector(".sidebar");
  if (sidebarToggle && sidebar) {
    sidebarToggle.addEventListener("click", () => sidebar.classList.toggle("show"));
  }
});
