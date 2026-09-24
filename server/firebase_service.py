"""
EVPS - Emergency Vehicles Priority System
Firebase Integration Service (Firebase Admin, Firestore, & Auth sync)
Team: PHANTOM DELUX
"""

import os
import json
import time
from typing import Dict, Any, Optional, List

# Try importing firebase_admin
try:
    import firebase_admin
    from firebase_admin import credentials, firestore, auth
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False

FIREBASE_CONFIG_PATH = os.environ.get(
    "FIREBASE_CONFIG_PATH",
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "firebase_service_account.json")
)

class FirebaseService:
    def __init__(self):
        self.app = None
        self.db = None
        self.is_initialized = False
        self.project_id = os.environ.get("FIREBASE_PROJECT_ID", "evps-phantom-delux")
        self._init_firebase()

    def _init_firebase(self):
        if not FIREBASE_AVAILABLE:
            print("[Firebase] firebase_admin python package not loaded. Operating in cloud-bridge mirror mode.")
            return

        try:
            raw_credentials_json = os.environ.get("FIREBASE_CREDENTIALS_JSON")
            if raw_credentials_json:
                cred_dict = json.loads(raw_credentials_json)
                cred = credentials.Certificate(cred_dict)
                self.app = firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.is_initialized = True
                print("[Firebase Admin] Initialized from FIREBASE_CREDENTIALS_JSON environment variable.")
            elif os.path.exists(FIREBASE_CONFIG_PATH):
                cred = credentials.Certificate(FIREBASE_CONFIG_PATH)
                self.app = firebase_admin.initialize_app(cred)
                self.db = firestore.client()
                self.is_initialized = True
                print(f"[Firebase Admin] Initialized with service account: {FIREBASE_CONFIG_PATH}")
            else:
                # Initialize default / test app for EVPS
                if not firebase_admin._apps:
                    self.app = firebase_admin.initialize_app(options={
                        'projectId': self.project_id
                    })
                else:
                    self.app = firebase_admin.get_app()
                
                try:
                    self.db = firestore.client()
                    self.is_initialized = True
                    print(f"[Firebase Admin] Connected to project: {self.project_id}")
                except Exception as ex:
                    print(f"[Firebase Admin Note] Firestore client offline fallback: {ex}")
                    self.is_initialized = False
        except Exception as e:
            print(f"[Firebase Init Note]: {e}")
            self.is_initialized = False

    def sync_support_ticket(self, ticket: Dict[str, Any]):
        """Sync support ticket to Cloud Firestore collection 'support_tickets'."""
        if not self.is_initialized or not self.db:
            return False
        try:
            doc_ref = self.db.collection("support_tickets").document(ticket["ticket_code"])
            doc_ref.set({
                "ticket_code": ticket["ticket_code"],
                "user_name": ticket["user_name"],
                "category": ticket["category"],
                "priority": ticket["priority"],
                "subject": ticket["subject"],
                "description": ticket["description"],
                "status": ticket["status"],
                "assigned_to": ticket.get("assigned_to", "EVPS Support"),
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            print(f"[Firebase Sync Ticket Error]: {e}")
            return False

    def sync_telemetry_event(self, event_type: str, data: Dict[str, Any]):
        """Sync telemetry and priority events to Firestore collection 'telemetry_events'."""
        if not self.is_initialized or not self.db:
            return False
        try:
            doc_ref = self.db.collection("telemetry_events").document(f"evt_{int(time.time() * 1000)}")
            doc_ref.set({
                "type": event_type,
                "data": data,
                "timestamp": firestore.SERVER_TIMESTAMP
            })
            return True
        except Exception as e:
            return False

    def get_firebase_client_config(self) -> Dict[str, Any]:
        """Returns client-side Firebase web configuration parameters."""
        return {
            "apiKey": "AIzaSyDemoKeyEVPSPhantomDelux2026",
            "authDomain": "evps-phantom-delux.firebaseapp.com",
            "projectId": "evps-phantom-delux",
            "storageBucket": "evps-phantom-delux.appspot.com",
            "messagingSenderId": "847291039201",
            "appId": "1:847291039201:web:9c847a9e7f82b1d30f",
            "status": "ONLINE" if self.is_initialized else "DEMO_READY"
        }

firebase_service = FirebaseService()
