#!/usr/bin/env python3
"""
Universal Python Obfuscator / Decoder (+ self‑updater)
Made by @ItsMeJeff
v2.5
"""

import base64, zlib, marshal, types, re, sys, os, subprocess, tempfile, struct, time, importlib, shutil, urllib.request
from pathlib import Path
from io import StringIO

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.prompt import Prompt
    from rich.table import Table
except ImportError:
    print("[!] pip install rich")
    sys.exit(1)

console = Console()
VERSION = "2.5"
UPDATE_URL = "https://github.com/CodeHax-ItsMeJeff/CodeHax/raw/refs/heads/main/main.py"

# ------------------------------------------------------------
#  Decoding engines
# ------------------------------------------------------------
def decode_layer_v1(enc):
    try:
        c = enc.replace('\n','').replace(' ','')
        l1 = base64.b64decode(c.encode()).decode()
        l2 = l1[::-1]
        l3 = base64.b64decode(l2.encode())
        return zlib.decompress(l3).decode()
    except:
        return None

def extract_pyobf_payload(s):
    m = re.search(r"exec\(\(_\)\(b'([^']*)'\)\)", s)
    return m.group(1) if m else None

def try_uncompyle6(code_obj):
    try:
        from uncompyle6.main import decompile
    except:
        return None
    for ver in [3.12, 3.11, 3.10, 3.9, 3.8, 3.7, 3.6, 3.5, 2.7]:
        try:
            buf = StringIO()
            decompile(ver, code_obj, out=buf)
            res = buf.getvalue().strip()
            if res:
                console.print(f"[green]uncompyle6 {ver}[/green]")
                return res
        except:
            continue
    return None

def try_decompyle3(code_obj):
    try:
        from decompyle3.main import decompile as d3decomp
    except:
        return None
    for ver in [3.7, 3.8, 3.9, 3.10, 3.11]:
        try:
            buf = StringIO()
            d3decomp(ver, code_obj, out=buf)
            res = buf.getvalue().strip()
            if res:
                console.print(f"[green]decompyle3 {ver}[/green]")
                return res
        except:
            continue
    return None

def try_pycdc(code_obj):
    if not shutil.which("pycdc"):
        return None
    try:
        magic = importlib.util.MAGIC_NUMBER
        fd, tmp = tempfile.mkstemp(suffix=".pyc")
        with open(tmp, 'wb') as f:
            f.write(magic)
            f.write(struct.pack('<i', int(time.time())))
            f.write(struct.pack('<i', len(marshal.dumps(code_obj))))
            f.write(marshal.dumps(code_obj))
        result = subprocess.run(["pycdc", tmp], capture_output=True, text=True, timeout=10)
        os.unlink(tmp)
        if result.returncode == 0 and result.stdout.strip():
            console.print("[green]pycdc succeeded[/green]")
            return result.stdout
    except Exception as e:
        console.print(f"[dim]pycdc error: {e}[/dim]")
    return None

def decompile_fallback(code_obj):
    raw = marshal.dumps(code_obj)
    with open("raw_bytecode.marshal", "wb") as f:
        f.write(raw)
    console.print("[yellow]All decompilers failed. Saved raw_bytecode.marshal[/yellow]")
    try:
        import dis
        out = StringIO()
        dis.disassemble(code_obj, file=out)
        lines = out.getvalue().splitlines()[:20]
        console.print("[dim]Disassembly (first 20 lines):[/dim]")
        for l in lines:
            console.print(l)
    except:
        pass
    return None

