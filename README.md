# EVPS - Emergency Vehicles Priority System

**Team:** PHANTOM DELUX  
**Theme:** SMART VEHICLES  
**Category:** Smart Traffic Management & Emergency Vehicle Preemption

---

## 🚑 Project Overview

**Emergency Vehicles Priority System (EVPS)** is a full-stack, hardware-integrated intelligent traffic management platform designed to eliminate emergency vehicle delays at signalized intersections.

Using **ESP32 microcontrollers, u-blox GPS, NRF24L01+ RF transceivers, and a central real-time IoT platform**, EVPS automatically detects an approaching ambulance, transmits a priority request to the upcoming traffic junction receiver, grants immediate **GREEN** priority, detects when the ambulance clears the intersection, and safely restores the normal traffic light cycle.

---

## 🌟 Key Features

1. **Rapido / Uber-Style Live Emergency Tracking**:
   - High-precision GPS tracking with heading angle rotation.
   - Live route progress stepper (Ambulance $\rightarrow$ Next Junction $\rightarrow$ Hospital).
   - Speedometer, Distance Remaining, and ETA countdown.
2. **Interactive Live OpenStreetMap / Leaflet Map**:
   - Custom rotating ambulance markers with glowing emergency pulse rings.
   - Junction markers with active 3-color mini LEDs.
   - Destination hospital markers and animated glowing route polylines.
3. **Realistic 3D Traffic Light Component**:
   - 3D-styled physical housing with glowing LED lenses (Red, Yellow, Green).
   - Live cycle transitions and emergency override banner.
4. **Automated Multi-Tier Geofencing**:
   - **500m**: Corridor detection & approaching radar ping.
   - **250m**: Priority pre-request packet generated.
   - **120m**: Receiver acknowledged $\rightarrow$ Traffic signal switches to **GREEN PRIORITY**.
   - **0m**: Ambulance intersection crossing event recorded.
   - **50m past junction**: Priority cleared $\rightarrow$ Normal signal cycle restored.
5. **Safety Failsafes & Watchdog**:
   - 45s maximum priority timeout to prevent indefinite green lights.
   - Fault injection simulator (GPS Loss, Receiver Disconnect) for bench testing.
6. **Dual Mode Architecture**:
   - **SIMULATION MODE**: Instant interactive demonstration for SIH presentations.
   - **LIVE HARDWARE MODE**: Connects directly to physical ESP32 transmitters and junction receivers via standard REST & WebSockets.
7. **Complete Role-Based Authentication**:
   - Chief Admin, Dispatch Operator, and Read-Only Observer roles.

---

## 🛠️ Tech Stack

- **Backend:** Python 3.14+, FastAPI, Asynchronous WebSockets, SQLite (`aiosqlite`)
- **Frontend:** HTML5, CSS3 Glassmorphism Design System, Vanilla JS, Leaflet.js
- **Audio:** Web Audio API native sound synthesizer (Siren, Radar Ping, Priority Chimes)
- **Hardware Firmware:** Arduino C++ for ESP32 NodeMCU, NEO-6M GPS, NRF24L01+ RF, 3-Channel 5V Relay

---

## 🚀 Quick Start & Installation

### 1. Run the Application
```bash
python run.py
```
Or with uvicorn:
```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 2. Access the Application
Open your browser and navigate to:
```
http://localhost:8000
```

---

## 🎯 How to Present during SIH Demo

1. Open `http://localhost:8000` to view the **Landing Page & Flowchart**.
2. Click **"Launch Live Dashboard & Demo"**.
3. Click the glowing red **"START EMERGENCY DEMO"** button.
4. Watch the ambulance move in real-time along the corridor:
   - **Corridor Radar** tracks the approaching distance (e.g. 500m $\rightarrow$ 250m $\rightarrow$ 120m).
   - **Priority Request** is sent to Receiver `RX-ESP32-J04`.
   - The **3D Traffic Signal** transitions immediately to **🟢 GREEN PRIORITY**.
   - The ambulance crosses the intersection.
   - The system displays **✓ JUNCTION CLEARED** and automatically restores normal traffic cycles.
   - The **Live Event Log** records every timestamp and clearance duration.
5. Explore the **Ambulance Fleet**, **Traffic Junctions**, **Analytics**, and **Admin Geofence Settings** tabs!

---

## 📡 REST API & ESP32 Integration Endpoints

- `POST /api/ambulances/location` - Ingests live ESP32 GPS packets:
  ```json
  {
    "device_id": "TX-ESP32-A001",
    "ambulance_id": "A-001",
    "latitude": 28.6145,
    "longitude": 77.2180,
    "speed": 48.0,
    "emergency_status": "EMERGENCY_ACTIVE",
    "gps_status": "CONNECTED"
  }
  ```
- `POST /api/receivers/status` - Ingests junction receiver telemetry and confirmations.
- `POST /api/priority/override` - Dispatcher manual green signal override.
- `GET /api/firmware/code` - Generates ready-to-flash Arduino C++ sketches for ESP32.

---

**Built with pride for Smart India Hackathon by Team PHANTOM DELUX**
