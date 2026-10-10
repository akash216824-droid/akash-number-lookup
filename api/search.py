from http.server import BaseHTTPRequestHandler
import urllib.parse
import urllib.request
import json
import re
import os

# ---------- CONFIGURATION ----------
REAL_API_URL = os.getenv("REAL_API_URL", "https://dark-info.site/test/api.php")
REAL_API_KEY = os.getenv("REAL_API_KEY", "Demo")
DEVELOPER = "𐙚 𓆩𝘼𝙠𝙖𝙨𝗵 𝙊𝙨𝙞𝙣𝙩𓆪𓂃🧑💻🎀⃤"
API_KEY = "DEMO"


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

        if parsed.path != "/api/search":
            self.wfile.write(json.dumps({"error": "Invalid Key"}, indent=4).encode())
            return

        if key != API_KEY:
            self.wfile.write(json.dumps({"error": "Invalid Key"}, indent=4).encode())
            return

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

    # ---------- Parse Response ----------
    def parse_response(self, text, query):
        # Clean unicode & HTML
        text = text.replace("\\u003c", "<").replace("\\u003e", ">")
        text = text.replace("\\u0026", "&")
        text = re.sub(r"<[^>]+>", " ", text)

        # Remove Source sections
        text = re.split(r"-+Source-\d+-+", text)[0]
        # Remove header
        text = re.sub(r"-+Main.*?-+", "", text, flags=re.DOTALL)

        lines = text.split("\n")
        blocks = []
        current_block = []

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Match key: value (key may have emojis, spaces, symbols)
            m = re.match(r"^(.+?)\s*:\s*(.+)$", line)
            if not m:
                continue

            k = m.group(1).strip()
            v = m.group(2).strip()

            if not v:
                continue

            # Clean key: remove emojis and symbols, keep only letters, digits, spaces
            clean_key = re.sub(r"[^\w\s]", "", k, flags=re.UNICODE)
            clean_key = clean_key.strip().lower()
            clean_key = re.sub(r"\s+", "", clean_key)

            # Start new block if it's main phone
            if clean_key in ("mobile", "phone", "telephone"):
                if current_block:
                    blocks.append(current_block)
                    current_block = []
                current_block.append((clean_key, v))
            else:
                current_block.append((clean_key, v))

        if current_block:
            blocks.append(current_block)

        if not blocks:
            return {"error": "No data found"}

        data = []
        seen_phones = set()

        for block in blocks:
            rec = {
                "phones": [],
                "addresses": [],
                "name": None,
                "father_name": None,
                "aadhar": None,
                "email": None,
                "circle": None
            }

            for k, v in block:
                if k.startswith("mobile") or k.startswith("phone") or k.startswith("telephone"):
                    if v not in rec["phones"]:
                        rec["phones"].append(v)
                elif k.startswith("adres") or k.startswith("address"):
                    rec["addresses"].append(v)
                elif k in ("fullname", "name"):
                    # NOTE: Real API में Full Name में father का नाम आ रहा है
                    # Swap: FullName → father_name
                    rec["father_name"] = v
                elif "father" in k or k == "thenameofthefather":
                    # NOTE: Real API में Father's Name में user का नाम आ रहा है
                    # Swap: Father's Name → name
                    rec["name"] = v
                elif k.startswith("documentnumber") or k == "aadhar" or k == "documentnumber":
                    if rec["aadhar"] is None:
                        rec["aadhar"] = v
                elif "passport" in k:
                    if rec["aadhar"] is None:
                        rec["aadhar"] = v
                elif k == "email":
                    rec["email"] = v
                elif "region" in k or "network" in k or "circle" in k:
                    rec["circle"] = v

            if not rec["phones"]:
                continue

            unique_phones = rec["phones"]
            address = " | ".join(rec["addresses"]) if rec["addresses"] else "N/A"
            name = rec["name"]
            father = rec["father_name"]
            aadhar = rec["aadhar"]
            email = rec["email"]
            circle = rec["circle"]

            for i, phone in enumerate(unique_phones):
                digits = re.sub(r"\D", "", str(phone))
                if not digits:
                    continue
                if digits.startswith("91") and len(digits) == 12:
                    formatted_mobile = "+" + digits
                elif len(digits) == 10:
                    formatted_mobile = "+91" + digits
                else:
                    formatted_mobile = "+" + digits

                if formatted_mobile in seen_phones:
                    continue
                seen_phones.add(formatted_mobile)

                alternate = None
                if len(unique_phones) > 1:
                    next_idx = (i + 1) % len(unique_phones)
                    alt_digits = re.sub(r"\D", "", str(unique_phones[next_idx]))
                    if alt_digits:
                        if alt_digits.startswith("91") and len(alt_digits) == 12:
                            alternate = "+" + alt_digits
                        elif len(alt_digits) == 10:
                            alternate = "+91" + alt_digits
                        else:
                            alternate = "+" + alt_digits

                record = {
                    "mobile": formatted_mobile,
                    "name": name if name else "N/A",
                    "father_name": father if father else "N/A",
                    "address": address,
                    "alternate": alternate,
                    "aadhar": aadhar if aadhar else "N/A",
                    "email": email,
                    "circle": circle if circle else "N/A"
                }
                data.append(record)

        if not data:
            return {"error": "No data found"}

        return {
            "status": "success",
            "total_records": len(data),
            "number": query,
            "data": data,
            "developer": DEVELOPER
        }

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
