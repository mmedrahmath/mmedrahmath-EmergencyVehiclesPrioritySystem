"""
EVPS - Emergency Vehicles Priority System
Server Launcher
Team: PHANTOM DELUX | Theme: SMART VEHICLES
"""

import uvicorn
import os
import sys

if __name__ == "__main__":
    # Ensure current directory is on python path
    sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

    # Fix Windows console encoding for Unicode output
    if sys.platform == "win32":
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    print("\n=======================================================")
    print("  EVPS - Emergency Vehicles Priority System")
    print("  Team: PHANTOM DELUX | Theme: SMART VEHICLES")
    print("  Server running on: http://localhost:8000")
    print("=======================================================\n")
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=False)
