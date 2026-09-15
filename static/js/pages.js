/**
 * EVPS - Page Renderers & View Managers
 * Team: PHANTOM DELUX
 */

class EVPSPages {
  constructor() {}

  // 1. Render Ambulances Fleet Page
  async renderAmbulances() {
    const container = document.getElementById("fleet-table-body");
    if (!container) return;

    try {
      const res = await fetch("/api/ambulances");
      const ambulances = await res.json();

      container.innerHTML = ambulances.map(a => {
        const isEmergency = a.status === "EMERGENCY_ACTIVE";
        const statusBadge = isEmergency 
          ? `<span class="badge badge-red"><i class="fas fa-exclamation-triangle"></i> EMERGENCY ACTIVE</span>`
          : `<span class="badge" style="background: rgba(255,255,255,0.08); color: #94a3b8;">${a.status}</span>`;

        const gpsBadge = a.gps_status === "CONNECTED"
          ? `<span class="badge badge-green"><i class="fas fa-satellite"></i> 3D Fix (${a.battery_level}%)</span>`
          : `<span class="badge badge-red"><i class="fas fa-exclamation-circle"></i> LOST</span>`;

        return `
          <tr>
            <td><strong>${a.id}</strong></td>
            <td>
              <div style="display: flex; align-items: center; gap: 8px;">
                <i class="fas fa-ambulance" style="color: ${isEmergency ? '#ff1744' : '#00e5ff'};"></i>
                <span>${a.callsign}</span>
              </div>
            </td>
            <td>${a.plate_number}</td>
            <td><code>${a.esp32_device_id}</code></td>
            <td>${statusBadge}</td>
            <td>${gpsBadge}</td>
            <td><strong>${a.speed_kmh} km/h</strong></td>
            <td>${a.hospital_name || 'City Apex Hospital'}</td>
            <td>
              <button class="btn btn-secondary btn-sm" onclick="window.evpsApp.navigateTo('trip-view'); window.evpsSimUI.startEmergencyDemo('${a.id}', 1);">
                <i class="fas fa-location-arrow"></i> Track Live
              </button>
            </td>
          </tr>
        `;
      }).join("");
    } catch (e) {
      console.error("Error fetching ambulances:", e);
    }
  }

  // 2. Render Junctions Page
  async renderJunctions() {
    const container = document.getElementById("junctions-grid");
    if (!container) return;

    try {
      const res = await fetch("/api/junctions");
      const junctions = await res.json();

      container.innerHTML = junctions.map(j => {
        const signalColor = j.current_signal || 'RED';
        const isPriority = j.priority_state === 'ACTIVE';

        return `
          <div class="glass-panel" style="padding: 18px; border-left: 4px solid ${isPriority ? '#00e676' : '#334155'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
              <h3 style="font-size: 16px;">🚦 ${j.code} - ${j.name}</h3>
              <span class="badge ${j.status === 'ONLINE' ? 'badge-green' : 'badge-red'}">${j.status}</span>
            </div>
            <div style="display: flex; gap: 16px; align-items: center; margin-bottom: 14px;">
              <div class="traffic-light-housing" style="width: 70px; padding: 10px 8px; margin: 0;">
                <div class="signal-lens-wrap"><div class="signal-lens red ${signalColor === 'RED' ? 'active' : ''}" style="width: 36px; height: 36px;"></div></div>
                <div class="signal-lens-wrap"><div class="signal-lens yellow ${signalColor === 'YELLOW' ? 'active' : ''}" style="width: 36px; height: 36px;"></div></div>
                <div class="signal-lens-wrap"><div class="signal-lens green ${(signalColor === 'GREEN' || isPriority) ? 'active' : ''}" style="width: 36px; height: 36px;"></div></div>
              </div>
              <div style="font-size: 12px; color: var(--text-secondary); line-height: 1.6;">
                <p>Receiver: <code>${j.receiver_id}</code></p>
                <p>Signal RSSI: <strong>${j.signal_rssi || -52} dBm</strong></p>
                <p>Normal Cycle: <strong>${j.normal_cycle_sec}s</strong></p>
                <p>Priority State: <strong>${j.priority_state}</strong></p>
              </div>
            </div>
            <div style="display: flex; gap: 8px; padding-top: 10px; border-top: 1px solid var(--glass-border);">
              <button class="btn btn-emergency btn-sm" style="flex: 1; font-size: 11px;" onclick="window.evpsPages.overrideSignal(${j.id}, 'FORCE_GREEN')">
                <i class="fas fa-bolt"></i> Force Green
              </button>
              <button class="btn btn-secondary btn-sm" style="flex: 1; font-size: 11px;" onclick="window.evpsPages.overrideSignal(${j.id}, 'RESTORE_NORMAL')">
                <i class="fas fa-undo"></i> Restore Cycle
              </button>
            </div>
          </div>
        `;
      }).join("");
    } catch (e) {
      console.error("Error fetching junctions:", e);
    }
  }