def decode_pyobf(file):
    with open(file, 'r', encoding='utf-8') as f:
        cont = f.read()
    payload = extract_pyobf_payload(cont)
    if not payload:
        return None
    console.print("[cyan]Reverse string[/cyan]")
    s1 = payload[::-1]
    console.print("[cyan]Base64 decode[/cyan]")
    try:
        s2 = base64.b64decode(s1.encode())
    except Exception as e:
        console.print(f"[red]Base64: {e}[/red]"); return None
    console.print("[cyan]zlib decompress[/cyan]")
    try:
        s3 = zlib.decompress(s2)
    except Exception as e:
        console.print(f"[red]zlib: {e}[/red]"); return None
    console.print("[cyan]marshal.loads[/cyan]")
    try:
        code = marshal.loads(s3)
    except Exception as e:
        console.print(f"[red]marshal: {e}[/red]"); return None
    if not isinstance(code, types.CodeType):
        console.print("[yellow]Not a code object[/yellow]"); return None
    # Try all engines in order
    for engine in (try_uncompyle6, try_decompyle3, try_pycdc):
        res = engine(code)
        if res:
            return res
    return decompile_fallback(code)

def auto_decode(file_path):
    if not os.path.exists(file_path):
        console.print(f"[red]File not found: {file_path}[/red]")
        return
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    if extract_pyobf_payload(content):
        console.print("[bold yellow]PyObfuscate style[/bold yellow]")
        res = decode_pyobf(file_path)
        if res:
            out = Path(file_path).stem + "_decoded.py"
            with open(out, 'w', encoding='utf-8') as f:
                f.write(res)
            console.print(f"[green]✅ Saved: {out}[/green]")
            lines = res.splitlines()[:15]
            prev = "\n".join(lines) + ("\n..." if len(res.splitlines())>15 else "")
            console.print(Panel(prev, title="Preview", border_style="green"))
        else:
            console.print("[red]Decoding failed[/red]")
        return
    m = re.search(r'encoded\s*=\s*["\']([^"\']+)["\']', content)
    if m:
        console.print("[bold yellow]Protected Loader v1.0[/bold yellow]")
        enc = m.group(1)
        res = decode_layer_v1(enc)
        if res:
            while re.search(r'encoded\s*=\s*["\']', res):
                console.print("[cyan]Unwrapping layer...[/cyan]")
                inner = re.search(r'encoded\s*=\s*["\']([^"\']+)["\']', res)
                if inner:
                    res = decode_layer_v1(inner.group(1))
                else:
                    break
            out = Path(file_path).stem + "_decoded.py"
            with open(out, 'w', encoding='utf-8') as f:
                f.write(res)
            console.print(f"[green]✅ Saved: {out}[/green]")
            lines = res.splitlines()[:15]
            prev = "\n".join(lines) + ("\n..." if len(res.splitlines())>15 else "")
            console.print(Panel(prev, title="Preview", border_style="green"))
        else:
            console.print("[red]Decoding failed[/red]")
        return
    console.print("[yellow]No header, trying raw base64...[/yellow]")
    res = decode_layer_v1(content.strip().strip("'").strip('"'))
    if res:
        out = Path(file_path).stem + "_decoded.py"
        with open(out, 'w', encoding='utf-8') as f:
            f.write(res)
        console.print(f"[green]✅ Saved: {out}[/green]")
    else:
        console.print("[red]Cannot decode[/red]")

# ------------------------------------------------------------
#  Obfuscation engines
# ------------------------------------------------------------
def one_layer_encode(text):
    comp = zlib.compress(text.encode())
    b64_1 = base64.b64encode(comp).decode()
    rev = b64_1[::-1]
    return base64.b64encode(rev.encode()).decode()

def loader_template(payload, author="@ItsMeJeff"):
    return f'''# Author: {author}
# Developer: {author}
# Protected Code Loader

import base64, zlib, sys
def decode_me():
    print("""
    ╔══════════════════════════════════════╗
    ║     Protected Python Loader v1.0     ║
    ║        Cracked By: {author:<12}║
    ║       Full credit: {author:<13}║
    ╚══════════════════════════════════════╝
    """)
def decode_and_run():
    try:
        decode_me()
        encoded = "{payload}"
        layer1 = base64.b64decode(encoded.encode()).decode()
        layer2 = layer1[::-1]
        layer3 = base64.b64decode(layer2.encode())
        original = zlib.decompress(layer3).decode()
        exec(original, {{'__name__': '__main__'}})
    except:
        print("Error"); sys.exit(1)
if __name__ == "__main__":
    decode_and_run()
'''

