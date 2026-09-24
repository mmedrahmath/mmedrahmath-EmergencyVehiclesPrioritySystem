"""
EVPS - Emergency Vehicles Priority System
FastAPI Main Application & WebSocket Live Stream Server
Team: PHANTOM DELUX | Theme: SMART VEHICLES
"""

import os
import json
import asyncio
from typing import List, Set
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from server.database import init_db
from server.simulation import sim_engine
from server.routes_api import router as api_router

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")

# ==========================================
# WEBSOCKET CONNECTION MANAGER
# ==========================================

class ConnectionManager:
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.add(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.discard(websocket)

    async def broadcast(self, message: dict):
        if not self.active_connections:
            return
        dead_connections = set()
        text_data = json.dumps(message)
        for connection in self.active_connections:
            try:
                await connection.send_text(text_data)
            except Exception:
                dead_connections.add(connection)
        for dead in dead_connections:
            self.active_connections.discard(dead)

ws_manager = ConnectionManager()

# ==========================================
# BACKGROUND SIMULATION & TELEMETRY WORKER
# ==========================================

async def simulation_worker():
    """Background task executing simulation steps and broadcasting to WebSockets."""
    while True:
        try:
            state = sim_engine.step()
            await ws_manager.broadcast({
                "type": "TELEMETRY_UPDATE",
                "data": state
            })
        except Exception as e:
            print(f"[Simulation Worker Error]: {e}")
        await asyncio.sleep(0.5)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Initialize Database
    init_db()
    # Start background task
    sim_task = asyncio.create_task(simulation_worker())
    yield
    # Shutdown
    sim_task.cancel()

# ==========================================
# FASTAPI APP INSTANCE
# ==========================================

app = FastAPI(
    title="EVPS - Emergency Vehicles Priority System",
    description="Intelligent Traffic Light Preemption & Real-Time Emergency Fleet Tracking by Team PHANTOM DELUX",
    version="2.4.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Static Files
os.makedirs(STATIC_DIR, exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "css"), exist_ok=True)
os.makedirs(os.path.join(STATIC_DIR, "js"), exist_ok=True)
os.makedirs(TEMPLATES_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Include REST API
app.include_router(api_router)

# ==========================================
# WEBSOCKET ENDPOINTS
# ==========================================

@app.websocket("/ws/live")
async def websocket_live_feed(websocket: WebSocket):
    await ws_manager.connect(websocket)
    # Send immediate current snapshot
    initial_state = sim_engine._build_snapshot_state()
    await websocket.send_text(json.dumps({
        "type": "INITIAL_STATE",
        "data": initial_state
    }))
    try:
        while True:
            # Listen for client control messages
            data = await websocket.receive_text()
            try:
                msg = json.loads(data)
                action = msg.get("action")
                if action == "START_EMERGENCY":
                    sim_engine.start_emergency(
                        ambulance_id=msg.get("ambulance_id", "A-001"),
                        hospital_id=msg.get("hospital_id", 1)
                    )
                elif action == "PAUSE":
                    sim_engine.pause_simulation()
                elif action == "RESUME":
                    sim_engine.resume_simulation()
                elif action == "RESET":
                    sim_engine.reset_simulation()
                elif action == "SET_SPEED":
                    sim_engine.set_speed_multiplier(float(msg.get("speed", 1.5)))
                elif action == "INJECT_FAULT":
                    sim_engine.set_fault(msg.get("fault_type"), msg.get("enabled", False))
            except Exception as ex:
                print(f"[WS Inbound Parse Error]: {ex}")
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


# ==========================================
# PAGE ROUTING (SPA CONTAINER)
# ==========================================

INDEX_HTML_PATH = os.path.join(TEMPLATES_DIR, "index.html")

@app.get("/", response_class=HTMLResponse)
async def page_index():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/dashboard", response_class=HTMLResponse)
async def page_dashboard():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/trip/{trip_id}", response_class=HTMLResponse)
async def page_trip(trip_id: str):
    return FileResponse(INDEX_HTML_PATH)

@app.get("/ambulances", response_class=HTMLResponse)
async def page_ambulances():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/junctions", response_class=HTMLResponse)
async def page_junctions():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/analytics", response_class=HTMLResponse)
async def page_analytics():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/admin", response_class=HTMLResponse)
async def page_admin():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/login", response_class=HTMLResponse)
async def page_login():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/support", response_class=HTMLResponse)
async def page_support():
    return FileResponse(INDEX_HTML_PATH)

@app.get("/health")
def health_check():
    return {"status": "ONLINE", "system": "EVPS Core", "team": "PHANTOM DELUX"}
