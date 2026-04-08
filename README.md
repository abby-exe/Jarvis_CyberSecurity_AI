# 🛡️ JARVIS — Local Cybersecurity AI Assistant

A fully local, private AI assistant built for ethical hacking, CTF solving, and cybersecurity learning.

## Architecture

```
Microphone → Whisper STT → Ollama LLM → Piper TTS → Speaker
                 ↓               ↓
           Wake Word         Tool Use
          (OpenWakeWord)  (nmap, shell, decode, search...)
                 ↓
            Gradio Web UI (http://localhost:7860)
```

## Quick Start

```bash
chmod +x setup.sh
./setup.sh
source venv/bin/activate
python jarvis_ui.py
```

Open → http://localhost:7860

## Manual Installation

### 1. Install Ollama + model
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5          # recommended
ollama pull deepseek-r1      # best reasoning for CTFs
ollama pull qwen2.5-coder    # best for exploit dev
```

### 2. Python deps
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. Piper TTS (optional — better voice)
```bash
# Download from: https://github.com/rhasspy/piper/releases
# Then download voice model:
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx
```

### 4. Run
```bash
python jarvis_ui.py     # Web UI
python jarvis_core.py   # CLI only
```

## Environment Variables

| Variable | Default | Description |
|---|---|---|
| `OLLAMA_MODEL` | `qwen2.5` | Which Ollama model to use |
| `WHISPER_MODEL` | `base` | Whisper size: tiny/base/small/medium |
| `TTS_VOICE` | `en_US-lessac-medium` | Piper voice model |

## Features

- **Voice Chat** — Say "Jarvis" to wake, then ask your question
- **CTF Templates** — One-click prompts for web, crypto, pwn, forensics, reversing
- **Tool Use** — AI can run shell commands, search the web, read/write files, decode data
- **Direct Tool Panel** — Run nmap, hashcat, gobuster etc. directly from the UI
- **Quick Reference** — Always-visible cheatsheet for common commands
- **Multi-model** — Switch between Ollama models live

## Built-in Tools

| Tool | What it does |
|---|---|
| `run_command` | Execute shell commands (nmap, sqlmap, hashcat...) |
| `web_search` | Search for CVEs, writeups, documentation |
| `read_file` | Read challenge files from disk |
| `write_file` | Save scripts, payloads, notes |
| `decode` | Base64, hex, rot13, URL, binary, morse |

## Recommended Models

| Model | Best for |
|---|---|
| `qwen2.5` | General cybersecurity, good balance |
| `deepseek-r1` | Complex CTF reasoning, step-by-step |
| `qwen2.5-coder` | Exploit dev, script writing |
| `llama3.2` | Fast responses, general use |
| `mistral` | Lightweight, fast on CPU |

## Legal Notice

This tool is for **ethical hacking only**:
- Your own systems
- CTF challenges (HackTheBox, TryHackMe, PicoCTF, etc.)
- Authorized penetration testing engagements
- Security research in controlled lab environments

Do not use against systems you don't own or have explicit written permission to test.
