import subprocess
import time
import urllib.request
import urllib.parse
import json
import base64
import os
import sys

CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
PORT = 9228

PAGES = [
    ("01_dashboard.png", "http://localhost:5173/?page=dashboard"),
    ("02_create_order.png", "http://localhost:5173/?page=create-order"),
    ("03_order_management.png", "http://localhost:5173/?page=orders"),
    ("04_agent_monitoring.png", "http://localhost:5173/?page=agents"),
    ("05_fraud_review.png", "http://localhost:5173/?page=fraud-review"),
    ("06_order_details.png", "http://localhost:5173/?page=order-details&id=ORD-B84AF9C7"),
    ("07_order_details_held.png", "http://localhost:5173/?page=order-details&id=ORD-7200CB9C"),
]

def main():
    os.makedirs(r"docs\screenshots", exist_ok=True)
    
    # Launch Chrome in headless mode with remote debugging port
    user_data = os.path.abspath(r"scratch\chrome_user_data_full")
    os.makedirs(user_data, exist_ok=True)
    
    cmd = [
        CHROME_PATH,
        "--headless=new",
        "--disable-gpu",
        "--no-sandbox",
        f"--user-data-dir={user_data}",
        f"--remote-debugging-port={PORT}",
        "--window-size=1440,900"
    ]
    
    proc = subprocess.Popen(cmd)
    try:
        # Wait for Chrome debug port to respond
        for _ in range(25):
            time.sleep(0.5)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json") as resp:
                    break
            except Exception:
                pass
        
        import asyncio
        import websockets
        
        async def capture_all():
            for filename, url in PAGES:
                out_path = os.path.join(r"docs\screenshots", filename)
                print(f"Capturing {url} -> {out_path}...")
                
                # Properly URL-encode the target URL for Chrome /json/new endpoint
                encoded_target = urllib.parse.quote(url, safe="")
                create_url = f"http://127.0.0.1:{PORT}/json/new?{encoded_target}"
                req = urllib.request.Request(create_url, method="PUT")
                with urllib.request.urlopen(req) as resp:
                    target_info = json.loads(resp.read().decode())
                
                ws_url = target_info.get("webSocketDebuggerUrl")
                target_id = target_info.get("id")
                
                async with websockets.connect(ws_url) as ws:
                    # Enable Page domain
                    await ws.send(json.dumps({"id": 1, "method": "Page.enable"}))
                    
                    # Wait 3.5 seconds for React components, API calls, and icons to render
                    await asyncio.sleep(3.5)
                    
                    # Capture screenshot
                    await ws.send(json.dumps({
                        "id": 100,
                        "method": "Page.captureScreenshot",
                        "params": {"format": "png"}
                    }))
                    
                    data_b64 = None
                    while True:
                        res = await ws.recv()
                        msg = json.loads(res)
                        if msg.get("id") == 100:
                            data_b64 = msg["result"]["data"]
                            break
                    
                    img_bytes = base64.b64decode(data_b64)
                    with open(out_path, "wb") as f:
                        f.write(img_bytes)
                    print(f"Saved {filename} ({len(img_bytes)} bytes)")
                
                # Close target tab
                close_url = f"http://127.0.0.1:{PORT}/json/close/{target_id}"
                urllib.request.urlopen(close_url)
        
        asyncio.run(capture_all())
        print("All screenshots successfully captured!")
    finally:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass

if __name__ == "__main__":
    main()
