import os
import psutil
import datetime
from fastapi import APIRouter
from fastapi.responses import HTMLResponse
from .logger_db import get_recent_conversations, get_recent_actions
from .router import check_endpoint
from .config import LM_STUDIO_URL, OLLAMA_LOCAL_URL, GEMINI_API_KEY, ALLOWED_TELEGRAM_USER_IDS

admin_router = APIRouter()

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="fr" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Jarvis Core | Command Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://unpkg.com/vue@3/dist/vue.global.prod.js"></script>
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap" rel="stylesheet">
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <script>
        tailwind.config = {
            darkMode: 'class',
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Plus Jakarta Sans"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        dark: {
                            950: '#07090e',
                            900: '#0b0f19',
                            850: '#111726',
                            800: '#172033',
                            700: '#23304a',
                        },
                        brand: {
                            cyan: '#06b6d4',
                            emerald: '#10b981',
                            violet: '#8b5cf6',
                            amber: '#f59e0b',
                            rose: '#f43f5e'
                        }
                    }
                }
            }
        }
    </script>
    <style>
        ::-webkit-scrollbar { width: 6px; height: 6px; }
        ::-webkit-scrollbar-track { background: #0b0f19; }
        ::-webkit-scrollbar-thumb { background: #23304a; border-radius: 9999px; }
        ::-webkit-scrollbar-thumb:hover { background: #334155; }
        .glass-panel {
            background: rgba(17, 23, 38, 0.75);
            backdrop-filter: blur(12px);
            border: 1px solid rgba(255, 255, 255, 0.07);
        }
    </style>
</head>
<body class="bg-dark-950 text-slate-100 min-h-screen font-sans antialiased selection:bg-brand-cyan/20 selection:text-brand-cyan">
    <div id="app" class="flex flex-col min-h-screen">
        <!-- Top Navigation Bar -->
        <header class="sticky top-0 z-50 glass-panel border-b border-dark-700/60 px-6 py-3.5">
            <div class="max-w-7xl mx-auto flex items-center justify-between">
                <div class="flex items-center space-x-3">
                    <div class="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-cyan to-blue-600 shadow-lg shadow-brand-cyan/20">
                        <i class="fa-solid fa-brain text-white text-lg"></i>
                        <span class="absolute -bottom-0.5 -right-0.5 flex h-3 w-3">
                            <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                            <span class="relative inline-flex rounded-full h-3 w-3 bg-emerald-500"></span>
                        </span>
                    </div>
                    <div>
                        <div class="flex items-center space-x-2">
                            <span class="font-extrabold text-lg tracking-tight bg-clip-text text-transparent bg-gradient-to-r from-white via-slate-200 to-slate-400">JARVIS OS</span>
                            <span class="text-[10px] font-mono font-semibold px-2 py-0.5 rounded-full bg-brand-cyan/10 text-brand-cyan border border-brand-cyan/20">v5.2 HYBRID</span>
                        </div>
                        <p class="text-xs text-slate-400">Homelab Autonomous Agent & Security Hub</p>
                    </div>
                </div>

                <!-- Backends Live Status -->
                <div class="hidden md:flex items-center space-x-3 text-xs">
                    <div :class="backends.lm_studio ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-300' : 'border-slate-800 bg-slate-900/60 text-slate-500'" 
                         class="flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-medium transition-all">
                        <span :class="backends.lm_studio ? 'bg-emerald-400' : 'bg-slate-600'" class="w-2 h-2 rounded-full"></span>
                        <span>Mac (M4 LM Studio)</span>
                    </div>

                    <div :class="backends.gemini ? 'border-blue-500/30 bg-blue-500/10 text-blue-300' : 'border-slate-800 bg-slate-900/60 text-slate-500'" 
                         class="flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-medium transition-all">
                        <span :class="backends.gemini ? 'bg-blue-400' : 'bg-slate-600'" class="w-2 h-2 rounded-full"></span>
                        <span>Gemini Flash (Cloud)</span>
                    </div>

                    <div :class="backends.ollama ? 'border-amber-500/30 bg-amber-500/10 text-amber-300' : 'border-slate-800 bg-slate-900/60 text-slate-500'" 
                         class="flex items-center space-x-2 px-3 py-1.5 rounded-lg border font-medium transition-all">
                        <span :class="backends.ollama ? 'bg-amber-400' : 'bg-slate-600'" class="w-2 h-2 rounded-full"></span>
                        <span>Toshiba (Ollama SLM)</span>
                    </div>
                </div>

                <!-- Live Metrics -->
                <div class="flex items-center space-x-4">
                    <div class="flex items-center space-x-3 bg-dark-900/80 px-3.5 py-1.5 rounded-xl border border-dark-700/80 text-xs font-mono">
                        <div class="flex items-center space-x-1.5">
                            <i class="fa-solid fa-microchip text-slate-400"></i>
                            <span class="text-slate-300">{{ stats.cpu }}%</span>
                        </div>
                        <div class="h-3 w-px bg-dark-700"></div>
                        <div class="flex items-center space-x-1.5">
                            <i class="fa-solid fa-memory text-slate-400"></i>
                            <span class="text-slate-300">{{ stats.ram }}%</span>
                        </div>
                    </div>
                    <button @click="fetchData" class="p-2 rounded-xl bg-dark-850 hover:bg-dark-800 border border-dark-700 text-slate-300 hover:text-white transition">
                        <i :class="loading ? 'fa-spin' : ''" class="fa-solid fa-arrows-rotate text-xs"></i>
                    </button>
                </div>
            </div>
        </header>

        <!-- Main Workspace -->
        <main class="flex-1 max-w-7xl w-full mx-auto p-6 space-y-6">
            <!-- Controls & Filters Toolbar -->
            <div class="flex flex-col sm:flex-row items-center justify-between gap-4 glass-panel p-4 rounded-2xl">
                <!-- Navigation Tabs -->
                <div class="flex items-center space-x-2 bg-dark-900 p-1 rounded-xl border border-dark-700/60 w-full sm:w-auto">
                    <button @click="currentTab = 'timeline'" 
                            :class="currentTab === 'timeline' ? 'bg-dark-800 text-brand-cyan shadow-sm border border-dark-700' : 'text-slate-400 hover:text-slate-200'"
                            class="px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition">
                        <i class="fa-solid fa-stream"></i>
                        <span>Activité & Timeline</span>
                    </button>
                    <button @click="currentTab = 'conversations'" 
                            :class="currentTab === 'conversations' ? 'bg-dark-800 text-brand-cyan shadow-sm border border-dark-700' : 'text-slate-400 hover:text-slate-200'"
                            class="px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition">
                        <i class="fa-solid fa-comments"></i>
                        <span>Conversations ({{ filteredConversations.length }})</span>
                    </button>
                    <button @click="currentTab = 'actions'" 
                            :class="currentTab === 'actions' ? 'bg-dark-800 text-brand-cyan shadow-sm border border-dark-700' : 'text-slate-400 hover:text-slate-200'"
                            class="px-4 py-2 rounded-lg text-xs font-semibold flex items-center space-x-2 transition">
                        <i class="fa-solid fa-terminal"></i>
                        <span>Actions & Outils ({{ filteredActions.length }})</span>
                    </button>
                </div>

                <!-- Search Input -->
                <div class="relative w-full sm:w-72">
                    <i class="fa-solid fa-magnifying-glass absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-500 text-xs"></i>
                    <input v-model="searchQuery" type="text" placeholder="Filtrer les messages, actions..." 
                           class="w-full bg-dark-900 border border-dark-700/70 rounded-xl pl-9 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-cyan/50 focus:ring-1 focus:ring-brand-cyan/50 transition">
                </div>
            </div>

            <!-- VIEW 1: Split Timeline Mode (Dual View) -->
            <div v-if="currentTab === 'timeline'" class="grid grid-cols-1 lg:grid-cols-12 gap-6">
                <!-- Left: Conversations Feed (7 cols) -->
                <section class="lg:col-span-7 flex flex-col space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                            <i class="fa-solid fa-message text-brand-cyan"></i>
                            <span>Dernières Conversations</span>
                        </h2>
                        <span class="text-xs text-slate-500 font-mono">{{ filteredConversations.length }} enregistrements</span>
                    </div>

                    <div class="space-y-4 overflow-y-auto max-h-[750px] pr-1">
                        <div v-if="filteredConversations.length === 0" class="glass-panel rounded-2xl p-8 text-center text-slate-500">
                            <i class="fa-solid fa-inbox text-3xl mb-2 opacity-50"></i>
                            <p class="text-sm">Aucune conversation enregistrée.</p>
                        </div>

                        <article v-for="c in filteredConversations" :key="c.id" 
                                 class="glass-panel rounded-2xl p-5 border border-dark-700/70 hover:border-dark-700 transition space-y-4">
                            <!-- Card Meta Header -->
                            <div class="flex items-center justify-between text-xs">
                                <div class="flex items-center space-x-2">
                                    <span :class="c.source === 'telegram' ? 'bg-blue-500/10 text-blue-400 border-blue-500/20' : 'bg-brand-cyan/10 text-brand-cyan border-brand-cyan/20'"
                                          class="px-2.5 py-0.5 rounded-full border text-[11px] font-semibold flex items-center space-x-1.5">
                                        <i :class="c.source === 'telegram' ? 'fa-brands fa-telegram' : 'fa-solid fa-desktop'"></i>
                                        <span class="capitalize">{{ c.source }}</span>
                                    </span>
                                    <span class="font-mono text-slate-400">UID: {{ c.user_id || 'local' }}</span>
                                </div>
                                <span class="font-mono text-slate-500 text-[11px]">{{ formatDate(c.timestamp) }}</span>
                            </div>

                            <!-- User Prompt -->
                            <div class="bg-dark-900/90 rounded-xl p-3.5 border border-dark-800">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-emerald-400 mb-1 flex items-center space-x-1">
                                    <i class="fa-solid fa-user text-[9px]"></i>
                                    <span>Utilisateur</span>
                                </div>
                                <p class="text-sm text-slate-200 leading-relaxed">{{ c.message_in }}</p>
                            </div>

                            <!-- Jarvis Response -->
                            <div class="bg-dark-850/80 rounded-xl p-3.5 border border-dark-700/60">
                                <div class="text-[10px] font-bold uppercase tracking-wider text-brand-cyan mb-1 flex items-center justify-between">
                                    <span class="flex items-center space-x-1">
                                        <i class="fa-solid fa-robot text-[9px]"></i>
                                        <span>Jarvis</span>
                                    </span>
                                    <span v-if="c.model_used" class="px-2 py-0.5 rounded-md bg-dark-900 text-brand-cyan border border-brand-cyan/20 font-mono text-[10px] font-semibold flex items-center space-x-1">
                                        <i class="fa-solid fa-server text-[8px]"></i>
                                        <span>{{ c.model_used }}</span>
                                    </span>
                                </div>
                                <div class="text-xs text-slate-300 whitespace-pre-wrap leading-relaxed font-sans">{{ c.message_out }}</div>
                            </div>
                        </article>
                    </div>
                </section>

                <!-- Right: Tool Execution Feed (5 cols) -->
                <section class="lg:col-span-5 flex flex-col space-y-4">
                    <div class="flex items-center justify-between">
                        <h2 class="text-sm font-bold uppercase tracking-wider text-slate-400 flex items-center space-x-2">
                            <i class="fa-solid fa-bolt text-brand-amber"></i>
                            <span>Exécution des Outils</span>
                        </h2>
                        <span class="text-xs text-slate-500 font-mono">{{ filteredActions.length }} actions</span>
                    </div>

                    <div class="space-y-4 overflow-y-auto max-h-[750px] pr-1">
                        <div v-if="filteredActions.length === 0" class="glass-panel rounded-2xl p-8 text-center text-slate-500">
                            <i class="fa-solid fa-microchip text-3xl mb-2 opacity-50"></i>
                            <p class="text-sm">Aucun appel d'outil pour l'instant.</p>
                        </div>

                        <article v-for="a in filteredActions" :key="a.id" 
                                 class="glass-panel rounded-2xl p-4 border border-dark-700/70 hover:border-dark-700 transition space-y-3">
                            <div class="flex items-center justify-between text-xs">
                                <div class="flex items-center space-x-2">
                                    <span class="w-2 h-2 rounded-full bg-brand-amber animate-pulse"></span>
                                    <span class="font-mono font-bold text-brand-amber">{{ a.tool_name }}</span>
                                </div>
                                <span class="font-mono text-slate-500 text-[11px]">{{ formatDate(a.timestamp) }}</span>
                            </div>

                            <!-- Tool Arguments -->
                            <div class="bg-dark-950 rounded-xl p-3 border border-dark-800 font-mono text-xs">
                                <div class="text-[10px] text-slate-500 mb-1 uppercase tracking-wider">Arguments</div>
                                <pre class="text-pink-300 overflow-x-auto">{{ formatJson(a.arguments) }}</pre>
                            </div>

                            <!-- Tool Output Result -->
                            <div class="bg-dark-950/80 rounded-xl p-3 border border-dark-800 font-mono text-xs">
                                <div class="text-[10px] text-slate-500 mb-1 uppercase tracking-wider">Résultat / Sortie</div>
                                <pre class="text-emerald-400 overflow-x-auto whitespace-pre-wrap max-h-48">{{ a.result }}</pre>
                            </div>
                        </article>
                    </div>
                </section>
            </div>

            <!-- VIEW 2: Dedicated Conversations Tab -->
            <div v-if="currentTab === 'conversations'" class="space-y-4">
                <article v-for="c in filteredConversations" :key="c.id" class="glass-panel rounded-2xl p-5 border border-dark-700/70 space-y-3">
                    <div class="flex justify-between items-center text-xs text-slate-400">
                        <span class="font-mono">{{ formatDate(c.timestamp) }} • Canal: {{ c.source }}</span>
                        <span class="font-mono text-slate-500">{{ c.model_used }}</span>
                    </div>
                    <div class="bg-dark-900 p-4 rounded-xl text-sm font-medium text-slate-200">
                        <span class="text-emerald-400 text-xs font-bold block mb-1">PROMPT</span>
                        {{ c.message_in }}
                    </div>
                    <div class="bg-dark-850 p-4 rounded-xl text-sm text-slate-300 whitespace-pre-wrap">
                        <span class="text-brand-cyan text-xs font-bold block mb-1">RÉPONSE JARVIS</span>
                        {{ c.message_out }}
                    </div>
                </article>
            </div>

            <!-- VIEW 3: Dedicated Actions Tab -->
            <div v-if="currentTab === 'actions'" class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <article v-for="a in filteredActions" :key="a.id" class="glass-panel rounded-2xl p-5 border border-dark-700/70 space-y-3">
                    <div class="flex justify-between items-center">
                        <span class="font-mono font-bold text-brand-amber text-sm">{{ a.tool_name }}</span>
                        <span class="font-mono text-xs text-slate-500">{{ formatDate(a.timestamp) }}</span>
                    </div>
                    <pre class="bg-dark-950 p-3 rounded-xl font-mono text-xs text-pink-300 overflow-x-auto">{{ formatJson(a.arguments) }}</pre>
                    <pre class="bg-dark-950 p-3 rounded-xl font-mono text-xs text-emerald-400 overflow-x-auto whitespace-pre-wrap max-h-60">{{ a.result }}</pre>
                </article>
            </div>
        </main>
    </div>

    <script>
        const { createApp } = Vue

        createApp({
            data() {
                return {
                    currentTab: 'timeline',
                    searchQuery: '',
                    loading: false,
                    conversations: [],
                    actions: [],
                    backends: {
                        lm_studio: false,
                        gemini: false,
                        ollama: false
                    },
                    stats: { cpu: 0, ram: 0 }
                }
            },
            computed: {
                filteredConversations() {
                    if (!this.searchQuery) return this.conversations
                    const q = this.searchQuery.toLowerCase()
                    return this.conversations.filter(c => 
                        (c.message_in && c.message_in.toLowerCase().includes(q)) ||
                        (c.message_out && c.message_out.toLowerCase().includes(q)) ||
                        (c.source && c.source.toLowerCase().includes(q))
                    )
                },
                filteredActions() {
                    if (!this.searchQuery) return this.actions
                    const q = this.searchQuery.toLowerCase()
                    return this.actions.filter(a => 
                        (a.tool_name && a.tool_name.toLowerCase().includes(q)) ||
                        (a.arguments && a.arguments.toLowerCase().includes(q)) ||
                        (a.result && a.result.toLowerCase().includes(q))
                    )
                }
            },
            mounted() {
                this.fetchData()
                setInterval(this.fetchData, 3500)
            },
            methods: {
                async fetchData() {
                    try {
                        this.loading = true
                        const res = await fetch('/admin/api/data')
                        const data = await res.json()
                        this.conversations = data.conversations
                        this.actions = data.actions
                        this.stats = data.stats
                        this.backends = data.backends
                    } catch (e) {
                        console.error("Dashboard sync error", e)
                    } finally {
                        this.loading = false
                    }
                },
                formatDate(ts) {
                    if (!ts) return ''
                    const d = new Date(ts)
                    return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
                },
                formatJson(str) {
                    try {
                        return JSON.stringify(JSON.parse(str), null, 2)
                    } catch {
                        return str
                    }
                }
            }
        }).mount('#app')
    </script>
</body>
</html>
"""

@admin_router.get("/admin", response_class=HTMLResponse)
async def admin_dashboard():
    return HTMLResponse(content=DASHBOARD_HTML)

@admin_router.get("/admin/api/data")
async def admin_api_data():
    convs = get_recent_conversations(50)
    acts = get_recent_actions(50)
    
    lm_up = await check_endpoint(LM_STUDIO_URL, 1.5)
    ollama_up = await check_endpoint(OLLAMA_LOCAL_URL, 1.5)
    
    return {
        "conversations": convs,
        "actions": acts,
        "backends": {
            "lm_studio": lm_up,
            "gemini": bool(GEMINI_API_KEY),
            "ollama": ollama_up
        },
        "stats": {
            "cpu": psutil.cpu_percent(),
            "ram": psutil.virtual_memory().percent
        }
    }
