# core/gui_components/progress_dialogs.py
import random, time
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QApplication, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QMutex, Signal
from PySide6.QtGui import QPainter, QLinearGradient, QColor


class AnimatedProgressBar(QProgressBar):
    """无边框彩色进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._wave_position = 0
        self._color_shift = 0
        self._sparkle_positions = []
        self._is_animating = False
        self._last_update_time = 0
        self._draw_mutex = QMutex()
        self.setMinimumHeight(20)

        # 初始化火花效果
        self._init_sparkles()

        # 设置动画定时器
        self._animation_interval = 16

        # 始终运行动画，不受进度值影响
        self._animation_timer.start(self._animation_interval)
        self._is_animating = True
        self._last_update_time = time.time()

    def _init_sparkles(self):
        """初始化火花效果"""
        self._sparkle_positions = []
        for _ in range(5):  # 减少火花数量以提高性能
            self._sparkle_positions.append({
                'x': 0,
                'y': 0,
                'size': 0,
                'alpha': 0,
                'speed': 0
            })

    def _update_animation(self):
        """更新动画效果 - 添加时间增量计算"""
        current_time = time.time()
        delta_time = min(0.1, current_time - self._last_update_time)  # 限制最大增量时间
        self._last_update_time = current_time

        # 基于时间增量更新动画
        self._wave_position = (self._wave_position + 40 * delta_time) % 100
        self._color_shift = (self._color_shift + 15 * delta_time) % 360

        # 更新火花效果
        for sparkle in self._sparkle_positions:
            if sparkle['alpha'] <= 0:
                # 重新激活火花
                if self.value() > 0 and random.randint(0, 100) < 4:  # 降低火花出现概率
                    progress_width = int(self.width() * self.value() / self.maximum())
                    if progress_width > 0:  # 确保进度宽度大于0
                        sparkle['x'] = random.randint(0, progress_width)
                        sparkle['y'] = random.randint(5, self.height() - 5)
                        sparkle['size'] = random.randint(2, 5)  # 减小火花尺寸
                        sparkle['alpha'] = random.randint(100, 180)  # 降低火花亮度
                        sparkle['speed'] = random.randint(1, 3) / 10.0  # 调整火花消失速度
            else:
                sparkle['alpha'] -= sparkle['speed'] * 40 * delta_time

        # 只在实际需要时更新UI
        if self.isVisible():
            self.update()

    def setValue(self, value):
        """设置进度值 - 不影响动画运行"""
        super().setValue(value)

    def showEvent(self, event):
        """显示事件 - 确保动画运行"""
        super().showEvent(event)
        if not self._is_animating:
            self._animation_timer.start(self._animation_interval)
            self._is_animating = True
            self._last_update_time = time.time()

    def hideEvent(self, event):
        """隐藏事件 - 暂停动画以节省资源"""
        super().hideEvent(event)
        if self._is_animating:
            self._animation_timer.stop()
            self._is_animating = False

    def get_rainbow_color(self, position):
        """获取更鲜艳的彩虹色"""
        hue = (position + self._color_shift) % 360
        return QColor.fromHsl(hue, 255, 120)

    def paintEvent(self, event):
        """重写绘制事件 - 添加错误处理和性能优化"""
        # 使用互斥锁防止重入
        if not self._draw_mutex.tryLock():
            return

        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # 绘制背景 - 使用更浅的颜色
            bg_rect = self.rect()
            bg_gradient = QLinearGradient(0, 0, 0, self.height())
            bg_gradient.setColorAt(0, QColor("#F0F0F0"))
            bg_gradient.setColorAt(1, QColor("#E0E0E0"))
            painter.setBrush(bg_gradient)
            painter.setPen(Qt.NoPen)  # 无边框
            painter.drawRoundedRect(bg_rect, 8, 8)

            # 绘制进度部分
            if self.value() > 0:
                progress_width = int(self.width() * self.value() / self.maximum())
                if progress_width > 0:  # 确保进度宽度大于0
                    progress_rect = bg_rect.adjusted(0, 0, -(self.width() - progress_width), 0)

                    # 创建更鲜艳的彩虹渐变背景
                    rainbow_gradient = QLinearGradient(0, 0, progress_width, 0)
                    for i in range(5):
                        pos = i / 4.0
                        color = self.get_rainbow_color(pos * 360)
                        rainbow_gradient.setColorAt(pos, color)

                    painter.setBrush(rainbow_gradient)
                    painter.drawRoundedRect(progress_rect, 8, 8)

                    # 添加更强的光泽效果 - 顶部高光
                    highlight_rect = progress_rect.adjusted(0, 0, 0, -progress_rect.height() / 2)
                    highlight_gradient = QLinearGradient(0, 0, 0, highlight_rect.height())
                    highlight_gradient.setColorAt(0, QColor(255, 255, 255, 50))
                    highlight_gradient.setColorAt(1, QColor(255, 255, 255, 50))

                    painter.setBrush(highlight_gradient)
                    painter.drawRoundedRect(highlight_rect, 8, 8)

                    # 添加更突出的移动光效
                    wave_width = progress_width * 0.35
                    wave_pos = int(self._wave_position / 100.0 * progress_width)

                    if wave_pos + wave_width > 0:
                        wave_rect = progress_rect.adjusted(
                            max(0, wave_pos - wave_width / 2), 0,
                            min(0, wave_pos + wave_width / 2 - progress_width), 0
                        )

                        # 更亮的波浪渐变
                        wave_gradient = QLinearGradient(
                            wave_rect.left(), 0,
                            wave_rect.right(), 0
                        )
                        wave_gradient.setColorAt(0, QColor(255, 255, 255, 0))
                        wave_gradient.setColorAt(0.4, QColor(255, 255, 255, 250))
                        wave_gradient.setColorAt(0.6, QColor(255, 255, 255, 250))
                        wave_gradient.setColorAt(1, QColor(255, 255, 255, 0))

                        painter.setBrush(wave_gradient)
                        painter.drawRoundedRect(wave_rect, 8, 8)

                    # 绘制火花效果
                    for sparkle in self._sparkle_positions:
                        if sparkle['alpha'] > 0 and sparkle['x'] < progress_width:
                            # 使用彩虹色火花
                            sparkle_color = self.get_rainbow_color(sparkle['x'] / progress_width * 360)
                            sparkle_color.setAlpha(sparkle['alpha'])
                            painter.setPen(Qt.NoPen)
                            painter.setBrush(sparkle_color)

                            # 绘制带光晕的火花
                            painter.drawEllipse(
                                sparkle['x'],
                                sparkle['y'],
                                sparkle['size'],
                                sparkle['size']
                            )

            # 绘制文字
            text_color = QColor("#333333")
            text_color.setAlpha(240)

            # 绘制文字阴影
            shadow_color = QColor(0, 0, 0, 80)
            painter.setPen(shadow_color)
            painter.drawText(self.rect().adjusted(1, 1, 1, 1), Qt.AlignCenter,
                             f"{int(self.value() / self.maximum() * 100)}%")

            # 绘制主文字
            painter.setPen(text_color)
            font = painter.font()
            font.setBold(True)
            font.setPointSize(font.pointSize() + 1)
            painter.setFont(font)
            painter.drawText(self.rect(), Qt.AlignCenter, f"{int(self.value() / self.maximum() * 100)}%")

        except Exception as e:
            # 捕获并忽略绘制过程中的异常，防止程序崩溃
            print(f"绘制进度条时发生错误: {e}")
        finally:
            self._draw_mutex.unlock()


class ModelLoadingProgress(QDialog):
    """模型加载进度条窗口"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型加载进度")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.resize(450, 160)
        self.setStyleSheet("""
            background-color: #F8F8F8; 
            border-radius: 10px;
            border: 1px solid #E0E0E0;
        """)

        # 居中显示
        if parent:
            parent_geo = parent.geometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )

        self.init_ui()

    def init_ui(self):
        """初始化UI界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # 标题
        self.title_label = QLabel("正在加载模型...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            margin: 5px; 
            color: #333333;
            background-color: transparent;
            border: none;
            padding: 0px; 
        """)
        layout.addWidget(self.title_label)

        # 进度条
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("准备加载模型...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 13px; 
            margin: 5px; 
            color: #666666;
            background-color: transparent;
            border: none;
            padding: 0px;
        """)
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def update_progress(self, value, text=""):
        """更新进度条"""
        self.progress_bar.setValue(value)
        if text:
            self.status_label.setText(text)
        # 确保界面及时更新
        QApplication.processEvents()

    def update_title(self, title):
        """更新标题"""
        self.title_label.setText(title)


class TheoreticalDataGenerationProgress(QDialog):
    """理论数据生成进度条窗口"""
    stop_requested = Signal() # 定义停止信号
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("理论数据生成进度")
        self.setModal(True)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.resize(450, 160)
        self.setStyleSheet("""
            background-color: #F8F8F8; 
            border-radius: 10px;
            border: 1px solid #E0E0E0;
        """)

        # 居中显示
        if parent:
            parent_geo = parent.geometry()
            self.move(
                parent_geo.center().x() - self.width() // 2,
                parent_geo.center().y() - self.height() // 2
            )

        self.init_ui()

    def init_ui(self):
        """初始化UI界面"""
        layout = QVBoxLayout()
        layout.setContentsMargins(25, 25, 25, 25)
        layout.setSpacing(15)

        # 标题
        self.title_label = QLabel("正在生成理论数据...")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setStyleSheet("""
            font-size: 16px; 
            font-weight: bold; 
            margin: 5px; 
            color: #333333;
            background-color: transparent;
            border: none; 
            padding: 0px;
        """)
        layout.addWidget(self.title_label)

        # 进度条
        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)

        # 状态标签
        self.status_label = QLabel("准备生成理论数据...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            font-size: 13px; 
            margin: 5px; 
            color: #666666;
            background-color: transparent;
            border: none;
            padding: 0px;
        """)
        layout.addWidget(self.status_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        # 停止按钮
        self.stop_button = QPushButton("停止生成")
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                font-family: "Microsoft YaHei";
                font-weight: bold;
                font-size: 12px;
                border: 2px solid #c0392b;
                border-radius: 6px;
                padding: 6px 12px;
                min-height: 28px;
            }
            QPushButton:hover {
                background-color: #ff6b6b;
                border: 2px solid #e74c3c;
            }
            QPushButton:pressed {
                background-color: #c0392b;
                border: 2px solid #a5281b;
            }
        """)
        self.stop_button.clicked.connect(self.request_stop)
        button_layout.addWidget(self.stop_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_progress(self, value, text=""):
        """更新进度条"""
        self.progress_bar.setValue(value)
        if text:
            self.status_label.setText(text)
        QApplication.processEvents()

    def update_title(self, title):
        """更新标题"""
        self.title_label.setText(title)

    def request_stop(self):
        """请求停止生成"""
        self.stop_requested.emit()
        self.stop_button.setEnabled(False)
        self.status_label.setText("正在停止生成...")