  async overrideSignal(junctionId, action) {
    try {
      await fetch("/api/priority/override", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ junction_id: junctionId, ambulance_id: "A-001", action: action })
      });
      window.evpsApp.showToast(`Manual Override: Junction #${junctionId} ${action}`, "info");
      this.renderJunctions();
    } catch (e) {
      console.error(e);
    }
  }

  // 3. Render Dedicated Rapido-Style Trip Tracker Page
  async renderTripView(tripId = 1) {
    try {
      const res = await fetch(`/api/trips/${tripId}`);
      const data = await res.json();
      const { trip, crossings, priority_requests } = data;

      const container = document.getElementById("trip-view-crossings");
      if (container && crossings) {
        container.innerHTML = crossings.length > 0 ? crossings.map(c => `
          <div style="display: flex; align-items: center; justify-content: space-between; padding: 10px 14px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 3px solid #00e676;">
            <div>
              <strong style="color: #00e676;">✓ ${c.junction_code} (${c.junction_name})</strong>
              <div style="font-size: 11px; color: #94a3b8;">Speed: ${c.speed_at_crossing_kmh} km/h • Clearance: ${c.clearance_time_seconds}s</div>
            </div>
            <span class="badge badge-green">CLEARED</span>
          </div>
        `).join("") : `<p style="font-size: 12px; color: #64748b;">No junction crossings logged for this trip yet.</p>`;
      }
    } catch (e) {
      console.error("Error loading trip view:", e);
    }
  }

  // 4. Render Analytics Page
  async renderAnalytics() {
    try {
      const res = await fetch("/api/analytics");
      const data = await res.json();

      const elTrips = document.getElementById("analytics-total-trips");
      const elCrossings = document.getElementById("analytics-total-crossings");
      const elClearance = document.getElementById("analytics-avg-clearance");
      const elTimeSaved = document.getElementById("analytics-time-saved");

      if (elTrips) elTrips.innerText = data.total_trips;
      if (elCrossings) elCrossings.innerText = data.total_crossings;
      if (elClearance) elClearance.innerText = `${data.avg_clearance_seconds}s`;
      if (elTimeSaved) elTimeSaved.innerText = `${data.estimated_time_saved_minutes} min`;

      // Render Junction table
      const jTable = document.getElementById("analytics-junctions-table");
      if (jTable && data.junction_stats) {
        jTable.innerHTML = data.junction_stats.map(j => `
          <tr>
            <td><strong>${j.code}</strong></td>
            <td>${j.name}</td>
            <td>${j.total_crossings || 0}</td>
            <td>${j.avg_clearance_sec ? Math.round(j.avg_clearance_sec) + 's' : '16s'}</td>
            <td><span class="badge badge-green">99.8%</span></td>
          </tr>
        `).join("");
      }
    } catch (e) {
      console.error("Error fetching analytics:", e);
    }
  }

  // 5. Render Admin & ESP32 Code Viewer
  async renderAdmin() {
    try {
      // Load current config
      const res = await fetch("/api/config");
      const config = await res.json();

      const inApproaching = document.getElementById("cfg-approaching");
      const inPrepare = document.getElementById("cfg-prepare");
      const inActivate = document.getElementById("cfg-activate");
      const inClearance = document.getElementById("cfg-clearance");
      const inTimeout = document.getElementById("cfg-timeout");

      if (inApproaching) inApproaching.value = config.approaching_dist_m;
      if (inPrepare) inPrepare.value = config.prepare_dist_m;
      if (inActivate) inActivate.value = config.activate_dist_m;
      if (inClearance) inClearance.value = config.clearance_dist_m;
      if (inTimeout) inTimeout.value = config.priority_timeout_sec;

      // Load Arduino firmware code
      const fwRes = await fetch("/api/firmware/code?device_type=transmitter");
      const fwData = await fwRes.json();
      const codeBlock = document.getElementById("esp32-code-display");
      if (codeBlock) {
        codeBlock.innerText = fwData.code;
      }
    } catch (e) {
      console.error("Error loading admin config:", e);
    }
  }

  async saveAdminConfig() {
    const data = {
      approaching_dist_m: parseFloat(document.getElementById("cfg-approaching").value),
      prepare_dist_m: parseFloat(document.getElementById("cfg-prepare").value),
      activate_dist_m: parseFloat(document.getElementById("cfg-activate").value),
      clearance_dist_m: parseFloat(document.getElementById("cfg-clearance").value),
      priority_timeout_sec: parseInt(document.getElementById("cfg-timeout").value)
    };

    try {
      await fetch("/api/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(data)
      });
      window.evpsApp.showToast("Configuration Saved & Applied to Live Geofences", "success");
    } catch (e) {
      console.error(e);
      if (window.evpsApp) {
        window.evpsApp.showToast("Failed to save configuration", "danger");
      }
    }
  }

  // 6. Render Customer Support & Emergency Dispatch Helpdesk
  async renderSupport() {
    await this.renderSupportTickets();
    this.bindSupportChat();
  }

  async renderSupportTickets() {
    const container = document.getElementById("support-tickets-list");
    if (!container) return;

    try {
      const res = await fetch("/api/support/tickets");
      const tickets = await res.json();

      container.innerHTML = tickets.map(t => {
        let pColor = "badge-amber";
        if (t.priority === "CRITICAL") pColor = "badge-red";
        else if (t.priority === "MEDIUM") pColor = "badge-cyan";

        let sColor = "badge-amber";
        if (t.status === "RESOLVED") sColor = "badge-green";
        else if (t.status === "IN_PROGRESS") sColor = "badge-cyan";

        return `
          <div class="glass-panel" style="padding: 16px; margin-bottom: 12px; border-left: 4px solid ${t.priority === 'CRITICAL' ? '#ff1744' : '#00e5ff'};">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
              <div style="display: flex; align-items: center; gap: 10px;">
                <strong style="color: var(--accent-cyan);">${t.ticket_code}</strong>
                <span class="badge ${pColor}">${t.priority}</span>
                <span class="badge" style="background: rgba(255,255,255,0.08);">${t.category}</span>
              </div>
              <span class="badge ${sColor}">${t.status}</span>
            </div>
            <h4 style="font-size: 14px; margin-bottom: 4px;">${t.subject}</h4>
            <p style="font-size: 12px; color: var(--text-secondary); line-height: 1.5; margin-bottom: 10px;">${t.description}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 11px; color: var(--text-muted); border-top: 1px solid var(--glass-border); padding-top: 8px;">
              <span>Submitted by: <strong>${t.user_name}</strong></span>
              <div style="display: flex; gap: 6px;">
                ${t.status !== 'RESOLVED' ? `<button class="btn btn-secondary btn-sm" style="font-size: 10px; padding: 2px 8px;" onclick="window.evpsPages.updateTicketStatus(${t.id}, 'RESOLVED')"><i class="fas fa-check"></i> Mark Resolved</button>` : ''}
                ${t.status === 'OPEN' ? `<button class="btn btn-secondary btn-sm" style="font-size: 10px; padding: 2px 8px;" onclick="window.evpsPages.updateTicketStatus(${t.id}, 'IN_PROGRESS')"><i class="fas fa-spinner"></i> In Progress</button>` : ''}
              </div>
            </div>
          </div>
        `;
      }).join("");
    } catch (e) {
      console.error("Error loading support tickets:", e);
    }
  }

  async submitSupportTicket(e) {
    if (e) e.preventDefault();
    const category = document.getElementById("ticket-category").value;
    const priority = document.getElementById("ticket-priority").value;
    const subject = document.getElementById("ticket-subject").value;
    const description = document.getElementById("ticket-desc").value;

    if (!subject || !description) {
      window.evpsApp.showToast("Please fill in subject and details", "warning");
      return;
    }

    try {
      const user = window.evpsApp.currentUser || { name: "Chief Dispatcher Sharma", id: 1 };
      const res = await fetch("/api/support/tickets", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          category,
          priority,
          subject,
          description,
          user_name: user.name,
          user_id: user.id || 1
        })
      });
      const data = await res.json();
      
      // Clear form
      document.getElementById("ticket-subject").value = "";
      document.getElementById("ticket-desc").value = "";
      
      window.evpsApp.showToast(`Support Ticket ${data.ticket.ticket_code} Created & Synced with Firebase Firestore!`, "success");
      
      // Sync to client Firebase Firestore if active
      if (window.evpsFirebase) {
        window.evpsFirebase.syncTicketToFirestore(data.ticket);
      }

      this.renderSupportTickets();
    } catch (err) {
      console.error(err);
      window.evpsApp.showToast("Failed to create ticket", "alert");
    }
  }

  async updateTicketStatus(ticketId, newStatus) {
    try {
      await fetch(`/api/support/tickets/${ticketId}/status`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: newStatus })
      });
      window.evpsApp.showToast(`Ticket #${ticketId} updated to ${newStatus}`, "info");
      this.renderSupportTickets();
    } catch (e) {
      console.error(e);
    }
  }

  bindSupportChat() {
    const chatInput = document.getElementById("support-chat-input");
    const sendBtn = document.getElementById("support-chat-send");
    if (!chatInput || !sendBtn) return;

    const handleSend = async () => {
      const text = chatInput.value.trim();
      if (!text) return;

      const chatBox = document.getElementById("support-chat-messages");
      chatInput.value = "";

      // Append user msg
      chatBox.innerHTML += `
        <div style="align-self: flex-end; background: linear-gradient(135deg, #0284c7, #0369a1); color: white; padding: 10px 14px; border-radius: 12px 12px 2px 12px; font-size: 13px; max-width: 80%;">
          <strong>You (${window.evpsApp.currentUser.role}):</strong>
          <p style="margin: 2px 0 0 0;">${text}</p>
        </div>
      `;
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        const res = await fetch("/api/support/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, role: window.evpsApp.currentUser.role })
        });
        const data = await res.json();

        setTimeout(() => {
          chatBox.innerHTML += `
            <div style="align-self: flex-start; background: #1e293b; border: 1px solid var(--glass-border); color: #f8fafc; padding: 10px 14px; border-radius: 12px 12px 12px 2px; font-size: 13px; max-width: 85%;">
              <div style="display: flex; align-items: center; gap: 6px; margin-bottom: 4px; color: var(--accent-cyan);">
                <i class="fas fa-robot"></i>
                <strong>${data.responder}</strong>
              </div>
              <p style="margin: 0; white-space: pre-line; color: #cbd5e1;">${data.reply}</p>
            </div>
          `;
          chatBox.scrollTop = chatBox.scrollHeight;
        }, 400);
      } catch (e) {
        console.error(e);
      }
    };

    sendBtn.onclick = handleSend;
    chatInput.onkeydown = (e) => {
      if (e.key === "Enter") handleSend();
    };
  }
}

window.evpsPages = new EVPSPages();

