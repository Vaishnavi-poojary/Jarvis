import ctypes
import re
import shutil
from dataclasses import dataclass
from datetime import datetime


@dataclass
class QuickDecision:
    route: str = "chat"
    intent: str = "quick_response"
    action: str = "quick_response"
    target: str | None = None
    query: str | None = None
    response: str | None = None
    confidence: float = 1.0
    should_speak: bool = True


def get_quick_response(command: str) -> str | None:
    text = _normalize(command)
    if not text:
        return None

    response = (
        _time_or_date_response(text)
        or _greeting_response(text)
        or _identity_response(text)
        or _basic_conversation_response(text)
        or _emotional_support_response(text)
        or _gratitude_or_farewell_response(text)
        or _system_status_response(text)
    )
    return response


def make_quick_decision(response: str, command: str = "") -> QuickDecision:
    return QuickDecision(response=response, query=command.strip() or None)


def _normalize(command: str) -> str:
    text = command.lower().strip()
    text = text.replace("today's", "todays")
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return " ".join(text.split())


def _time_or_date_response(text: str) -> str | None:
    now = datetime.now()
    if text in {"what time is it", "current time", "time", "tell me the time"}:
        return f"It is {now.strftime('%I:%M %p').lstrip('0')}."

    if text in {"what date is it", "todays date", "today date", "date", "current date"}:
        return f"Today is {now.strftime('%A, %d %B %Y')}."

    if text in {"what day is it", "which day is it", "day today", "current day"}:
        return f"Today is {now.strftime('%A')}."

    return None


def _greeting_response(text: str) -> str | None:
    if text in {"hi", "hello", "hey"}:
        return "Hello. How can I help?"

    if text == "good morning":
        return "Good morning. Systems are ready."

    if text == "good afternoon":
        return "Good afternoon. I am online."

    if text in {"good evening", "good night"}:
        return "Good evening. I am here if you need anything."

    return None


def _identity_response(text: str) -> str | None:
    if text == "who are you":
        return "I am Jarvis, your local assistant for chat, voice, memory, automation, and quick system help."

    if text in {"what can you do", "help", "show commands"}:
        return (
            "I can answer questions, remember details, use voice input, open apps or websites, "
            "search the web or YouTube, and report basic system status."
        )

    return None


def _basic_conversation_response(text: str) -> str | None:
    if text == "how are you":
        return "I am running smoothly and ready to help."

    if text == "what are you doing":
        return "I am monitoring the interface and waiting for your next command."

    return None


def _emotional_support_response(text: str) -> str | None:
    support = {
        "i feel sad": "I am sorry you feel sad. I am here with you. Want to talk about it?",
        "i am sad": "I am sorry you feel sad. I am here with you. Want to talk about it?",
        "i feel bored": "Boredom happens. We can play music, search something fun, or plan a small task.",
        "i am bored": "Boredom happens. We can play music, search something fun, or plan a small task.",
        "i feel tired": "You sound tired. A short break, water, and a few slow breaths might help.",
        "i am tired": "You sound tired. A short break, water, and a few slow breaths might help.",
        "i am stressed": "That sounds stressful. Take one slow breath with me. We can handle one thing at a time.",
        "i feel stressed": "That sounds stressful. Take one slow breath with me. We can handle one thing at a time.",
    }
    return support.get(text)


def _gratitude_or_farewell_response(text: str) -> str | None:
    if text in {"thank you", "thanks", "arigato"}:
        return "You are welcome."

    if text in {"bye", "goodbye", "see you"}:
        return "Goodbye. I will be here when you need me."

    return None


def _system_status_response(text: str) -> str | None:
    if text == "battery status":
        return _battery_status()

    if text == "cpu usage":
        return _cpu_status()

    if text == "memory usage":
        return _memory_status()

    return None


def _battery_status() -> str:
    psutil = _try_psutil()
    if psutil:
        battery = psutil.sensors_battery()
        if battery:
            plugged = "charging" if battery.power_plugged else "on battery"
            return f"Battery is at {battery.percent:.0f}% and {plugged}."

    status = _windows_battery_status()
    if status:
        return status

    return "Battery status is not available on this system."


def _cpu_status() -> str:
    psutil = _try_psutil()
    if psutil:
        return f"CPU usage is {psutil.cpu_percent(interval=0.1):.0f}%."

    return "CPU usage is not available without system stats support."


def _memory_status() -> str:
    psutil = _try_psutil()
    if psutil:
        memory = psutil.virtual_memory()
        used_gb = memory.used / (1024 ** 3)
        total_gb = memory.total / (1024 ** 3)
        return f"Memory usage is {memory.percent:.0f}% ({used_gb:.1f} GB of {total_gb:.1f} GB)."

    total, used = _windows_memory_status()
    if total:
        percent = used / total * 100
        return f"Memory usage is {percent:.0f}% ({used:.1f} GB of {total:.1f} GB)."

    fallback = shutil.disk_usage(".")
    if fallback:
        return "Memory usage is not available, but local disk stats are accessible."

    return "Memory usage is not available on this system."


def _try_psutil():
    try:
        import psutil
    except ImportError:
        return None
    return psutil


def _windows_battery_status() -> str | None:
    try:
        class SystemPowerStatus(ctypes.Structure):
            _fields_ = [
                ("ACLineStatus", ctypes.c_byte),
                ("BatteryFlag", ctypes.c_byte),
                ("BatteryLifePercent", ctypes.c_byte),
                ("SystemStatusFlag", ctypes.c_byte),
                ("BatteryLifeTime", ctypes.c_ulong),
                ("BatteryFullLifeTime", ctypes.c_ulong),
            ]

        status = SystemPowerStatus()
        if not ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(status)):
            return None
        if status.BatteryLifePercent == 255:
            return None

        plugged = "charging" if status.ACLineStatus == 1 else "on battery"
        return f"Battery is at {status.BatteryLifePercent}% and {plugged}."
    except Exception:
        return None


def _windows_memory_status() -> tuple[float | None, float | None]:
    try:
        class MemoryStatusEx(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
            ]

        status = MemoryStatusEx()
        status.dwLength = ctypes.sizeof(MemoryStatusEx)
        if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            return None, None

        total = status.ullTotalPhys / (1024 ** 3)
        available = status.ullAvailPhys / (1024 ** 3)
        return total, total - available
    except Exception:
        return None, None
