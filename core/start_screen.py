# core.start_screen.py
import time, logging
from PyQt5.QtWidgets import QSplashScreen
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont
from PyQt5.QtCore import Qt, QTimer
from .utils import get_output_path

logger = logging.getLogger("StartScreen")

class StartScreen:
    def __init__(self, app):
        self.app = app
        self.splash = None
        self.alpha = 0.0
        self.animation_active = True
        self.creation_time = time.time()

    def showWelcome(self):
        try:
            # 加载欢迎图片
            image_path = get_output_path('./img/welcome.jpg')
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                logger.error(f"无法加载启动图片: {image_path}")
                return

            # 创建启动画面
            self.splash = SplashScreen(pixmap)  # 使用自定义的SplashScreen
            self.splash.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
            self.splash.setWindowOpacity(0.0)
            self.splash.show()

            # 开始淡入动画
            self.start_fade_in()
            return True
        except Exception as e:
            logger.error(f"欢迎界面创建错误: {str(e)}")
            return False

    def start_fade_in(self):
        """开始淡入动画"""
        self.alpha = 0.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.fade_in_step)
        self.timer.start(16)  # 约60fps

    def fade_in_step(self):
        """淡入动画单步"""
        if not self.animation_active or self.alpha >= 1.0:
            self.timer.stop()
            self.splash.setWindowOpacity(1.0)
            return

        self.alpha += 0.06
        if self.alpha > 1.0:
            self.alpha = 1.0
        self.splash.setWindowOpacity(self.alpha)

    def closeWelcome(self):
        """关闭欢迎界面"""
        self.start_fade_out()

    def start_fade_out(self):
        """开始淡出动画"""
        self.alpha = 1.0
        self.timer = QTimer()
        self.timer.timeout.connect(self.fade_out_step)
        self.timer.start(16)

    def fade_out_step(self):
        """淡出动画单步"""
        if not self.animation_active or self.alpha <= 0.0:
            self.timer.stop()
            self.splash.close()
            self.app.processEvents()
            return

        self.alpha -= 0.06
        if self.alpha < 0.0:
            self.alpha = 0.0
        self.splash.setWindowOpacity(self.alpha)

    def stop_animation(self):
        """安全停止所有动画"""
        self.animation_active = False
        if hasattr(self, 'timer') and self.timer.isActive():
            self.timer.stop()


class SplashScreen(QSplashScreen):
    """自定义启动画面，添加文字"""
    def __init__(self, pixmap):
        super().__init__(pixmap)
        self.pixmap = pixmap
        self.setFixedSize(pixmap.size())

    def paintEvent(self, event):
        """重绘事件，添加文字"""
        super().paintEvent(event)

        # 创建绘制器
        painter = QPainter(self)

        # 绘制背景图片
        painter.drawPixmap(0, 0, self.pixmap)

        # 设置文字样式
        painter.setPen(QColor(255, 255, 0))  # 黄色文字
        painter.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))

        # 绘制文字 - 居中显示
        text = "Welcome to OptiSVR Spectral Refractive Index Prediction System"
        text_rect = self.rect()
        text_rect.setHeight(100)  # 文字区域高度
        text_rect.moveTop(self.height() // 2 - 30)  # 垂直居中

        painter.drawText(text_rect, Qt.AlignCenter, text)