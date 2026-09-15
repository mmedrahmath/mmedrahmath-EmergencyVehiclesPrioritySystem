/**
 * EVPS - Master Application Orchestrator & WebSocket Client
 * Team: PHANTOM DELUX | Theme: SMART VEHICLES
 */

class EVPSApplication {
  constructor() {
    this.ws = null;
    this.currentUser = {
      name: "Chief Dispatcher Sharma",
      role: "ADMIN",
      badge_number: "EVPS-ADMIN-01"
    };
    this.currentPage = "landing";
    this.reconnectTimer = null;
  }

  init() {
    console.log("[EVPS] Initializing EVPS Application...");
    this.setupRouting();
    this.setupTheme();
    this.setupMobileMenu();
    this.initWebSocket();
    window.evpsSimUI.init();

    // Determine initial route from URL path or hash
    const path = window.location.pathname;
    if (path.includes("dashboard")) this.navigateTo("dashboard");
    else if (path.includes("trip")) this.navigateTo("trip-view");
    else if (path.includes("ambulances")) this.navigateTo("ambulances");
    else if (path.includes("junctions")) this.navigateTo("junctions");
    else if (path.includes("analytics")) this.navigateTo("analytics");
    else if (path.includes("admin")) this.navigateTo("admin");
    else if (path.includes("login")) this.navigateTo("login");
    else if (window.location.hash) this.navigateTo(window.location.hash.replace("#", ""));
    else this.navigateTo("landing");
  }