def marshal_template(payload_b64, author="@ItsMeJeff"):
    return f'''# Author: {author}
# Obfuscated with PyObfuscate style
_ = lambda __ : __import__('marshal').loads(__import__('zlib').decompress(__import__('base64').b64decode(__[::-1])))
exec((_)(b'{payload_b64}'))
'''

def one_layer_encode_marshal(text):
    code = compile(text, '<obf>', 'exec')
    comp = zlib.compress(marshal.dumps(code))
    b64_1 = base64.b64encode(comp).decode()
    rev = b64_1[::-1]
    return base64.b64encode(rev.encode()).decode()

# ------------------------------------------------------------
#  Self‑updater
# ------------------------------------------------------------
def self_update(restart=True):
    console.print("[cyan]🔍 Checking for updates...[/cyan]")
    try:
        with urllib.request.urlopen(UPDATE_URL) as r:
            new_code = r.read().decode()
        me = Path(sys.argv[0]).read_text()
        if new_code == me:
            console.print("[green]Already up to date.[/green]")
            return
        console.print("[yellow]New version found! Updating and restarting...[/yellow]")
        with open(sys.argv[0], 'w', encoding='utf-8') as f:
            f.write(new_code)
        if restart:
            os.execv(sys.executable, [sys.executable] + sys.argv)
    except Exception as e:
        console.print(f"[red]Update failed: {e}[/red]")

# ------------------------------------------------------------
#  Menus
# ------------------------------------------------------------
def decode_menu():
    console.print(Panel.fit("📜 Decoder", border_style="blue"))
    file_path = Prompt.ask("Obfuscated file path")
    auto_decode(file_path)

def encrypt_menu():
    console.print(Panel.fit("🔒 Obfuscator", border_style="magenta"))
    src = Prompt.ask("File to obfuscate")
    if not os.path.exists(src):
        console.print("[red]Not found[/red]")
        return
    with open(src, 'r', encoding='utf-8') as f:
        code = f.read()
    console.print("[1] Protected Loader (text)")
    console.print("[2] PyObfuscate (marshal, stronger)")
    mode = Prompt.ask("Mode", choices=["1","2"], default="2")
    layers = int(Prompt.ask("Layers (1-10)", default="1", choices=[str(i) for i in range(1,11)]))
    author = Prompt.ask("Author", default="@ItsMeJeff")
    if mode == "2":
        payload = code
        for i in range(layers):
            payload = one_layer_encode_marshal(payload)
            console.print(f"[cyan]Marshal layer {i+1}/{layers}[/cyan]")
        out_code = marshal_template(payload, author)
    else:
        payload = code
        for i in range(layers):
            payload = one_layer_encode(payload)
            console.print(f"[cyan]Text layer {i+1}/{layers}[/cyan]")
        out_code = loader_template(payload, author)
    out = Path(src).stem + "_obfuscated.py"
    with open(out, 'w', encoding='utf-8') as f:
        f.write(out_code)
    console.print(f"[green]Saved: {out}[/green]")

def main():
    console.clear()
    console.print(Panel.fit(
        "[bold bright_cyan]🛡️ Universal Python Obfuscator / Decoder[/bold bright_cyan]\n"
        f"v{VERSION} – Made by @ItsMeJeff",
        border_style="bright_cyan"))
    while True:
        console.print()
        t = Table(show_header=False, box=None)
        t.add_row("[bold][1][/bold] Decoder")
        t.add_row("[bold][2][/bold] Obfuscator")
        t.add_row("[bold][3][/bold] Check for updates")
        t.add_row("[bold][4][/bold] Exit")
        console.print(t)
        c = Prompt.ask("Select", choices=["1","2","3","4"], default="1")
        if c == "1":
            decode_menu()
        elif c == "2":
            encrypt_menu()
        elif c == "3":
            self_update(restart=True)
        elif c == "4":
            console.print("[green]Goodbye[/green]")
            sys.exit(0)
        input("\nPress Enter to return to menu...")
        console.clear()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Interrupted[/red]")
        sys.exit(0)
