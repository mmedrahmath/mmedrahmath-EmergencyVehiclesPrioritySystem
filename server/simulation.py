"""
EVPS - Emergency Vehicles Priority System
Simulation & Telemetry Engine (High precision geofencing, route physics, signal cycle)
Team: PHANTOM DELUX
"""

import math
import asyncio
import time
import json
from typing import Dict, List, Any, Optional
from server.database import query_db, execute_db, log_system_event, get_db_connection

def haversine_distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on Earth in meters."""
    R = 6371000  # Earth radius in meters
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (math.sin(delta_phi / 2.0) ** 2 +
         math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2)
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return R * c

def calculate_heading(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate compass heading angle in degrees (0 = North, 90 = East, 180 = South, 270 = West)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing = math.degrees(math.atan2(y, x))
    return (bearing + 360.0) % 360.0


# Pre-defined high-density waypoints for realistic city road paths
# Route 1: Connaught Corridor -> Apex Trauma Hospital (via J-01, J-02, J-03, J-04, J-05)
ROUTE_APEX_HOSPITAL = [
    {"lat": 28.6105, "lng": 77.2110, "name": "Dispatch Origin Station"},
    {"lat": 28.6120, "lng": 77.2138, "name": "Outer Circle Sector 1"},
    {"lat": 28.6132, "lng": 77.2158, "name": "Connaught Approach"},
    {"lat": 28.6145, "lng": 77.2180, "name": "Junction J-01 (Connaught Central)"}, # J-01
    {"lat": 28.6158, "lng": 77.2205, "name": "Janpath Road North"},
    {"lat": 28.6168, "lng": 77.2225, "name": "Janpath Crosswalk"},
    {"lat": 28.6178, "lng": 77.2245, "name": "Junction J-02 (Janpath Crossing)"}, # J-02
    {"lat": 28.6192, "lng": 77.2272, "name": "Tolstoy Marg Avenue"},
    {"lat": 28.6202, "lng": 77.2290, "name": "Barakhamba Approach"},
    {"lat": 28.6212, "lng": 77.2310, "name": "Junction J-03 (Barakhamba Intersect)"}, # J-03
    {"lat": 28.6226, "lng": 77.2332, "name": "Mandi House Roundabout"},
    {"lat": 28.6238, "lng": 77.2348, "name": "Tilak Marg Flyover ramp"},
    {"lat": 28.6248, "lng": 77.2365, "name": "Junction J-04 (Tilak Marg Metro)"}, # J-04
    {"lat": 28.6260, "lng": 77.2385, "name": "Supreme Court Boulevard"},
    {"lat": 28.6275, "lng": 77.2405, "name": "Junction J-05 (Hospital Gate North)"}, # J-05
    {"lat": 28.6289, "lng": 77.2425, "name": "City Apex Trauma Hospital (Destination)"} # HOSP-01
]

# Generate interpolated smooth sub-steps between waypoints
def generate_dense_path(waypoints: List[Dict[str, Any]], step_meters: float = 12.0) -> List[Dict[str, Any]]:
    dense_path = []
    for i in range(len(waypoints) - 1):
        p1 = waypoints[i]
        p2 = waypoints[i + 1]
        dist = haversine_distance_m(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
        num_steps = max(1, int(dist / step_meters))
        for step in range(num_steps):
            t = step / float(num_steps)
            lat = p1["lat"] + (p2["lat"] - p1["lat"]) * t
            lng = p1["lng"] + (p2["lng"] - p1["lng"]) * t
            heading = calculate_heading(p1["lat"], p1["lng"], p2["lat"], p2["lng"])
            dense_path.append({
                "lat": lat,
                "lng": lng,
                "heading": heading,
                "segment_index": i,
                "current_name": p1.get("name", "")
            })
    # Add final destination point
    dense_path.append({
        "lat": waypoints[-1]["lat"],
        "lng": waypoints[-1]["lng"],
        "heading": dense_path[-1]["heading"] if dense_path else 0.0,
        "segment_index": len(waypoints) - 1,
        "current_name": waypoints[-1].get("name", "")
    })
    return dense_path


class SimulationEngine:
    def __init__(self):
        self.is_running = False
        self.is_paused = False
        self.system_mode = "SIMULATION" # or "LIVE_HARDWARE"
        self.active_ambulance_id = "A-001"
        self.active_hospital_id = 1
        self.current_trip_id = 1
        self.dense_route = generate_dense_path(ROUTE_APEX_HOSPITAL, step_meters=8.0)
        self.route_index = 0
        self.speed_multiplier = 1.5
        self.base_speed_kmh = 45.0
        
        # Priority Lifecycle Tracking
        self.current_priority_junction_id: Optional[int] = None
        self.priority_phase: str = "IDLE" # IDLE, DETECTED, REQUESTED, ACKNOWLEDGED, GREEN_ACTIVE, CROSSING, CLEARED
        self.priority_start_time: float = 0
        self.priority_countdown: int = 45
        self.last_crossed_junction_id: Optional[int] = None
        self.last_crossing_duration: int = 0

        # Junction normal cycle clock
        self.junction_cycle_counters: Dict[int, int] = {}
        
        # Telemetry State Broadcast Cache
        self.last_broadcast_state: Dict[str, Any] = {}

        # Error / Injected Fault simulation
        self.fault_gps_lost = False
        self.fault_receiver_offline = False

    def get_config(self) -> Dict[str, Any]:
        conf = query_db("SELECT * FROM system_config WHERE id = 1", one=True)
        if not conf:
            return {
                "approaching_dist_m": 500.0,
                "prepare_dist_m": 250.0,
                "activate_dist_m": 120.0,
                "clearance_dist_m": 50.0,
                "priority_timeout_sec": 45,
                "system_mode": "SIMULATION"
            }
        return dict(conf)

    def start_emergency(self, ambulance_id: str = "A-001", hospital_id: int = 1):
        """Start or restart emergency demo."""
        self.active_ambulance_id = ambulance_id
        self.active_hospital_id = hospital_id
        self.route_index = 0
        self.is_running = True
        self.is_paused = False
        self.priority_phase = "IDLE"
        self.current_priority_junction_id = None
        self.last_crossed_junction_id = None

        # Reset ambulance in DB
        start_pt = self.dense_route[0]
        execute_db("""
        UPDATE ambulances
        SET status = 'EMERGENCY_ACTIVE',
            speed_kmh = ?,
            heading = ?,
            lat = ?,
            lng = ?,
            gps_status = 'CONNECTED',
            priority_status = 'SEARCHING_CORRIDOR',
            current_hospital_id = ?,
            last_update = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (self.base_speed_kmh, start_pt["heading"], start_pt["lat"], start_pt["lng"], hospital_id, ambulance_id))

        # Create or update emergency trip record
        dest_pt = self.dense_route[-1]
        trip_code = f"TRIP-EVPS-{int(time.time()) % 100000:05d}"
        total_dist_km = haversine_distance_m(start_pt["lat"], start_pt["lng"], dest_pt["lat"], dest_pt["lng"]) / 1000.0

        trip_id = execute_db("""
        INSERT INTO emergency_trips (
            trip_code, ambulance_id, hospital_id, patient_status, status,
            start_lat, start_lng, dest_lat, dest_lng, total_distance_km,
            distance_remaining_km, eta_seconds, avg_speed_kmh, route_data
        ) VALUES (?, ?, ?, 'CRITICAL - LEVEL 1 DISPATCH', 'ACTIVE', ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            trip_code, ambulance_id, hospital_id,
            start_pt["lat"], start_pt["lng"], dest_pt["lat"], dest_pt["lng"],
            round(total_dist_km, 2), round(total_dist_km, 2),
            int(total_dist_km / (self.base_speed_kmh / 3600)), self.base_speed_kmh,
            json.dumps(ROUTE_APEX_HOSPITAL)
        ))
        self.current_trip_id = trip_id

        log_system_event(
            "ALERT",
            "SYSTEM",
            f"🚨 EMERGENCY DISPATCH ACTIVATED for {ambulance_id} -> Hospital #{hospital_id}. Trip: {trip_code}"
        )

    def pause_simulation(self):
        self.is_paused = True
        log_system_event("INFO", "SIMULATION", "Simulation paused by operator.")

    def resume_simulation(self):
        self.is_paused = False
        log_system_event("INFO", "SIMULATION", "Simulation resumed.")

    def reset_simulation(self):
        self.is_running = False
        self.is_paused = False
        self.route_index = 0
        self.priority_phase = "IDLE"
        self.current_priority_junction_id = None
        self.last_crossed_junction_id = None

        # Reset all junctions back to normal cycles
        execute_db("""
        UPDATE junctions
        SET priority_state = 'NORMAL',
            active_ambulance_id = NULL
        """)

        # Reset ambulance to IDLE
        start_pt = self.dense_route[0]
        execute_db("""
        UPDATE ambulances
        SET status = 'IDLE',
            speed_kmh = 0.0,
            priority_status = 'NONE',
            lat = ?,
            lng = ?,
            heading = ?
        WHERE id = ?
        """, (start_pt["lat"], start_pt["lng"], start_pt["heading"], self.active_ambulance_id))

        log_system_event("INFO", "SIMULATION", "Simulation reset to initial state.")

    def set_speed_multiplier(self, val: float):
        self.speed_multiplier = max(0.5, min(5.0, val))

    def set_fault(self, fault_type: str, enabled: bool):
        if fault_type == "gps_loss":
            self.fault_gps_lost = enabled
            execute_db("UPDATE ambulances SET gps_status = ? WHERE id = ?", 
                       ("LOST" if enabled else "CONNECTED", self.active_ambulance_id))
            log_system_event("WARN" if enabled else "INFO", "ESP32", 
                             f"GPS Signal {'LOST! Retrying...' if enabled else 'RESTORED. 3D Fix re-acquired.'}")
        elif fault_type == "receiver_offline":
            self.fault_receiver_offline = enabled
            if self.current_priority_junction_id:
                execute_db("UPDATE junctions SET status = ? WHERE id = ?",
                           ("OFFLINE" if enabled else "ONLINE", self.current_priority_junction_id))
            log_system_event("ALERT" if enabled else "INFO", "RECEIVER",
                             f"Junction Receiver {'DISCONNECTED (Offline fault injected)' if enabled else 'RECONNECTED online.'}")

    def update_normal_traffic_cycles(self):
        """Update normal traffic signal colors (Red <-> Green) when no emergency priority is active."""
        junctions = query_db("SELECT id, current_signal, normal_cycle_sec, priority_state FROM junctions")
        now = int(time.time())
        for j in junctions:
            j_id = j["id"]
            if j["priority_state"] == "ACTIVE" or (self.current_priority_junction_id == j_id and self.priority_phase == "GREEN_ACTIVE"):
                # Locked in EMERGENCY_GREEN
                continue
            
            # Normal periodic cycle (e.g. 20s Red, 3s Yellow, 20s Green)
            cycle_time = j["normal_cycle_sec"] or 40
            time_in_cycle = (now + j_id * 7) % cycle_time
            if time_in_cycle < (cycle_time * 0.45):
                color = "RED"
            elif time_in_cycle < (cycle_time * 0.55):
                color = "YELLOW"
            else:
                color = "GREEN"

            if j["current_signal"] != color:
                execute_db("UPDATE junctions SET current_signal = ? WHERE id = ?", (color, j_id))

    def step(self) -> Dict[str, Any]:
        """Perform one simulation step (called every ~500ms)."""
        config = self.get_config()
        approaching_m = config.get("approaching_dist_m", 500.0)
        prepare_m = config.get("prepare_dist_m", 250.0)
        activate_m = config.get("activate_dist_m", 120.0)
        clear_m = config.get("clearance_dist_m", 50.0)
        priority_timeout = config.get("priority_timeout_sec", 45)

        self.update_normal_traffic_cycles()

        if not self.is_running or self.is_paused:
            return self._build_snapshot_state()

        # Advance route index based on speed multiplier
        step_increment = max(1, int(1 * self.speed_multiplier))
        self.route_index += step_increment

        if self.route_index >= len(self.dense_route) - 1:
            # Reached Hospital!
            self.route_index = len(self.dense_route) - 1
            cur_pt = self.dense_route[self.route_index]
            self.is_running = False
            self.priority_phase = "IDLE"

            execute_db("""
            UPDATE ambulances
            SET status = 'ARRIVED_DESTINATION',
                speed_kmh = 0.0,
                priority_status = 'NONE',
                lat = ?, lng = ?
            WHERE id = ?
            """, (cur_pt["lat"], cur_pt["lng"], self.active_ambulance_id))

            execute_db("""
            UPDATE emergency_trips
            SET status = 'COMPLETED',
                end_time = CURRENT_TIMESTAMP,
                distance_remaining_km = 0.0,
                eta_seconds = 0
            WHERE id = ?
            """, (self.current_trip_id,))

            log_system_event(
                "SUCCESS",
                "SYSTEM",
                f"🏥 AMBULANCE {self.active_ambulance_id} ARRIVED SAFELY at Hospital! Emergency priority mission complete."
            )
            return self._build_snapshot_state()

        current_pt = self.dense_route[self.route_index]
        current_lat = current_pt["lat"]
        current_lng = current_pt["lng"]
        current_heading = current_pt["heading"]
        current_speed = self.base_speed_kmh * (1.0 + 0.1 * math.sin(self.route_index * 0.2))

        # Check distances to all junctions
        junctions = query_db("SELECT id, code, name, lat, lng, receiver_id, status, current_signal, priority_state FROM junctions")
        
        nearest_junction = None
        min_dist = 999999.0

        for j in junctions:
            d = haversine_distance_m(current_lat, current_lng, j["lat"], j["lng"])
            if d < min_dist:
                min_dist = d
                nearest_junction = j

        # Check destination remaining distance and ETA
        dest_pt = self.dense_route[-1]
        dist_to_dest_m = haversine_distance_m(current_lat, current_lng, dest_pt["lat"], dest_pt["lng"])
        dist_to_dest_km = round(dist_to_dest_m / 1000.0, 2)
        eta_seconds = int((dist_to_dest_m / ((current_speed * 1000) / 3600))) if current_speed > 0 else 0

        # Update Ambulance in Database
        execute_db("""
        UPDATE ambulances
        SET lat = ?,
            lng = ?,
            heading = ?,
            speed_kmh = ?,
            current_junction_id = ?,
            last_update = CURRENT_TIMESTAMP
        WHERE id = ?
        """, (current_lat, current_lng, current_heading, round(current_speed, 1),
              nearest_junction["id"] if nearest_junction else None, self.active_ambulance_id))

        # Update Emergency Trip
        execute_db("""
        UPDATE emergency_trips
        SET distance_remaining_km = ?,
            eta_seconds = ?
        WHERE id = ?
        """, (dist_to_dest_km, eta_seconds, self.current_trip_id))

        # ==========================================
        # GEOFENCING & AUTOMATIC PRIORITY STATE MACHINE
        # ==========================================
        if nearest_junction:
            j_id = nearest_junction["id"]
            j_code = nearest_junction["code"]
            j_name = nearest_junction["name"]

            # Calculate if ambulance is approaching or has passed the junction
            # We check the vector from junction to next waypoint
            next_pt = self.dense_route[min(len(self.dense_route) - 1, self.route_index + 1)]
            dist_next = haversine_distance_m(next_pt["lat"], next_pt["lng"], nearest_junction["lat"], nearest_junction["lng"])
            is_getting_closer = dist_next < min_dist

            # Geofence 1: Approaching (500m)
            if min_dist <= approaching_m and min_dist > prepare_m and is_getting_closer:
                if self.current_priority_junction_id != j_id:
                    self.current_priority_junction_id = j_id
                    self.priority_phase = "DETECTED"
                    execute_db("UPDATE junctions SET priority_state = 'APPROACHING' WHERE id = ?", (j_id,))
                    execute_db("UPDATE ambulances SET priority_status = 'JUNCTION_DETECTED' WHERE id = ?", (self.active_ambulance_id,))
                    log_system_event(
                        "INFO",
                        "ESP32",
                        f"📍 Approaching Junction {j_code} ({j_name}) - Distance: {int(min_dist)}m"
                    )

            # Geofence 2: Prepare Priority & Pre-Request (250m)
            elif min_dist <= prepare_m and min_dist > activate_m and is_getting_closer:
                if self.priority_phase in ["DETECTED", "IDLE"] or self.current_priority_junction_id != j_id:
                    self.current_priority_junction_id = j_id
                    self.priority_phase = "REQUESTED"
                    execute_db("UPDATE junctions SET priority_state = 'PREPARED' WHERE id = ?", (j_id,))
                    execute_db("UPDATE ambulances SET priority_status = 'PRIORITY_REQUESTED' WHERE id = ?", (self.active_ambulance_id,))
                    
                    # Create Priority Request record in DB
                    execute_db("""
                    INSERT INTO priority_requests (trip_id, ambulance_id, junction_id, status, distance_at_request_m, requested_at)
                    VALUES (?, ?, ?, 'REQUESTED', ?, CURRENT_TIMESTAMP)
                    """, (self.current_trip_id, self.active_ambulance_id, j_id, round(min_dist, 1)))

                    log_system_event(
                        "WARN",
                        "ESP32",
                        f"📡 WIRELESS PRIORITY REQUEST TRANSMITTED -> Receiver {nearest_junction['receiver_id']} for {j_code} ({int(min_dist)}m)"
                    )

            # Geofence 3: Activate GREEN Priority (120m -> 0m)
            elif min_dist <= activate_m and is_getting_closer:
                if self.priority_phase in ["REQUESTED", "DETECTED", "IDLE"]:
                    if not self.fault_receiver_offline:
                        self.priority_phase = "GREEN_ACTIVE"
                        self.priority_start_time = time.time()
                        self.priority_countdown = priority_timeout

                        # Receiver Acknowledges & Switches Traffic Signal to EMERGENCY_GREEN
                        execute_db("""
                        UPDATE junctions
                        SET current_signal = 'GREEN',
                            priority_state = 'ACTIVE',
                            active_ambulance_id = ?
                        WHERE id = ?
                        """, (self.active_ambulance_id, j_id))

                        execute_db("UPDATE ambulances SET priority_status = 'GREEN_GRANTED' WHERE id = ?", (self.active_ambulance_id,))

                        execute_db("""
                        UPDATE priority_requests
                        SET status = 'GRANTED_GREEN',
                            acknowledged_at = CURRENT_TIMESTAMP,
                            green_granted_at = CURRENT_TIMESTAMP
                        WHERE trip_id = ? AND junction_id = ? AND status = 'REQUESTED'
                        """, (self.current_trip_id, j_id))

                        log_system_event(
                            "ALERT",
                            "RECEIVER",
                            f"🟢 GREEN PRIORITY ACTIVATED at {j_code} ({j_name}). All conflicting signals locked RED."
                        )
                    else:
                        log_system_event(
                            "ERROR",
                            "RECEIVER",
                            f"❌ RECEIVER OFFLINE at {j_code}! Failsafe: Emergency priority could not be acknowledged."
                        )

            # Geofence 4: Crossing Event (Ambulance reaches junction intersection <= 25m)
            elif min_dist <= 25.0:
                if self.priority_phase == "GREEN_ACTIVE":
                    self.priority_phase = "CROSSING"
                    execute_db("UPDATE junctions SET priority_state = 'CROSSING' WHERE id = ?", (j_id,))
                    log_system_event(
                        "SUCCESS",
                        "SIMULATION",
                        f"🚑 AMBULANCE CROSSING {j_code} ({j_name}) at {int(current_speed)} km/h"
                    )

            # Geofence 5: Cleared Junction (> 50m past junction and moving away)
            elif not is_getting_closer and min_dist >= clear_m and (self.current_priority_junction_id == j_id or self.priority_phase in ["CROSSING", "GREEN_ACTIVE"]):
                duration_sec = int(time.time() - self.priority_start_time) if self.priority_start_time > 0 else 16
                self.last_crossed_junction_id = j_id
                self.last_crossing_duration = duration_sec
                self.priority_phase = "CLEARED"
                self.current_priority_junction_id = None

                # Restore junction to normal cycle
                execute_db("""
                UPDATE junctions
                SET priority_state = 'NORMAL',
                    active_ambulance_id = NULL
                WHERE id = ?
                """, (j_id,))

                execute_db("UPDATE ambulances SET priority_status = 'CLEARED' WHERE id = ?", (self.active_ambulance_id,))

                # Record Crossing Event in DB
                execute_db("""
                INSERT INTO crossing_events (trip_id, ambulance_id, junction_id, speed_at_crossing_kmh, clearance_time_seconds, status)
                VALUES (?, ?, ?, ?, ?, 'SUCCESSFUL')
                """, (self.current_trip_id, self.active_ambulance_id, j_id, round(current_speed, 1), duration_sec))

                execute_db("""
                UPDATE priority_requests
                SET status = 'CLEARED',
                    cleared_at = CURRENT_TIMESTAMP,
                    duration_seconds = ?
                WHERE trip_id = ? AND junction_id = ?
                """, (duration_sec, self.current_trip_id, j_id))

                log_system_event(
                    "SUCCESS",
                    "SYSTEM",
                    f"✓ JUNCTION {j_code} CLEARED! Priority cleared in {duration_sec}s. Signal restoring to normal traffic cycle."
                )

        # Failsafe Priority Timeout check
        if self.priority_phase == "GREEN_ACTIVE" and self.priority_start_time > 0:
            elapsed = time.time() - self.priority_start_time
            self.priority_countdown = max(0, int(priority_timeout - elapsed))
            if elapsed > priority_timeout:
                # Failsafe auto-clear to prevent infinite Green
                if self.current_priority_junction_id:
                    execute_db("""
                    UPDATE junctions
                    SET priority_state = 'NORMAL',
                        active_ambulance_id = NULL
                    WHERE id = ?
                    """, (self.current_priority_junction_id,))
                self.priority_phase = "IDLE"
                self.current_priority_junction_id = None
                log_system_event(
                    "WARN",
                    "SYSTEM",
                    f"⚠️ FAILSAFE TIMEOUT TRIGGERED: Priority automatically cleared after {priority_timeout}s to maintain traffic safety."
                )

        return self._build_snapshot_state()

    def _build_snapshot_state(self) -> Dict[str, Any]:
        """Build full real-time telemetry dictionary for WebSocket / UI."""
        ambulance = query_db("SELECT * FROM ambulances WHERE id = ?", (self.active_ambulance_id,), one=True)
        hospitals = query_db("SELECT * FROM hospitals")
        junctions = query_db("SELECT * FROM junctions")
        trip = query_db("SELECT * FROM emergency_trips WHERE id = ?", (self.current_trip_id,), one=True)
        recent_logs = query_db("SELECT * FROM system_logs ORDER BY id DESC LIMIT 15")
        recent_crossings = query_db("""
            SELECT c.*, j.code as junction_code, j.name as junction_name 
            FROM crossing_events c
            JOIN junctions j ON c.junction_id = j.id
            ORDER BY c.id DESC LIMIT 5
        """)
        config = self.get_config()

        next_junction_info = None
        if ambulance:
            # find next upcoming junction
            min_dist = 999999.0
            for j in junctions:
                d = haversine_distance_m(ambulance["lat"], ambulance["lng"], j["lat"], j["lng"])
                if d < min_dist:
                    min_dist = d
                    next_junction_info = {
                        "id": j["id"],
                        "code": j["code"],
                        "name": j["name"],
                        "distance_m": int(d),
                        "signal": j["current_signal"],
                        "priority_state": j["priority_state"],
                        "receiver_id": j["receiver_id"]
                    }

        state = {
            "timestamp": time.time(),
            "is_running": self.is_running,
            "is_paused": self.is_paused,
            "system_mode": config.get("system_mode", "SIMULATION"),
            "speed_multiplier": self.speed_multiplier,
            "ambulance": dict(ambulance) if ambulance else None,
            "hospitals": [dict(h) for h in hospitals],
            "junctions": [dict(j) for j in junctions],
            "trip": dict(trip) if trip else None,
            "next_junction": next_junction_info,
            "priority_phase": self.priority_phase,
            "priority_countdown": self.priority_countdown,
            "last_crossing": {
                "junction_id": self.last_crossed_junction_id,
                "duration_sec": self.last_crossing_duration
            } if self.last_crossed_junction_id else None,
            "logs": [dict(l) for l in recent_logs],
            "recent_crossings": [dict(rc) for rc in recent_crossings],
            "route_coords": ROUTE_APEX_HOSPITAL,
            "route_progress_pct": round((self.route_index / max(1, len(self.dense_route) - 1)) * 100, 1) if self.is_running else 0.0,
            "faults": {
                "gps_lost": self.fault_gps_lost,
                "receiver_offline": self.fault_receiver_offline
            }
        }
        self.last_broadcast_state = state
        return state

# Global engine instance
sim_engine = SimulationEngine()
