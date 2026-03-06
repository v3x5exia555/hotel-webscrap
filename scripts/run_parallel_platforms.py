#!/usr/bin/env python3
"""
run_parallel_platforms.py
=========================
Launches Booking, Agoda, and Traveloka scrapers in TRUE PARALLEL —
each platform gets its own dedicated OS process and worker pool.

Usage:
    python3 scripts/run_parallel_platforms.py [--monthly] [--week] [--workers N]
                                               [--nights N] [--no-sync]

Examples:
    python3 scripts/run_parallel_platforms.py --monthly --workers 3
    python3 scripts/run_parallel_platforms.py --week --workers 2 --nights 2
"""

import sys
import os
import argparse
import subprocess
import threading
import time
from datetime import datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
LOG_DIR = PROJECT_ROOT / "scripts" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

PLATFORMS = ["booking", "agoda", "traveloka", "airbnb"]

PLATFORM_COLORS = {
    "booking": "\033[94m",   # Blue
    "agoda":   "\033[92m",   # Green
    "traveloka": "\033[95m", # Magenta
    "airbnb": "\033[93m",    # Yellow
}
RESET = "\033[0m"
BOLD  = "\033[1m"
RED   = "\033[91m"
YELLOW = "\033[93m"
CYAN  = "\033[96m"


def timestamp():
    return datetime.now().strftime("%H:%M:%S")


def log(msg, color=""):
    print(f"{color}[{timestamp()}] {msg}{RESET}", flush=True)


def stream_output(proc, platform, log_file_path):
    """
    Read stdout/stderr from a subprocess line by line,
    pretty-print to console with platform prefix, and write to log file.
    """
    color = PLATFORM_COLORS.get(platform, "")
    prefix = f"{BOLD}{color}[{platform.upper():^10}]{RESET}{color}"

    with open(log_file_path, "w", buffering=1) as lf:
        lf.write(f"=== {platform.upper()} scraper started at {datetime.now().isoformat()} ===\n\n")
        for raw_line in iter(proc.stdout.readline, ""):
            line = raw_line.rstrip("\n")
            console_line = f"{prefix} {line}{RESET}"
            print(console_line, flush=True)
            lf.write(raw_line)
        lf.write(f"\n=== {platform.upper()} scraper finished at {datetime.now().isoformat()} ===\n")


def run_platform(platform: str, args: argparse.Namespace) -> tuple[str, int, float]:
    """
    Launch one platform's scraper as a subprocess.
    Returns (platform, returncode, elapsed_seconds).
    """
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_path = LOG_DIR / f"{platform}_{ts}.log"

    cmd = [
        sys.executable,
        str(PROJECT_ROOT / "main.py"),
        "--platform", platform,
        "--workers",  str(args.workers),
    ]
    if args.monthly:
        cmd.append("--monthly")
    elif args.week:
        cmd.append("--week")
    if args.nights > 1:
        cmd += ["--nights", str(args.nights)]

    color = PLATFORM_COLORS.get(platform, "")
    log(f"🚀 Starting {platform.upper()} scraper  →  {' '.join(cmd[2:])}", color)
    log(f"   Log file: {log_path}", color)

    t_start = time.time()
    proc = subprocess.Popen(
        cmd,
        cwd=str(PROJECT_ROOT),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    # Stream output in a dedicated thread so all 3 print simultaneously
    streamer = threading.Thread(target=stream_output, args=(proc, platform, log_path), daemon=True)
    streamer.start()

    proc.wait()
    streamer.join()

    elapsed = time.time() - t_start
    return platform, proc.returncode, elapsed


def run_sync():
    """Run the Supabase sync after all scrapers finish."""
    log("🔄 Running Supabase sync (push_data_to_supabase.py)...", CYAN)
    sync_proc = subprocess.run(
        [sys.executable, str(PROJECT_ROOT / "push_data_to_supabase.py")],
        cwd=str(PROJECT_ROOT),
        capture_output=False,
    )
    if sync_proc.returncode == 0:
        log("✅ Supabase sync completed successfully.", CYAN)
    else:
        log(f"⚠️  Supabase sync exited with code {sync_proc.returncode}.", YELLOW)


def main():
    parser = argparse.ArgumentParser(
        description="Run Booking / Agoda / Traveloka scrapers in TRUE parallel.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--monthly", action="store_true", help="Scrape 30 days ahead")
    mode.add_argument("--week",    action="store_true", help="Scrape 7 days ahead")
    parser.add_argument("--workers",  type=int, default=3, help="Worker processes per platform (default: 3)")
    parser.add_argument("--nights",   type=int, default=1, help="Max nights per stay (default: 1)")
    parser.add_argument("--no-sync",  action="store_true", help="Skip Supabase sync after scraping")
    parser.add_argument("--platforms", nargs="+", default=PLATFORMS,
                        choices=PLATFORMS, help="Platforms to run (default: all 3)")
    args = parser.parse_args()

    if not args.monthly and not args.week:
        log("⚠️  No mode specified — defaulting to --week (7 days).", YELLOW)
        args.week = True

    # ---- Print banner ----
    mode_label = "MONTHLY (30 days)" if args.monthly else "WEEKLY (7 days)"
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  🏨 Hotel Parallel Scraper Launcher{RESET}")
    print(f"{BOLD}{CYAN}  Mode    : {mode_label}{RESET}")
    print(f"{BOLD}{CYAN}  Platforms: {', '.join(p.upper() for p in args.platforms)}{RESET}")
    print(f"{BOLD}{CYAN}  Workers  : {args.workers} per platform  ({args.workers * len(args.platforms)} total){RESET}")
    print(f"{BOLD}{CYAN}  Nights   : {args.nights}{RESET}")
    print(f"{BOLD}{CYAN}  Started  : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

    wall_start = time.time()

    # ---- Fire all platforms in parallel using threads ----
    threads = []
    results = {}

    def platform_worker(platform):
        pf, rc, elapsed = run_platform(platform, args)
        results[pf] = {"returncode": rc, "elapsed": elapsed}

    for platform in args.platforms:
        t = threading.Thread(target=platform_worker, args=(platform,), name=f"scraper-{platform}")
        threads.append(t)

    # Start all at the same time
    for t in threads:
        t.start()

    # Wait for all to finish
    for t in threads:
        t.join()

    wall_elapsed = time.time() - wall_start

    # ---- Print summary ----
    print(f"\n{BOLD}{CYAN}{'='*60}{RESET}")
    print(f"{BOLD}{CYAN}  📊 Parallel Scrape Summary{RESET}")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}")
    all_ok = True
    for platform in args.platforms:
        info = results.get(platform, {})
        rc = info.get("returncode", -1)
        elapsed = info.get("elapsed", 0)
        color = PLATFORM_COLORS.get(platform, "")
        status_icon = "✅" if rc == 0 else "❌"
        status_text = "OK" if rc == 0 else f"FAILED (exit {rc})"
        if rc != 0:
            all_ok = False
        print(f"  {color}{status_icon} {platform.upper():<12} {status_text:<20} ⏱ {elapsed:.1f}s{RESET}")

    print(f"\n  ⏱  Total wall-clock time : {wall_elapsed:.1f}s")
    print(f"  ⚡ Time saved vs serial   : ~{sum(r['elapsed'] for r in results.values()) - wall_elapsed:.1f}s")
    print(f"{BOLD}{CYAN}{'='*60}{RESET}\n")

    # ---- Optional Supabase sync ----
    if not args.no_sync:
        run_sync()
    else:
        log("⏭️  Supabase sync skipped (--no-sync).", YELLOW)

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()
