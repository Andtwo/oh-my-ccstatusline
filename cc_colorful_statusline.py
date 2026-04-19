#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

PALETTE = {
    "crust": "#0b1320",
    "text": "#cdd6f4",
    "muted": "#bac2de",
    "subtle": "#7f849c",
    "dot_off": "#6c7086",
    "user_bg": "#38bdf8",
    "dir_bg": "#22d3ee",
    "git_bg": "#2dd4bf",
    "context_bg": "#74c7ec",
    "cost_bg": "#a6e3a1",
    "time_bg": "#f9e2af",
    "rosewater": "#f5e0dc",
    "flamingo": "#f2cdcd",
    "pink": "#f5c2e7",
    "mauve": "#cba6f7",
    "surface2": "#585b70",
    "red": "#f38ba8",
    "maroon": "#eba0ac",
    "peach": "#fab387",
    "yellow": "#f9e2af",
    "green": "#a6e3a1",
    "teal": "#94e2d5",
    "sky": "#89dceb",
    "sapphire": "#74c7ec",
    "blue": "#89b4fa",
    "lavender": "#b4befe",
    "cyan": "#89dceb",
}

LEFT_CAP = ""
SEP = ""
END_CAP = ""
BADGE_LEFT = ""
BADGE_RIGHT = ""
BRANCH = ""
CLOCK = ""
DURATION = ""
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"


def color_code(hex_value: str, is_bg: bool) -> str:
    hex_value = hex_value.lstrip("#")
    r = int(hex_value[0:2], 16)
    g = int(hex_value[2:4], 16)
    b = int(hex_value[4:6], 16)
    prefix = "48" if is_bg else "38"
    return f"\033[{prefix};2;{r};{g};{b}m"


def fg(hex_value: str) -> str:
    return color_code(hex_value, False)


def bg(hex_value: str) -> str:
    return color_code(hex_value, True)


def badge(text: str, bg_color: str, fg_color: str | None = None) -> str:
    fg_color = fg_color or PALETTE["crust"]
    return (
        f"{fg(bg_color)}{BADGE_LEFT}{RESET}"
        f"{bg(bg_color)}{fg(fg_color)} {text} {RESET}"
        f"{fg(bg_color)}{BADGE_RIGHT}{RESET}"
    )


def segment(text: str, bg_color: str, fg_color: str, previous_bg: str | None) -> tuple[str, str]:
    if previous_bg is None:
        prefix = f"{fg(bg_color)}{LEFT_CAP}{RESET}"
        body = f"{bg(bg_color)}{fg(fg_color)} {text} {RESET}"
    elif bg_color == previous_bg:
        prefix = ""
        body = f"{bg(bg_color)}{fg(fg_color)}{text} {RESET}"
    else:
        prefix = f"{bg(bg_color)}{fg(previous_bg)}{SEP}{RESET}"
        body = f"{bg(bg_color)}{fg(fg_color)} {text} {RESET}"
    return prefix + body, bg_color


def finish(previous_bg: str | None) -> str:
    if previous_bg is None:
        return ""
    return f"{fg(previous_bg)}{END_CAP}{RESET}"


def safe_get(data: dict, *keys, default=None):
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def shorten_path(path: str, home: str) -> str:
    if path.startswith(home):
        path = path.replace(home, "~", 1)
    if path in {"/", "~"}:
        return path

    prefix = ""
    raw = path
    if path.startswith("~/"):
        prefix = "~/"
        raw = path[2:]
    elif path.startswith("/"):
        prefix = "/"
        raw = path[1:]

    parts = [part for part in raw.split("/") if part]
    substitutions = {
        "Documents": "󰈙",
        "Downloads": "",
        "Music": "󰝚",
        "Pictures": "",
        "Developer": "󰲋",
        "Desktop": "󰟀",
    }
    if len(parts) > 3:
        parts = ["…", *parts[-3:]]
    parts = [substitutions.get(part, part) for part in parts]
    return prefix + "/".join(parts)


def format_duration(milliseconds: int) -> str:
    total_seconds = milliseconds // 1000
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    if hours > 0:
        return f"{hours}h {minutes:02d}m"
    if minutes > 0:
        return f"{minutes}m {seconds:02d}s"
    return f"{seconds}s"


def format_token_count(value) -> str:
    try:
        num = int(value or 0)
    except Exception:
        return "0"
    if num >= 1_000_000:
        return f"{num / 1_000_000:.1f}M"
    if num >= 1_000:
        return f"{num / 1_000:.1f}K"
    return str(num)


