import json
import gzip
import shutil
import os
import re
import urllib.request

CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return None

def save_config(cookie, place_id):
    data = {
        "cookie": cookie,
        "place_id": place_id
    }
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)
    print(f"[SYSTEM]: Settings saved to {CONFIG_FILE}")

# --- REUSABLE UTILS ---
def safe_filename(name: str) -> str:
    name = re.sub(r'[<>:"/\\|?*\x00-\x1F]', '', name)
    name = name.strip()
    return name[:120] if name else "unknown"

def http_get(url, headers=None):
    if headers is None: headers = {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req) as res:
        return res.getcode(), res.read()

def http_post(url, data_bytes, headers=None):
    if headers is None: headers = {}
    req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")
    with urllib.request.urlopen(req) as res:
        return res.getcode(), res.read()

def get_asset_name(asset_id, cookie, asset_type):
    url = f"https://economy.roblox.com/v2/assets/{asset_id}/details"
    headers = {"User-Agent": "Roblox/WinInet", "Cookie": f".ROBLOSECURITY={cookie}"}
    try:
        code, data = http_get(url, headers)
        if code == 200:
            info = json.loads(data.decode("utf-8", errors="ignore"))
            name = info.get("Name", f"{asset_type}_{asset_id}")
            creator = info.get("Creator", {}).get("Name", "Unknown")
            return safe_filename(f"{name} - {creator}")
    except: pass
    return safe_filename(f"{asset_type}_{asset_id} - Unknown")

def get_locations(id_array, asset_type, place_id, cookie):
    body_array = [{"assetId": aid, "assetType": asset_type, "requestId": "0"} for aid in id_array]
    url = "https://assetdelivery.roblox.com/v2/assets/batch"
    headers = {
        "User-Agent": "Roblox/WinInet",
        "Content-Type": "application/json",
        "Cookie": f".ROBLOSECURITY={cookie}",
        "Roblox-Place-Id": str(place_id),
        "Accept": "*/*",
        "Roblox-Browser-Asset-Request": "false"
    }
    try:
        payload = json.dumps(body_array).encode("utf-8")
        code, data = http_post(url, payload, headers)
        if code != 200: return []
        results_json = json.loads(data.decode("utf-8", errors="ignore"))
        return [{"assetId": body_array[i]["assetId"], "url": obj["locations"][0]["location"]} 
                for i, obj in enumerate(results_json) if "locations" in obj and obj["locations"]]
    except: return []

def download_asset(url, name, folder, ext):
    if not os.path.exists(folder): os.makedirs(folder)
    path = f"./{folder}/{name}.{ext}"
    gz_path = path + ".gz"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Roblox/WinInet"})
        with urllib.request.urlopen(req) as res, open(gz_path, "wb") as f:
            shutil.copyfileobj(res, f)
        with open(gz_path, "rb") as f: is_gz = f.read(2) == b"\x1f\x8b"
        if is_gz:
            with gzip.open(gz_path, "rb") as f_in, open(path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            os.remove(gz_path)
        else:
            os.rename(gz_path, path)
        print(f"[SUCCESS]: {name}")
    except Exception as e: print(f"[ERROR]: {name}: {e}")

# --- MAIN INTERFACE ---
def main():
    print("=== ROBLOX ASSET DOWNLOADER ===\n")
    
    config = load_config()
    if config:
        print("[INFO]: Loaded saved credentials from config.json")
        cookie = config['cookie']
        place_id = config['place_id']
    else:
        cookie = input("Enter .ROBLOSECURITY: ").strip()
        place_id = input("Enter Place ID: ").strip()
        
        save_prompt = input("\nWould you like to save these credentials to a config file? (y/n): ").lower()
        if save_prompt == 'y':
            save_config(cookie, place_id)

    while True:
        print("\n1. Download Audios")
        print("2. Download Animations")
        print("3. Reset Config / Change Cookie")
        print("4. Exit")
        
        choice = input("\nChoice: ").strip()
        
        if choice == "4": break
        
        if choice == "3":
            if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
            print("[SYSTEM]: Config deleted. Please restart the script.")
            break

        raw_ids = input("Enter IDs (comma separated): ").split(",")
        ids = [i.strip() for i in raw_ids if i.strip()]

        if choice == "1":
            locs = get_locations(ids, "Audio", place_id, cookie)
            for obj in locs:
                name = get_asset_name(obj["assetId"], cookie, "Audio")
                download_asset(obj["url"], name, "audios", "ogg")
        elif choice == "2":
            locs = get_locations(ids, "Animation", place_id, cookie)
            for obj in locs:
                name = get_asset_name(obj["assetId"], cookie, "Animation")
                download_asset(obj["url"], name, "anims", "rbxm")
            
    print("\nExiting...")

if __name__ == "__main__":
    main()