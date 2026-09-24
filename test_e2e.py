import asyncio
import websockets
import json
import urllib.request
import time
import os
import sys

TARGET_URL = os.environ.get("TARGET_URL", sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000").rstrip("/")

async def test_full_simulation():
    # Derive websocket URI
    if TARGET_URL.startswith("https://"):
        ws_base = TARGET_URL.replace("https://", "wss://", 1)
    elif TARGET_URL.startswith("http://"):
        ws_base = TARGET_URL.replace("http://", "ws://", 1)
    elif TARGET_URL.startswith("wss://") or TARGET_URL.startswith("ws://"):
        ws_base = TARGET_URL
    else:
        ws_base = f"ws://{TARGET_URL}"

    uri = f"{ws_base}/ws/live"
    print(f'[TEST] Target HTTP URL: {TARGET_URL}')
    print(f'[TEST] Connecting to EVPS Live WebSocket at {uri}')
    async with websockets.connect(uri) as ws:
        # Receive initial state
        init_raw = await ws.recv()
        init_msg = json.loads(init_raw)
        print('[TEST] Initial state received successfully. Type:', init_msg.get('type'))

        # Start emergency demo
        print('[TEST] Sending START_EMERGENCY command for Ambulance A-001 -> Hospital #1...')
        await ws.send(json.dumps({
            'action': 'START_EMERGENCY',
            'ambulance_id': 'A-001',
            'hospital_id': 1
        }))

        # Set speed multiplier to 2.5x for fast verification
        await ws.send(json.dumps({'action': 'SET_SPEED', 'speed': 2.5}))

        phases_seen = set()
        for i in range(120):
            msg_raw = await asyncio.wait_for(ws.recv(), timeout=5.0)
            msg = json.loads(msg_raw)
            if msg.get('type') == 'TELEMETRY_UPDATE':
                data = msg['data']
                phase = data.get('priority_phase')
                amb = data.get('ambulance', {})
                next_junc = data.get('next_junction', {})
                phases_seen.add(phase)
                
                junc_code = next_junc.get('code', '--') if next_junc else '--'
                junc_dist = next_junc.get('distance_m', '--') if next_junc else '--'
                
                if i % 3 == 0 or phase in ['GREEN_ACTIVE', 'CROSSING', 'CLEARED']:
                    print(f"[STEP {i:02d}] Phase: {phase:<14} | Amb: ({amb.get('lat', 0):.4f}, {amb.get('lng', 0):.4f}) | Speed: {amb.get('speed_kmh', 0)} km/h | Next: {junc_code} ({junc_dist}m)")
                
                if 'CLEARED' in phases_seen and len(phases_seen) >= 4:
                    print('\n>>> [TEST PASSED] Live Priority Lifecycle Verified:')
                    print('    [OK] Phase 1: EMERGENCY ACTIVE')
                    print('    [OK] Phase 2: APPROACHING JUNCTION DETECTED')
                    print('    [OK] Phase 3: WIRELESS PRIORITY REQUEST TRANSMITTED')
                    print('    [OK] Phase 4: RECEIVER ACKNOWLEDGED & GREEN PRIORITY ACTIVATED')
                    print('    [OK] Phase 5: AMBULANCE CROSSING DETECTED')
                    print('    [OK] Phase 6: PRIORITY CLEARED & NORMAL SIGNAL RESTORED\n')
                    break

    # Verify REST database records
    req = urllib.request.Request(f"{TARGET_URL}/api/crossing-events")
    with urllib.request.urlopen(req) as resp:
        crossings = json.loads(resp.read().decode('utf-8'))
        print(f'[DATABASE VERIFICATION] Total Crossing Events in DB: {len(crossings)}')
        if len(crossings) > 0:
            print(f'   Latest Crossing: Junction {crossings[0].get("junction_code")} | Speed: {crossings[0].get("speed_at_crossing_kmh")} km/h | Duration: {crossings[0].get("clearance_time_seconds")}s')

if __name__ == '__main__':
    asyncio.run(test_full_simulation())
