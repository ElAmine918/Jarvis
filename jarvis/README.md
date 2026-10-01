# 🎩 Jarvis AI Assistant

![Python Version](https://img.shields.io/badge/Python-3.12-blue)
![Docker](https://img.shields.io/badge/Docker-Enabled-2496ED)
![FastAPI](https://img.shields.io/badge/FastAPI-009688)
![Telegram](https://img.shields.io/badge/Telegram-Bot-2CA5E0)

Jarvis is a personal, multi-backend AI assistant engineered as a British butler ('Monsieur' Amine's aide). It operates through a unified agent architecture accessible via both a Telegram bot and an OpenAI-compatible FastAPI server, built for high availability using a 4-tier LLM failover cascade.

---

## 🏗 Architecture Overview

Jarvis runs two concurrent services powered by an intelligent agent loop capable of executing 18 distinct tools, featuring real-time response streaming and context-aware behavior.

```mermaid
flowchart TD
    User([User])
    User -->|Telegram Bot| Agent
    User -->|Open WebUI| API[FastAPI Server]
    API --> Agent[Jarvis Agent Core]
    
    subgraph LLM Cascade [Multi-Backend LLM Routing]
        Tier1[Tier 1: Gemini Flash]
        Tier2[Tier 2: OpenRouter]
        Tier3[Tier 3: LM Studio LAN]
        Tier4[Tier 4: Ollama Local]
        Tier1 -.Failover.-> Tier2
        Tier2 -.Failover.-> Tier3
        Tier3 -.Failover.-> Tier4
    end
    
    Agent --> LLM Cascade
    
    subgraph Execution [Tool Execution & Memory]
        Tools[18 Sandboxed Tools]
        Memory[(Memory & Logs SQLite)]
        Approvals{Telegram Approvals}
    end
    
    Agent --> Execution
```

## ✨ Key Features

* **Multi-Backend LLM Cascade**: Automatic mid-stream failover across 4 tiers:
  1. Google Gemini Flash (Primary)
  2. OpenRouter (Cloud multi-provider fallback)
  3. LM Studio (Local LAN via Tailscale)
  4. Ollama (Homelab SLM survival mode)
* **Dual Interfaces**: Personal Telegram bot for on-the-go access and an OpenAI-compatible REST API for integration with clients like Open WebUI.
* **Persistent Memory**: SQLite-backed facts and skills retention (`memory.db`), alongside comprehensive token and action logging (`logs.db`).
* **Voice Support**: Integrated STT (Whisper/Gemini) and TTS (edge-tts with French-localized neural voice).
* **Admin Dashboard**: Real-time Vue 3 / Tailwind CSS web interface for monitoring metrics, tokens, and active logs.

## 🛠 Capabilities & Tools

The agent can utilize 18 specialized tools to perform tasks on your behalf:

| Category | Tools | Description |
| :--- | :--- | :--- |
| **System & Files** | `FileSystemTool`, `SystemInfoTool` | Sandboxed file I/O in `/app/workspace` and read-only OS metrics. |
| **Docker** | `DockerTool`, `AdminActionTool` | Container management with strict label whitelisting and human-in-the-loop Telegram approvals. |
| **Web & Info** | `WebReaderTool`, `NewsSearchTool`, `BrowserNavigateTool` | Web scraping, DuckDuckGo news searches, and browser automation. |
| **Agents & Logic** | `SubagentTool`, `AdvisorTool`, `FusionTool`, `PythonREPLTool` | Spawns sub-agents, reaches consensus, and runs sandboxed Python code. |
| **DevOps & Code** | `GitTool`, `ApplyPatchTool` | Git operations and diff patching inside the workspace. |
| **Memory & Data** | `DocumentRAGTool`, `MemoryRecallTool` | Basic document Q&A and historical conversation retrieval. |
| **Misc** | `ImageGenerationTool`, `SchedulerTool` | External image generation and in-memory delayed reminders. |

> **Note**: `ShellTool` is intentionally disabled for security.

## 🛡 Security Model

Jarvis is designed with a defense-in-depth approach:

1. **No Shell Access**: Arbitrary shell command execution is explicitly blocked.
2. **Filesystem Sandboxing**: Operations are restricted to `/app/workspace`. Path traversal attempts are neutralized.
3. **Docker Whitelisting**: Can only manage containers explicitly tagged with the `jarvis.manageable=true` label. Destructive commands (`rm`, `prune`) are disabled.
4. **Human-in-the-Loop**: Privileged actions require explicit asynchronous approval via Telegram inline keyboards.
5. **API & UI Auth**: Protected by constant-time bearer token comparisons and HTTP Basic Auth.
6. **Access Control**: Telegram interactions are restricted to a hardcoded whitelist of User IDs.

## 🚀 Quick Start

Jarvis is designed to run in Docker.

1. **Environment Setup**:
   Copy the environment template located at the **root of the MyCloud repository** (one directory above `jarvis/`) and fill in your API keys.
   ```bash
   cp ../.env.example ../.env
   ```

2. **Launch with Docker Compose**:
   ```bash
   docker-compose up -d --build
   ```

3. **Verify**:
   Send `/status` or `/start` to your Telegram bot, or visit the Admin UI at `http://localhost:8080/admin`.

## ⚙️ Environment Variables

Key variables required in your `.env` file:

| Variable | Description |
| :--- | :--- |
| `TELEGRAM_BOT_TOKEN` | Your Telegram Bot Father token |
| `ALLOWED_TELEGRAM_USER_IDS` | Comma-separated list of permitted User IDs |
| `GEMINI_API_KEY` | Primary Tier 1 LLM key |
| `OPENROUTER_API_KEY` | Tier 2 fallback LLM key |
| `JARVIS_API_KEY` | Bearer token for FastAPI clients (Open WebUI) |
| `ADMIN_PASSWORD` | Password for the Vue 3 Admin Dashboard |

## ⚠️ Known Limitations

* Docker socket is mounted raw (a `docker-socket-proxy` integration is planned).
* API keys are managed via environment variables rather than a dedicated secrets manager.
* The `SchedulerTool` operates in-memory; pending reminders are lost upon container restart.
* RAG capabilities currently rely on plain text truncation and LLM context limits, lacking a true vector database.
* The browser tool is registered, but the underlying Chromium container has been temporarily removed from the architecture.

---

### License
MIT License
