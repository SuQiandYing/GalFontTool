from PyQt6.QtWidgets import QPushButton, QFrame, QLineEdit, QTextEdit, QGraphicsDropShadowEffect, QSizePolicy
from PyQt6.QtCore import Qt, QPropertyAnimation, QEasingCurve, QPoint, QRectF, QUrl, pyqtProperty
from PyQt6.QtGui import QColor, QPainter, QPen, QDragEnterEvent, QDropEvent, QDesktopServices


class AnimButton(QPushButton):
    def __init__(self, btn_type, func, parent=None):
        super().__init__(parent)
        self.setFixedSize(45, 30)
        self.clicked.connect(func)
        self.btn_type = btn_type
        self._hover_progress = 0.0
        self.parent_win = parent
        self.anim = QPropertyAnimation(self, b"hoverProgress")
        self.anim.setDuration(200)
        self.anim.setEasingCurve(QEasingCurve.Type.OutQuad)
        self.icon_color = QColor(0, 0, 0)

    @pyqtProperty(float)
    def hoverProgress(self): return self._hover_progress
    @hoverProgress.setter
    def hoverProgress(self, val): self._hover_progress = val; self.update()

    def enterEvent(self, e):
        self.anim.setStartValue(self.hoverProgress)
        self.anim.setEndValue(1.0)
        self.anim.start()
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.anim.setStartValue(self.hoverProgress)
        self.anim.setEndValue(0.0)
        self.anim.start()
        super().leaveEvent(e)

    def update_icon_color(self, c):
        self.icon_color = QColor(c)
        self.update()

    def paintEvent(self, e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.btn_type == "close":
            bg_col = QColor(232, 17, 35, int(255 * self._hover_progress))
            icon_col = self.icon_color if self._hover_progress < 0.5 else QColor(255, 255, 255)
        else:
            bg_col = QColor(0, 0, 0, int(20 * self._hover_progress))
            icon_col = self.icon_color
        p.fillRect(self.rect(), bg_col)
        pen = QPen(icon_col)
        pen.setWidthF(1.2)
        p.setPen(pen)
        w, h = self.width(), self.height()
        cx, cy = w / 2, h / 2

        if self.btn_type == "close":
            p.drawLine(QPoint(int(cx - 4), int(cy - 4)), QPoint(int(cx + 4), int(cy + 4)))
            p.drawLine(QPoint(int(cx + 4), int(cy - 4)), QPoint(int(cx - 4), int(cy + 4)))
        elif self.btn_type == "max":
            is_max = False
            if self.parent_win and hasattr(self.parent_win, 'is_max'): is_max = self.parent_win.is_max
            if is_max:
                p.drawRect(QRectF(cx - 2, cy - 4, 6, 6))
                p.drawLine(QPoint(int(cx - 4), int(cy - 2)), QPoint(int(cx - 4), int(cy + 4)))
                p.drawLine(QPoint(int(cx - 4), int(cy + 4)), QPoint(int(cx + 2), int(cy + 4)))
            else:
                p.drawRect(QRectF(cx - 4, cy - 4, 8, 8))
        elif self.btn_type == "min":
            p.drawLine(QPoint(int(cx - 4), int(cy)), QPoint(int(cx + 4), int(cy)))


class IOSButton(QPushButton):
    def __init__(self, text, color="#007AFF", parent=None):
        super().__init__(text, parent)
        self.base_color = color
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(45)
        self.shadow = QGraphicsDropShadowEffect()
        self.shadow.setBlurRadius(15)
        self.shadow.setColor(QColor(0, 0, 0, 40))
        self.shadow.setOffset(0, 4)
        self.setGraphicsEffect(self.shadow)
        self.update_style()

    def set_theme_color(self, c):
        self.base_color = c
        self.update_style()

    def update_style(self, pressed=False):
        self.setStyleSheet(f"QPushButton {{background-color: {self.base_color}; color: white; border-radius: 12px; border: none; padding: 10px; font-family: 'Microsoft YaHei'; font-weight: bold; font-size: 10pt;}} QPushButton:hover {{background-color: {QColor(self.base_color).lighter(110).name()};}}")

    def enterEvent(self, e):
        self.shadow.setBlurRadius(25)
        self.shadow.setOffset(0, 6)
        super().enterEvent(e)

    def leaveEvent(self, e):
        self.shadow.setBlurRadius(15)
        self.shadow.setOffset(0, 4)
        super().leaveEvent(e)

    def mousePressEvent(self, e):
        self.update_style(True)
        super().mousePressEvent(e)

    def mouseReleaseEvent(self, e):
        self.update_style(False)
        super().mouseReleaseEvent(e)


class IOSCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("IOSCard {background-color: rgba(255, 255, 255, 0.65); border-radius: 20px; border: 1px solid rgba(255, 255, 255, 0.8);}")
        s = QGraphicsDropShadowEffect()
        s.setBlurRadius(30)
        s.setColor(QColor(0, 0, 0, 20))
        s.setOffset(0, 8)
        self.setGraphicsEffect(s)

    def update_theme(self, bg, border):
        self.setStyleSheet(f"IOSCard {{background-color: {bg}; border-radius: 20px; border: 1px solid {border};}}")


class IOSInput(QLineEdit):
    def __init__(self, ph, default="", parent=None):
        super().__init__(parent)
        self.setPlaceholderText(str(ph))
        self.setText(str(default))
        self.setFixedHeight(38)
        self.setAcceptDrops(True)

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
        else:
            super().dragEnterEvent(e)

    def dropEvent(self, e: QDropEvent):
        if e.mimeData().hasUrls():
            urls = e.mimeData().urls()
            if urls:
                path = urls[0].toLocalFile()
                self.setText(path)
                self.editingFinished.emit()
            e.acceptProposedAction()
        else:
            super().dropEvent(e)

    def update_theme(self, bg, focus_bg, accent, text):
        self.setStyleSheet(f"""
            QLineEdit {{background-color: {bg}; border: 1px solid rgba(128,128,128,0.2); border-radius: 10px; padding: 0 10px; font-size: 13px; color: {text};}} 
            QLineEdit:focus {{border: 1px solid {accent}; background-color: {focus_bg};}}
            QLineEdit:disabled {{background-color: rgba(0,0,0,0.05); color: rgba(128,128,128,0.5); border: 1px dashed rgba(128,128,128,0.2);}}
        """)


class IOSLog(QTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def mouseReleaseEvent(self, e):
        super().mouseReleaseEvent(e)
        anchor = self.anchorAt(e.pos())
        if anchor: QDesktopServices.openUrl(QUrl.fromLocalFile(anchor))

    def update_theme(self, text, bg, scrollbar_style=""):
        self.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg};
                border: none;
                border-radius: 15px;
                padding: 15px;
                font-family: 'Consolas';
                font-size: 12px;
                color: {text};
            }}
            {scrollbar_style}
        """)
