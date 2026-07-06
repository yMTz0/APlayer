"""Tela de carregamento (splash) — Frutiger Aero dark, com logo e animação."""
from PySide6.QtCore import (Qt, QTimer, QPropertyAnimation, QEasingCurve,
                            QAbstractAnimation, Signal)
from PySide6.QtGui import QPixmap, QFont, QGuiApplication
from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QProgressBar,
                               QGraphicsOpacityEffect)

from utils import logo_path
from widgets import (SKY_TOP, SKY_MID, BACKDROP_BOTTOM, TEAL, TEAL_HOVER,
                     TEAL_DARK, TEXT_PRIMARY, TEXT_SECONDARY, BG_DARK)


class SplashScreen(QWidget):
    finished = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.SplashScreen
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setFixedSize(480, 540)
        self._center()

        panel = QWidget(self)
        panel.setObjectName("panel")
        panel.setGeometry(0, 0, 480, 540)
        panel.setStyleSheet(f"""
            #panel {{
                background: qlineargradient(x1:0, y1:0, x2:0.4, y2:1,
                    stop:0 {SKY_TOP}, stop:0.5 {SKY_MID}, stop:1 {BACKDROP_BOTTOM});
                border-radius: 28px;
                border: 1px solid rgba(255,255,255,0.14);
            }}
        """)

        layout = QVBoxLayout(panel)
        layout.setContentsMargins(40, 44, 40, 40)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # --- Logo ---
        self._logo = QLabel()
        self._logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lp = logo_path()
        if lp:
            pix = QPixmap(lp).scaled(
                260, 260, Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation)
            self._logo.setPixmap(pix)
        else:
            self._logo.setText("▶")
            self._logo.setFont(QFont("Segoe UI", 90, QFont.Weight.Black))
            self._logo.setStyleSheet(f"color: {TEAL}; background: transparent;")
        self._logo.setFixedHeight(270)
        layout.addWidget(self._logo)

        # --- Título ---
        title = QLabel("APlayer")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setFont(QFont("Segoe UI", 26, QFont.Weight.Black))
        title.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; letter-spacing: 3px;")
        layout.addWidget(title)

        subtitle = QLabel("MEDIA CENTER")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setFont(QFont("Segoe UI", 9, QFont.Weight.DemiBold))
        subtitle.setStyleSheet(f"color: {TEAL}; background: transparent; letter-spacing: 6px;")
        layout.addWidget(subtitle)

        layout.addSpacing(28)

        # --- Barra de carregamento (glossy, indeterminada) ---
        self._bar = QProgressBar()
        self._bar.setRange(0, 0)  # modo "busy"
        self._bar.setTextVisible(False)
        self._bar.setFixedHeight(6)
        self._bar.setStyleSheet(f"""
            QProgressBar {{
                background: rgba(255,255,255,0.08);
                border: 1px solid rgba(255,255,255,0.10);
                border-radius: 3px;
            }}
            QProgressBar::chunk {{
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 {TEAL_DARK}, stop:0.5 {TEAL_HOVER}, stop:1 {TEAL_DARK});
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self._bar)

        layout.addSpacing(12)
        self._status = QLabel("carregando…")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setFont(QFont("Segoe UI", 9))
        self._status.setStyleSheet(f"color: {TEXT_SECONDARY}; background: transparent;")
        layout.addWidget(self._status)

        # Pulso suave no logo
        self._logo_fx = QGraphicsOpacityEffect(self._logo)
        self._logo.setGraphicsEffect(self._logo_fx)
        self._pulse = QPropertyAnimation(self._logo_fx, b"opacity", self)
        self._pulse.setDuration(1400)
        self._pulse.setStartValue(0.55)
        self._pulse.setKeyValueAt(0.5, 1.0)
        self._pulse.setEndValue(0.55)
        self._pulse.setLoopCount(-1)
        self._pulse.setEasingCurve(QEasingCurve.Type.InOutSine)

        self.setWindowOpacity(0.0)

    def _center(self):
        screen = QGuiApplication.primaryScreen().availableGeometry()
        self.move(screen.center().x() - self.width() // 2,
                  screen.center().y() - self.height() // 2)

    def showEvent(self, event):
        super().showEvent(event)
        self._pulse.start()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(320)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._in_anim = anim

    def finish(self):
        """Fade-out e fecha, emitindo `finished`."""
        self._pulse.stop()
        anim = QPropertyAnimation(self, b"windowOpacity", self)
        anim.setDuration(360)
        anim.setStartValue(1.0)
        anim.setEndValue(0.0)
        anim.setEasingCurve(QEasingCurve.Type.InCubic)

        def _done():
            self.close()
            self.finished.emit()

        anim.finished.connect(_done)
        anim.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)
        self._out_anim = anim
