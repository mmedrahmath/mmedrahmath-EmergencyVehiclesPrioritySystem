/**
 * EVPS - Leaflet Live Interactive Map Manager
 * Handles Ambulance moving marker, heading rotation, hospital markers, junction status indicators, and route polylines.
 * Team: PHANTOM DELUX
 */

class EVPSMapManager {
  constructor(containerId = "leaflet-map") {
    this.containerId = containerId;
    this.map = null;
    this.ambulanceMarker = null;
    this.hospitalMarkers = {};
    this.junctionMarkers = {};
    this.junctionCircles = {};
    this.routePolyline = null;
    this.isInitialized = false;
  }

  init(centerLat = 28.6212, centerLng = 77.2280, zoom = 14) {
    const container = document.getElementById(this.containerId);
    if (!container || this.isInitialized) return;

    // Create Leaflet Map Instance
    this.map = L.map(this.containerId, {
      center: [centerLat, centerLng],
      zoom: zoom,
      zoomControl: false,
      attributionControl: false
    });

    // Add Zoom Control at Top Right
    L.control.zoom({ position: 'topright' }).addTo(this.map);

    // Dark Tile Layer (CARTO Dark Matter or OpenStreetMap)
    L.tileLayer('https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png', {
      maxZoom: 19,
      subdomains: 'abcd',
    }).addTo(this.map);

    this.isInitialized = true;
    console.log("[EVPS Map] Initialized successfully.");
  }

