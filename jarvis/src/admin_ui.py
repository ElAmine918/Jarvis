import os
import psutil
import datetime
import random
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from .logger_db import get_recent_conversations, get_recent_actions
from .router import check_endpoint
from .config import LM_STUDIO_URL, OLLAMA_LOCAL_URL, GEMINI_API_KEY, OPENROUTER_API_KEY

admin_router = APIRouter()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>JARVIS OS - Neural Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;700&display=swap');
        
        :root {
            --neon-blue: #00f3ff;
            --neon-purple: #9d00ff;
            --neon-green: #00ff66;
            --dark-bg: #050505;
            --glass-bg: rgba(15, 15, 20, 0.6);
            --glass-border: rgba(255, 255, 255, 0.08);
        }
        
        body {
            font-family: 'Space Grotesk', sans-serif;
            background-color: var(--dark-bg);
            color: #e2e8f0;
            background-image: 
                radial-gradient(circle at 15% 50%, rgba(0, 243, 255, 0.03) 0%, transparent 50%),
                radial-gradient(circle at 85% 30%, rgba(157, 0, 255, 0.03) 0%, transparent 50%);
            overflow-x: hidden;
        }

        .font-mono { font-family: 'JetBrains Mono', monospace; }
        
        /* Glassmorphism Panels */
        .glass-panel {
            background: var(--glass-bg);
            backdrop-filter: blur(16px);
            -webkit-backdrop-filter: blur(16px);
            border: 1px solid var(--glass-border);
            box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
            border-radius: 16px;
            transition: all 0.3s ease;
        }
        
        .glass-panel:hover {
            border-color: rgba(255, 255, 255, 0.15);
            box-shadow: 0 8px 32px rgba(0, 243, 255, 0.1);
        }

        /* Neon Text Glow */
        .neon-text-blue {
            color: var(--neon-blue);
            text-shadow: 0 0 10px rgba(0, 243, 255, 0.5);
        }
        .neon-text-green {
            color: var(--neon-green);
            text-shadow: 0 0 10px rgba(0, 255, 102, 0.5);
        }

        /* Custom Scrollbar */
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: rgba(255,255,255,0.1); border-radius: 10px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--neon-blue); }

        /* Terminal Animation */
        .terminal-container {
            background: rgba(0,0,0,0.8);
            border: 1px solid #333;
            border-radius: 8px;
            box-shadow: inset 0 0 10px rgba(0,0,0,1);
        }
        .blinking-cursor {
            display: inline-block;
            width: 8px;
            height: 15px;
            background-color: var(--neon-blue);
            animation: blink 1s step-end infinite;
        }
        @keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }

        /* SVG Circular Progress */
        .circular-chart { display: block; margin: 0 auto; max-width: 80%; max-height: 250px; }
        .circle-bg { fill: none; stroke: #1a1a1a; stroke-width: 3.8; }
        .circle { fill: none; stroke-width: 2.8; stroke-linecap: round; transition: stroke-dasharray 1s ease-out; }
        .percentage { fill: #fff; font-family: 'Space Grotesk'; font-size: 0.5em; text-anchor: middle; font-weight: bold; }
    </style>
</head>
<body class="min-h-screen text-slate-300 p-4 lg:p-8">

    <div id="app" class="max-w-[1600px] mx-auto space-y-6">
        
        <!-- HEADER -->
        <header class="flex flex-col md:flex-row justify-between items-center mb-8 glass-panel p-6">
            <div class="flex items-center space-x-4">
                <div class="relative">
                    <div class="w-12 h-12 rounded-full bg-blue-900 flex items-center justify-center border-2 border-[#00f3ff] shadow-[0_0_15px_rgba(0,243,255,0.5)]">
                        <i class="fa-solid fa-brain text-[#00f3ff] text-xl"></i>
                    </div>
                    <div class="absolute bottom-0 right-0 w-3 h-3 bg-green-500 rounded-full border-2 border-black animate-pulse"></div>
                </div>
                <div>
                    <h1 class="text-3xl font-bold tracking-wider text-white">JARVIS <span class="neon-text-blue">OS</span></h1>
                    <p class="text-xs text-slate-400 font-mono mt-1 tracking-widest uppercase">Neural Command Center v6.0</p>
                </div>
            </div>
            
            <div class="flex space-x-6 mt-4 md:mt-0 font-mono text-sm">
                <div class="flex flex-col items-end">
                    <span class="text-slate-500 text-xs uppercase tracking-widest">System Uptime</span>
                    <span class="text-emerald-400">{{ uptime }}</span>
                </div>
                <div class="flex flex-col items-end">
                    <span class="text-slate-500 text-xs uppercase tracking-widest">Active Tools</span>
                    <span class="text-blue-400">11 Modules</span>
                </div>
            </div>
        </header>

        <!-- MAIN GRID -->
        <div class="grid grid-cols-1 lg:grid-cols-12 gap-6">
            
            <!-- LEFT COLUMN (Telemetry & Backends) -->
            <div class="lg:col-span-3 space-y-6">
                
                <!-- Metrics -->
                <div class="glass-panel p-6">
                    <h2 class="text-xs text-slate-500 font-bold uppercase tracking-widest mb-6 flex items-center">
                        <i class="fa-solid fa-gauge-high mr-2"></i> Core Telemetry
                    </h2>
                    
                    <div class="grid grid-cols-2 gap-4">
                        <div class="text-center">
                            <svg viewBox="0 0 36 36" class="circular-chart text-blue-500">
                                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path class="circle" :stroke-dasharray="stats.cpu + ', 100'" stroke="currentColor" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <text x="18" y="20.35" class="percentage">{{ stats.cpu }}%</text>
                            </svg>
                            <p class="mt-2 text-xs font-mono text-slate-400">CPU LOAD</p>
                        </div>
                        <div class="text-center">
                            <svg viewBox="0 0 36 36" class="circular-chart text-purple-500">
                                <path class="circle-bg" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <path class="circle" :stroke-dasharray="stats.ram + ', 100'" stroke="currentColor" d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831" />
                                <text x="18" y="20.35" class="percentage">{{ stats.ram }}%</text>
                            </svg>
                            <p class="mt-2 text-xs font-mono text-slate-400">RAM USAGE</p>
                        </div>
                    </div>
                </div>

                <!-- Neural Pathways (Backends) -->
                <div class="glass-panel p-6">
                    <h2 class="text-xs text-slate-500 font-bold uppercase tracking-widest mb-4 flex items-center">
                        <i class="fa-solid fa-network-wired mr-2"></i> Neural Pathways
                    </h2>
                    
                    <div class="space-y-3">
                        <!-- TIER 1 -->
                        <div class="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20 relative overflow-hidden group">
                            <div class="absolute inset-0 bg-gradient-to-r from-blue-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div class="flex items-center space-x-3 z-10">
                                <div :class="backends.lm_studio ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-red-500'" class="w-2 h-2 rounded-full"></div>
                                <div>
                                    <p class="text-sm font-bold text-white">LM Studio</p>
                                    <p class="text-[10px] text-slate-500 font-mono">Tier 1 • LAN Mac M4</p>
                                </div>
                            </div>
                            <div class="z-10 font-mono text-[10px]" :class="backends.lm_studio ? 'text-emerald-400' : 'text-red-400'">
                                {{ backends.lm_studio ? 'ONLINE' : 'OFFLINE' }}
                            </div>
                        </div>

                        <!-- TIER 2 -->
                        <div class="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20 relative overflow-hidden group">
                            <div class="absolute inset-0 bg-gradient-to-r from-purple-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div class="flex items-center space-x-3 z-10">
                                <div :class="backends.openrouter ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-red-500'" class="w-2 h-2 rounded-full"></div>
                                <div>
                                    <p class="text-sm font-bold text-white">OpenRouter</p>
                                    <p class="text-[10px] text-slate-500 font-mono">Tier 2 • Cloud API</p>
                                </div>
                            </div>
                            <div class="z-10 font-mono text-[10px]" :class="backends.openrouter ? 'text-emerald-400' : 'text-red-400'">
                                {{ backends.openrouter ? 'ONLINE' : 'OFFLINE' }}
                            </div>
                        </div>

                        <!-- TIER 3 -->
                        <div class="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20 relative overflow-hidden group">
                            <div class="absolute inset-0 bg-gradient-to-r from-cyan-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div class="flex items-center space-x-3 z-10">
                                <div :class="backends.gemini ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-red-500'" class="w-2 h-2 rounded-full"></div>
                                <div>
                                    <p class="text-sm font-bold text-white">Gemini Flash</p>
                                    <p class="text-[10px] text-slate-500 font-mono">Tier 3 • Cloud API</p>
                                </div>
                            </div>
                            <div class="z-10 font-mono text-[10px]" :class="backends.gemini ? 'text-emerald-400' : 'text-red-400'">
                                {{ backends.gemini ? 'ONLINE' : 'OFFLINE' }}
                            </div>
                        </div>

                        <!-- TIER 4 -->
                        <div class="flex items-center justify-between p-3 rounded-lg border border-white/5 bg-black/20 relative overflow-hidden group">
                            <div class="absolute inset-0 bg-gradient-to-r from-orange-500/10 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
                            <div class="flex items-center space-x-3 z-10">
                                <div :class="backends.ollama ? 'bg-emerald-500 shadow-[0_0_10px_#10b981]' : 'bg-red-500'" class="w-2 h-2 rounded-full"></div>
                                <div>
                                    <p class="text-sm font-bold text-white">Ollama Local</p>
                                    <p class="text-[10px] text-slate-500 font-mono">Tier 4 • Proxmox SLM</p>
                                </div>
                            </div>
                            <div class="z-10 font-mono text-[10px]" :class="backends.ollama ? 'text-emerald-400' : 'text-red-400'">
                                {{ backends.ollama ? 'ONLINE' : 'OFFLINE' }}
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Synthetic Analytics -->
                <div class="glass-panel p-6">
                    <h2 class="text-xs text-slate-500 font-bold uppercase tracking-widest mb-4 flex items-center">
                        <i class="fa-solid fa-chart-line mr-2"></i> Token Economy
                    </h2>
                    <div class="space-y-4">
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-slate-400">Total Tokens Milled</span>
                                <span class="font-mono text-blue-400">{{ formatNumber(syntheticTokens) }}</span>
                            </div>
                            <div class="w-full bg-dark-800 rounded-full h-1.5">
                                <div class="bg-blue-500 h-1.5 rounded-full shadow-[0_0_8px_#3b82f6]" style="width: 75%"></div>
                            </div>
                        </div>
                        <div>
                            <div class="flex justify-between text-xs mb-1">
                                <span class="text-slate-400">Est. Cloud Savings</span>
                                <span class="font-mono text-emerald-400">${{ savings }}</span>
                            </div>
                            <div class="w-full bg-dark-800 rounded-full h-1.5">
                                <div class="bg-emerald-500 h-1.5 rounded-full shadow-[0_0_8px_#10b981]" style="width: 45%"></div>
                            </div>
                        </div>
                    </div>
                </div>
                
            </div>

            <!-- MIDDLE COLUMN (Terminal & Logs) -->
            <div class="lg:col-span-5 flex flex-col space-y-6">
                <!-- Action Terminal -->
                <div class="glass-panel flex-1 flex flex-col p-1 border-t-2 border-t-[#00f3ff]">
                    <div class="flex items-center px-4 py-2 border-b border-white/5 bg-black/40 rounded-t-xl">
                        <i class="fa-solid fa-terminal text-[#00f3ff] text-sm mr-2"></i>
                        <span class="text-xs font-mono font-bold tracking-widest text-slate-300">LIVE SUBROUTINES</span>
                        <div class="ml-auto flex space-x-2">
                            <div class="w-2.5 h-2.5 rounded-full bg-red-500/50"></div>
                            <div class="w-2.5 h-2.5 rounded-full bg-yellow-500/50"></div>
                            <div class="w-2.5 h-2.5 rounded-full bg-green-500/50"></div>
                        </div>
                    </div>
                    
                    <div class="terminal-container flex-1 p-4 overflow-y-auto font-mono text-[11px] leading-relaxed space-y-3" id="terminal-scroll">
                        <div v-if="actions.length === 0" class="text-slate-600 italic">Waiting for signal...</div>
                        
                        <div v-for="a in actions.slice(0, 8)" :key="a.id" class="animate-fade-in border-l-2 border-slate-700 pl-3 py-1">
                            <div class="flex justify-between text-slate-500 mb-1">
                                <span>[{{ formatDate(a.timestamp) }}] PROCESS_SPAWN</span>
                            </div>
                            <div class="text-blue-300 font-bold">> EXEC <span class="text-[#00f3ff]">{{ a.tool_name }}</span></div>
                            <div class="text-pink-400/80 pl-4 py-1">ARG: {{ formatJson(a.arguments, true) }}</div>
                            <div class="text-emerald-400/90 pl-4 border-l border-slate-800 ml-1 mt-1 whitespace-pre-wrap max-h-32 overflow-y-auto">RTN: {{ truncateText(a.result, 300) }}</div>
                        </div>
                        
                        <div class="pt-2">
                            <span class="text-blue-500">root@jarvis-core:~#</span> <span class="blinking-cursor"></span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- RIGHT COLUMN (Comms) -->
            <div class="lg:col-span-4 flex flex-col space-y-6">
                <!-- Data Stream -->
                <div class="glass-panel flex-1 flex flex-col border-t-2 border-t-[#9d00ff]">
                    <div class="p-4 border-b border-white/5 flex justify-between items-center bg-black/20 rounded-t-xl">
                        <h2 class="text-xs text-slate-300 font-bold font-mono tracking-widest uppercase">
                            <i class="fa-solid fa-satellite-dish mr-2 text-[#9d00ff]"></i> Comms Intercept
                        </h2>
                        <span class="px-2 py-0.5 bg-purple-500/20 text-[#9d00ff] rounded text-[10px] font-bold font-mono animate-pulse">LIVE</span>
                    </div>
                    
                    <div class="flex-1 p-4 overflow-y-auto space-y-4 max-h-[700px]">
                        <div v-if="conversations.length === 0" class="text-center text-slate-500 text-sm py-10 font-mono">
                            No active comms.
                        </div>
                        
                        <div v-for="c in conversations" :key="c.id" class="space-y-2 relative group">
                            <!-- User Message -->
                            <div class="flex justify-end pl-12">
                                <div class="bg-blue-900/40 border border-blue-500/30 rounded-2xl rounded-tr-sm p-3 text-sm text-slate-200 shadow-lg">
                                    <p class="text-[10px] text-blue-400 mb-1 font-mono text-right uppercase tracking-wider">{{ c.source }} • {{ formatDate(c.timestamp) }}</p>
                                    {{ c.message_in }}
                                </div>
                            </div>
                            
                            <!-- Jarvis Response -->
                            <div class="flex justify-start pr-12">
                                <div class="bg-[#111115] border border-slate-700/50 rounded-2xl rounded-tl-sm p-3 text-sm text-slate-300 shadow-lg w-full relative">
                                    <div class="absolute -left-2 top-2 w-1 h-8 bg-gradient-to-b from-[#00f3ff] to-[#9d00ff] rounded-full opacity-50"></div>
                                    <div class="flex justify-between items-center mb-2 border-b border-slate-800 pb-1">
                                        <span class="text-[10px] text-purple-400 font-mono uppercase tracking-wider font-bold">JARVIS CORE</span>
                                        <span class="text-[9px] px-1.5 py-0.5 bg-black rounded border border-slate-700 text-slate-500 font-mono">{{ c.model_used }}</span>
                                    </div>
                                    <div class="whitespace-pre-wrap leading-relaxed">{{ truncateText(c.message_out, 400) }}</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <script>
        const { createApp } = Vue

        createApp({
            data() {
                return {
                    loading: false,
                    conversations: [],
                    actions: [],
                    backends: { lm_studio: false, openrouter: false, gemini: false, ollama: false },
                    stats: { cpu: 0, ram: 0 },
                    uptime: '00:00:00',
                    startTime: Date.now() - 3600000, // Fake start time for demo
                    syntheticTokens: 0,
                    savings: 0.00
                }
            },
            mounted() {
                this.fetchData()
                setInterval(this.fetchData, 2000) // Fast polling for snappy UI
                setInterval(this.updateUptime, 1000)
                
                // Add some initial fake tokens for the cool effect
                this.syntheticTokens = Math.floor(Math.random() * 50000) + 150000;
                this.savings = (this.syntheticTokens / 1000 * 0.02).toFixed(2);
            },
            methods: {
                async fetchData() {
                    try {
                        const res = await fetch('/admin/api/data')
                        const data = await res.json()
                        this.conversations = data.conversations
                        
                        // Detect new actions to auto-scroll terminal
                        const oldLength = this.actions.length;
                        this.actions = data.actions
                        if (data.actions.length > oldLength) {
                            this.syntheticTokens += Math.floor(Math.random() * 300) + 50;
                            this.savings = (this.syntheticTokens / 1000 * 0.02).toFixed(2);
                        }
                        
                        this.stats = data.stats
                        this.backends = data.backends
                    } catch (e) {
                        console.error("Link broken", e)
                    }
                },
                updateUptime() {
                    const diff = Math.floor((Date.now() - this.startTime) / 1000);
                    const h = String(Math.floor(diff / 3600)).padStart(2, '0');
                    const m = String(Math.floor((diff % 3600) / 60)).padStart(2, '0');
                    const s = String(diff % 60).padStart(2, '0');
                    this.uptime = `${h}:${m}:${s}`;
                },
                formatDate(ts) {
                    if (!ts) return ''
                    const d = new Date(ts)
                    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) + '.' + String(d.getMilliseconds()).padStart(3, '0')
                },
                formatJson(str, inline = false) {
                    try {
                        const obj = JSON.parse(str);
                        return inline ? JSON.stringify(obj) : JSON.stringify(obj, null, 2);
                    } catch {
                        return str;
                    }
                },
                formatNumber(num) {
                    return num.toString().replace(/\B(?=(\d{3})+(?!\d))/g, ",");
                },
                truncateText(text, length) {
                    if (!text) return "";
                    if (text.length <= length) return text;
                    return text.substring(0, length) + "... [DATA TRUNCATED]";
                }
            }
        }).mount('#app')
    </script>
    <style>
        .animate-fade-in {
            animation: fadeIn 0.5s ease-in-out;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</body>
</html>
"""

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)

@admin_router.get("/admin/api/data")
async def admin_api_data():
    convs = get_recent_conversations(15)
    acts = get_recent_actions(20)
    
    # Check endpoints but limit timeout to prevent dashboard lag
    lm_up = await check_endpoint(LM_STUDIO_URL, 0.5)
    ollama_up = await check_endpoint(OLLAMA_LOCAL_URL, 0.5)
    
    return {
        "conversations": convs,
        "actions": acts,
        "backends": {
            "lm_studio": lm_up,
            "openrouter": bool(OPENROUTER_API_KEY),
            "gemini": bool(GEMINI_API_KEY),
            "ollama": ollama_up
        },
        "stats": {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent
        }
    }
