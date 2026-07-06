from PySide6.QtCore import Qt, Signal, QSize, QUrl
from PySide6.QtGui import QPalette, QColor, QFont, QPixmap, QCursor
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

# ----- Paleta Frutiger Aero DARK (vidro fosco escuro, aqua/teal glow) -----
# Tons do fundo (gradiente teal-navy profundo)
SKY_TOP = "#0f3d49"
SKY_MID = "#0a2d38"
BACKDROP_BOTTOM = "#061a21"
# Acentos aqua brilhantes (poster placeholder, brilhos)
AQUA = "#1f8fa8"
AQUA_DEEP = "#0c5566"

TEAL = "#2dd4bf"
TEAL_DARK = "#14b8a6"
TEAL_HOVER = "#5eead4"
GREEN = "#4ade80"

# Superfícies de vidro fosco escuro (translúcidas sobre o fundo)
GLASS = "rgba(255, 255, 255, 0.07)"
GLASS_HI = "rgba(255, 255, 255, 0.13)"
GLOSS = "rgba(255, 255, 255, 0.22)"

BG_DARK = "#04161c"          # texto escuro sobre acentos claros (badges/botões teal)
BG_CARD = GLASS
BG_CARD_HOVER = GLASS_HI
BG_SURFACE = "rgba(255, 255, 255, 0.06)"
BG_INPUT = "rgba(255, 255, 255, 0.10)"
TEXT_PRIMARY = "#e6f6fa"
TEXT_SECONDARY = "#8fb3bd"
BORDER = "rgba(255, 255, 255, 0.16)"
BORDER_SOFT = "rgba(255, 255, 255, 0.10)"
DUB_COLOR = "#f472b6"
LEG_COLOR = "#38bdf8"

# Gradientes reutilizáveis
BACKDROP = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
            f"stop:0 {SKY_TOP}, stop:0.45 {SKY_MID}, stop:1 {BACKDROP_BOTTOM})")
GLASS_PANEL = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
               "stop:0 rgba(255,255,255,0.15), stop:0.5 rgba(255,255,255,0.06), "
               "stop:1 rgba(255,255,255,0.03))")
GLASS_BAR = ("qlineargradient(x1:0, y1:0, x2:0, y2:1, "
             "stop:0 rgba(255,255,255,0.11), stop:1 rgba(255,255,255,0.04))")
GLOSS_BTN = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
             f"stop:0 {TEAL_HOVER}, stop:0.5 {TEAL}, stop:0.5 {TEAL_DARK}, stop:1 {TEAL})")
GLOSS_BTN_HI = (f"qlineargradient(x1:0, y1:0, x2:0, y2:1, "
                f"stop:0 #7ff0e2, stop:0.5 {TEAL_HOVER}, stop:0.5 {TEAL}, stop:1 {TEAL_HOVER})")

_net_manager: QNetworkAccessManager | None = None


def _network() -> QNetworkAccessManager:
    """QNetworkAccessManager único, parentado ao QApplication (vive o app todo).
    Nunca é destruído durante a navegação — assim replies em voo não crasham
    quando um card é removido; a validade do label é conferida no callback."""
    global _net_manager
    if _net_manager is None:
        _net_manager = QNetworkAccessManager(QApplication.instance())
    return _net_manager


def _load_image_async(url: str, label: QLabel, size: QSize):
    """Baixa uma imagem com headers de browser e a define no `label`.

    Se o card/label for destruído antes da resposta chegar, o callback detecta
    via shiboken6.isValid e simplesmente ignora — sem tocar objeto C++ morto.
    """
    if not url:
        return
    import shiboken6
    from utils import get_default_headers

    headers = get_default_headers()
    req = QNetworkRequest(QUrl(url))
    req.setRawHeader(b"User-Agent", headers["User-Agent"].encode())
    req.setRawHeader(b"Referer", headers["Referer"].encode())
    reply = _network().get(req)

    def _done():
        try:
            ok = reply.error() == QNetworkReply.NetworkError.NoError
            data = reply.readAll().data() if ok else b""
        finally:
            reply.deleteLater()
        if ok and shiboken6.isValid(label):
            pix = QPixmap()
            pix.loadFromData(data)
            if not pix.isNull():
                label.setPixmap(pix.scaled(
                    size,
                    Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                    Qt.TransformationMode.SmoothTransformation,
                ))

    reply.finished.connect(_done)


