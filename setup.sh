#!/bin/bash
# ══════════════════════════════════════════════════════
#  JARVIS Cybersecurity AI — Setup Script
#  Tested on Ubuntu 22.04 / Debian 12 / Kali Linux
# ══════════════════════════════════════════════════════

set -e
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ╔═══════════════════════════════════════╗"
echo "  ║     JARVIS — CYBERSECURITY AI         ║"
echo "  ║         Setup & Installation          ║"
echo "  ╚═══════════════════════════════════════╝"
echo -e "${NC}"

# ─── 1. System deps ───────────────────────────
echo -e "${GREEN}[1/6] Installing system packages...${NC}"
sudo apt-get update -qq
sudo apt-get install -y -qq \
    python3-pip python3-venv \
    portaudio19-dev python3-pyaudio \
    espeak espeak-data \
    ffmpeg \
    curl wget git \
    nmap netcat-openbsd \
    binwalk exiftool \
    steghide 2>/dev/null || true

# ─── 2. Python venv ───────────────────────────
echo -e "${GREEN}[2/6] Creating Python virtual environment...${NC}"
python3 -m venv venv
source venv/bin/activate

# ─── 3. Python packages ───────────────────────
echo -e "${GREEN}[3/6] Installing Python packages...${NC}"
pip install --upgrade pip -q
pip install \
    gradio \
    faster-whisper \
    sounddevice \
    numpy \
    requests \
    pyaudio \
    openwakeword \
    onnxruntime 2>/dev/null || \
pip install \
    gradio \
    faster-whisper \
    sounddevice \
    numpy \
    requests

echo -e "${YELLOW}  ℹ Optional: pip install openwakeword onnxruntime${NC}"

# ─── 4. Ollama ────────────────────────────────
echo -e "${GREEN}[4/6] Installing Ollama...${NC}"
if ! command -v ollama &> /dev/null; then
    curl -fsSL https://ollama.com/install.sh | sh
    echo "✅ Ollama installed"
else
    echo "✅ Ollama already installed"
fi

# Start ollama service
ollama serve &>/dev/null &
sleep 3

# Pull recommended model
echo -e "${GREEN}    Pulling qwen2.5 model (good for cybersecurity)...${NC}"
echo -e "${YELLOW}    This may take a few minutes on first run...${NC}"
ollama pull qwen2.5 || echo "⚠️  Pull failed — run 'ollama pull qwen2.5' manually"

# ─── 5. Piper TTS (optional) ──────────────────
echo -e "${GREEN}[5/6] Installing Piper TTS (optional, better voice)...${NC}"
PIPER_URL="https://github.com/rhasspy/piper/releases/latest/download/piper_linux_x86_64.tar.gz"
if ! command -v piper &> /dev/null; then
    wget -q "$PIPER_URL" -O /tmp/piper.tar.gz && \
    tar -xzf /tmp/piper.tar.gz -C /usr/local/bin/ 2>/dev/null && \
    echo "✅ Piper installed" || \
    echo "⚠️  Piper install failed — will use espeak fallback"

    # Download voice model
    mkdir -p ~/.local/share/piper
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx" \
        -O ~/.local/share/piper/en_US-lessac-medium.onnx 2>/dev/null || true
    wget -q "https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/lessac/medium/en_US-lessac-medium.onnx.json" \
        -O ~/.local/share/piper/en_US-lessac-medium.onnx.json 2>/dev/null || true
else
    echo "✅ Piper already installed"
fi

# ─── 6. Done ──────────────────────────────────
echo -e "${GREEN}[6/6] Setup complete!${NC}"
echo ""
echo -e "${CYAN}══════════════════════════════════════════${NC}"
echo -e "${CYAN}  JARVIS is ready! Start with:${NC}"
echo ""
echo -e "  ${YELLOW}source venv/bin/activate${NC}"
echo -e "  ${YELLOW}python jarvis_ui.py${NC}      ← Web UI (recommended)"
echo -e "  ${YELLOW}python jarvis_core.py${NC}    ← CLI mode"
echo ""
echo -e "  Web UI: ${CYAN}http://localhost:7860${NC}"
echo ""
echo -e "  Optional models to pull:"
echo -e "  ${YELLOW}ollama pull deepseek-r1${NC}  ← Best reasoning"
echo -e "  ${YELLOW}ollama pull llama3.2${NC}     ← Fast general"
echo -e "  ${YELLOW}ollama pull qwen2.5-coder${NC} ← Best for code/exploits"
echo -e "${CYAN}══════════════════════════════════════════${NC}"
