# core.start_screen.py
import time, logging
from PySide6.QtWidgets import QSplashScreen, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap, QFont, QColor
from PIL import Image, ImageQt

from .utils import get_output_path

logger = logging.getLogger("StartScreen")


class StartScreen(QSplashScreen):
    def __init__(self):
        super().__init__()
        self.animation_active = True
        self.timers = []  # 存储动画定时器
        self.creation_time = time.time()  # 记录创建时间
        self.main_window = None
        self.message_text = ""  # 存储要显示的消息文本

        # 创建欢迎界面
        self.show_welcome()

    def show_welcome(self):
        """显示欢迎界面"""
        try:
            # 加载并显示欢迎图片
            pil_image = Image.open(get_output_path('./img/welcome.jpg'))
            pil_image = pil_image.resize((700, 200))

            # 转换为QPixmap
            if pil_image.mode != "RGB":
                pil_image = pil_image.convert("RGB")

            qimage = ImageQt.ImageQt(pil_image)
            self.pixmap = QPixmap.fromImage(qimage)

            # 设置启动画面
            self.setPixmap(self.pixmap)
            self.setFixedSize(700, 200)

            # 设置要显示的消息文本
            self.message_text = 'Welcome to OptiSVR Spectral Refractive Index Prediction System'

            # 显示启动画面
            self.setWindowFlags(Qt.SplashScreen | Qt.FramelessWindowHint)
            self.setWindowOpacity(0.0)  # 初始透明度为0
            self.show()

            # 开始淡入动画
            QTimer.singleShot(50, lambda: self.welcome_fade_in(0.0))

        except Exception as e:
            logger.error(f"欢迎界面创建错误: {str(e)}")

    def showMessage(self, message, alignment=Qt.AlignLeft, color=QColor()):
        """重写showMessage方法以支持自定义字体"""
        self.message_text = message
        super().showMessage(message, alignment, color)

    def drawContents(self, painter):
        """重写绘制内容方法以自定义文本显示"""
        super().drawContents(painter)

        if self.message_text:
            font = QFont("Microsoft YaHei", 14, QFont.Bold)
            painter.setFont(font)
            painter.setPen(QColor(255, 255, 0))

            # 获取绘制区域
            rect = self.rect()

            # 在中心绘制文本
            painter.drawText(rect, Qt.AlignCenter, self.message_text)

    def welcome_fade_in(self, alpha=0.0):
        """淡入动画"""
        if not self.animation_active:
            return

        try:
            if alpha <= 1.0:
                self.setWindowOpacity(alpha)
                timer = QTimer()
                timer.timeout.connect(lambda: self.welcome_fade_in(alpha + 0.05))
                timer.setSingleShot(True)
                timer.start(10)
                self.timers.append(timer)
            else:
                self.setWindowOpacity(1.0)
        except Exception as e:
            logger.error(f"淡入动画错误: {str(e)}")

    def close_welcome(self):
        """关闭欢迎界面"""
        QTimer.singleShot(50, lambda: self.welcome_fade_out(1.0))

    def welcome_fade_out(self, alpha=1.0):
        """淡出动画"""
        if not self.animation_active:
            return

        try:
            if alpha >= 0.0:
                self.setWindowOpacity(alpha)
                timer = QTimer()
                timer.timeout.connect(lambda: self.welcome_fade_out(alpha - 0.05))  # 调整步长使动画更丝滑
                timer.setSingleShot(True)
                timer.start(10)
                self.timers.append(timer)
            else:
                if not self.animation_active:
                    return

                # 关闭启动画面
                self.close()

                # 显示主窗口
                if self.main_window:
                    QTimer.singleShot(50, lambda: self.expand_to_maximized())
        except Exception as e:
            logger.error(f"淡出动画错误: {str(e)}")

    def set_main_window(self, main_window):
        """设置主窗口引用"""
        self.main_window = main_window

    def expand_to_maximized(self):
        """扩展至最大化窗口动画"""
        if not self.animation_active or not self.main_window:
            return

        try:
            # 获取屏幕尺寸
            screen = QApplication.primaryScreen()
            screen_geometry = screen.availableGeometry()
            screen_width = screen_geometry.width()
            screen_height = screen_geometry.height()

            # 设置初始位置和大小（居中）
            start_width, start_height = 700, 200
            x = (screen_width - start_width) // 2
            y = (screen_height - start_height) // 2

            self.main_window.setGeometry(x, y, start_width, start_height)
            self.main_window.setWindowOpacity(0.0)
            self.main_window.show()

            # 开始动画
            QTimer.singleShot(1, lambda: self.main_animate(0, 60, screen_width, screen_height))
        except Exception as e:
            logger.error(f"最大化动画启动错误: {str(e)}")

    def main_animate(self, step=0, total_steps=60, screen_width=0, screen_height=0):  # 增加步骤使动画更丝滑
        """最大化窗口动画过程"""
        if not self.animation_active or not self.main_window:
            return

        try:
            if step <= total_steps:
                progress = step / total_steps
                # 使用更平滑的缓动函数
                ease_progress = progress * progress * (3 - 2 * progress)

                current_width = int(700 + (screen_width - 700) * ease_progress)
                current_height = int(200 + (screen_height - 200) * ease_progress)
                current_alpha = 0.0 + 1.0 * ease_progress

                current_width = max(1, current_width)
                current_height = max(1, current_height)

                # 居中显示
                x = (screen_width - current_width) // 2
                y = (screen_height - current_height) // 2
                self.main_window.setGeometry(x, y, current_width, current_height)
                self.main_window.setWindowOpacity(current_alpha)

                timer = QTimer()
                timer.timeout.connect(lambda: self.main_animate(step + 1, total_steps, screen_width, screen_height))
                timer.setSingleShot(True)
                timer.start(0.01)
                self.timers.append(timer)
            else:
                # 动画完成，最大化窗口
                self.main_window.setWindowState(Qt.WindowMaximized)
                self.main_window.setWindowOpacity(1.0)
        except Exception as e:
            logger.error(f"最大化动画错误: {str(e)}")

    def stop_animation(self):
        """安全停止所有动画"""
        self.animation_active = False
        for timer in self.timers[:]:
            if timer is not None:
                try:
                    timer.stop()
                    self.timers.remove(timer)
                except:
                    pass
