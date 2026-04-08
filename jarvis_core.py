"""
JARVIS - Cybersecurity AI Assistant
Core Engine: STT → LLM → TTS with tool use
"""

import os
import json
import subprocess
import threading
import queue
import tempfile
import time
import re
import requests
from pathlib import Path

# ──────────────────────────────────────────────
# CONFIGURATION
# ──────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5:latest")  # change to deepseek-r1 etc.

SYSTEM_PROMPT = """You are JARVIS, an elite cybersecurity AI assistant built for ethical hacking, CTF challenges, and security research. You are running fully locally and privately.

Your capabilities:
- CTF challenge solving (web, pwn, crypto, forensics, reversing, OSINT, steganography)
- Penetration testing methodology (for authorized systems and practice labs)
- Vulnerability analysis and exploit development (educational)
- Malware analysis and reverse engineering
- Network analysis and packet inspection
- Cryptography and decryption
- Tool usage: nmap, metasploit, burpsuite, gobuster, sqlmap, john, hashcat, ghidra, etc.
- Write scripts in Python, Bash, C for security research
- Explain CVEs, attack techniques, and defenses

Rules:
- You assist with ethical hacking, CTFs, authorized pentests, and security research ONLY
- You do NOT assist with attacking systems the user does not own or have permission to test
- You are educational, thorough, and provide working code/commands

Always respond in a concise, technical manner befitting an elite security assistant.
When given a CTF challenge, think step by step: enumerate, identify, exploit, capture flag."""

# ──────────────────────────────────────────────
# TOOL DEFINITIONS
# ──────────────────────────────────────────────
TOOLS = {
    "run_command": {
        "description": "Run a shell command (nmap, gobuster, hashcat, python scripts, etc.)",
        "params": ["command"]
    },
    "web_search": {
        "description": "Search the web for CVEs, writeups, tool documentation",
        "params": ["query"]
    },
    "read_file": {
        "description": "Read a file from disk (captured flags, challenge files, configs)",
        "params": ["path"]
    },
    "write_file": {
        "description": "Write content to a file (scripts, payloads, notes)",
        "params": ["path", "content"]
    },
    "decode": {
        "description": "Decode/encode: base64, hex, rot13, url, morse, binary",
        "params": ["text", "encoding"]
    }
}


def run_tool(tool_name: str, params: dict) -> str:
    try:
        if tool_name == "run_command":
            cmd = params.get("command", "")
            # Safety: block obviously dangerous commands
            blocked = ["rm -rf /", "mkfs", "dd if=/dev/zero of=/dev/sd"]
            if any(b in cmd for b in blocked):
                return "⛔ Blocked: potentially destructive command."
            result = subprocess.run(
                cmd, shell=True, capture_output=True, text=True, timeout=30
            )
            out = result.stdout + result.stderr
            return out[:3000] if out else "(no output)"

        elif tool_name == "web_search":
            query = params.get("query", "")
            resp = requests.get(
                "https://ddg-webapp-aagd.vercel.app/search",
                params={"q": query, "max_results": 5},
                timeout=10
            )
            results = resp.json()
            return "\n".join([f"{r['title']}: {r['href']}\n{r.get('body','')[:200]}" for r in results[:5]])

        elif tool_name == "read_file":
            path = params.get("path", "")
            return Path(path).read_text(errors="replace")[:5000]

        elif tool_name == "write_file":
            path = params.get("path", "")
            content = params.get("content", "")
            Path(path).write_text(content)
            return f"✅ Written to {path}"

        elif tool_name == "decode":
            text = params.get("text", "")
            enc = params.get("encoding", "").lower()
            import base64, urllib.parse, codecs
            if enc == "base64":
                return base64.b64decode(text).decode(errors="replace")
            elif enc == "hex":
                return bytes.fromhex(text.replace(" ", "")).decode(errors="replace")
            elif enc == "rot13":
                return codecs.encode(text, "rot_13")
            elif enc == "url":
                return urllib.parse.unquote(text)
            elif enc == "binary":
                parts = text.split()
                return "".join(chr(int(b, 2)) for b in parts)
            elif enc == "morse":
                MORSE = {'.-':'A','-...':'B','-.-.':'C','-..':'D','.':'E','..-.':'F','--.':'G','....':'H','..':'I','.---':'J','-.-':'K','.-..':'L','--':'M','-.':'N','---':'O','.--.':'P','--.-':'Q','.-.':'R','...':'S','-':'T','..-':'U','...-':'V','.--':'W','-..-':'X','-.--':'Y','--..':'Z','-----':'0','.----':'1','..---':'2','...--':'3','....-':'4','.....':'5','-....':'6','--...':'7','---..':'8','----.':'9'}
                return "".join(MORSE.get(w, "?") for w in text.split())
            else:
                return f"Unknown encoding: {enc}"
    except Exception as e:
        return f"Tool error: {e}"


