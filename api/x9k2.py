from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import json
import re
import os

# ---------- CONFIGURATION ----------
REAL_API_URL = os.getenv("REAL_API_URL", "https://dark-info.site/test/api.php")
REAL_API_KEY = os.getenv("REAL_API_KEY", "Demo")
DEVELOPER = "𐙚 𓆩𝘼𝙠𝙖𝙨𝗵 𝙊𝙨𝙞𝙣𝙩𓆪𓂂🧑‍💻🎀⃤"
API_KEY = "DEMO"

# 🔥 यह है नया गुप्त रास्ता (कोई guess नहीं कर सकता)
SECRET_PATH = "/v4/lookup-x9k2"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        key = params.get("key", [None])[0]
        raw_num = params.get("query", [None])[0]

        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        # 🔥 1. अगर URL गलत है (पुराना URL या कोई गलत अंदाज़ा) -> Invalid Key
        if parsed.path != SECRET_PATH:
            self.wfile.write(json.dumps({"error": "Invalid Key"}, indent=4).encode())
            return

        # 2. अगर Key गलत है -> Invalid Key
        if key != API_KEY:
            self.wfile.write(json.dumps({"error": "Invalid Key"}, indent=4).encode())
            return

        # 3. अगर Query खाली है -> Invalid Key
        if not raw_num:
            self.wfile.write(json.dumps({"error": "Invalid Key"}, indent=4).encode())
            return

        num = re.sub(r"[^\d]", "", raw_num.strip())

        if len(num) == 10:
            num = "91" + num
        elif len(num) == 12 and num.startswith("91"):
            pass
        else:
            self.wfile.write(json.dumps({"error": "No data found"}, indent=4).encode())
            return

        # असली API को कॉल करें
        try:
            real_url = f"{REAL_API_URL}?key={REAL_API_KEY}&num={num}"
            req = urllib.request.Request(real_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=25) as resp:
                raw_text = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            self.wfile.write(json.dumps({"error": "No data found"}, indent=4).encode())
            return

        result = self.parse_response(raw_text, num)
        self.wfile.write(json.dumps(result, indent=4, ensure_ascii=False).encode())

    # ---------- PARSE RESPONSE ----------
    def parse_response(self, text, query):
        text = text.replace("\\u003c", "<").replace("\\u003e", ">")
        text = text.replace("\\u0026", "&")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.split(r"-+Source-\d+-+", text)[0]
        text = re.sub(r"-+Main.*?-+", "", text, flags=re.DOTALL)

        lines = text.split("\n")
        blocks, current_block = [], []

        for line in lines:
            line = line.strip()
            if not line: continue
            m = re.match(r"^(.+?)\s*:\s*(.+)$", line)
            if not m: continue
            k = re.sub(r"\s+", "", re.sub(r"[^\w\s]", "", m.group(1).strip(), flags=re.UNICODE).lower())
            v = m.group(2).strip()
            if not v: continue

            if k in ("mobile", "phone", "telephone"):
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                current_block.append((k, v))
            else:
                current_block.append((k, v))
        if current_block: blocks.append(current_block)

        if not blocks: return {"error": "No data found"}

        data, seen = [], set()
        for block in blocks:
            rec = {"phones": [], "addresses": [], "name": None, "father_name": None, "aadhar": None, "email": None, "circle": None}
            for k, v in block:
                if k.startswith(("mobile", "phone", "telephone")): 
                    if v not in rec["phones"]: rec["phones"].append(v)
                elif k.startswith(("adres", "address")): rec["addresses"].append(v)
                elif k in ("fullname", "name"): rec["father_name"] = v
                elif "father" in k or k == "thenameofthefather": rec["name"] = v
                elif k.startswith("documentnumber") or k == "aadhar": rec["aadhar"] = rec["aadhar"] or v
                elif "passport" in k: rec["aadhar"] = rec["aadhar"] or v
                elif k == "email": rec["email"] = v
                elif "region" in k or "network" in k or "circle" in k: rec["circle"] = v

            if not rec["phones"]: continue
            
            uniq = rec["phones"]
            addr = " | ".join(rec["addresses"]) if rec["addresses"] else "N/A"

            for i, phone in enumerate(uniq):
                digits = re.sub(r"\D", "", str(phone))
                if not digits: continue
                fm = "+" + digits if (digits.startswith("91") and len(digits) == 12) else ("+91" + digits if len(digits) == 10 else "+" + digits)
                if fm in seen: continue
                seen.add(fm)

                alt = None
                if len(uniq) > 1:
                    nx = (i + 1) % len(uniq)
                    ad = re.sub(r"\D", "", str(uniq[nx]))
                    if ad: alt = "+" + ad if (ad.startswith("91") and len(ad) == 12) else ("+91" + ad if len(ad) == 10 else "+" + ad)

                data.append({
                    "mobile": fm, "name": rec["name"] or "N/A", "father_name": rec["father_name"] or "N/A",
                    "address": addr, "alternate": alt, "aadhar": rec["aadhar"] or "N/A",
                    "email": rec["email"], "circle": rec["circle"] or "N/A"
                })

        return {"status": "success", "total_records": len(data), "number": query, "data": data, "developer": DEVELOPER} if data else {"error": "No data found"}

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
