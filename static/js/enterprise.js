/**
 * EnterpriseOne Core Client Utilities
 * Version: 1.0.0
 */

document.addEventListener("DOMContentLoaded", () => {
  // 1. Theme Management (Light / Dark / System)
  initTheme();

  // 2. Sidebar Toggle
  initSidebar();

  // 3. User Menu Dropdown
  initUserDropdown();

  // 4. Alert Auto-Dismissal
  initAlertDismissal();

  // 5. Password Visibility Toggles
  initPasswordToggles();
});

/**
 * Initializes and persists theme preference.
 */
function initTheme() {
  const themeToggleBtn = document.getElementById("themeToggleBtn");
  const storedTheme = localStorage.getItem("enterprise_theme") || "system";
  applyTheme(storedTheme);

  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-theme") || "light";
      const nextTheme = currentTheme === "dark" ? "light" : "dark";
      applyTheme(nextTheme);
      localStorage.setItem("enterprise_theme", nextTheme);
    });
  }
}

function applyTheme(theme) {
  if (theme === "system") {
    const prefersDark = window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.setAttribute("data-theme", prefersDark ? "dark" : "light");
  } else {
    document.documentElement.setAttribute("data-theme", theme);
  }
}

/**
 * Initializes sidebar collapse and responsive behavior.
 */
function initSidebar() {
  const toggleBtn = document.getElementById("sidebarToggleBtn");
  const sidebar = document.querySelector(".app-sidebar");
  const mainContent = document.querySelector(".app-main");

  if (!toggleBtn || !sidebar || !mainContent) return;

  const isCollapsed = localStorage.getItem("enterprise_sidebar_collapsed") === "true";
  if (isCollapsed) {
    sidebar.classList.add("collapsed");
    mainContent.classList.add("expanded");
  }

  toggleBtn.addEventListener("click", () => {
    sidebar.classList.toggle("collapsed");
    mainContent.classList.toggle("expanded");
    localStorage.setItem("enterprise_sidebar_collapsed", sidebar.classList.contains("collapsed"));
  });
}

/**
 * Handles user profile dropdown opening and outside-click dismissal.
 */
function initUserDropdown() {
  const userBtn = document.getElementById("userProfileBtn");
  const userMenu = document.getElementById("userDropdownMenu");

  if (!userBtn || !userMenu) return;

  userBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    userMenu.classList.toggle("show");
  });

  document.addEventListener("click", (e) => {
    if (!userMenu.contains(e.target) && !userBtn.contains(e.target)) {
      userMenu.classList.remove("show");
    }
  });
}

/**
 * Handles alert dismissal with fade-out effect.
 */
function initAlertDismissal() {
  const closeButtons = document.querySelectorAll(".alert-close");
  closeButtons.forEach((btn) => {
    btn.addEventListener("click", () => {
      const alert = btn.closest(".alert");
      if (alert) {
        alert.style.opacity = "0";
        alert.style.transition = "opacity 0.2s ease-out";
        setTimeout(() => alert.remove(), 200);
      }
    });
  });
}

/**
 * Adds toggle buttons for password reveal/hide fields.
 */
function initPasswordToggles() {
  const passwordInputs = document.querySelectorAll("input[type='password']");
  passwordInputs.forEach((input) => {
    const wrapper = input.parentElement;
    if (wrapper && !wrapper.querySelector(".password-toggle-icon")) {
      const toggleBtn = document.createElement("button");
      toggleBtn.type = "button";
      toggleBtn.className = "password-toggle-icon";
      toggleBtn.setAttribute("aria-label", "Toggle password visibility");
      toggleBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M2 12s3-7 10-7 10 7 10 7-3 7-10 7-10-7-10-7Z"/>
          <circle cx="12" cy="12" r="3"/>
        </svg>
      `;
      toggleBtn.style.cssText = "position: absolute; right: 10px; top: 50%; transform: translateY(-50%); background: none; border: none; cursor: pointer; color: #94a3b8; display: flex; align-items: center;";

      wrapper.style.position = "relative";
      wrapper.appendChild(toggleBtn);

      toggleBtn.addEventListener("click", () => {
        const isPassword = input.type === "password";
        input.type = isPassword ? "text" : "password";
        toggleBtn.style.color = isPassword ? "#0284c7" : "#94a3b8";
      });
    }
  });
}
