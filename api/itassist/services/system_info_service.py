
import platform
import psutil
import cpuinfo
import sys
import winreg
from pynvml import *

def is_windows_11():
    try:
        key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows NT\CurrentVersion")
        product_name, _ = winreg.QueryValueEx(key, "ProductName")
        print(f"Product Name: {product_name}")
    
        return "Windows 11" in product_name
    except Exception:
        return False

def get_system_info():
    try:
        cpu = cpuinfo.get_cpu_info()
    except Exception:
        cpu = {}

    windows_version = "Windows 11" if is_windows_11() else platform.system()

    info = {
        "os": windows_version,
        "os_version": platform.version(),
        "processor": cpu.get("brand_raw") or platform.processor() or "Unknown",
        "physical_cores": psutil.cpu_count(logical=False),
        "total_cores": psutil.cpu_count(logical=True),
        "total_ram_gib": round(psutil.virtual_memory().total / (1024 ** 3), 2),
        "igpu": "Not detected",
        "igpu_memory_gib": "Not detected",
    }

    try:
        nvmlInit()
        handle = nvmlDeviceGetHandleByIndex(0)
        gpu_name = nvmlDeviceGetName(handle).decode("utf-8")
        mem_info = nvmlDeviceGetMemoryInfo(handle)
        info["igpu"] = gpu_name
        info["igpu_memory_gib"] = round(mem_info.total / (1024 ** 3), 2)
        nvmlShutdown()
    except NVMLError:
        pass

    return info

# print(get_system_info())