def apply_dark_theme(app: QApplication) -> None:
    """Aplica o tema Frutiger Aero (vidro glossy sobre gradiente aqua)."""
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(SKY_MID))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Base, QColor(SKY_MID))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(SKY_TOP))
    palette.setColor(QPalette.ColorRole.Text, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Button, QColor(SKY_TOP))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(TEXT_PRIMARY))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(TEAL))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(BG_DARK))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(TEXT_SECONDARY))
    app.setPalette(palette)
    app.setFont(QFont("Segoe UI", 10))

    app.setStyleSheet(f"""
        QWidget {{ color: {TEXT_PRIMARY}; }}
        QToolTip {{
            background: {GLASS_HI}; color: {TEXT_PRIMARY};
            border: 1px solid {BORDER}; padding: 4px 8px; border-radius: 6px;
        }}
        QScrollBar:vertical {{ background: transparent; width: 12px; margin: 3px; }}
        QScrollBar::handle:vertical {{
            background: {GLOSS_BTN}; min-height: 36px; border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.6); }}
        QScrollBar::handle:vertical:hover {{ background: {GLOSS_BTN_HI}; }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
        QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 3px; }}
        QScrollBar::handle:horizontal {{
            background: {GLOSS_BTN}; min-width: 36px; border-radius: 6px;
            border: 1px solid rgba(255,255,255,0.6); }}
        QScrollBar::handle:horizontal:hover {{ background: {GLOSS_BTN_HI}; }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    """)


def _audio_badge(audio: str) -> tuple[str, str] | None:
    a = (audio or "").lower()
    if a in ("ptbr", "dub", "dublado"):
        return "DUB", DUB_COLOR
    if a in ("jap", "leg", "legendado"):
        return "LEG", LEG_COLOR
    return None


