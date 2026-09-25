"""
Edge AI Resource & Latency Monitor
----------------------------------------------------------------
Hesabatda birbaşa qeyd olunan boşluğu həll edir: "Edge AI Resurs və
Gecikmə Monitorinqi" — köhnə demoda münsiflərə inference vaxtını və
CPU/RAM istifadəsini canlı göstərən heç nə yox idi. Bu modul kiçik və
asılılığı azdır (yalnız psutil), ona görə Raspberry Pi / Jetson üzərində
özü əlavə yük yaratmır.
"""

import os
import psutil


def get_resource_snapshot() -> dict:
    process = psutil.Process(os.getpid())
    return {
        "edge_cpu_usage_pct": round(psutil.cpu_percent(interval=0.05), 1),
        "edge_ram_usage_mb": round(process.memory_info().rss / (1024 * 1024), 1),
        "edge_ram_usage_pct": round(psutil.virtual_memory().percent, 1),
    }