def format_cost(cost: float) -> str:
    if cost >= 1:
        return f"${cost:.2f}"
    if cost >= 0.1:
        return f"${cost:.3f}"
    return f"${cost:.4f}"


def color_for_pct(percentage: int) -> str:
    if percentage >= 80:
        return PALETTE["red"]
    if percentage >= 50:
        return PALETTE["peach"]
    return PALETTE["teal"]


def colored_percentage(percentage: int) -> str:
    return f"{fg(color_for_pct(percentage))}{percentage}%{RESET}"


def progress_bar(used_percentage: int, off_color: str | None = None) -> str:
    width = 15
    raw_filled = used_percentage * width / 100
    filled = max(0, min(width, int(raw_filled)))
    if used_percentage > 0 and filled == 0:
        filled = 1
    bar = []
    on = fg(PALETTE["teal"] if used_percentage < 50 else color_for_pct(used_percentage))
    off = fg(off_color or PALETTE["dot_off"])
    for _ in range(filled):
        bar.append(f"{on}●{RESET}")
    for _ in range(width - filled):
        bar.append(f"{off}●{RESET}")
    return "".join(bar)


def fmt_countdown(reset_at) -> str:
    try:
        reset_at = int(reset_at)
    except Exception:
        return ""
    diff = reset_at - int(time.time())
    if diff <= 0:
        return "now"
    hours = diff // 3600
    minutes = (diff % 3600) // 60
    return f"{hours}h {minutes}m"


def run_git(cwd: str, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=cwd, stderr=subprocess.DEVNULL, text=True).strip()


def git_remote_link(cwd: str) -> tuple[str, str]:
    try:
        remote = run_git(cwd, "remote", "get-url", "origin")
    except Exception:
        return "", ""
    if remote.startswith("git@github.com:"):
        remote = remote.replace("git@github.com:", "https://github.com/", 1)
    if remote.endswith(".git"):
        remote = remote[:-4]
    repo_name = os.path.basename(remote) if remote else ""
    return remote, repo_name


def osc8_link(url: str, text: str) -> str:
    if not url or not text:
        return text
    return f"\033]8;;{url}\a{text}\033]8;;\a"


def compute_git_info(cwd: str, session_id: str) -> dict:
    info = {
        "branch": "",
        "status_text": "",
        "stats_text": "",
        "repo_url": "",
        "repo_name": os.path.basename(cwd),
    }
    try:
        inside = run_git(cwd, "rev-parse", "--is-inside-work-tree")
        if inside != "true":
            return info
    except Exception:
        return info

    cache_file = Path(tempfile.gettempdir()) / f"claude-statusline-git-{session_id or 'default'}.json"
    now = time.time()
    if cache_file.exists():
        try:
            cached = json.loads(cache_file.read_text())
            if cached.get("cwd") == cwd and now - cached.get("timestamp", 0) < 5:
                return cached.get("value", info)
        except Exception:
            pass

    branch = ""
    for args in (
        ("symbolic-ref", "--quiet", "--short", "HEAD"),
        ("describe", "--tags", "--exact-match", "HEAD"),
        ("rev-parse", "--short", "HEAD"),
    ):
        try:
            branch = run_git(cwd, *args)
            if branch:
                break
        except Exception:
            continue

    try:
        status_lines = run_git(cwd, "status", "--porcelain")
    except Exception:
        status_lines = ""

    staged = modified = renamed = deleted = untracked = conflicted = 0
    if status_lines:
        for line in status_lines.splitlines():
            xy = line[:2]
            if xy == "??":
                untracked += 1
                continue
            if xy in {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}:
                conflicted += 1
                continue
            x, y = line[0], line[1]
            if x != " ":
                staged += 1
            if x == "R" or y == "R":
                renamed += 1
            if x == "D" or y == "D":
                deleted += 1
            if x in {"M", "T"} or y in {"M", "T"}:
                modified += 1

    status_parts = []
    if staged:
        status_parts.append(f"+{staged}")
    if modified:
        status_parts.append(f"!{modified}")
    if renamed:
        status_parts.append(f">{renamed}")
    if deleted:
        status_parts.append(f"x{deleted}")
    if untracked:
        status_parts.append(f"?{untracked}")
    if conflicted:
        status_parts.append(f"={conflicted}")
    try:
        ahead = int(run_git(cwd, "rev-list", "--count", "@{upstream}..HEAD") or "0")
    except Exception:
        ahead = 0
    try:
        behind = int(run_git(cwd, "rev-list", "--count", "HEAD..@{upstream}") or "0")
    except Exception:
        behind = 0
    if ahead:
        status_parts.append(f"⇡{ahead}")
    if behind:
        status_parts.append(f"⇣{behind}")

    try:
        git_m = int(run_git(cwd, "diff", "--name-only").count("\n") + (1 if run_git(cwd, "diff", "--name-only") else 0))
    except Exception:
        git_m = 0
    try:
        git_a = int(run_git(cwd, "ls-files", "--others", "--exclude-standard").count("\n") + (1 if run_git(cwd, "ls-files", "--others", "--exclude-standard") else 0))
    except Exception:
        git_a = 0
    try:
        git_d = int(run_git(cwd, "diff", "--diff-filter=D", "--name-only").count("\n") + (1 if run_git(cwd, "diff", "--diff-filter=D", "--name-only") else 0))
    except Exception:
        git_d = 0

    stats_parts = []
    if git_m > 0:
        stats_parts.append(f"{fg(PALETTE['yellow'])}{git_m}M{RESET}")
    if git_a > 0:
        stats_parts.append(f"{fg(PALETTE['green'])}{git_a}A{RESET}")
    if git_d > 0:
        stats_parts.append(f"{fg(PALETTE['red'])}{git_d}D{RESET}")

    repo_url, repo_name = git_remote_link(cwd)
    info = {
        "branch": branch,
        "status_text": " ".join(status_parts),
        "stats_text": " ".join(stats_parts),
        "repo_url": repo_url,
        "repo_name": repo_name or os.path.basename(cwd),
    }
    try:
        cache_file.write_text(json.dumps({"cwd": cwd, "timestamp": now, "value": info}))
    except Exception:
        pass
    return info


