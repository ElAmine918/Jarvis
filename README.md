# 🤖 Jarvis — Agentic AI Assistant

> A self-hosted, highly autonomous AI assistant running on Docker. Jarvis is a multi-backend agentic AI with an automatic failover cascade, advanced memory (PostgreSQL + pgvector), and full DevOps capabilities (Docker, Git, Shell).

---

## 🌟 Overview

Jarvis acts as an autonomous infrastructure manager, researcher, and daily assistant. By interacting with Jarvis via **Telegram** or **Open WebUI**, you can ask it to deploy code, search the web, manage your Docker containers, or synthesize documents using advanced RAG (Retrieval-Augmented Generation).

### Key Features
- **4-Tier LLM Cascade:** Automatically falls back from cloud APIs (Gemini/OpenRouter) to local LLMs (Ollama/LM Studio) if the internet goes down or an API rate limits.
- **Advanced RAG Memory:** Uses PostgreSQL with the `pgvector` extension for semantic hybrid search over your past conversations and documents.
- **DevOps Capabilities:** Can read logs, execute shell commands, manage Git repositories, and control Docker containers.
- **Human-in-the-Loop:** Critical actions (like modifying containers or making destructive system changes) are pushed to Telegram as interactive buttons for your approval before execution.
- **Multi-Agent Consensus:** Can spawn a panel of sub-agents to debate complex problems and synthesize a final answer.
- **Voice Capabilities:** Supports Speech-to-Text and Text-to-Speech via local models or cloud fallback.

## 🏗️ Architecture

```text
                     ┌────────────────────────────────┐
                     │           INTERNET             │
                     └──────▲─────────────────▲───────┘
                            │                 │
                  Telegram / HTTPS    OpenRouter / Gemini APIs
                            │                 │
                            ▼                 ▼
┌───────────────────────────────────────────────────────────┐
│                    DOCKER HOST                            │
│                                                           │
│  ┌─────────────────────────────────────────────────────┐  │
│  │ Docker Compose Stack                                │  │
│  │                                                     │  │
│  │  ├─ jarvis          (Core AI Agent, :8080)          │  │
│  │  ├─ jarvis-live     (LiveKit Voice Agent)           │  │
│  │  ├─ jarvis-pgvector (PostgreSQL + Vector Memory)    │  │
│  │  ├─ open-webui      (Web Chat Interface)            │  │
│  │  ├─ caddy           (Reverse Proxy / HTTPS)         │  │
│  │  └─ docker-proxy    (Security Socket Proxy)         │  │
│  └─────────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────────┘
```

## 🔒 Security & Privacy

- **Private Persona:** The agent's personality is entirely driven by `data/system_prompt.txt`. This file is intentionally `.gitignore`d so you can give your assistant a highly personal, private persona (e.g., a specific character, a personal friend, or an efficient robot) without leaking it to public repositories.
- **Docker Socket Security:** Jarvis does not have raw access to `/var/run/docker.sock`. All commands are routed through an isolated `tecnativa/docker-socket-proxy`.
- **Filesystem Sandbox:** Jarvis is restricted to reading and writing within `/app/workspace/`.
- **Interactive Approvals:** Destructive actions trigger an approval flow on Telegram.

## 🚀 Quick Start

### 1. Prerequisites
- A Docker-compatible host (Linux/Mac/Proxmox)
- A Telegram bot token from [@BotFather](https://t.me/BotFather)
- API Keys (Gemini, OpenRouter, etc.)

### 2. Setup
Clone the repository and prepare your environment:

```bash
git clone https://github.com/YourUsername/Jarvis.git
cd Jarvis

# Configure your environment variables
cp .env.example .env  # (Create this file and add your keys)
nano .env

# Configure the agent's persona (This file remains private)
mkdir -p data
echo "You are a highly efficient and concise AI assistant." > data/system_prompt.txt
```

### 3. Launch
```bash
docker compose up -d --build
```

### 4. Interact
- **Telegram:** Send `/start` to your bot.
- **Web UI:** Navigate to `http://your-server-ip:3000` (or your domain handled by Caddy).

## 📁 Repository Structure

```text
Jarvis/
├── docker-compose.yml     # Orchestration stack
├── Dockerfile             # Agent build instructions
├── Caddyfile              # Reverse proxy configurations
├── requirements.txt       # Python dependencies
├── src/jarvis/            # Core application code
│   ├── core/              # LLM routing, Agent logic, Config
│   ├── interfaces/        # API, Telegram Bot, Voice inputs
│   ├── storage/           # PostgreSQL memory & SQLite logs
│   └── tools/             # 18+ agentic capabilities
├── db/                    # PostgreSQL schemas and backfills
├── tests/                 # Pytest suite
└── scripts/               # Backup and operational shell scripts
```

## 🛠️ Developing & Extending

Jarvis is built with standard Python (FastAPI). Adding a new tool is as simple as creating a new file in `src/jarvis/tools/` that inherits from `Tool` and registers itself. 

To run tests locally:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
PYTHONPATH=src pytest tests/
```

---
**License:** MIT