# ──────────────────────────────────────────────
# LLM ENGINE
# ──────────────────────────────────────────────
class JarvisLLM:
    def __init__(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

    def chat(self, user_msg: str, on_token=None) -> str:
        self.history.append({"role": "user", "content": user_msg})

        # Build messages with tool info injected — do NOT mutate self.history
        tool_str = json.dumps(TOOLS, indent=2)
        system_with_tools = SYSTEM_PROMPT + f"""

AVAILABLE TOOLS (call by including JSON in your response):
{tool_str}

To use a tool, include this EXACTLY in your response:
<tool>
{{"name": "tool_name", "params": {{"key": "value"}}}}
</tool>

After the tool runs, you'll see the result and can continue.
"""
        messages = [{"role": "system", "content": system_with_tools}] + self.history[1:]

        full_response = ""
        try:
            resp = requests.post(OLLAMA_URL, json={
                "model": OLLAMA_MODEL,
                "messages": messages,
                "stream": True
            }, stream=True, timeout=120)

            resp.raise_for_status()

            for line in resp.iter_lines():
                if line:
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = chunk.get("message", {}).get("content", "")
                    if token:
                        full_response += token
                        if on_token:
                            on_token(token)
                    if chunk.get("done"):
                        break

            if not full_response:
                full_response = "⚠️ Empty response from Ollama. Try again."

            # Handle tool calls
            tool_matches = re.findall(r"<tool>(.*?)</tool>", full_response, re.DOTALL)
            if tool_matches:
                tool_results = []
                for match in tool_matches:
                    try:
                        tool_call = json.loads(match.strip())
                        result = run_tool(tool_call["name"], tool_call.get("params", {}))
                        tool_results.append(f"[Tool: {tool_call['name']}]\n{result}")
                    except Exception as e:
                        tool_results.append(f"[Tool error: {e}]")

                combined = full_response + "\n\nTool Results:\n" + "\n\n".join(tool_results)
                self.history.append({"role": "assistant", "content": combined})
                followup = self.chat("Continue based on the tool results above.", on_token)
                return followup

            self.history.append({"role": "assistant", "content": full_response})
            return full_response

        except requests.exceptions.ConnectionError:
            err = "❌ Cannot connect to Ollama. Make sure it's running: `ollama serve`"
            if on_token: on_token(err)
            return err
        except Exception as e:
            err = f"❌ LLM Error: {e}"
            if on_token: on_token(err)
            return err

    def reset(self):
        self.history = [{"role": "system", "content": SYSTEM_PROMPT}]

# ──────────────────────────────────────────────
# MAIN ASSISTANT LOOP (CLI mode)
# ──────────────────────────────────────────────
class JarvisAssistant:
    def __init__(self):
        self.llm = JarvisLLM()

    def process(self, user_input: str, on_token=None) -> str:
        return self.llm.chat(user_input, on_token=on_token)

    def run_cli(self):
        print("\n" + "="*60)
        print("  🛡️  JARVIS - Cybersecurity AI Assistant")
        print("  Type 'voice' to enable voice mode")
        print("  Type 'reset' to clear conversation")
        print("  Type 'exit' to quit")
        print("="*60 + "\n")

        while True:
            try:
                user_input = input("👤 You: ").strip()
                if not user_input:
                    continue
                if user_input.lower() == "exit":
                    break
                if user_input.lower() == "reset":
                    self.llm.reset()
                    print("🔄 Conversation reset.")
                    continue

                print("🤖 JARVIS: ", end="", flush=True)
                response = self.process(user_input, on_token=lambda t: print(t, end="", flush=True))
                print()

            except KeyboardInterrupt:
                print("\n👋 JARVIS offline.")
                break


if __name__ == "__main__":
    assistant = JarvisAssistant()
    assistant.run_cli()