class SearchWidget(QWidget):
    search_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        self._input = QLineEdit()
        self._input.setPlaceholderText("🔍  Buscar anime…")
        self._input.setMinimumHeight(42)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: {GLASS_HI}; color: {TEXT_PRIMARY};
                border: 1px solid {BORDER}; border-radius: 21px;
                padding: 8px 20px; font-size: 14px;
                selection-background-color: {TEAL};
            }}
            QLineEdit:focus {{ border: 2px solid {TEAL}; background: rgba(255,255,255,0.16); }}
        """)
        self._input.returnPressed.connect(self._on_search)
        layout.addWidget(self._input)

        self._btn = QPushButton("Buscar")
        self._btn.setMinimumHeight(42)
        self._btn.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self._btn.setStyleSheet(f"""
            QPushButton {{
                background: {GLOSS_BTN}; color: #ffffff;
                border: 1px solid rgba(255,255,255,0.7); border-radius: 21px;
                padding: 8px 28px; font-size: 14px; font-weight: 700;
            }}
            QPushButton:hover {{ background: {GLOSS_BTN_HI}; }}
            QPushButton:pressed {{ background: {TEAL_DARK}; }}
            QPushButton:disabled {{ background: rgba(255,255,255,0.5); color: {TEXT_SECONDARY};
                border: 1px solid {BORDER}; }}
        """)
        self._btn.clicked.connect(self._on_search)
        layout.addWidget(self._btn)

    def _on_search(self):
        text = self._input.text().strip()
        if text:
            self.search_requested.emit(text)

    def set_enabled(self, enabled: bool):
        self._input.setEnabled(enabled)
        self._btn.setEnabled(enabled)
        self._btn.setText("Buscar" if enabled else "…")


class _PosterCard(QFrame):
    """Base para cards com poster/thumbnail + título."""

    clicked = Signal(object)
    favorite_clicked = Signal(object)
    watched_toggled = Signal(object, bool)

    def __init__(self, data, img_url, title, subtitle, badge, poster_size,
                 favoritable=False, is_favorite=False, watched=False,
                 highlight=False, checkable=False, parent=None):
        super().__init__(parent)
        self._data = data
        self._poster_size = poster_size
        self._is_favorite = is_favorite
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFixedWidth(poster_size.width() + 16)
        edge = TEAL if highlight else BORDER
        # Vidro glossy Frutiger Aero. Sem QGraphicsDropShadowEffect: reposicionar
        # widgets com efeito gráfico durante o reflow do grid pode causar segfault.
        self.setStyleSheet(f"""
            _PosterCard {{
                background: {GLASS_PANEL}; border: 1px solid {edge}; border-radius: 14px;
            }}
            _PosterCard:hover {{
                background: {GLASS_HI}; border: 1px solid {TEAL};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 10)
        layout.setSpacing(8)

        # Poster
        poster_holder = QWidget()
        poster_holder.setFixedSize(poster_size)
        ph_layout = QVBoxLayout(poster_holder)
        ph_layout.setContentsMargins(0, 0, 0, 0)

        self._poster = QLabel()
        self._poster.setFixedSize(poster_size)
        self._poster.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._poster.setStyleSheet(f"""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 {AQUA}, stop:1 {AQUA_DEEP});
            border-radius: 9px; color: rgba(255,255,255,0.85); font-size: 26px;
        """)
        self._poster.setText("🎬")
        ph_layout.addWidget(self._poster)

        # Faixa de brilho (gloss) na metade superior do poster — assinatura Aero
        gloss = QLabel(self._poster)
        gloss.setGeometry(3, 3, poster_size.width() - 6, poster_size.height() // 2 - 3)
        gloss.setStyleSheet("""
            background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                stop:0 rgba(255,255,255,0.45), stop:1 rgba(255,255,255,0.0));
            border-top-left-radius: 8px; border-top-right-radius: 8px;
        """)
        gloss.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

        # Badge de áudio (canto superior direito)
        if badge:
            text, color = badge
            badge_lbl = QLabel(text, self._poster)
            badge_lbl.setFixedSize(38, 20)
            badge_lbl.move(poster_size.width() - 46, 8)
            badge_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            badge_lbl.setFont(QFont("Segoe UI", 8, QFont.Weight.Bold))
            badge_lbl.setStyleSheet(f"background: {color}; color: {BG_DARK}; border-radius: 5px;")

        # Selo de "assistido" (canto superior direito) — visível conforme estado
        self._watched_badge = QLabel("✓", self._poster)
        self._watched_badge.setFixedSize(22, 22)
        self._watched_badge.move(poster_size.width() - 30, 34 if badge else 8)
        self._watched_badge.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._watched_badge.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self._watched_badge.setStyleSheet(
            f"background: {TEAL_DARK}; color: {BG_DARK}; border-radius: 11px;")
        self._watched_badge.setVisible(watched)

        # Estrela de favorito (canto superior esquerdo, clicável)
        if favoritable:
            self._star = QPushButton("★" if is_favorite else "☆", self._poster)
            self._star.setFixedSize(28, 28)
            self._star.move(8, 8)
            self._star.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._star.setToolTip("Favoritar")
            self._update_star_style()
            self._star.clicked.connect(self._on_star)

        layout.addWidget(poster_holder)

        # Título
        title_lbl = QLabel(title)
        title_lbl.setFont(QFont("Segoe UI", 10, QFont.Weight.DemiBold))
        title_lbl.setStyleSheet(f"color: {TEXT_PRIMARY}; background: transparent; border: none;")
        title_lbl.setWordWrap(True)
        title_lbl.setFixedHeight(34)
        title_lbl.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.addWidget(title_lbl)

        # Subtítulo
        if subtitle:
            sub_lbl = QLabel(subtitle)
            sub_lbl.setFont(QFont("Segoe UI", 9))
            sub_lbl.setStyleSheet(f"color: {TEAL}; background: transparent; border: none;")
            layout.addWidget(sub_lbl)

        # Caixa de marcação "Assistido" (só é marcada manualmente pelo usuário)
        if checkable:
            self._check = QCheckBox("Assistido")
            self._check.setChecked(watched)
            self._check.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
            self._check.setFont(QFont("Segoe UI", 9))
            self._check.setStyleSheet(f"""
                QCheckBox {{ color: {TEXT_SECONDARY}; background: transparent; spacing: 6px; }}
                QCheckBox::indicator {{ width: 15px; height: 15px; border-radius: 4px;
                    border: 1px solid {BORDER}; background: {BG_SURFACE}; }}
                QCheckBox::indicator:checked {{ background: {TEAL_DARK}; border-color: {TEAL_DARK}; }}
                QCheckBox:hover {{ color: {TEXT_PRIMARY}; }}
            """)
            self._check.toggled.connect(self._on_check)
            layout.addWidget(self._check)

        if img_url:
            _load_image_async(img_url, self._poster, poster_size)

    def _on_check(self, checked: bool):
        self._watched_badge.setVisible(checked)
        self.watched_toggled.emit(self._data, checked)

    def _update_star_style(self):
        color = "#fbbf24" if self._is_favorite else TEXT_PRIMARY
        self._star.setText("★" if self._is_favorite else "☆")
        self._star.setStyleSheet(f"""
            QPushButton {{ background: rgba(0,0,0,0.55); color: {color};
                border: none; border-radius: 14px; font-size: 15px; }}
            QPushButton:hover {{ background: rgba(0,0,0,0.8); color: #fbbf24; }}
        """)

    def _on_star(self):
        self._is_favorite = not self._is_favorite
        self._update_star_style()
        self.favorite_clicked.emit(self._data)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._data)
        super().mousePressEvent(event)


class AnimeCard(_PosterCard):
    POSTER = QSize(150, 210)

    def __init__(self, anime_data, is_favorite=False, subtitle=None, parent=None):
        super().__init__(
            data=anime_data,
            img_url=anime_data.thumbnail,
            title=anime_data.title,
            subtitle=subtitle if subtitle is not None else (anime_data.year or ""),
            badge=_audio_badge(anime_data.audio),
            poster_size=self.POSTER,
            favoritable=True,
            is_favorite=is_favorite,
            parent=parent,
        )


class VideoCard(_PosterCard):
    POSTER = QSize(200, 112)

    def __init__(self, episode_data, watched=False, highlight=False, parent=None):
        title = episode_data.title or f"Episódio {episode_data.number}"
        super().__init__(
            data=episode_data,
            img_url=episode_data.thumbnail,
            title=title,
            subtitle=f"EP {episode_data.number}",
            badge=_audio_badge(episode_data.audio),
            poster_size=self.POSTER,
            watched=watched,
            highlight=highlight,
            checkable=True,
            parent=parent,
        )


class StatusBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(30)
        self.setStyleSheet(f"background: {GLASS_BAR}; border-top: 1px solid rgba(255,255,255,0.7);")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 0, 16, 0)

        self._dot = QLabel("●")
        self._dot.setStyleSheet(f"color: {TEAL};")
        layout.addWidget(self._dot)

        self._label = QLabel("Pronto")
        self._label.setFont(QFont("Segoe UI", 9))
        self._label.setStyleSheet(f"color: {TEXT_SECONDARY};")
        layout.addWidget(self._label)
        layout.addStretch()

    def set_message(self, text: str, is_error: bool = False):
        color = "#ef4444" if is_error else TEAL
        self._dot.setStyleSheet(f"color: {color};")
        self._label.setText(text)
