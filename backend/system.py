"""
system.py — Native Windows system diagnostics.
Fetches CPU, GPU, RAM size, and Disk Drive storage capabilities.
"""

import os
import sys
import string
import shutil
import winreg
import subprocess
import ctypes
import platform
import re
from ctypes import wintypes

# ── Windows MEMORYSTATUSEX Struct ──────────────────────────────────────

class MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [
        ('dwLength', wintypes.DWORD),
        ('dwMemoryLoad', wintypes.DWORD),
        ('ullTotalPhys', ctypes.c_uint64),
        ('ullAvailPhys', ctypes.c_uint64),
        ('ullTotalPageFile', ctypes.c_uint64),
        ('ullAvailPageFile', ctypes.c_uint64),
        ('ullTotalVirtual', ctypes.c_uint64),
        ('ullAvailVirtual', ctypes.c_uint64),
        ('ullAvailExtendedVirtual', ctypes.c_uint64),
    ]


def _get_usable_ram_gb() -> int:
    """Get currently usable physical system memory in GB."""
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(stat)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat)):
            # Convert bytes to GB and round to nearest integer
            return int(round(stat.ullTotalPhys / (1024 ** 3)))
    except Exception:
        pass
    return 8  # Fallback to standard 8GB


def _get_installed_ram_gb() -> int:
    """Get installed physical memory from Windows CIM/WMIC when available."""
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "(Get-CimInstance Win32_PhysicalMemory | Measure-Object Capacity -Sum).Sum",
            ],
            stderr=subprocess.DEVNULL,
            timeout=5,
        )
        value = int(out.decode("utf-8", errors="ignore").strip() or 0)
        if value:
            return int(round(value / (1024 ** 3)))
    except Exception:
        pass
    return _get_usable_ram_gb()


def _get_cpu_name() -> str:
    """Read CPU name directly from Windows Registry."""
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0") as key:
            name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            return name.strip()
    except Exception:
        pass
    return "Unknown CPU"


def _gpu_score(name: str) -> int:
    value = name.lower()
    score = 0
    if any(token in value for token in ("nvidia", "geforce", "rtx", "gtx", "quadro")):
        score += 300
    if any(token in value for token in ("radeon rx", "radeon pro", "amd rx")):
        score += 250
    if any(token in value for token in ("intel", "uhd", "iris", "radeon graphics")):
        score -= 50
    match = re.search(r"\b(?:rtx|gtx|rx)\s*([0-9]{3,4})", value)
    if match:
        score += int(match.group(1))
    return score


def _get_gpu_records() -> list[dict]:
    """Query GPUs with PowerShell CIM first, then WMIC for older systems."""
    records = []
    try:
        out = subprocess.check_output(
            [
                "powershell",
                "-NoProfile",
                "-Command",
                "Get-CimInstance Win32_VideoController | Select-Object Name,AdapterRAM | ConvertTo-Json -Compress",
            ],
            stderr=subprocess.DEVNULL,
            timeout=7,
        )
        text = out.decode("utf-8", errors="ignore").strip()
        if text:
            import json
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                parsed = [parsed]
            for item in parsed or []:
                name = str(item.get("Name") or "").strip()
                if not name:
                    continue
                ram = int(item.get("AdapterRAM") or 0)
                records.append({"name": name, "vram_gb": round(ram / (1024 ** 3), 1) if ram > 0 else 0})
    except Exception:
        records = []

    if records:
        return sorted(records, key=lambda item: _gpu_score(item.get("name", "")), reverse=True)

    return [{"name": name, "vram_gb": 0} for name in _get_gpu_names_wmic()]


def _get_gpu_names_wmic() -> list[str]:
    """Query GPU names via WMIC for older Windows systems."""
    try:
        out = subprocess.check_output("wmic path win32_VideoController get Name", shell=True)
        lines = out.decode("utf-8", errors="ignore").strip().splitlines()
        gpus = [line.strip() for line in lines if line.strip() and not line.strip().lower().startswith("name")]
        if gpus:
            return sorted(dict.fromkeys(gpus), key=_gpu_score, reverse=True)
    except Exception:
        pass
    return []


def _get_gpu_names() -> list[str]:
    return [record["name"] for record in _get_gpu_records()]


def _get_gpu_name() -> str:
    gpus = _get_gpu_names()
    return gpus[0] if gpus else "Unknown GPU"


def _get_windows_name() -> str:
    if sys.platform != "win32":
        return platform.system() or "Unknown OS"
    try:
        version = sys.getwindowsversion()
        build = int(version.build)
        if version.major == 10 and build >= 22000:
            return f"Windows 11 ({build})"
        if version.major == 10:
            return f"Windows 10 ({build})"
        return f"Windows {version.major}.{version.minor} ({build})"
    except Exception:
        return platform.platform() or "Windows"


# ── Public APIs ────────────────────────────────────────────────────────

def get_pc_specs() -> dict:
    """Query CPU, GPU, RAM size, and OS name."""
    ram_usable_gb = _get_usable_ram_gb()
    ram_installed_gb = max(_get_installed_ram_gb(), ram_usable_gb)
    cpu = _get_cpu_name()
    gpu = _get_gpu_name()
    gpu_records = _get_gpu_records()
    gpus = [record["name"] for record in gpu_records]
    
    return {
        "cpu": cpu,
        "gpu": gpu,
        "gpus": gpus,
        "gpu_vram_gb": gpu_records[0].get("vram_gb", 0) if gpu_records else 0,
        "gpu_details": gpu_records,
        "ram": ram_installed_gb,
        "ram_gb": ram_installed_gb,
        "ram_usable_gb": ram_usable_gb,
        "ram_installed_gb": ram_installed_gb,
        "os": _get_windows_name(),
    }


def get_drive_space() -> list:
    """Scan and return total/free bytes for all active drives."""
    drives = []
    for letter in string.ascii_uppercase:
        drive_path = f"{letter}:\\"
        if os.path.exists(drive_path):
            try:
                total, used, free = shutil.disk_usage(drive_path)
                drives.append({
                    "drive": drive_path,
                    "name": drive_path,
                    "total": total,
                    "used": used,
                    "free": free,
                    "total_gb": round(total / (1024 ** 3), 1),
                    "used_gb": round(used / (1024 ** 3), 1),
                    "free_gb": round(free / (1024 ** 3), 1),
                    "label": f"Local Disk ({letter}:)"
                })
            except Exception:
                pass
    return drives