try:
    payload = json.load(sys.stdin)
except Exception:
    payload = {}

session_id = safe_get(payload, "session_id", default="")
model_name = safe_get(payload, "model", "display_name", default="Claude")
cwd = safe_get(payload, "workspace", "current_dir", default=safe_get(payload, "cwd", default=os.getcwd()))
ctx_size = safe_get(payload, "context_window", "context_window_size", default=0) or 0
used_pct = int(float(safe_get(payload, "context_window", "used_percentage", default=0) or 0))
duration_ms = int(safe_get(payload, "cost", "total_duration_ms", default=0) or 0)
api_duration_ms = int(safe_get(payload, "cost", "total_api_duration_ms", default=0) or 0)
cost_total = float(safe_get(payload, "cost", "total_cost_usd", default=0) or 0)
lines_add = safe_get(payload, "cost", "total_lines_added", default=0) or 0
lines_del = safe_get(payload, "cost", "total_lines_removed", default=0) or 0
vim_mode = safe_get(payload, "vim", "mode", default="") or ""
agent_name = safe_get(payload, "agent", "name", default="") or ""
version = safe_get(payload, "version", default="") or ""
rate_5h = safe_get(payload, "rate_limits", "five_hour", "used_percentage", default=None)
rate_7d = safe_get(payload, "rate_limits", "seven_day", "used_percentage", default=None)
reset_5h = safe_get(payload, "rate_limits", "five_hour", "resets_at", default=None)
reset_7d = safe_get(payload, "rate_limits", "seven_day", "resets_at", default=None)
total_in = safe_get(payload, "context_window", "total_input_tokens", default=0) or 0
total_out = safe_get(payload, "context_window", "total_output_tokens", default=0) or 0
cur_input = safe_get(payload, "context_window", "current_usage", "input_tokens", default=0) or 0
cache_read = safe_get(payload, "context_window", "current_usage", "cache_read_input_tokens", default=0) or 0
cache_create = safe_get(payload, "context_window", "current_usage", "cache_creation_input_tokens", default=0) or 0
clock_text = time.strftime("%H:%M")

ctx_label = "1M" if ctx_size and int(ctx_size) >= 1_000_000 else ("200K" if ctx_size else "")
repo_info = compute_git_info(cwd, session_id)
repo_label = osc8_link(repo_info["repo_url"], repo_info["repo_name"]) if repo_info["repo_name"] else os.path.basename(cwd)

lines_part = []
if str(lines_add) not in {"", "0"} and int(lines_add) != 0:
    lines_part.append(f"{fg(PALETTE['green'])}+{lines_add}{RESET}")
if str(lines_del) not in {"", "0"} and int(lines_del) != 0:
    lines_part.append(f"{fg(PALETTE['red'])}-{lines_del}{RESET}")