  updateFromTelemetry(state) {
    if (!this.map) return;

    const { ambulance, hospitals, junctions, route_coords, priority_phase } = state;

    // 1. Render / Update Route Polyline
    if (route_coords && route_coords.length > 0) {
      const latlngs = route_coords.map(pt => [pt.lat, pt.lng]);
      if (!this.routePolyline) {
        this.routePolyline = L.polyline(latlngs, {
          color: '#ff1744',
          weight: 5,
          opacity: 0.85,
          dashArray: '8, 8',
          lineJoin: 'round'
        }).addTo(this.map);
      }
    }

    // 2. Render / Update Hospitals
    if (hospitals) {
      hospitals.forEach(h => {
        if (!this.hospitalMarkers[h.id]) {
          const hospIcon = L.divIcon({
            className: 'custom-hosp-marker',
            html: `
              <div class="hospital-marker-box" title="${h.name}">
                <i class="fas fa-hospital-alt"></i>
              </div>
            `,
            iconSize: [38, 38],
            iconAnchor: [19, 19]
          });
          const marker = L.marker([h.lat, h.lng], { icon: hospIcon }).addTo(this.map);
          marker.bindPopup(`
            <div style="color: #0f172a; font-family: sans-serif; padding: 4px;">
              <h4 style="margin: 0 0 4px 0; color: #1e40af;">🏥 ${h.name}</h4>
              <p style="margin: 0; font-size: 11px; color: #475569;">${h.address}</p>
              <p style="margin: 4px 0 0 0; font-size: 11px; font-weight: bold; color: #059669;">Trauma: ${h.trauma_level} | Beds: ${h.emergency_beds}</p>
            </div>
          `);
          this.hospitalMarkers[h.id] = marker;
        }
      });
    }

    // 3. Render / Update Junctions with 3-color LEDs
    if (junctions) {
      junctions.forEach(j => {
        const signalColor = j.current_signal || 'RED';
        const isPriority = j.priority_state === 'ACTIVE' || (j.current_signal === 'GREEN' && priority_phase === 'GREEN_ACTIVE');

        const redActive = signalColor === 'RED' ? 'active-red' : '';
        const yellowActive = signalColor === 'YELLOW' ? 'active-yellow' : '';
        const greenActive = (signalColor === 'GREEN' || isPriority) ? 'active-green' : '';

        const iconHtml = `
          <div class="junction-marker-box" title="${j.code} - ${j.name}">
            <span style="font-weight: 800; font-size: 10px; color: #94a3b8; margin-right: 2px;">${j.code}</span>
            <div class="j-light-dot ${redActive}"></div>
            <div class="j-light-dot ${yellowActive}"></div>
            <div class="j-light-dot ${greenActive}"></div>
          </div>
        `;

        if (!this.junctionMarkers[j.id]) {
          const juncIcon = L.divIcon({
            className: 'custom-junc-marker',
            html: iconHtml,
            iconSize: [80, 24],
            iconAnchor: [40, 12]
          });
          const marker = L.marker([j.lat, j.lng], { icon: juncIcon }).addTo(this.map);
          marker.bindPopup(`
            <div style="color: #0f172a; font-family: sans-serif; padding: 6px;">
              <h4 style="margin: 0 0 4px 0; color: #0f172a;">🚦 Junction ${j.code}</h4>
              <p style="margin: 0; font-size: 11px; color: #475569;">${j.name}</p>
              <p style="margin: 4px 0 0 0; font-size: 12px; font-weight: bold;">Receiver: ${j.receiver_id}</p>
              <p style="margin: 2px 0 0 0; font-size: 12px;">Signal: <strong>${signalColor}</strong> | Status: <strong>${j.status}</strong></p>
            </div>
          `);
          this.junctionMarkers[j.id] = marker;

          // Add Geofence detection circles (500m & 120m)
          const circle500 = L.circle([j.lat, j.lng], {
            radius: 500,
            color: '#00e5ff',
            weight: 1,
            opacity: 0.25,
            fillColor: '#00e5ff',
            fillOpacity: 0.03
          }).addTo(this.map);
          this.junctionCircles[j.id] = circle500;
        } else {
          // Update marker icon HTML
          const icon = this.junctionMarkers[j.id].getIcon();
          icon.options.html = iconHtml;
          this.junctionMarkers[j.id].setIcon(icon);
        }
      });
    }

    // 4. Render / Update Moving Ambulance Marker with Heading Rotation
    if (ambulance) {
      const heading = ambulance.heading || 0;
      const isEmergency = ambulance.status === 'EMERGENCY_ACTIVE';
      const ambHtml = `
        <div class="leaflet-ambulance-marker">
          ${isEmergency ? '<div class="amb-pulse-ring"></div>' : ''}
          <div class="amb-icon-box" style="transform: rotate(${heading}deg);">
            <i class="fas fa-ambulance"></i>
          </div>
        </div>
      `;

      const ambIcon = L.divIcon({
        className: 'custom-amb-marker',
        html: ambHtml,
        iconSize: [44, 44],
        iconAnchor: [22, 22]
      });

      if (!this.ambulanceMarker) {
        this.ambulanceMarker = L.marker([ambulance.lat, ambulance.lng], { icon: ambIcon, zIndexOffset: 1000 }).addTo(this.map);
        this.ambulanceMarker.bindPopup(`
          <div style="color: #0f172a; font-family: sans-serif; padding: 6px;">
            <h4 style="margin: 0 0 4px 0; color: #dc2626;">🚑 ${ambulance.callsign}</h4>
            <p style="margin: 0; font-size: 12px;">Speed: <strong>${ambulance.speed_kmh} km/h</strong></p>
            <p style="margin: 2px 0 0 0; font-size: 12px;">GPS Status: <strong>${ambulance.gps_status}</strong></p>
            <p style="margin: 2px 0 0 0; font-size: 12px;">Priority: <strong>${ambulance.priority_status}</strong></p>
          </div>
        `);
      } else {
        this.ambulanceMarker.setLatLng([ambulance.lat, ambulance.lng]);
        this.ambulanceMarker.setIcon(ambIcon);
      }
    }
  }

  recenter(lat, lng, zoom = 15) {
    if (this.map) {
      this.map.setView([lat, lng], zoom, { animate: true });
    }
  }

  invalidateSize() {
    if (this.map) {
      setTimeout(() => this.map.invalidateSize(), 200);
    }
  }
}

window.evpsMap = new EVPSMapManager("leaflet-map");
