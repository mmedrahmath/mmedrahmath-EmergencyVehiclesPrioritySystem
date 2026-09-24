# EVPS - Emergency Vehicles Priority System

**Team:** PHANTOM DELUX  
**Theme:** SMART VEHICLES  
**Category:** Smart Traffic Management & Emergency Vehicle Preemption  
**Backend Framework:** **FastAPI** (ASGI, Asynchronous WebSockets, Pydantic, SQLite)

---

## 🚑 Project Overview

**Emergency Vehicles Priority System (EVPS)** is a full-stack, hardware-integrated intelligent traffic management platform designed to eliminate emergency vehicle delays at signalized intersections.

Using **ESP32 microcontrollers, u-blox GPS, NRF24L01+ RF transceivers, and a central real-time IoT platform**, EVPS automatically detects an approaching ambulance, transmits a priority request to the upcoming traffic junction receiver, grants immediate **GREEN** priority, detects when the ambulance clears the intersection, and safely restores the normal traffic light cycle.

---

## 🌟 Key Features

1. **Live Emergency Tracking & Navigation**:
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

## 🛠️ Production Tech Stack

- **Backend Framework:** FastAPI (`fastapi>=0.110.0`)
- **ASGI Server:** Uvicorn with standard extras (`uvicorn[standard]>=0.28.0`), Gunicorn (`gunicorn>=21.2.0`)
- **Real-time Engine:** Asynchronous WebSockets (`/ws/live`), Bidirectional Telemetry Stream
- **Database:** SQLite (`aiosqlite` / `sqlite3`) with dynamic schema creation and automatic seed data
- **Cloud Integrations:** Optional Google Firebase Firestore & Auth bridge via environment variables
- **Frontend:** Responsive Single-Page Application (HTML5, Vanilla CSS Glassmorphism, Vanilla JS, Leaflet.js)

---

## 🌐 Deploying EVPS to Public HTTPS (Free Cloud Hosting)

This project is pre-configured with `render.yaml`, `Procfile`, `.python-version`, and dynamic `HOST` / `PORT` binding (`0.0.0.0:$PORT`) for 1-click cloud deployment on **Render**, **Railway**, or **Koyeb**.

### Option A: 1-Click Deploy on Render (Recommended - Free Tier)

1. **Sign Up / Log In to Render**:
   - Go to [render.com](https://render.com) and sign in using your GitHub account.

2. **Create New Web Service**:
   - In the Render Dashboard, click **New +** $\rightarrow$ **Web Service**.
   - Connect your GitHub repository: `mmedrahmath/EmergencyVehiclesPrioritySystem` (or your fork/repository).
   
3. **Configure Settings** (Automatically detected via `render.yaml` or fill manually):
   - **Name:** `emergency-vehicles-priority-system` (or any custom name)
   - **Environment:** `Python 3`
   - **Region:** Any (e.g. `Oregon (US West)` or `Frankfurt (EU)`)
   - **Branch:** `main`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python run.py`
   - **Instance Type:** `Free`

4. **Environment Variables** (Optional):
   - `PYTHON_VERSION`: `3.11.9`
   - `PORT`: (Render sets this automatically)
   - `DATABASE_PATH`: (Optional, defaults to `./evps_database.sqlite`)

5. **Deploy**:
   - Click **Create Web Service**.
   - Render will build the container, install dependencies, and launch the service.
   - Your public HTTPS URL will be ready in 1-2 minutes:
     ```
     https://emergency-vehicles-priority-system.onrender.com
     ```

---

### Option B: Deploy on Railway (Free / Low Cost)

1. Go to [railway.app](https://railway.app) and log in with GitHub.
2. Click **New Project** $\rightarrow$ **Deploy from GitHub repo**.
3. Select your repository.
4. Railway will automatically detect the `Procfile` (`web: python run.py`) and deploy with public HTTPS and WebSocket support.

---

### Option C: Deploy on Koyeb (Free Tier)

1. Go to [koyeb.com](https://koyeb.com) and create an account.
2. Select **GitHub** as the deployment source and select this repository.
3. Set the build type to **Buildpack**, Build Command `pip install -r requirements.txt`, and Run Command `python run.py`.
4. Deploy to get a free `https://<app>.koyeb.app` URL with SSL and WebSockets.

---

## 🧪 Local Testing & Verification

### 1. Run Server Locally
```bash
python run.py
```
Or with custom port:
```bash
$env:PORT="8080"; python run.py    # Windows PowerShell
PORT=8080 python run.py            # Linux / macOS
```

### 2. Run Automated End-to-End Test Suite
To verify the full simulation lifecycle, WebSocket handshake, and REST database records:

- **Local test:**
  ```bash
  python test_e2e.py
  ```
- **Remote test on your deployed public HTTPS URL:**
  ```bash
  python test_e2e.py https://your-app-name.onrender.com
  ```

---

## 📡 REST API & ESP32 Integration Endpoints

- `GET /health` - Health check endpoint for uptime monitors.
- `GET /ws/live` - Real-time bidirectional WebSocket telemetry stream.
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
- `GET /api/firmware/code` - Dynamically generates ready-to-flash Arduino C++ sketches for ESP32 with your server's live URL.

---

**Built with pride for Smart India Hackathon by Team PHANTOM DELUX**