rate_parts = []
if rate_5h is not None:
    r5 = int(round(float(rate_5h)))
    piece = f"{fg(PALETTE['mauve'])}5h{RESET} {colored_percentage(r5)}"
    cd = fmt_countdown(reset_5h)
    if cd:
        piece += f" {fg(PALETTE['lavender'])}({cd}){RESET}"
    rate_parts.append(piece)
if rate_7d is not None:
    r7 = int(round(float(rate_7d)))
    piece = f"{fg(PALETTE['pink'])}7d{RESET} {colored_percentage(r7)}"
    cd = fmt_countdown(reset_7d)
    if cd:
        piece += f" {fg(PALETTE['lavender'])}({cd}){RESET}"
    rate_parts.append(piece)

line2_parts = [
    badge(model_name, PALETTE['sky']),
]
if ctx_label:
    line2_parts.append(f"{fg(PALETTE['lavender'])}{ctx_label}{RESET}")
if version:
    line2_parts.append(f"{fg(PALETTE['mauve'])}v{version}{RESET}")
context_badge = badge(
    f"{progress_bar(used_pct, PALETTE['surface2'])} {used_pct}%",
    PALETTE['mauve'],
)
line2_parts.extend([
    f"{fg(PALETTE['rosewater'])}{shorten_path(cwd, os.path.expanduser('~'))}{RESET}",
    context_badge,
    badge(format_cost(cost_total), PALETTE['yellow']),
    f"{fg(PALETTE['flamingo'])}{format_duration(duration_ms)}{RESET}",
])
if repo_info["branch"]:
    branch_text = f"{BRANCH} {repo_info['branch']}"
    if repo_info["status_text"]:
        branch_text += f" {repo_info['status_text']}"
    line2_parts.append(f"{fg(PALETTE['green'])}{branch_text}{RESET}")
if rate_parts:
    line2_parts.extend(rate_parts)
if lines_part:
    line2_parts.append(" ".join(lines_part) + f" {fg(PALETTE['mauve'])}lines{RESET}")
if repo_info["stats_text"]:
    line2_parts.append(repo_info["stats_text"])
if agent_name:
    line2_parts.append(f"{fg(PALETTE['blue'])}{agent_name}{RESET}")
if vim_mode:
    mode_label = "NOR" if vim_mode == "NORMAL" else "INS"
    mode_color = PALETTE["blue"] if vim_mode == "NORMAL" else PALETTE["green"]
    line2_parts.append(f"{fg(mode_color)}{BOLD}{mode_label}{RESET}")
line2_parts.append(badge(f"{CLOCK} {clock_text}", PALETTE['peach']))
line2 = f"{DIM} | {RESET}".join(line2_parts)

cache_total = int(cache_read) + int(cur_input) + int(cache_create)
cache_hit_text = ""
if cache_total > 0:
    cache_pct = int((int(cache_read) * 100) / cache_total)
    cache_hit_text = f"{fg(PALETTE['mauve'])}cache{RESET} {colored_percentage(cache_pct)}"

tokens_part = f"{fg(PALETTE['lavender'])}in:{RESET} {fg(PALETTE['sky'])}{format_token_count(total_in)}{RESET} {fg(PALETTE['lavender'])}out:{RESET} {fg(PALETTE['pink'])}{format_token_count(total_out)}{RESET}"
api_dur = format_duration(api_duration_ms)
if duration_ms > 0 and api_duration_ms > 0:
    api_pct = int((api_duration_ms * 100) / duration_ms)
    api_part = f"{fg(PALETTE['peach'])}api wait{RESET} {fg(PALETTE['sapphire'])}{api_dur}{RESET} {fg(PALETTE['lavender'])}({api_pct}%){RESET}"
else:
    api_part = f"{fg(PALETTE['peach'])}api wait{RESET} {fg(PALETTE['sapphire'])}{api_dur}{RESET}"
cur_part = f"{fg(PALETTE['teal'])}cur{RESET} {fg(PALETTE['rosewater'])}{format_token_count(cur_input)}{RESET} {fg(PALETTE['teal'])}in{RESET} {fg(PALETTE['rosewater'])}{format_token_count(cache_read)}{RESET} {fg(PALETTE['teal'])}read{RESET} {fg(PALETTE['rosewater'])}{format_token_count(cache_create)}{RESET} {fg(PALETTE['teal'])}write{RESET}"

line3_parts = []
if cache_hit_text:
    line3_parts.append(cache_hit_text)
line3_parts.append(tokens_part)
line3_parts.append(api_part)
line3_parts.append(cur_part)
line3 = f"{DIM} | {RESET}".join(line3_parts)

sys.stdout.write(line2 + "\n")
sys.stdout.write(line3)
