# ☁️ MyCloud — Personal AI Infrastructure

> Self-hosted AI assistant stack running on a hybrid homelab (Proxmox + Mac + Cloud), orchestrated by **Jarvis** — a multi-backend agentic AI with automatic failover.

---

## 🏗️ Architecture

```text
                     ┌────────────────────────────────┐
                     │           INTERNET              │
                     └──────▲─────────────────▲────────┘
                            │                 │
                  Telegram / HTTPS    OpenRouter / Gemini APIs
                            │                 │
                            ▼                 ▼
┌───────────────────────────────────────────┐    ┌──────────────────────────┐
│  TOSHIBA LAPTOP (Proxmox VE 8 Server)    │    │  MAC M4 (Dev Machine)    │
│  Intel i7-4700MQ · 16 GB DDR3            │    │  Tailscale VPN           │
│                                           │    │  LM Studio (port 1234)   │
│  ┌─────────────────────────────────────┐ │    └──────────▲───────────────┘
│  │ LXC 100 (Ubuntu 24.04)              │ │               │
│  │                                     │◄┴───────────────┘
│  │  Docker Services:                   │     Tailscale Mesh
│  │  ├─ jarvis       (AI Agent, :8080)  │
│  │  ├─ open-webui   (Chat UI, :3000)   │
│  │  ├─ caddy        (Reverse Proxy)    │
│  │  ├─ docker-proxy (Socket Security)  │
│  │  ├─ ollama       (Local SLM)        │
│  │  ├─ chromium     (Headless Browser) │
│  │  └─ portainer    (Docker Dashboard) │
│  └─────────────────────────────────────┘ │
└───────────────────────────────────────────┘
```

## 🧠 Jarvis AI Agent

The core of the project. A personal AI assistant with a British butler persona, 18 sandboxed tools, and a 4-tier LLM failover cascade ensuring 24/7 availability.

**→ See [`jarvis/README.md`](jarvis/README.md) for full documentation.**

### LLM Cascade (Priority Order)

| Tier | Backend | Type | Default Model |
|------|---------|------|---------------|
| 1 | **Gemini Flash** | Cloud (Google) | `gemini-2.0-flash` |
| 2 | **OpenRouter** | Cloud (Multi-provider) | `qwen/qwen3.8-27b:free` |
| 3 | **LM Studio** | Local LAN (Mac M4) | `qwen2.5-14b-instruct` |
| 4 | **Ollama** | Local Homelab (Toshiba) | `qwen2.5:7b` |

If a backend fails mid-stream, the agent automatically cascades to the next tier.

### Interfaces

- **Telegram Bot** — Personal mobile interface with command system (`/status`, `/backend`, `/skills`, `/test_tiers`)
- **Open WebUI** — Full-featured web chat UI (OpenAI-compatible API)
- **Admin Dashboard** — Vue 3 real-time monitoring panel at `/admin`
- **CLI Monitor** — Terminal TUI dashboard (Rich-based, 2 FPS live refresh)

### Key Capabilities

| Category | Tools |
|----------|-------|
| System & Files | Sandboxed filesystem, system metrics, Docker management |
| Web & Research | Web scraping, news search, headless browser |
| AI & Logic | Sub-agents, advisor panel, consensus fusion, Python REPL |
| DevOps | Git operations, diff patching, document RAG |
| Communication | Telegram reminders, human-in-the-loop approvals |
| Media | Image generation, voice STT/TTS |

## 🔒 Security

- **Docker Socket Proxy** — Jarvis never touches the raw Docker socket. All Docker operations go through `tecnativa/docker-socket-proxy` on an isolated internal network.
- **Container Hardening** — `no-new-privileges`, `cap_drop: ALL` (only `SETUID`/`SETGID` for user switching).
- **Label Whitelisting** — Only containers with `jarvis.manageable=true` can be managed. All infrastructure containers are explicitly `false`.
- **Filesystem Sandbox** — Agent can only read/write within `/app/workspace`.
- **Shell Disabled** — No arbitrary command execution.
- **Approval Workflow** — Critical Docker actions require interactive Telegram approval (inline keyboard).

## 🚀 Quick Start

### Prerequisites
- Proxmox VE server (or any Docker host)
- Tailscale (optional, for Mac LM Studio access)
- Telegram bot token from [@BotFather](https://t.me/BotFather)

### Setup

```bash
# Clone the repo
git clone https://github.com/ElAmine918/MyCloud.git
cd MyCloud

# Configure environment
cp .env.example .env
# Edit .env with your API keys and tokens

# Launch everything
docker compose up -d --build
```

### Verify
- Send `/start` to your Telegram bot
- Visit Open WebUI at `http://your-server:3000`
- Access Admin Dashboard at `http://your-server:8080/admin`

## 📁 Repository Structure

```
MyCloud/
├── .env.example           # Environment variable template
├── docker-compose.yml     # Full service stack (7 containers)
├── Caddyfile              # Reverse proxy configuration
├── HANDOVER.md            # Technical handover document
├── jarvis/                # AI Agent source code
│   ├── README.md          # Detailed agent documentation
│   ├── Dockerfile         # Multi-stage Python 3.12 build
│   ├── requirements.txt   # Python dependencies
│   ├── src/               # Application source (~3,750 LOC)
│   ├── tests/             # Security adversarial tests
│   └── skills/            # Skills system docs
└── setup/                 # Infrastructure provisioning
    ├── README.md           # Setup guide
    ├── create-lxc.sh       # Proxmox LXC creation script
    └── install-docker.sh   # Docker installation script
```

## 📖 Documentation

| Document | Description |
|----------|-------------|
| [`jarvis/README.md`](jarvis/README.md) | Agent architecture, tools, security model |
| [`HANDOVER.md`](HANDOVER.md) | Full technical handover (infrastructure, deployment, pitfalls) |
| [`setup/README.md`](setup/README.md) | Infrastructure provisioning guide |
| [`.env.example`](.env.example) | Complete environment variable reference |

---

**License**: MIT
