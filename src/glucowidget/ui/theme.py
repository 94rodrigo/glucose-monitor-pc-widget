"""Design tokens e geração de QSS. Único lugar para ajustar o visual."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QFontDatabase, QGuiApplication

FONT_DIR = Path(__file__).resolve().parent.parent / "assets" / "fonts"
FONT_FAMILIES = ["Inter", "Inter Variable", "Segoe UI Variable Text", "Segoe UI", "Cantarell",
                 "Noto Sans", "Ubuntu", "Helvetica Neue", "Arial"]

# Grade de espaçamento (px, antes da escala)
SPACE = {"xs": 4, "sm": 8, "md": 12, "lg": 16, "xl": 24}
RADIUS = {"sm": 6, "md": 10, "lg": 16, "pill": 999}


@dataclass(frozen=True)
class Palette:
    name: str
    card: QColor         # fundo do widget (com alfa)
    window: QColor       # fundo de diálogos
    surface: QColor      # cartões / inputs
    surface_hover: QColor
    border: QColor
    text: QColor
    text_muted: QColor
    text_subtle: QColor
    accent: QColor
    accent_text: QColor
    low: QColor
    high: QColor
    in_range: QColor
    stale: QColor
    band: QColor         # faixa-alvo no gráfico


DARK = Palette(
    name="dark",
    card=QColor(17, 20, 28, 222),
    window=QColor("#11141c"),
    surface=QColor("#1a1f2b"),
    surface_hover=QColor("#232a38"),
    border=QColor(255, 255, 255, 26),
    text=QColor("#f3f5f9"),
    text_muted=QColor("#a7b0c0"),
    text_subtle=QColor("#6f7a8c"),
    accent=QColor("#7c83ff"),
    accent_text=QColor("#ffffff"),
    low=QColor("#ff6b6b"),
    high=QColor("#fbbf24"),
    in_range=QColor("#34d399"),
    stale=QColor("#8b95a7"),
    band=QColor(52, 211, 153, 26),
)

LIGHT = Palette(
    name="light",
    card=QColor(255, 255, 255, 232),
    window=QColor("#f6f7fb"),
    surface=QColor("#ffffff"),
    surface_hover=QColor("#eef0f6"),
    border=QColor(15, 23, 42, 28),
    text=QColor("#0f172a"),
    text_muted=QColor("#475569"),
    text_subtle=QColor("#7b8597"),
    accent=QColor("#4f46e5"),
    accent_text=QColor("#ffffff"),
    low=QColor("#dc2626"),
    high=QColor("#b45309"),
    in_range=QColor("#047857"),
    stale=QColor("#64748b"),
    band=QColor(4, 120, 87, 22),
)


def system_is_dark() -> bool:
    try:
        return QGuiApplication.styleHints().colorScheme() == Qt.ColorScheme.Dark
    except AttributeError:
        return QGuiApplication.palette().window().color().lightness() < 128


def palette_for(theme: str) -> Palette:
    if theme == "dark":
        return DARK
    if theme == "light":
        return LIGHT
    return DARK if system_is_dark() else LIGHT


def load_fonts() -> None:
    if FONT_DIR.is_dir():
        for f in FONT_DIR.iterdir():
            if f.suffix.lower() in (".ttf", ".otf"):
                QFontDatabase.addApplicationFont(str(f))


def ui_font(px: float, weight: QFont.Weight = QFont.Weight.Normal, tabular: bool = False) -> QFont:
    font = QFont()
    font.setFamilies(FONT_FAMILIES)
    font.setPixelSize(max(1, round(px)))
    font.setWeight(weight)
    font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
    if tabular:
        try:
            font.setFeature(QFont.Tag("tnum"), 1)
        except (AttributeError, TypeError):
            pass
    return font


def rgba(c: QColor) -> str:
    return f"rgba({c.red()},{c.green()},{c.blue()},{c.alpha()})"


def with_alpha(c: QColor, alpha: int) -> QColor:
    out = QColor(c)
    out.setAlpha(alpha)
    return out


def dialog_qss(p: Palette) -> str:
    """Estilo dos diálogos (configurações, onboarding, análise)."""
    return f"""
    QDialog, QWidget#page {{ background: {rgba(p.window)}; color: {rgba(p.text)}; }}
    QWidget {{ color: {rgba(p.text)}; font-size: 13px; }}
    QLabel#h1 {{ font-size: 22px; font-weight: 600; }}
    QLabel#h2 {{ font-size: 15px; font-weight: 600; }}
    QLabel#muted {{ color: {rgba(p.text_muted)}; }}
    QLabel#subtle {{ color: {rgba(p.text_subtle)}; font-size: 12px; }}
    QLabel#ok {{ color: {rgba(p.in_range)}; }}
    QLabel#err {{ color: {rgba(p.low)}; }}
    QLabel#link {{ color: {rgba(p.accent)}; }}
    QFrame#card {{
        background: {rgba(p.surface)}; border: 1px solid {rgba(p.border)};
        border-radius: {RADIUS['md']}px;
    }}
    QFrame#card QLabel {{ background: transparent; }}
    QFrame#sep {{ background: {rgba(p.border)}; max-height: 1px; min-height: 1px; border: none; }}
    QListWidget#nav {{
        background: transparent; border: none; outline: none; padding: 4px;
    }}
    QListWidget#nav::item {{
        padding: 9px 12px; border-radius: 8px; margin: 1px 0; color: {rgba(p.text_muted)};
    }}
    QListWidget#nav::item:hover {{ background: {rgba(p.surface_hover)}; color: {rgba(p.text)}; }}
    QListWidget#nav::item:selected {{
        background: {rgba(with_alpha(p.accent, 40))}; color: {rgba(p.text)};
    }}
    QWidget#sidebar {{ background: {rgba(p.surface)}; border-right: 1px solid {rgba(p.border)}; }}
    QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
        background: {rgba(p.window)}; border: 1px solid {rgba(p.border)}; border-radius: 8px;
        padding: 7px 10px; selection-background-color: {rgba(p.accent)}; min-height: 18px;
    }}
    QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
        border: 1px solid {rgba(p.accent)};
    }}
    QAbstractSpinBox QLineEdit {{ padding: 0 0 0 2px; border: none; background: transparent; min-height: 0; }}
    QAbstractSpinBox::up-button, QAbstractSpinBox::down-button {{ width: 0; border: none; }}
    QLineEdit[invalid="true"] {{ border: 1px solid {rgba(p.low)}; }}
    QComboBox::drop-down {{ border: none; width: 22px; }}
    QComboBox QAbstractItemView {{
        background: {rgba(p.surface)}; border: 1px solid {rgba(p.border)};
        selection-background-color: {rgba(with_alpha(p.accent, 60))}; outline: none; padding: 4px;
    }}
    QScrollArea, QScrollArea > QWidget > QWidget#page {{ background: {rgba(p.window)}; border: none; }}
    QPushButton {{
        background: {rgba(p.surface)}; border: 1px solid {rgba(p.border)}; border-radius: 8px;
        padding: 8px 16px; font-weight: 500;
    }}
    QPushButton:hover {{ background: {rgba(p.surface_hover)}; }}
    QPushButton:disabled {{ color: {rgba(p.text_subtle)}; }}
    QPushButton#primary {{
        background: {rgba(p.accent)}; color: {rgba(p.accent_text)}; border: none;
    }}
    QPushButton#primary:hover {{ background: {rgba(p.accent.lighter(112))}; }}
    QPushButton#ghost {{ background: transparent; border: none; color: {rgba(p.text_muted)}; }}
    QPushButton#ghost:hover {{ color: {rgba(p.text)}; background: {rgba(p.surface_hover)}; }}
    QPushButton#segment {{
        border-radius: 0; border: 1px solid {rgba(p.border)}; padding: 7px 18px;
        background: {rgba(p.window)}; color: {rgba(p.text_muted)};
    }}
    QPushButton#segment:checked {{
        background: {rgba(p.accent)}; color: {rgba(p.accent_text)}; border-color: {rgba(p.accent)};
    }}
    QPushButton#segment[first="true"] {{ border-top-left-radius: 8px; border-bottom-left-radius: 8px; }}
    QPushButton#segment[last="true"] {{ border-top-right-radius: 8px; border-bottom-right-radius: 8px; }}
    QSlider::groove:horizontal {{ height: 4px; background: {rgba(p.surface_hover)}; border-radius: 2px; }}
    QSlider::sub-page:horizontal {{ background: {rgba(p.accent)}; border-radius: 2px; }}
    QSlider::handle:horizontal {{
        background: {rgba(p.text)}; width: 16px; height: 16px; margin: -6px 0; border-radius: 8px;
    }}
    QTextBrowser {{
        background: transparent; border: none; selection-background-color: {rgba(p.accent)};
        font-size: 14px;
    }}
    QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
    QScrollBar::handle:vertical {{ background: {rgba(p.border)}; border-radius: 4px; min-height: 30px; }}
    QScrollBar::add-line, QScrollBar::sub-line {{ height: 0; }}
    QToolTip {{
        background: {rgba(p.surface)}; color: {rgba(p.text)}; border: 1px solid {rgba(p.border)};
        border-radius: 6px; padding: 6px 8px;
    }}
    QMenu {{
        background: {rgba(p.surface)}; border: 1px solid {rgba(p.border)}; border-radius: 10px; padding: 6px;
    }}
    QMenu::item {{ padding: 7px 22px 7px 12px; border-radius: 6px; }}
    QMenu::item:selected {{ background: {rgba(p.surface_hover)}; }}
    QMenu::item:disabled {{ color: {rgba(p.text_subtle)}; }}
    QMenu::separator {{ height: 1px; background: {rgba(p.border)}; margin: 5px 8px; }}
    """
