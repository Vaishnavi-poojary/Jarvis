import math
import sys
import time
from enum import Enum

try:
    from PyQt6.QtCore import Qt, QTimer, QRectF, QPointF, QThread, pyqtSignal
    from PyQt6.QtGui import QColor, QPainter, QPen, QBrush, QRadialGradient
    from PyQt6.QtWidgets import (
        QApplication,
        QFrame,
        QGridLayout,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QPushButton,
        QScrollArea,
        QSizePolicy,
        QSpacerItem,
        QStackedWidget,
        QTextEdit,
        QVBoxLayout,
        QWidget,
    )
except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
        "PyQt6 is required for the JARVIS UI. Install it with: pip install PyQt6"
    ) from exc


CYAN = "#00eaff"
CYAN_DIM = "#02708e"
GREEN = "#00ff88"
YELLOW = "#ffd23f"
RED = "#ff2d3a"
BG = "#02070d"
TEXT = "#b9f8ff"


class ReactorState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    THINKING = "thinking"
    SPEAKING = "speaking"
    ERROR = "error"
    STOP = "stop"


class ArcReactorWidget(QWidget):
    """Lightweight animated placeholder for future assistant state visuals."""

    STATE_COLORS = {
        ReactorState.IDLE: QColor(CYAN),
        ReactorState.LISTENING: QColor("#00ffb3"),
        ReactorState.THINKING: QColor("#7cf7ff"),
        ReactorState.SPEAKING: QColor("#3bff75"),
        ReactorState.ERROR: QColor(RED),
        ReactorState.STOP: QColor(RED),
    }

    STATE_PROFILES = {
        ReactorState.IDLE: {"speed": 0.45, "pulse_speed": 1.1, "glow": 0.72, "pulse": 0.07},
        ReactorState.LISTENING: {"speed": 2.4, "pulse_speed": 4.0, "glow": 1.35, "pulse": 0.20},
        ReactorState.THINKING: {"speed": 1.25, "pulse_speed": 1.8, "glow": 0.98, "pulse": 0.10},
        ReactorState.SPEAKING: {"speed": 1.0, "pulse_speed": 5.6, "glow": 1.18, "pulse": 0.24},
        ReactorState.ERROR: {"speed": 0.9, "pulse_speed": 7.5, "glow": 1.55, "pulse": 0.28},
        ReactorState.STOP: {"speed": 0.7, "pulse_speed": 8.0, "glow": 1.5, "pulse": 0.26},
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.state = ReactorState.IDLE
        self.rotation_phase = 0.0
        self.pulse_phase = 0.0
        self.scan_phase = 0.0
        self.state_token = 0
        self.setMinimumSize(360, 360)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.tick)
        self.timer.start(33)

    def set_state(self, state, auto_idle_ms=None):
        self.state = ReactorState(state)
        self.state_token += 1
        token = self.state_token

        if self.state in {ReactorState.ERROR, ReactorState.STOP} and auto_idle_ms is None:
            auto_idle_ms = 900

        if auto_idle_ms:
            QTimer.singleShot(auto_idle_ms, lambda: self._return_to_idle(token))

        self.update()

    def _return_to_idle(self, token):
        if token == self.state_token:
            self.set_state(ReactorState.IDLE)

    def tick(self):
        profile = self.STATE_PROFILES[self.state]
        self.rotation_phase = (self.rotation_phase + profile["speed"]) % 360
        self.pulse_phase = (self.pulse_phase + profile["pulse_speed"]) % 360
        self.scan_phase = (self.scan_phase + 3.2) % 360
        self.update()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 0))

        side = min(self.width(), self.height()) - 24
        cx = self.width() / 2
        cy = self.height() / 2
        radius = side / 2
        base = self.STATE_COLORS[self.state]
        profile = self.STATE_PROFILES[self.state]
        pulse = 1.0 + math.sin(math.radians(self.pulse_phase)) * profile["pulse"]
        glow_power = profile["glow"] * pulse

        glow = QRadialGradient(QPointF(cx, cy), radius)
        glow.setColorAt(0.0, QColor(220, 255, 255, min(255, int(210 * glow_power))))
        glow.setColorAt(0.08, QColor(base.red(), base.green(), base.blue(), min(230, int(135 * glow_power))))
        glow.setColorAt(0.34, QColor(base.red(), base.green(), base.blue(), min(95, int(30 * glow_power))))
        glow.setColorAt(1.0, QColor(0, 0, 0, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), radius, radius)

        self._draw_crosshair(painter, cx, cy, radius, base)
        self._draw_rings(painter, cx, cy, radius, base)
        if self.state == ReactorState.THINKING:
            self._draw_radar_scan(painter, cx, cy, radius, base)
        if self.state == ReactorState.SPEAKING:
            self._draw_speaking_pulse(painter, cx, cy, radius, base)
        if self.state in {ReactorState.ERROR, ReactorState.STOP}:
            self._draw_red_flash(painter, cx, cy, radius)
        self._draw_core(painter, cx, cy, base, pulse)

    def _draw_crosshair(self, painter, cx, cy, radius, color):
        pen = QPen(QColor(color.red(), color.green(), color.blue(), 90), 1)
        painter.setPen(pen)
        painter.drawLine(int(cx - radius * 0.95), int(cy), int(cx + radius * 0.95), int(cy))
        painter.drawLine(int(cx), int(cy - radius * 0.95), int(cx), int(cy + radius * 0.95))

    def _draw_rings(self, painter, cx, cy, radius, color):
        ring_count = 8
        for index in range(ring_count):
            ring_radius = radius * (0.22 + index * 0.095)
            rect = QRectF(cx - ring_radius, cy - ring_radius, ring_radius * 2, ring_radius * 2)
            alpha = max(55, 180 - index * 12)
            width = 1 if index % 2 else 2

            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), width))
            painter.drawEllipse(rect)

            dash_pen = QPen(QColor(color.red(), color.green(), color.blue(), alpha + 20), width + 1)
            dash_pen.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(dash_pen)
            for segment in range(3):
                start = int((self.rotation_phase * (1 if index % 2 else -1)) + segment * 120 + index * 17)
                span = 28 + (index % 3) * 12
                painter.drawArc(rect, start * 16, span * 16)

        tick_pen = QPen(QColor(color.red(), color.green(), color.blue(), 130), 1)
        painter.setPen(tick_pen)
        outer = radius * 0.86
        inner = radius * 0.80
        for degree in range(0, 360, 10):
            angle = math.radians(degree + self.rotation_phase * 0.18)
            length = 1.0 if degree % 30 else 1.9
            x1 = cx + math.cos(angle) * inner
            y1 = cy + math.sin(angle) * inner
            x2 = cx + math.cos(angle) * (outer + length)
            y2 = cy + math.sin(angle) * (outer + length)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

    def _draw_radar_scan(self, painter, cx, cy, radius, color):
        scan_angle = math.radians(self.scan_phase)
        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 170), 2))
        painter.drawLine(
            int(cx),
            int(cy),
            int(cx + math.cos(scan_angle) * radius * 0.82),
            int(cy + math.sin(scan_angle) * radius * 0.82),
        )

        painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), 70), 1))
        for offset in (-10, -20):
            angle = math.radians(self.scan_phase + offset)
            painter.drawLine(
                int(cx),
                int(cy),
                int(cx + math.cos(angle) * radius * 0.72),
                int(cy + math.sin(angle) * radius * 0.72),
            )

    def _draw_speaking_pulse(self, painter, cx, cy, radius, color):
        wave = (math.sin(math.radians(self.pulse_phase)) + 1.0) / 2.0
        for index in range(3):
            ring_radius = radius * (0.22 + index * 0.13 + wave * 0.08)
            alpha = max(30, 120 - index * 30 - int(wave * 34))
            painter.setPen(QPen(QColor(color.red(), color.green(), color.blue(), alpha), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawEllipse(QPointF(cx, cy), ring_radius, ring_radius)

    def _draw_red_flash(self, painter, cx, cy, radius):
        flash = (math.sin(math.radians(self.pulse_phase * 2.2)) + 1.0) / 2.0
        painter.setPen(QPen(QColor(255, 45, 58, int(120 + flash * 100)), 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(cx, cy), radius * 0.93, radius * 0.93)

    def _draw_core(self, painter, cx, cy, color, pulse):
        painter.setPen(QPen(QColor(210, 255, 255, 230), 2))
        painter.setBrush(QBrush(QColor(color.red(), color.green(), color.blue(), 210)))
        painter.drawEllipse(QPointF(cx, cy), 24 * pulse, 24 * pulse)
        painter.setBrush(QBrush(QColor(230, 255, 255, 245)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), 12 * pulse, 12 * pulse)


class MiniMeter(QWidget):
    def __init__(self, value=0.65, color=CYAN, parent=None):
        super().__init__(parent)
        self.value = value
        self.color = QColor(color)
        self.setFixedHeight(16)

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(QPen(QColor(CYAN_DIM), 2))
        y = self.height() - 5
        painter.drawLine(0, y, self.width(), y)
        painter.setPen(QPen(self.color, 3))
        painter.drawLine(0, y, int(self.width() * self.value), y)


class ChatBubble(QFrame):
    def __init__(self, sender, body, assistant=False):
        super().__init__()
        self.setObjectName("assistantBubble" if assistant else "userBubble")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(6)

        header = QLabel(sender.upper())
        header.setObjectName("bubbleHeader")
        text = QLabel(body)
        text.setWordWrap(True)
        text.setObjectName("bubbleText")

        layout.addWidget(header)
        layout.addWidget(text)


class JarvisWorker(QThread):
    command_ready = pyqtSignal(str)
    result_ready = pyqtSignal(dict)

    def __init__(self, command="", use_voice=False, parent=None):
        super().__init__(parent)
        self.command = command
        self.use_voice = use_voice

    def run(self):
        started_at = time.perf_counter()
        try:
            if self.use_voice:
                from voice.listener import listen

                self.command = listen()
                if self.command:
                    self.command_ready.emit(self.command)

            command = self.command.strip()
            if not command:
                self.result_ready.emit(
                    {
                        "response": "I did not catch that. Please try again.",
                        "last_action": "voice input" if self.use_voice else "text input",
                        "current_task": "Waiting for command",
                        "response_time": self._elapsed(started_at),
                        "error": "No command received",
                        "active_model": "idle",
                    }
                )
                return

            from ai.ai_engine import get_ai_response
            from ai.router import choose_model
            from brain.planner import plan
            from executor.executor import execute_plan
            from memory.store import get_context_summary, remember_event

            active_model = choose_model(command)
            decision = plan(command)

            if decision.route in {"action", "ask", "multi"}:
                response = execute_plan(decision)
            elif decision.response:
                response = decision.response
            else:
                response = get_ai_response(command, context=get_context_summary())

            remember_event(command, decision, response)

            self.result_ready.emit(
                {
                    "response": response,
                    "last_action": decision.action or decision.intent or decision.route,
                    "current_task": self._describe_task(decision),
                    "response_time": self._elapsed(started_at),
                    "error": self._detect_error(response),
                    "active_model": active_model,
                }
            )
        except Exception as error:
            self.result_ready.emit(
                {
                    "response": "Something went wrong while processing that command.",
                    "last_action": "error",
                    "current_task": "Command failed",
                    "response_time": self._elapsed(started_at),
                    "error": str(error),
                    "active_model": "unknown",
                }
            )

    def _elapsed(self, started_at):
        return f"{time.perf_counter() - started_at:.2f}s"

    def _describe_task(self, decision):
        parts = [decision.intent or decision.route]
        if decision.target:
            parts.append(str(decision.target))
        if decision.query:
            if isinstance(decision.query, list):
                parts.append(f"{len(decision.query)} steps")
            else:
                parts.append(str(decision.query))
        return " - ".join(parts)

    def _detect_error(self, response):
        if not isinstance(response, str):
            return "None"

        text = response.lower()
        if text.startswith("error:") or "ollama is not running" in text:
            return response
        if "taking too long" in text or "something went wrong" in text:
            return response
        return "None"


class GreetingWorker(QThread):
    def run(self):
        try:
            from voice.speaker import speak

            speak(self._build_greeting())
        except Exception as error:
            print("Greeting TTS error:", error)

    def _build_greeting(self):
        name = self._load_user_name()
        if not name:
            return "Hello, systems are online."

        return f"{self._time_greeting()} {name}, systems are online."

    def _load_user_name(self):
        try:
            from memory.store import load_memory

            memory = load_memory()
        except Exception:
            return ""

        for section in ("preferences", "facts"):
            data = memory.get(section, {})
            if not isinstance(data, dict):
                continue

            for key in ("name", "user_name", "first_name"):
                value = data.get(key)
                if isinstance(value, str) and value.strip():
                    return self._format_name(value)

        return ""

    def _format_name(self, name):
        return " ".join(part.capitalize() for part in name.strip().split())

    def _time_greeting(self):
        hour = time.localtime().tm_hour
        if hour < 12:
            return "Good morning"
        if hour < 17:
            return "Good afternoon"
        return "Good evening"


class BootWindow(QFrame):
    finished = pyqtSignal()

    BOOT_STEPS = [
        "Initializing systems",
        "Loading memory",
        "Voice module online",
        "AI core online",
    ]

    def __init__(self):
        super().__init__()
        self.step_index = 0
        self.setObjectName("bootWindow")
        self.setWindowTitle("J.A.R.V.I.S Boot")
        self.resize(720, 420)
        self.setStyleSheet(self._style())

        layout = QVBoxLayout(self)
        layout.setContentsMargins(42, 36, 42, 36)
        layout.setSpacing(16)

        title = QLabel("J . A . R . V . I . S")
        title.setObjectName("bootTitle")
        self.status_label = QLabel(self.BOOT_STEPS[0])
        self.status_label.setObjectName("bootStatus")
        self.log_label = QLabel("")
        self.log_label.setObjectName("bootLog")
        self.log_label.setWordWrap(True)

        layout.addStretch(1)
        layout.addWidget(title, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.log_label)
        layout.addStretch(1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._advance)
        self.timer.start(650)

    def _advance(self):
        completed = self.BOOT_STEPS[: self.step_index + 1]
        self.log_label.setText("\n".join(f"OK {step}" for step in completed))
        self.step_index += 1

        if self.step_index < len(self.BOOT_STEPS):
            self.status_label.setText(self.BOOT_STEPS[self.step_index])
            return

        self.timer.stop()
        QTimer.singleShot(450, self.finished.emit)

    def _style(self):
        return f"""
        #bootWindow {{
            background: qradialgradient(cx:0.5, cy:0.4, radius:0.8, stop:0 #062033, stop:1 {BG});
            border: 1px solid {CYAN_DIM};
        }}
        #bootTitle {{
            color: {CYAN};
            font-family: Consolas, 'Cascadia Mono', monospace;
            font-size: 30px;
            font-weight: 800;
        }}
        #bootStatus {{
            color: {GREEN};
            font-family: Consolas, 'Cascadia Mono', monospace;
            font-size: 20px;
        }}
        #bootLog {{
            color: #73cfe2;
            border: 1px solid {CYAN_DIM};
            border-radius: 6px;
            background: rgba(3, 17, 27, 205);
            padding: 16px;
            font-family: Consolas, 'Cascadia Mono', monospace;
            font-size: 14px;
        }}
        """


class JarvisWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.started_at = time.monotonic()
        self.worker = None
        self.nav_buttons = {}
        self.page_indexes = {}
        self.runtime_values = {}
        self.setWindowTitle("J.A.R.V.I.S")
        self.resize(1440, 900)
        self.setMinimumSize(1120, 760)

        self.clock_label = QLabel()
        self.uptime_value = QLabel("00h 00m")

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_top_bar())
        outer.addWidget(self._build_body(), 1)
        outer.addWidget(self._build_bottom_bar())

        self.setStyleSheet(self._style())
        self._seed_clock()

        self.clock_timer = QTimer(self)
        self.clock_timer.timeout.connect(self._seed_clock)
        self.clock_timer.start(1000)

    def _build_top_bar(self):
        bar = QFrame()
        bar.setObjectName("topBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(26, 14, 26, 14)

        title = QLabel("J . A . R . V . I . S")
        title.setObjectName("brand")
        status = QLabel("ONLINE")
        status.setObjectName("online")
        model = QLabel("ollama:mistral")
        model.setObjectName("modelPill")
        api = QLabel("API // ACTIVE")
        api.setObjectName("apiStatus")

        layout.addWidget(title)
        layout.addStretch(1)
        layout.addWidget(status)
        layout.addWidget(model)
        layout.addSpacing(16)
        layout.addWidget(api)
        layout.addSpacing(30)
        layout.addWidget(self.clock_label)
        self.clock_label.setObjectName("clock")
        return bar

    def _build_body(self):
        body = QFrame()
        body.setObjectName("body")
        layout = QHBoxLayout(body)
        layout.setContentsMargins(18, 0, 18, 0)
        layout.setSpacing(18)

        layout.addWidget(self._build_left_panel(), 0)
        layout.addWidget(self._build_center_stack(), 1)
        layout.addWidget(self._build_right_panel(), 0)
        return body

    def _build_left_panel(self):
        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(310)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(12)

        layout.addWidget(self._section_label("// navigation"))
        for index, (label, dot) in enumerate([
            ("Chat Interface", GREEN),
            ("Memory", YELLOW),
            ("Voice Mode", GREEN),
            ("Automation", YELLOW),
            ("Model Toggle", GREEN),
            ("Settings", CYAN),
        ]):
            button = self._nav_button(label, dot)
            button.clicked.connect(lambda checked=False, page=label: self._switch_page(page))
            self.nav_buttons[label] = button
            layout.addWidget(button)
            if index == 0:
                button.setProperty("active", True)

        layout.addSpacing(12)
        layout.addWidget(self._section_label("// system"))
        layout.addWidget(self._build_system_metrics_panel(), 1)
        return panel

    def _build_center_stack(self):
        self.center_stack = QStackedWidget()
        self.center_stack.setObjectName("centerStack")

        pages = [
            ("Chat Interface", self._build_center_panel()),
            (
                "Memory",
                self._build_placeholder_page(
                    "Memory",
                    [
                        ("CONTEXT STATUS", "Memory store online"),
                        ("RECENT EVENTS", "Conversation and command history ready"),
                        ("PREFERENCES", "Saved preferences will appear here"),
                    ],
                ),
            ),
            (
                "Voice Mode",
                self._build_placeholder_page(
                    "Voice Mode",
                    [
                        ("INPUT", "Microphone listener ready"),
                        ("LANGUAGE", "Recognition configured for en-IN"),
                        ("OUTPUT", "Speech response controls reserved"),
                    ],
                ),
            ),
            (
                "Automation",
                self._build_placeholder_page(
                    "Automation",
                    [
                        ("ACTIONS", "App and browser commands available"),
                        ("QUEUE", "No active automation queue"),
                        ("SAFETY", "Manual stop control armed"),
                    ],
                ),
            ),
            (
                "Model Toggle",
                self._build_placeholder_page(
                    "Model Toggle",
                    [
                        ("ACTIVE ROUTER", "Automatic model selection"),
                        ("FAST MODEL", "phi3"),
                        ("DEEP MODEL", "llama3"),
                    ],
                ),
            ),
            (
                "Settings",
                self._build_placeholder_page(
                    "Settings",
                    [
                        ("INTERFACE", "JARVIS visual profile active"),
                        ("BACKEND", "Planner, executor, AI, memory linked"),
                        ("SYSTEM", "Local runtime settings reserved"),
                    ],
                ),
            ),
        ]

        for page_name, widget in pages:
            self.page_indexes[page_name] = self.center_stack.addWidget(widget)

        return self.center_stack

    def _build_center_panel(self):
        panel = QFrame()
        panel.setObjectName("centerPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 14, 6, 18)
        layout.setSpacing(12)

        self.reactor = ArcReactorWidget()
        layout.addWidget(self.reactor, 5)

        layout.addWidget(self._section_label("// conversation"))
        layout.addWidget(self._build_chat_area(), 4)
        layout.addWidget(self._build_input_controls())
        return panel

    def _build_placeholder_page(self, title, cards):
        panel = QFrame()
        panel.setObjectName("centerPanel")
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(6, 24, 6, 18)
        layout.setSpacing(16)

        layout.addWidget(self._section_label(f"// {title.lower()}"))

        header = QFrame()
        header.setObjectName("pageHeader")
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(22, 18, 22, 18)
        header_layout.setSpacing(6)

        title_label = QLabel(title.upper())
        title_label.setObjectName("pageTitle")
        subtitle = QLabel("Module panel ready for backend controls")
        subtitle.setObjectName("pageSubtitle")

        header_layout.addWidget(title_label)
        header_layout.addWidget(subtitle)
        layout.addWidget(header)

        grid = QGridLayout()
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(14)
        for index, (card_title, card_value) in enumerate(cards):
            grid.addWidget(self._module_card(card_title, card_value), index // 2, index % 2)
        layout.addLayout(grid)
        layout.addStretch(1)
        return panel

    def _module_card(self, title, value):
        card = QFrame()
        card.setObjectName("moduleCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(18, 16, 18, 16)
        layout.setSpacing(8)

        title_label = QLabel(title)
        title_label.setObjectName("smallLabel")
        value_label = QLabel(value)
        value_label.setObjectName("moduleValue")
        value_label.setWordWrap(True)

        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card

    def _build_chat_area(self):
        scroll = QScrollArea()
        scroll.setObjectName("chatScroll")
        scroll.setWidgetResizable(True)
        content = QWidget()
        self.chat_layout = QVBoxLayout(content)
        self.chat_layout.setContentsMargins(8, 8, 8, 8)
        self.chat_layout.setSpacing(10)

        self.chat_layout.addWidget(ChatBubble("J.A.R.V.I.S", "Good evening, Sir.\nArc reactor stable. Neural pathways fully operational.\nHow may I assist you?", True))
        self.chat_layout.addWidget(ChatBubble("You", "Open YouTube and play lo-fi music."))
        self.chat_layout.addWidget(ChatBubble("J.A.R.V.I.S", "Opening YouTube...\nPlaying lo-fi music for you, Sir.\nTask completed successfully.", True))
        self.chat_layout.addStretch(1)
        scroll.setWidget(content)
        self.chat_scroll = scroll
        return scroll

    def _build_input_controls(self):
        area = QFrame()
        area.setObjectName("inputArea")
        layout = QGridLayout(area)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(14)
        layout.setVerticalSpacing(14)

        self.voice_button = QPushButton("VOICE")
        self.text_button = QPushButton("TEXT")
        self.stop_button = QPushButton("STOP")
        self.stop_button.setObjectName("stopButton")
        self.command_input = QLineEdit()
        self.command_input.setPlaceholderText("// command input...")
        self.send_button = QPushButton("SEND")
        self.send_button.setObjectName("sendButton")

        layout.addWidget(self.voice_button, 0, 0)
        layout.addWidget(self.text_button, 0, 1)
        layout.addWidget(self.stop_button, 0, 2)
        layout.addWidget(self.command_input, 1, 0, 1, 2)
        layout.addWidget(self.send_button, 1, 2)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)

        self.send_button.clicked.connect(self._send_text_command)
        self.command_input.returnPressed.connect(self._send_text_command)
        self.voice_button.clicked.connect(self._send_voice_command)
        self.stop_button.clicked.connect(self._stop_current_task)
        return area

    def _build_right_panel(self):
        panel = QFrame()
        panel.setObjectName("sidePanel")
        panel.setFixedWidth(340)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 24, 0, 24)
        layout.setSpacing(12)

        layout.addWidget(self._section_label("// runtime info"))
        for key, title, value, accent in [
            ("last_action", "LAST ACTION", "Idle", CYAN),
            ("active_model", "ACTIVE MODEL", "idle", GREEN),
            ("current_task", "CURRENT TASK", "Waiting for command", CYAN),
            ("response_time", "RESPONSE TIME", "--", CYAN),
            ("errors", "ERRORS", "None", GREEN),
            ("voice_mode", "VOICE MODE", "Ready (Indian Accent)", GREEN),
        ]:
            layout.addWidget(self._info_card(title, value, accent, key))

        layout.addSpacing(18)
        layout.addWidget(self._section_label("// event log"))
        layout.addWidget(self._event_log(), 1)
        return panel

    def _build_bottom_bar(self):
        bar = QFrame()
        bar.setObjectName("bottomBar")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(18)

        layout.addWidget(self._bottom_identity())
        for title, value in [
            ("LATENCY", "42ms"),
            ("QUERIES", "128"),
            ("UPTIME", "2d 14h"),
            ("ACTIVE MODEL", "ollama: mistral"),
            ("BATTERY", "82%"),
        ]:
            layout.addWidget(self._bottom_cell(title, value))
        layout.addWidget(self._bottom_security())
        return bar

    def _bottom_identity(self):
        box = QFrame()
        box.setObjectName("bottomIdentity")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(12, 2, 12, 2)
        time_label = QLabel("17:52:39")
        time_label.setObjectName("bottomTime")
        date_label = QLabel("SUN 26 APR 2026")
        date_label.setObjectName("smallLabel")
        layout.addWidget(time_label)
        layout.addWidget(date_label)
        return box

    def _bottom_cell(self, title, value):
        cell = QFrame()
        cell.setObjectName("bottomCell")
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(18, 8, 18, 8)
        value_label = QLabel(value)
        value_label.setObjectName("bottomValue")
        title_label = QLabel(title)
        title_label.setObjectName("smallLabel")
        layout.addWidget(value_label, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title_label, alignment=Qt.AlignmentFlag.AlignCenter)
        return cell

    def _bottom_security(self):
        box = QFrame()
        box.setObjectName("bottomSecurity")
        layout = QVBoxLayout(box)
        layout.setContentsMargins(18, 8, 18, 8)
        layout.addWidget(QLabel("STARK INDUSTRIES // JARVIS v3.14"))
        layout.addWidget(QLabel("CLEARANCE LEVEL 7"))
        layout.addWidget(QLabel("UNRESTRICTED ACCESS"))
        return box

    def _nav_button(self, label, dot_color):
        button = QPushButton(label)
        button.setObjectName("navButton")
        button.setProperty("dotColor", dot_color)
        button.setProperty("active", False)
        button.setMinimumHeight(54)
        return button

    def _metric(self, title, value, meter_value, color, meter=True):
        box = QFrame()
        box.setObjectName("metricBox")
        box.setMinimumHeight(76 if meter else 60)
        layout = QVBoxLayout(box)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("smallLabel")
        title_label.setMinimumHeight(14)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        value_label = QLabel(value)
        value_label.setObjectName("metricValue")
        value_label.setMinimumHeight(24)
        value_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(title_label, 0)
        layout.addWidget(value_label, 0)
        if meter:
            layout.addWidget(MiniMeter(meter_value, color), 0)
        return box

    def _build_system_metrics_panel(self):
        scroll = QScrollArea()
        scroll.setObjectName("systemMetricsScroll")
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        content = QWidget()
        content.setObjectName("systemMetricsContent")
        layout = QVBoxLayout(content)
        layout.setContentsMargins(18, 6, 18, 6)
        layout.setSpacing(5)

        layout.addWidget(self._metric("LATENCY", "42ms", 0.58, GREEN))
        layout.addWidget(self._metric("UPTIME", "2d 14h 37m", 0.0, CYAN, meter=False))
        layout.addWidget(self._metric("CPU USAGE", "23%", 0.23, CYAN))
        layout.addWidget(self._metric("MEMORY USAGE", "5.1 GB / 15.8 GB", 0.32, CYAN))
        layout.addWidget(self._metric("BATTERY", "82%", 0.82, GREEN))
        layout.addStretch(1)

        scroll.setWidget(content)
        return scroll

    def _info_card(self, title, value, accent, key=None):
        card = QFrame()
        card.setObjectName("infoCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(16, 12, 16, 12)
        title_label = QLabel(title)
        title_label.setObjectName("smallLabel")
        value_label = QLabel(value)
        value_label.setStyleSheet(f"color: {accent};")
        value_label.setWordWrap(True)
        if key:
            self.runtime_values[key] = value_label
        layout.addWidget(title_label)
        layout.addWidget(value_label)
        return card

    def _send_text_command(self):
        command = self.command_input.text().strip()
        if not command or self._worker_is_running():
            return

        self.command_input.clear()
        self._append_chat("You", command, assistant=False)
        self._start_worker(command=command)

    def _send_voice_command(self):
        if self._worker_is_running():
            return

        self._set_runtime("voice_mode", "Listening...")
        self._set_runtime("current_task", "Capturing voice input")
        self._start_worker(use_voice=True)

    def _start_worker(self, command="", use_voice=False):
        self._set_busy(True)
        self._set_runtime("errors", "None")
        self._set_runtime("last_action", "Listening" if use_voice else "Processing")
        self._set_runtime("current_task", "Capturing voice input" if use_voice else command)
        self._set_runtime("active_model", "resolving...")
        self._set_runtime("response_time", "--")
        self.reactor.set_state(ReactorState.LISTENING if use_voice else ReactorState.THINKING)

        self.worker = JarvisWorker(command=command, use_voice=use_voice, parent=self)
        self.worker.command_ready.connect(self._handle_voice_command)
        self.worker.result_ready.connect(self._handle_worker_finished)
        self.worker.finished.connect(self.worker.deleteLater)
        self.worker.start()

    def _handle_voice_command(self, command):
        self._append_chat("You", command, assistant=False)
        self._set_runtime("voice_mode", "Processing speech")
        self._set_runtime("current_task", command)
        self.reactor.set_state(ReactorState.THINKING)

    def _handle_worker_finished(self, result):
        response = result.get("response") or "I do not have a response yet."
        self._append_chat("J.A.R.V.I.S", response, assistant=True)
        self._set_runtime("last_action", result.get("last_action", "Complete"))
        self._set_runtime("active_model", result.get("active_model", "unknown"))
        self._set_runtime("current_task", result.get("current_task", "Idle"))
        self._set_runtime("response_time", result.get("response_time", "--"))
        self._set_runtime("errors", result.get("error", "None") or "None")
        self._set_runtime("voice_mode", "Ready (Indian Accent)")

        has_error = (result.get("error") or "None") != "None"
        if has_error:
            self.reactor.set_state(ReactorState.ERROR)
        else:
            self.reactor.set_state(ReactorState.SPEAKING, auto_idle_ms=1400)
        self._set_busy(False)
        self.worker = None

    def _stop_current_task(self):
        if self._worker_is_running():
            self._set_runtime("last_action", "Stop requested")
            self._set_runtime("current_task", "Waiting for backend call to finish")
            self._set_runtime("errors", "Stop cannot interrupt an active backend call yet")
            self.reactor.set_state(ReactorState.STOP)
            self.stop_button.setEnabled(False)
            return

        self.command_input.clear()
        self._set_runtime("last_action", "Stopped")
        self._set_runtime("current_task", "Idle")
        self._set_runtime("errors", "None")
        self.reactor.set_state(ReactorState.STOP)

    def _append_chat(self, sender, body, assistant=False):
        insert_at = max(0, self.chat_layout.count() - 1)
        self.chat_layout.insertWidget(insert_at, ChatBubble(sender, body, assistant))
        QTimer.singleShot(0, self._scroll_chat_to_bottom)

    def _scroll_chat_to_bottom(self):
        bar = self.chat_scroll.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _set_runtime(self, key, value):
        label = self.runtime_values.get(key)
        if label:
            label.setText(str(value))

    def _set_busy(self, busy):
        self.send_button.setEnabled(not busy)
        self.voice_button.setEnabled(not busy)
        self.text_button.setEnabled(not busy)
        self.command_input.setEnabled(not busy)
        self.stop_button.setEnabled(True)

    def _worker_is_running(self):
        return self.worker is not None and self.worker.isRunning()

    def _event_log(self):
        log = QTextEdit()
        log.setObjectName("eventLog")
        log.setReadOnly(True)
        log.setText(
            "OK SYSTEM BOOT                  17:50:12\n"
            "OK CORE INIT                    17:50:13\n"
            "OK MEMORY LOAD                  17:50:14\n"
            "OK MODEL READY                  17:50:18\n"
            "OK API LINKED                   17:50:20\n"
            "OK USER CONNECTED               17:50:25\n"
            "OK COMMAND RECEIVED             17:52:37\n"
            "OK TASK COMPLETED               17:52:38"
        )
        return log

    def _section_label(self, text):
        label = QLabel(text)
        label.setObjectName("sectionLabel")
        return label

    def _switch_page(self, page_name):
        index = self.page_indexes.get(page_name)
        if index is None:
            return

        self.center_stack.setCurrentIndex(index)
        for name, button in self.nav_buttons.items():
            button.setProperty("active", name == page_name)
            button.style().unpolish(button)
            button.style().polish(button)
            button.update()

    def _seed_clock(self):
        now = time.localtime()
        self.clock_label.setText(time.strftime("%H:%M:%S", now))
        elapsed = int(time.monotonic() - self.started_at)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        self.uptime_value.setText(f"{hours:02d}h {minutes:02d}m")

    def _style(self):
        return f"""
        QWidget {{
            background: {BG};
            color: {TEXT};
            font-family: Consolas, 'Cascadia Mono', monospace;
            font-size: 14px;
        }}
        #topBar, #bottomBar {{
            border-color: {CYAN_DIM};
            border-style: solid;
            background: #01060b;
        }}
        #topBar {{
            border-width: 0 0 1px 0;
        }}
        #bottomBar {{
            border-width: 1px 0 0 0;
        }}
        #brand {{
            color: {CYAN};
            font-size: 24px;
            font-weight: 700;
            letter-spacing: 0;
        }}
        #clock {{
            color: {CYAN};
            font-size: 24px;
        }}
        #online {{
            color: {GREEN};
            padding: 2px 8px;
        }}
        #apiStatus, #smallLabel, #sectionLabel {{
            color: #0e8fb0;
            font-size: 12px;
            font-weight: 700;
        }}
        #modelPill {{
            color: {CYAN};
            border: 1px solid {CYAN_DIM};
            border-radius: 5px;
            padding: 5px 18px;
            background: #03111b;
        }}
        #body {{
            background: qradialgradient(cx:0.5, cy:0.2, radius:0.8, stop:0 #062033, stop:1 {BG});
        }}
        #sidePanel {{
            border-color: {CYAN_DIM};
            border-style: solid;
            border-width: 0 1px 0 1px;
            background: rgba(1, 11, 18, 180);
        }}
        #centerPanel {{
            background: transparent;
        }}
        #centerStack {{
            background: transparent;
            border: 0;
        }}
        QPushButton {{
            color: {CYAN};
            border: 1px solid {CYAN};
            border-radius: 6px;
            background: rgba(0, 42, 58, 110);
            padding: 14px 18px;
            font-size: 15px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: rgba(0, 234, 255, 35);
        }}
        #navButton {{
            text-align: left;
            padding-left: 24px;
            margin: 0 18px;
            border-color: {CYAN_DIM};
        }}
        #navButton[active="true"] {{
            color: #e8fdff;
            border-color: {CYAN};
            background: rgba(0, 234, 255, 45);
        }}
        #stopButton {{
            color: {RED};
            border-color: {RED};
            background: rgba(255, 45, 58, 34);
        }}
        #sendButton {{
            font-size: 17px;
        }}
        #sectionLabel {{
            padding: 8px 24px;
            border-bottom: 1px solid #063044;
        }}
        #metricBox {{
            border-bottom: 1px solid #063044;
            margin: 0;
            padding: 1px 0 2px 0;
        }}
        #metricValue {{
            color: {CYAN};
            font-size: 21px;
            padding: 1px 0 2px 0;
        }}
        #systemMetricsScroll, #systemMetricsContent {{
            border: 0;
            background: transparent;
        }}
        #infoCard, #assistantBubble, #userBubble, #bottomCell, #bottomSecurity, #pageHeader, #moduleCard {{
            border: 1px solid {CYAN_DIM};
            border-radius: 6px;
            background: rgba(3, 17, 27, 205);
        }}
        #infoCard {{
            margin: 0 18px;
        }}
        #pageHeader {{
            margin: 0 18px;
        }}
        #pageTitle {{
            color: {CYAN};
            font-size: 28px;
            font-weight: 800;
        }}
        #pageSubtitle {{
            color: #73cfe2;
            font-size: 14px;
        }}
        #moduleCard {{
            min-height: 110px;
        }}
        #moduleValue {{
            color: {TEXT};
            font-size: 16px;
        }}
        #chatScroll {{
            border: 1px solid {CYAN_DIM};
            border-radius: 6px;
            background: rgba(1, 11, 18, 205);
        }}
        QScrollBar:vertical {{
            background: #03111b;
            width: 10px;
            margin: 2px;
        }}
        QScrollBar::handle:vertical {{
            background: #136b91;
            border-radius: 4px;
        }}
        #assistantBubble {{
            border-color: #075d7c;
            background: rgba(0, 39, 56, 180);
        }}
        #userBubble {{
            border-color: #063044;
            background: rgba(8, 20, 32, 205);
        }}
        #bubbleHeader {{
            color: {CYAN};
            font-size: 13px;
            font-weight: 800;
        }}
        #bubbleText {{
            color: {TEXT};
            line-height: 150%;
        }}
        QLineEdit {{
            color: #111820;
            background: #f7fbff;
            border: 1px solid #8fb8c6;
            border-radius: 6px;
            padding: 18px 24px;
            font-size: 22px;
        }}
        QLineEdit::placeholder {{
            color: #68737d;
        }}
        #eventLog {{
            border: 1px solid {CYAN_DIM};
            border-radius: 6px;
            background: rgba(1, 11, 18, 205);
            color: {GREEN};
            margin: 0 18px;
            padding: 12px;
            font-size: 12px;
        }}
        #bottomIdentity {{
            min-width: 260px;
            border: 0;
        }}
        #bottomTime {{
            color: {CYAN};
            font-size: 28px;
        }}
        #bottomValue {{
            color: {CYAN};
            font-size: 18px;
        }}
        #bottomSecurity {{
            color: {CYAN};
            min-width: 300px;
            font-size: 12px;
        }}
        """


def launch_ui():
    app = QApplication.instance() or QApplication(sys.argv)
    holders = {"main": None, "boot": BootWindow(), "greeting": None}

    def show_main_ui():
        holders["main"] = JarvisWindow()
        holders["main"].show()
        holders["boot"].close()
        holders["greeting"] = GreetingWorker()
        holders["greeting"].start()

    holders["boot"].finished.connect(show_main_ui)
    holders["boot"].show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(launch_ui())
