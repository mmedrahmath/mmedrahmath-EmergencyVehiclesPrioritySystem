"""
EVPS - Emergency Vehicles Priority System
Database Model & Seed Data (SQLite + async helper)
Team: PHANTOM DELUX
"""

import sqlite3
import json
import os
import time
from typing import List, Dict, Any, Optional

DB_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "evps_database.sqlite")

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Users
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        name TEXT NOT NULL,
        role TEXT NOT NULL DEFAULT 'OPERATOR', -- ADMIN, OPERATOR, VIEWER
        badge_number TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. ESP32 Devices
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS esp32_devices (
        id TEXT PRIMARY KEY,
        device_type TEXT NOT NULL, -- AMBULANCE_TRANSMITTER, JUNCTION_RECEIVER
        mac_address TEXT,
        firmware_version TEXT DEFAULT 'v2.4.1-EVPS',
        status TEXT DEFAULT 'ONLINE', -- ONLINE, OFFLINE, ERROR
        last_ping DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 3. Hospitals
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS hospitals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        address TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        emergency_beds INTEGER DEFAULT 12,
        trauma_level TEXT DEFAULT 'Level-1',
        contact_phone TEXT DEFAULT '+91-9876543210',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4. Traffic Junctions
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS junctions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        code TEXT UNIQUE NOT NULL,
        name TEXT NOT NULL,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        receiver_id TEXT,
        status TEXT DEFAULT 'ONLINE', -- ONLINE, OFFLINE, MAINTENANCE
        current_signal TEXT DEFAULT 'RED', -- RED, YELLOW, GREEN, EMERGENCY_GREEN
        normal_cycle_sec INTEGER DEFAULT 45,
        priority_state TEXT DEFAULT 'NORMAL', -- NORMAL, APPROACHING, PREPARED, ACTIVE, CLEARING
        active_ambulance_id TEXT,
        last_ping DATETIME DEFAULT CURRENT_TIMESTAMP,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (receiver_id) REFERENCES esp32_devices(id)
    );
    """)

    # 5. Receivers (Hardware link)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS receivers (
        id TEXT PRIMARY KEY,
        junction_id INTEGER,
        frequency TEXT DEFAULT '2.4 GHz NRF24L01 / Wi-Fi',
        signal_rssi INTEGER DEFAULT -48,
        status TEXT DEFAULT 'CONNECTED',
        last_ack DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (junction_id) REFERENCES junctions(id)
    );
    """)

    # 6. Ambulances
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS ambulances (
        id TEXT PRIMARY KEY,
        callsign TEXT UNIQUE NOT NULL,
        vehicle_type TEXT DEFAULT 'Advanced Life Support (ALS)',
        plate_number TEXT NOT NULL,
        esp32_device_id TEXT,
        status TEXT DEFAULT 'IDLE', -- IDLE, EMERGENCY_ACTIVE, RETURNING, OFFLINE
        speed_kmh REAL DEFAULT 0.0,
        heading REAL DEFAULT 90.0,
        lat REAL NOT NULL,
        lng REAL NOT NULL,
        battery_level INTEGER DEFAULT 98,
        gps_status TEXT DEFAULT 'CONNECTED', -- CONNECTED, SEARCHING, LOST
        current_hospital_id INTEGER,
        current_junction_id INTEGER,
        priority_status TEXT DEFAULT 'NONE', -- NONE, REQUESTED, ACTIVE, CLEARED
        last_update DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (current_hospital_id) REFERENCES hospitals(id),
        FOREIGN KEY (esp32_device_id) REFERENCES esp32_devices(id)
    );
    """)

    # 7. Emergency Trips
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS emergency_trips (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_code TEXT UNIQUE NOT NULL,
        ambulance_id TEXT NOT NULL,
        hospital_id INTEGER NOT NULL,
        patient_status TEXT DEFAULT 'CRITICAL',
        status TEXT DEFAULT 'ACTIVE', -- ACTIVE, COMPLETED, CANCELLED
        start_time DATETIME DEFAULT CURRENT_TIMESTAMP,
        end_time DATETIME,
        start_lat REAL NOT NULL,
        start_lng REAL NOT NULL,
        dest_lat REAL NOT NULL,
        dest_lng REAL NOT NULL,
        total_distance_km REAL DEFAULT 0.0,
        distance_remaining_km REAL DEFAULT 0.0,
        eta_seconds INTEGER DEFAULT 0,
        time_saved_sec INTEGER DEFAULT 0,
        avg_speed_kmh REAL DEFAULT 45.0,
        route_data TEXT, -- JSON polyline coordinates
        FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
        FOREIGN KEY (hospital_id) REFERENCES hospitals(id)
    );
    """)

    # 8. Priority Requests
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS priority_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER,
        ambulance_id TEXT NOT NULL,
        junction_id INTEGER NOT NULL,
        status TEXT DEFAULT 'REQUESTED', -- REQUESTED, ACKNOWLEDGED, GRANTED_GREEN, CLEARED, TIMEOUT, REJECTED
        distance_at_request_m REAL,
        requested_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        acknowledged_at DATETIME,
        green_granted_at DATETIME,
        cleared_at DATETIME,
        duration_seconds INTEGER DEFAULT 0,
        FOREIGN KEY (trip_id) REFERENCES emergency_trips(id),
        FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
        FOREIGN KEY (junction_id) REFERENCES junctions(id)
    );
    """)

    # 9. Crossing Events
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS crossing_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        trip_id INTEGER,
        ambulance_id TEXT NOT NULL,
        junction_id INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        speed_at_crossing_kmh REAL DEFAULT 48.0,
        clearance_time_seconds INTEGER DEFAULT 18,
        status TEXT DEFAULT 'SUCCESSFUL',
        FOREIGN KEY (trip_id) REFERENCES emergency_trips(id),
        FOREIGN KEY (ambulance_id) REFERENCES ambulances(id),
        FOREIGN KEY (junction_id) REFERENCES junctions(id)
    );
    """)

    # 10. System Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        level TEXT DEFAULT 'INFO', -- INFO, WARN, ALERT, ERROR, SUCCESS
        source TEXT NOT NULL, -- ESP32, RECEIVER, SYSTEM, SIMULATION, ADMIN
        message TEXT NOT NULL,
        details TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 11. System Configuration
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS system_config (
        id INTEGER PRIMARY KEY CHECK (id = 1),
        system_mode TEXT DEFAULT 'SIMULATION', -- SIMULATION, LIVE_HARDWARE
        approaching_dist_m REAL DEFAULT 500.0,
        prepare_dist_m REAL DEFAULT 250.0,
        activate_dist_m REAL DEFAULT 100.0,
        clearance_dist_m REAL DEFAULT 50.0,
        priority_timeout_sec INTEGER DEFAULT 45,
        failsafe_enabled INTEGER DEFAULT 1,
        audio_alerts_enabled INTEGER DEFAULT 1,
        auto_normal_cycle_sec INTEGER DEFAULT 30,
        simulation_speed_multiplier REAL DEFAULT 1.5,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 12. Support Tickets & Incident Logs
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS support_tickets (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ticket_code TEXT UNIQUE NOT NULL,
        user_id INTEGER,
        user_name TEXT NOT NULL,
        category TEXT NOT NULL, -- HARDWARE_FAULT, SIGNAL_OVERRIDE, GPS_DRIFT, SOFTWARE_INQUIRY, SOS_DISPATCH
        priority TEXT NOT NULL DEFAULT 'HIGH', -- CRITICAL, HIGH, MEDIUM, LOW
        subject TEXT NOT NULL,
        description TEXT NOT NULL,
        status TEXT DEFAULT 'OPEN', -- OPEN, IN_PROGRESS, RESOLVED, ESCALATED
        assigned_to TEXT DEFAULT 'EVPS Tech Support (Team PHANTOM DELUX)',
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """)

    conn.commit()
    seed_default_data(conn)
    conn.close()


def seed_default_data(conn):
    cursor = conn.cursor()

    # Check if data already exists
    cursor.execute("SELECT COUNT(*) FROM hospitals")
    if cursor.fetchone()[0] > 0:
        return

    # 1. Config
    cursor.execute("""
    INSERT INTO system_config (id, system_mode, approaching_dist_m, prepare_dist_m, activate_dist_m, clearance_dist_m, priority_timeout_sec)
    VALUES (1, 'SIMULATION', 500.0, 250.0, 120.0, 50.0, 45)
    """)

    # 2. Users
    users = [
        ("admin", "admin123", "Chief Dispatcher Sharma", "ADMIN", "EVPS-ADMIN-01"),
        ("operator", "oper123", "Officer Rajesh Kumar", "OPERATOR", "EVPS-OP-04"),
        ("viewer", "view123", "Emergency Observer", "VIEWER", "EVPS-VW-10")
    ]
    cursor.executemany("INSERT INTO users (username, password_hash, name, role, badge_number) VALUES (?, ?, ?, ?, ?)", users)

    # 3. Hospitals (Central City Coordinates - Example: New Delhi / Metro Hub Area)
    # Centered around lat: 28.6139, lng: 77.2090
    hospitals = [
        ("HOSP-01", "City Apex Trauma Hospital", "Ring Road, Central Corridor, Sector 4", 28.6289, 77.2425, 24, "Level-1", "+91-11-23456789"),
        ("HOSP-02", "National Medical Care & Research", "Main Boulevard, West Avenue", 28.6012, 77.1850, 16, "Level-1", "+91-11-24681357"),
        ("HOSP-03", "St. Jude Emergency Center", "South Parkway Extension", 28.5840, 77.2280, 10, "Level-2", "+91-11-29876543"),
        ("HOSP-04", "Metro Lifeline Super Specialty", "North Gateway Expressway", 28.6490, 77.2010, 18, "Level-1", "+91-11-21122334")
    ]
    cursor.executemany("INSERT INTO hospitals (code, name, address, lat, lng, emergency_beds, trauma_level, contact_phone) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", hospitals)

    # 4. Junctions with Receivers
    # Array of junctions strategically placed on corridors leading to City Apex Trauma Hospital
    junctions = [
        ("J-01", "Connaught Central Junction", 28.6145, 77.2180, "RX-ESP32-J01", "ONLINE", "RED", 40),
        ("J-02", "Janpath Crossing", 28.6178, 77.2245, "RX-ESP32-J02", "ONLINE", "GREEN", 45),
        ("J-03", "Barakhamba Intersection", 28.6212, 77.2310, "RX-ESP32-J03", "ONLINE", "RED", 35),
        ("J-04", "Tilak Marg Metro Junction", 28.6248, 77.2365, "RX-ESP32-J04", "ONLINE", "RED", 45),
        ("J-05", "Hospital Gate North Avenue", 28.6275, 77.2405, "RX-ESP32-J05", "ONLINE", "RED", 30),
        ("J-06", "West Park Corridor Junction", 28.6065, 77.1950, "RX-ESP32-J06", "ONLINE", "GREEN", 40),
        ("J-07", "Ring Road Flyover Junction", 28.5920, 77.2150, "RX-ESP32-J07", "ONLINE", "RED", 50),
        ("J-08", "South Ridge Bypass Junction", 28.5890, 77.2220, "RX-ESP32-J08", "ONLINE", "GREEN", 35)
    ]

    for code, name, lat, lng, rx_id, status, signal, cycle in junctions:
        # insert device
        cursor.execute("INSERT OR IGNORE INTO esp32_devices (id, device_type, mac_address, status) VALUES (?, 'JUNCTION_RECEIVER', ?, 'ONLINE')", 
                       (rx_id, f"A4:CF:12:00:{code[-2:]}:8E"))
        # insert junction
        cursor.execute("INSERT INTO junctions (code, name, lat, lng, receiver_id, status, current_signal, normal_cycle_sec) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                       (code, name, lat, lng, rx_id, status, signal, cycle))
        j_id = cursor.lastrowid
        # insert receiver link
        cursor.execute("INSERT INTO receivers (id, junction_id, frequency, signal_rssi, status) VALUES (?, ?, '2.4 GHz NRF24L01 + Wi-Fi', -52, 'CONNECTED')",
                       (rx_id, j_id))

    # 5. Ambulances
    # Primary demo ambulance A-001 positioned at the start of corridor towards J-01 -> J-02 -> J-03 -> J-04 -> J-05 -> HOSP-01
    ambulances = [
        ("A-001", "AMBULANCE A-001", "ALS Type-1", "DL-01-EV-9011", "TX-ESP32-A001", "IDLE", 0.0, 52.0, 28.6105, 77.2110, 96, "CONNECTED", 1, 1),
        ("A-002", "AMBULANCE A-002", "ALS Type-2", "DL-01-EV-9022", "TX-ESP32-A002", "IDLE", 0.0, 120.0, 28.6040, 77.1890, 91, "CONNECTED", 2, 6),
        ("A-003", "AMBULANCE A-003", "BLS Transport", "DL-01-EV-9033", "TX-ESP32-A003", "IDLE", 0.0, 18.0, 28.5800, 77.2200, 88, "CONNECTED", 3, 7),
        ("A-004", "AMBULANCE A-004", "Cardiac Rescue", "DL-01-EV-9044", "TX-ESP32-A004", "IDLE", 0.0, 290.0, 28.6410, 77.2080, 100, "CONNECTED", 4, 8)
    ]

    for a_id, callsign, vtype, plate, tx_id, status, speed, heading, lat, lng, battery, gps, hosp_id, junc_id in ambulances:
        cursor.execute("INSERT OR IGNORE INTO esp32_devices (id, device_type, mac_address, status) VALUES (?, 'AMBULANCE_TRANSMITTER', ?, 'ONLINE')", 
                       (tx_id, f"30:AE:A4:77:{a_id[-3:]}:F1"))
        cursor.execute("""
        INSERT INTO ambulances (id, callsign, vehicle_type, plate_number, esp32_device_id, status, speed_kmh, heading, lat, lng, battery_level, gps_status, current_hospital_id, current_junction_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (a_id, callsign, vtype, plate, tx_id, status, speed, heading, lat, lng, battery, gps, hosp_id, junc_id))

    # 6. Sample Initial Logs
    logs = [
        ("INFO", "SYSTEM", "EVPS System Core initialized successfully. Mode: SIMULATION"),
        ("INFO", "ESP32", "Ambulance TX-ESP32-A001 GPS synced with 12 satellites. Fix: 3D."),
        ("INFO", "RECEIVER", "8/8 Junction Receivers connected via 2.4 GHz NRF24L01 + Wi-Fi mesh."),
        ("SUCCESS", "SYSTEM", "Safe failsafe protocols active: Maximum priority duration 45s, Auto-clear enabled.")
    ]
    cursor.executemany("INSERT INTO system_logs (level, source, message) VALUES (?, ?, ?)", logs)

    # 7. Sample Initial Support Tickets
    tickets = [
        ("TCK-8091", 1, "Chief Dispatcher Sharma", "HARDWARE_FAULT", "CRITICAL", "Receiver RX-ESP32-J04 Relay Test", "Bench testing 5V relay channel 3 for GREEN override on Tilak Marg. Confirmed operating normally.", "RESOLVED", "Team PHANTOM DELUX Lead"),
        ("TCK-8092", 2, "Officer Rajesh Kumar", "GPS_DRIFT", "HIGH", "Ambulance A-002 GPS Baud Rate Calibration", "Requesting re-sync of u-blox NEO-6M to 9600 baud rate on HardwareSerial 2.", "IN_PROGRESS", "Hardware Field Engineer"),
        ("TCK-8093", 1, "Chief Dispatcher Sharma", "SIGNAL_OVERRIDE", "MEDIUM", "Corridor Geofence Expansion at J-02", "Increasing approach geofence from 450m to 500m for Janpath Crossing.", "RESOLVED", "EVPS System Admin")
    ]
    cursor.executemany("""
    INSERT INTO support_tickets (ticket_code, user_id, user_name, category, priority, subject, description, status, assigned_to)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tickets)

    conn.commit()


# Helper DB access functions
def query_db(query: str, args=(), one: bool = False):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    r = cur.fetchall()
    conn.close()
    return (dict(r[0]) if r else None) if one else [dict(row) for row in r]

def execute_db(query: str, args=()):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(query, args)
    conn.commit()
    last_id = cur.lastrowid
    conn.close()
    return last_id

def log_system_event(level: str, source: str, message: str, details: Optional[str] = None):
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("INSERT INTO system_logs (level, source, message, details) VALUES (?, ?, ?, ?)",
                (level, source, message, details))
    conn.commit()
    conn.close()
