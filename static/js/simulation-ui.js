/**
 * EVPS - Simulation UI & Live Telemetry State Controller
 * Binds buttons, sliders, sound alerts, and updates live UI components.
 * Team: PHANTOM DELUX
 */

class SimulationUIController {
  constructor() {
    this.previousPriorityPhase = "IDLE";
    this.previousJunctionId = null;
    this.lastState = null;
  }

  init() {
    this.bindControls();
  }

  bindControls() {
    // Start Emergency Demo Button
    const btnStart = document.getElementById("btn-start-demo");
    if (btnStart) {
      btnStart.addEventListener("click", () => {
        this.startEmergencyDemo();
      });
    }

    // Pause Button
    const btnPause = document.getElementById("btn-pause-demo");
    if (btnPause) {
      btnPause.addEventListener("click", () => {
        if (window.evpsApp && window.evpsApp.ws && window.evpsApp.ws.readyState === WebSocket.OPEN) {
          window.evpsApp.ws.send(JSON.stringify({ action: "PAUSE" }));
        } else {
          fetch("/api/simulation/pause", { method: "POST" });
        }
        window.evpsApp.showToast("Simulation Paused", "info");
      });
    }

    // Resume Button
    const btnResume = document.getElementById("btn-resume-demo");
    if (btnResume) {
      btnResume.addEventListener("click", () => {
        if (window.evpsApp && window.evpsApp.ws && window.evpsApp.ws.readyState === WebSocket.OPEN) {
          window.evpsApp.ws.send(JSON.stringify({ action: "RESUME" }));
        } else {
          fetch("/api/simulation/resume", { method: "POST" });
        }
        window.evpsApp.showToast("Simulation Resumed", "success");
      });
    }

    // Reset Button
    const btnReset = document.getElementById("btn-reset-demo");
    if (btnReset) {
      btnReset.addEventListener("click", () => {
        if (window.evpsApp && window.evpsApp.ws && window.evpsApp.ws.readyState === WebSocket.OPEN) {
          window.evpsApp.ws.send(JSON.stringify({ action: "RESET" }));
        } else {
          fetch("/api/simulation/reset", { method: "POST" });
        }
        window.evpsApp.showToast("Simulation Reset to Initial State", "info");
      });
    }

    // Speed Selector Buttons
    document.querySelectorAll(".speed-btn").forEach(btn => {
      btn.addEventListener("click", (e) => {
        document.querySelectorAll(".speed-btn").forEach(b => b.classList.remove("active"));
        e.target.classList.add("active");
        const speed = parseFloat(e.target.getAttribute("data-speed") || 1.5);
        if (window.evpsApp && window.evpsApp.ws && window.evpsApp.ws.readyState === WebSocket.OPEN) {
          window.evpsApp.ws.send(JSON.stringify({ action: "SET_SPEED", speed: speed }));
        } else {
          fetch(`/api/simulation/speed?speed=${speed}`, { method: "POST" });
        }
        window.evpsApp.showToast(`Simulation Speed: ${speed}x`, "info");
      });
    });

    // Sound / Siren Toggle Button
    const btnSiren = document.getElementById("btn-toggle-siren");
    if (btnSiren) {
      btnSiren.addEventListener("click", () => {
        const isActive = window.evpsAudio.toggleSiren();
        btnSiren.classList.toggle("btn-emergency", isActive);
        btnSiren.innerHTML = isActive 
          ? `<i class="fas fa-volume-up"></i> Siren ON` 
          : `<i class="fas fa-volume-mute"></i> Siren OFF`;
        window.evpsApp.showToast(isActive ? "Emergency Siren Activated" : "Emergency Siren Muted", "info");
      });
    }

    // Hardware Mode Toggle
    const modeSelect = document.getElementById("mode-select-toggle");
    if (modeSelect) {
      modeSelect.addEventListener("change", (e) => {
        const newMode = e.target.value;
        fetch("/api/config", {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ system_mode: newMode })
        }).then(() => {
          window.evpsApp.showToast(`System Mode: ${newMode}`, "success");
        });
      });
    }

    // Fault Injection: GPS Drop
    const chkGpsFault = document.getElementById("fault-gps-loss");
    if (chkGpsFault) {
      chkGpsFault.addEventListener("change", (e) => {
        fetch(`/api/simulation/fault?fault_type=gps_loss&enabled=${e.target.checked}`, { method: "POST" });
        window.evpsApp.showToast(e.target.checked ? "Fault Injected: GPS Lost" : "Fault Cleared: GPS Connected", e.target.checked ? "warning" : "info");
      });
    }

    // Fault Injection: Receiver Offline
    const chkRxFault = document.getElementById("fault-rx-offline");
    if (chkRxFault) {
      chkRxFault.addEventListener("change", (e) => {
        fetch(`/api/simulation/fault?fault_type=receiver_offline&enabled=${e.target.checked}`, { method: "POST" });
        window.evpsApp.showToast(e.target.checked ? "Fault Injected: Receiver Offline" : "Fault Cleared: Receiver Online", e.target.checked ? "warning" : "info");
      });
    }
  }

  startEmergencyDemo(ambulanceId = "A-001", hospitalId = 1) {
    if (window.evpsApp && window.evpsApp.ws && window.evpsApp.ws.readyState === WebSocket.OPEN) {
      window.evpsApp.ws.send(JSON.stringify({
        action: "START_EMERGENCY",
        ambulance_id: ambulanceId,
        hospital_id: hospitalId
      }));
    } else {
      fetch("/api/simulation/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ambulance_id: ambulanceId, hospital_id: hospitalId })
      });
    }
    window.evpsApp.showToast(`🚨 Emergency Priority Demo Started for ${ambulanceId}!`, "alert");
  }

  handleTelemetryUpdate(state) {
    this.lastState = state;

    // 1. Trigger Sound FX on State Transitions
    const phase = state.priority_phase;
    if (phase !== this.previousPriorityPhase) {
      if (phase === "DETECTED") {
        window.evpsAudio.playRadarPing();
      } else if (phase === "GREEN_ACTIVE") {
        window.evpsAudio.playGreenGrantedChime();
        window.evpsApp.showToast(`🟢 GREEN PRIORITY GRANTED at ${state.next_junction ? state.next_junction.code : 'Junction'}!`, "success");
      } else if (phase === "CLEARED") {
        window.evpsAudio.playClearedChime();
        window.evpsApp.showToast(`✓ Junction Cleared! Signal restoring to normal.`, "info");
      }
      this.previousPriorityPhase = phase;
    }

    // 2. Update Map
    if (window.evpsMap) {
      window.evpsMap.updateFromTelemetry(state);
    }

    // 3. Update Dashboard KPI & HUD Elements
    this.updateDashboardHUD(state);

    // 4. Update 3D Traffic Light Visual Component
    this.updateTrafficLightComponent(state);

    // 5. Update Upcoming Junction Radar
    this.updateJunctionRadar(state);

    // 6. Update Visual Event Timeline
    this.updateTimelineSteps(state);

    // 7. Update Event Logs Feed
    this.updateEventLogs(state.logs);
  }

  updateDashboardHUD(state) {
    const { ambulance, trip, next_junction, route_progress_pct } = state;

    // KPI Cards
    const elActiveEmergencies = document.getElementById("kpi-active-emergencies");
    if (elActiveEmergencies) {
      elActiveEmergencies.innerText = (ambulance && ambulance.status === "EMERGENCY_ACTIVE") ? "1" : "0";
    }
    const elSpeed = document.getElementById("hud-speed-val");
    if (elSpeed && ambulance) {
      elSpeed.innerText = `${ambulance.speed_kmh} km/h`;
    }
    const elDistRemaining = document.getElementById("hud-dist-val");
    if (elDistRemaining && trip) {
      elDistRemaining.innerText = `${trip.distance_remaining_km} km`;
    }
    const elEta = document.getElementById("hud-eta-val");
    if (elEta && trip) {
      const mins = Math.floor(trip.eta_seconds / 60);
      const secs = trip.eta_seconds % 60;
      elEta.innerText = mins > 0 ? `${mins}m ${secs}s` : `${secs}s`;
    }

    // Route Stepper Progress Line
    const elProgress = document.getElementById("hud-progress-fill");
    if (elProgress) {
      elProgress.style.width = `${route_progress_pct || 0}%`;
    }

    // Step indicators in HUD
    const stepNextJunc = document.getElementById("hud-step-junc");
    if (stepNextJunc) {
      if (state.priority_phase === "GREEN_ACTIVE" || state.priority_phase === "CROSSING") {
        stepNextJunc.className = "hud-step active";
      } else if (state.priority_phase === "CLEARED") {
        stepNextJunc.className = "hud-step completed";
      } else {
        stepNextJunc.className = "hud-step";
      }
    }
  }

  updateTrafficLightComponent(state) {
    const { next_junction, priority_phase, priority_countdown } = state;

    const lensRed = document.getElementById("lens-red");
    const lensYellow = document.getElementById("lens-yellow");
    const lensGreen = document.getElementById("lens-green");
    const banner = document.getElementById("signal-priority-banner");
    const labelJunc = document.getElementById("signal-junc-label");

    if (!lensRed || !lensYellow || !lensGreen) return;

    // Reset lenses
    lensRed.classList.remove("active");
    lensYellow.classList.remove("active");
    lensGreen.classList.remove("active");

    let activeColor = (next_junction && next_junction.signal) ? next_junction.signal : "RED";

    if (priority_phase === "GREEN_ACTIVE" || priority_phase === "CROSSING") {
      activeColor = "GREEN";
    }

    if (activeColor === "RED") lensRed.classList.add("active");
    else if (activeColor === "YELLOW") lensYellow.classList.add("active");
    else if (activeColor === "GREEN") lensGreen.classList.add("active");

    if (labelJunc) {
      labelJunc.innerText = next_junction ? `${next_junction.code} - ${next_junction.name}` : "J-04 Tilak Marg";
    }

    if (banner) {
      if (priority_phase === "GREEN_ACTIVE") {
        banner.className = "priority-banner emergency";
        banner.innerHTML = `<i class="fas fa-exclamation-triangle"></i> EMERGENCY GREEN PRIORITY (${priority_countdown}s)`;
      } else if (priority_phase === "CROSSING") {
        banner.className = "priority-banner emergency";
        banner.innerHTML = `<i class="fas fa-ambulance"></i> AMBULANCE CROSSING JUNCTION`;
      } else if (priority_phase === "CLEARED") {
        banner.className = "priority-banner normal";
        banner.innerHTML = `<i class="fas fa-check-circle" style="color: #00e676;"></i> JUNCTION CLEARED • RESTORING CYCLE`;
      } else {
        banner.className = "priority-banner normal";
        banner.innerHTML = `<i class="fas fa-traffic-light"></i> NORMAL TRAFFIC CYCLE (${activeColor})`;
      }
    }
  }

  updateJunctionRadar(state) {
    const { next_junction, priority_phase } = state;

    const elDist = document.getElementById("radar-distance-text");
    const elName = document.getElementById("radar-junction-name");
    const elStatus = document.getElementById("radar-junction-status");

    if (elDist) {
      elDist.innerText = next_junction ? `${next_junction.distance_m}m` : "--";
    }
    if (elName) {
      elName.innerText = next_junction ? `${next_junction.code} (${next_junction.name})` : "Scanning corridor...";
    }
    if (elStatus) {
      if (priority_phase === "DETECTED") {
        elStatus.innerHTML = `<span class="badge badge-cyan"><i class="fas fa-satellite-dish"></i> APPROACHING (500m)</span>`;
      } else if (priority_phase === "REQUESTED") {
        elStatus.innerHTML = `<span class="badge badge-amber"><i class="fas fa-paper-plane"></i> PRIORITY REQUESTED (250m)</span>`;
      } else if (priority_phase === "GREEN_ACTIVE") {
        elStatus.innerHTML = `<span class="badge badge-green"><i class="fas fa-bolt"></i> GREEN PRIORITY ACTIVE</span>`;
      } else if (priority_phase === "CROSSING") {
        elStatus.innerHTML = `<span class="badge badge-green"><i class="fas fa-ambulance"></i> CROSSING INTERSECTION</span>`;
      } else if (priority_phase === "CLEARED") {
        elStatus.innerHTML = `<span class="badge badge-cyan"><i class="fas fa-check"></i> CLEARED & NORMALIZED</span>`;
      } else {
        elStatus.innerHTML = `<span class="badge" style="background: rgba(255,255,255,0.05); color: #94a3b8;">NORMAL STANDBY</span>`;
      }
    }
  }

  updateTimelineSteps(state) {
    const { ambulance, priority_phase } = state;
    const isEmergency = ambulance && ambulance.status === "EMERGENCY_ACTIVE";

    const setStep = (id, status) => {
      const el = document.getElementById(id);
      if (!el) return;
      el.className = `t-step ${status}`;
    };

    setStep("t-step-1", isEmergency ? "completed" : "");
    setStep("t-step-2", isEmergency ? "completed" : "");
    setStep("t-step-3", ["DETECTED", "REQUESTED", "GREEN_ACTIVE", "CROSSING", "CLEARED"].includes(priority_phase) ? "completed" : "");
    setStep("t-step-4", ["REQUESTED", "GREEN_ACTIVE", "CROSSING", "CLEARED"].includes(priority_phase) ? "completed" : "");
    setStep("t-step-5", ["GREEN_ACTIVE", "CROSSING", "CLEARED"].includes(priority_phase) ? "completed" : "");
    setStep("t-step-6", priority_phase === "GREEN_ACTIVE" ? "active" : (["CROSSING", "CLEARED"].includes(priority_phase) ? "completed" : ""));
    setStep("t-step-7", priority_phase === "CROSSING" ? "active" : (priority_phase === "CLEARED" ? "completed" : ""));
    setStep("t-step-8", priority_phase === "CLEARED" ? "completed" : "");
  }

  updateEventLogs(logs) {
    const container = document.getElementById("live-event-logs-list");
    if (!container || !logs) return;

    container.innerHTML = logs.map(l => {
      const timeStr = l.created_at ? l.created_at.split(" ")[1] || l.created_at : "Now";
      return `
        <div class="log-entry ${l.level}">
          <span class="log-time">${timeStr}</span>
          <span class="log-source">${l.source}</span>
          <span class="log-msg">${l.message}</span>
        </div>
      `;
    }).join("");
  }
}

window.evpsSimUI = new SimulationUIController();