  // ==========================================
  // WEBSOCKET TELEMETRY CONNECTION
  // ==========================================
  initWebSocket() {
    const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
    const wsUrl = `${protocol}//${window.location.host}/ws/live`;

    console.log(`[EVPS WS] Connecting to ${wsUrl}...`);
    this.ws = new WebSocket(wsUrl);

    this.ws.onopen = () => {
      console.log("[EVPS WS] Connected to live telemetry stream.");
      const indicator = document.getElementById("ws-connection-badge");
      if (indicator) {
        indicator.className = "live-indicator";
        indicator.innerHTML = `<span class="pulse-dot"></span> LIVE SYNC`;
      }
      if (this.reconnectTimer) {
        clearTimeout(this.reconnectTimer);
        this.reconnectTimer = null;
      }
    };

    this.ws.onmessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type === "TELEMETRY_UPDATE" || msg.type === "INITIAL_STATE") {
          window.evpsSimUI.handleTelemetryUpdate(msg.data);
        }
      } catch (e) {
        console.error("[EVPS WS Parse Error]:", e);
      }
    };

    this.ws.onclose = () => {
      console.warn("[EVPS WS] Disconnected. Reconnecting in 2s...");
      const indicator = document.getElementById("ws-connection-badge");
      if (indicator) {
        indicator.className = "live-indicator";
        indicator.style.borderColor = "#ff1744";
        indicator.style.color = "#ff1744";
        indicator.innerHTML = `<span style="width:8px;height:8px;border-radius:50%;background:#ff1744;"></span> RECONNECTING`;
      }
      this.reconnectTimer = setTimeout(() => this.initWebSocket(), 2000);
    };

    this.ws.onerror = (err) => {
      console.error("[EVPS WS Error]:", err);
    };
  }

  // ==========================================
  // ROUTING & NAVIGATION
  // ==========================================
  setupRouting() {
    document.querySelectorAll("[data-nav]").forEach(el => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        const target = el.getAttribute("data-nav");
        this.navigateTo(target);
      });
    });

    window.addEventListener("popstate", () => {
      const page = window.location.hash.replace("#", "") || "landing";
      this.navigateTo(page, false);
    });
  }

  navigateTo(pageId, updateHistory = true) {
    this.currentPage = pageId;
    if (updateHistory) {
      window.location.hash = `#${pageId}`;
    }

    // Hide all pages, show target page
    document.querySelectorAll(".page-view").forEach(p => p.classList.remove("active-page"));
    const targetPage = document.getElementById(`page-${pageId}`);
    if (targetPage) {
      targetPage.classList.add("active-page");
    }

    // Update Sidebar Navigation state
    document.querySelectorAll(".nav-item").forEach(item => {
      const link = item.querySelector("[data-nav]");
      if (link && link.getAttribute("data-nav") === pageId) {
        item.classList.add("active");
      } else {
        item.classList.remove("active");
      }
    });

    // Update Mobile Nav
    document.querySelectorAll(".mobile-nav-link").forEach(link => {
      if (link.getAttribute("data-nav") === pageId) {
        link.classList.add("active");
      } else {
        link.classList.remove("active");
      }
    });

    // Close mobile drawer if open
    document.querySelector(".sidebar").classList.remove("open");

    // Page Specific Initializers
    if (pageId === "dashboard" || pageId === "trip-view") {
      window.evpsMap.init();
      window.evpsMap.invalidateSize();
    } else if (pageId === "ambulances") {
      window.evpsPages.renderAmbulances();
    } else if (pageId === "junctions") {
      window.evpsPages.renderJunctions();
    } else if (pageId === "analytics") {
      window.evpsPages.renderAnalytics();
    } else if (pageId === "admin") {
      window.evpsPages.renderAdmin();
    } else if (pageId === "support") {
      window.evpsPages.renderSupport();
    }
  }

  // ==========================================
  // THEME & MOBILE MENU
  // ==========================================
  setupTheme() {
    const btnTheme = document.getElementById("theme-toggle-btn");
    if (btnTheme) {
      btnTheme.addEventListener("click", () => {
        const current = document.documentElement.getAttribute("data-theme") || "dark";
        const next = current === "dark" ? "light" : "dark";
        document.documentElement.setAttribute("data-theme", next);
        btnTheme.innerHTML = next === "dark" ? `<i class="fas fa-moon"></i>` : `<i class="fas fa-sun"></i>`;
      });
    }
  }

  setupMobileMenu() {
    const btnToggle = document.getElementById("mobile-menu-toggle");
    const sidebar = document.querySelector(".sidebar");
    if (btnToggle && sidebar) {
      btnToggle.addEventListener("click", () => {
        sidebar.classList.toggle("open");
      });
    }
  }

  // ==========================================
  // TOAST NOTIFICATIONS
  // ==========================================
  showToast(message, type = "info") {
    const container = document.getElementById("toast-container");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = "toast-msg";

    let icon = "fa-info-circle";
    let color = "#00e5ff";
    if (type === "success") { icon = "fa-check-circle"; color = "#00e676"; }
    else if (type === "alert") { icon = "fa-exclamation-triangle"; color = "#ff1744"; }
    else if (type === "warning") { icon = "fa-exclamation-circle"; color = "#ffab00"; }

    toast.style.borderLeft = `4px solid ${color}`;
    toast.innerHTML = `
      <i class="fas ${icon}" style="color: ${color}; font-size: 16px;"></i>
      <span>${message}</span>
    `;

    container.appendChild(toast);
    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transform = "translateX(100%)";
      setTimeout(() => toast.remove(), 300);
    }, 3500);
  }

  // ==========================================
  // AUTH ROLE SWITCHER
  // ==========================================
  loginAs(role) {
    if (role === "ADMIN") {
      this.currentUser = { name: "Chief Dispatcher Sharma", role: "ADMIN", badge_number: "EVPS-ADMIN-01" };
    } else if (role === "OPERATOR") {
      this.currentUser = { name: "Officer Rajesh Kumar", role: "OPERATOR", badge_number: "EVPS-OP-04" };
    } else {
      this.currentUser = { name: "Observer Guest", role: "VIEWER", badge_number: "EVPS-VW-10" };
    }

    const badgeEl = document.getElementById("user-role-badge");
    if (badgeEl) {
      badgeEl.innerText = `${this.currentUser.role}: ${this.currentUser.name}`;
    }

    this.showToast(`Signed in as ${this.currentUser.role}`, "success");
    this.navigateTo("dashboard");
  }
}

// Instantiate global app instance and boot on DOM load
window.evpsApp = new EVPSApplication();
document.addEventListener("DOMContentLoaded", () => {
  window.evpsApp.init();
});
