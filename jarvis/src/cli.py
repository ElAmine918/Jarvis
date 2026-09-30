#!/usr/bin/env python3
import time
import os
import sqlite3
from collections import defaultdict
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich import box
from rich.text import Text
from rich.align import Align

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "logs.db")
console = Console()

def fetch_stats():
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        
        # Token usage
        tokens = conn.execute("SELECT model_name, SUM(tokens) as total FROM token_usage GROUP BY model_name").fetchall()
        token_data = {t["model_name"]: t["total"] for t in tokens}
        
        # Latest actions
        actions = conn.execute("SELECT * FROM actions ORDER BY timestamp DESC LIMIT 5").fetchall()
        
        # Threads
        threads = conn.execute("SELECT session_id, count(*) as c, max(timestamp) as ts FROM conversations GROUP BY session_id ORDER BY ts DESC LIMIT 5").fetchall()
        
        conn.close()
        return token_data, actions, threads
    except Exception:
        return {}, [], []

def generate_layout():
    tokens, actions, threads = fetch_stats()
    
    # Token Chart
    table_tokens = Table(box=box.SIMPLE, expand=True)
    table_tokens.add_column("Modèle (IA)", style="cyan")
    table_tokens.add_column("Tokens (Total)", justify="right", style="magenta")
    table_tokens.add_column("Coût Estimé", justify="right", style="green")
    
    total_t = 0
    for model, count in tokens.items():
        total_t += count
        cost = (count / 1000) * 0.002 # Fake average pricing
        table_tokens.add_row(model, f"{count:,}", f"${cost:.4f}")
    table_tokens.add_row("[bold]TOTAL[/bold]", f"[bold]{total_t:,}[/bold]", f"[bold]${(total_t/1000)*0.002:.4f}[/bold]")
    
    # Actions Table
    table_actions = Table(box=box.MINIMAL, expand=True)
    table_actions.add_column("Time", style="dim", width=10)
    table_actions.add_column("Model", style="cyan", width=15)
    table_actions.add_column("Action / Tool", style="yellow")
    table_actions.add_column("Session", style="dim")
    
    for a in actions:
        ts = a["timestamp"].split(" ")[1][:8]
        model = a.get("model_used", "unknown")[:15]
        tool = a["tool_name"]
        sess = (a.get("session_id") or "N/A")[:8]
        table_actions.add_row(ts, model, tool, sess)
        
    # Threads Table
    table_threads = Table(box=box.SIMPLE, expand=True)
    table_threads.add_column("Session ID", style="blue")
    table_threads.add_column("Messages", justify="right")
    table_threads.add_column("Last Active", justify="right")
    
    for t in threads:
        table_threads.add_row(t["session_id"][:12] + "...", str(t["c"]), t["ts"].split(" ")[1])

    layout = Layout()
    layout.split_column(
        Layout(name="header", size=3),
        Layout(name="main")
    )
    layout["main"].split_row(
        Layout(name="left", ratio=1),
        Layout(name="right", ratio=2)
    )
    layout["left"].split_column(
        Layout(Panel(table_tokens, title="📊 [bold]Consommation Tokens[/bold]", border_style="cyan")),
        Layout(Panel(table_threads, title="📂 [bold]Threads Actifs[/bold]", border_style="blue"))
    )
    layout["right"].update(Panel(table_actions, title="⚡ [bold]Dernières Actions (Live)[/bold]", border_style="yellow"))
    
    layout["header"].update(Panel(Align.center(Text("JARVIS OS - MONITORING CLI", style="bold white on blue")), style="blue"))
    
    return layout

if __name__ == "__main__":
    try:
        with Live(generate_layout(), refresh_per_second=2, screen=True) as live:
            while True:
                time.sleep(0.5)
                live.update(generate_layout())
    except KeyboardInterrupt:
        pass
