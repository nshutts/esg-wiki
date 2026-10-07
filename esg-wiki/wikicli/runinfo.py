"""Run metadata and evidence saving: device specs, network state, model identity,
memory use, and the evidence/ folder layout."""
from __future__ import annotations

import json
import platform
import re
import resource
import shutil
import socket
import subprocess
import sys
import time
from pathlib import Path

from .llm import LLMError, OllamaClient


def _sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return ""


def network_state() -> str:
    """'online' if the internet is reachable, 'offline' if not. Used to prove offline runs."""
    for host, port in (("1.1.1.1", 53), ("8.8.8.8", 53)):
        try:
            with socket.create_connection((host, port), timeout=2):
                return "online"
        except OSError:
            continue
    return "offline"


def device_info(root: Path) -> dict:
    info = {"os": f"{platform.system()} {platform.release()}", "machine": platform.machine(),
            "python": sys.version.split()[0]}
    if platform.system() == "Darwin":
        info["os"] = f"macOS {_sh(['sw_vers', '-productVersion'])}"
        info["chip"] = _sh(["sysctl", "-n", "machdep.cpu.brand_string"])
        mem = _sh(["sysctl", "-n", "hw.memsize"])
        if mem.isdigit():
            info["total_memory_gb"] = round(int(mem) / 1024**3, 1)
            info["memory_type"] = "unified (CPU and GPU share it)"
        vm = _sh(["vm_stat"])
        m = re.search(r"page size of (\d+)", vm)
        if m:
            page = int(m.group(1))
            pages = {k: int(v) for k, v in re.findall(r"Pages (free|inactive|speculative):\s+(\d+)", vm)}
            info["available_memory_gb_approx"] = round(sum(pages.values()) * page / 1024**3, 1)
    else:
        info["chip"] = platform.processor() or platform.machine()
        try:
            with open("/proc/meminfo") as f:
                mi = dict(re.findall(r"(\w+):\s+(\d+) kB", f.read()))
            info["total_memory_gb"] = round(int(mi["MemTotal"]) / 1024**2, 1)
            info["available_memory_gb_approx"] = round(int(mi["MemAvailable"]) / 1024**2, 1)
        except Exception:
            pass
    du = shutil.disk_usage(root)
    info["free_disk_gb"] = round(du.free / 1024**3, 1)
    return info


def harness_peak_rss_mb() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    # macOS reports bytes, Linux reports kilobytes
    return round(r / 1024**2 if platform.system() == "Darwin" else r / 1024, 1)


def model_identity(client: OllamaClient, name: str) -> dict:
    out = {"name": name}
    try:
        for m in client.list_models():
            if m.get("name") == name or m.get("model") == name or m.get("name") == f"{name}:latest":
                out["digest"] = (m.get("digest") or "")[:12]
                out["size_gb"] = round(m.get("size", 0) / 1e9, 2)
                d = m.get("details") or {}
                out.update(family=d.get("family"), parameter_size=d.get("parameter_size"),
                           quantization=d.get("quantization_level"), format=d.get("format"))
                break
        else:
            out["installed"] = False
    except LLMError:
        out["installed"] = "unknown (Ollama not reachable)"
    return out


def memory_snapshot(client: OllamaClient) -> list[dict]:
    try:
        return [{"model": m.get("name"), "loaded_size_gb": round(m.get("size", 0) / 1e9, 2),
                 "in_gpu_memory_gb": round(m.get("size_vram", 0) / 1e9, 2),
                 "context_length": m.get("context_length")}
                for m in client.loaded_models()]
    except LLMError:
        return []


def runtime_identity(client: OllamaClient) -> dict:
    try:
        return {"runtime": "Ollama", "version": client.version(), "url": client.base_url}
    except LLMError:
        return {"runtime": "Ollama", "version": "not reachable", "url": client.base_url}


def stamp() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S %Z")


def slugify(text: str, n: int = 50) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return s[:n].rstrip("-") or "run"


def save_evidence(evidence_dir: Path, kind: str, name: str, record: dict, markdown: str) -> Path:
    folder = evidence_dir / kind
    folder.mkdir(parents=True, exist_ok=True)
    json_path, md_path = folder / f"{name}.json", folder / f"{name}.md"
    json_path.write_text(json.dumps(record, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return md_path
