# core/gui_components/progress_dialogs.py
import random, time
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QProgressBar, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt, QTimer, QMutex, Signal, QRunnable, QThreadPool, QObject, QCoreApplication
from PySide6.QtGui import QPainter, QLinearGradient, QColor


class ProgressSignals(QObject):
    """定义工作线程的信号"""
    progress_updated = Signal(int, str)  # 进度值和文本
    title_updated = Signal(str)  # 标题更新信号
    finished = Signal()  # 完成信号
    stopped = Signal()  # 停止信号


class ProgressWorker(QRunnable):
    """在后台线程中执行耗时操作的工作线程"""
    def __init__(self, operation_func, *args, **kwargs):
        super().__init__()
        self.operation_func = operation_func
        self.args = args
        self.kwargs = kwargs
        self._is_running = True
        self.signals = ProgressSignals()

    def run(self):
        """在线程中执行操作"""
        try:
            self.operation_func(self, *self.args, **self.kwargs)
        except Exception as e:
            print(f"执行操作时出错: {e}")
        finally:
            if self._is_running:
                self.signals.finished.emit()
            else:
                self.signals.stopped.emit()

    def stop(self):
        """停止操作"""
        self._is_running = False

    def is_running(self):
        """检查操作是否仍在运行"""
        return self._is_running


class AnimatedProgressBar(QProgressBar):
    """蓝色渐变进度条"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self._animation_timer = QTimer(self)
        self._animation_timer.timeout.connect(self._update_animation)
        self._wave_position = 0
        self._sparkle_positions = []
        self._is_animating = False
        self._last_update_time = 0
        self._draw_mutex = QMutex()
        self._progress_mutex = QMutex()  # 添加互斥锁保护进度更新
        self.setMinimumHeight(20)

        # 初始化线程池
        self.thread_pool = QThreadPool()
        self.worker = None

        # 初始化火花效果
        self._init_sparkles()

        # 设置动画定时器
        self._animation_interval = 50

        # 始终运行动画，不受进度值影响
        self._animation_timer.start(self._animation_interval)
        self._is_animating = True
        self._last_update_time = time.time()

    def _init_sparkles(self):
        """初始化火花效果"""
        self._sparkle_positions = []
        for _ in range(3):  # 进一步减少火花数量以提高性能
            self._sparkle_positions.append({
                'x': 0,
                'y': 0,
                'size': 0,
                'alpha': 0,
                'speed': 0
            })

    def _update_animation(self):
        """更新动画效果"""
        current_time = time.time()
        delta_time = min(0.1, current_time - self._last_update_time)  # 限制最大增量时间
        self._last_update_time = current_time

        # 基于时间增量更新动画
        self._wave_position = (self._wave_position + 40 * delta_time) % 100

        # 更新火花效果
        for sparkle in self._sparkle_positions:
            if sparkle['alpha'] <= 0:
                # 重新激活火花
                if self.value() > 0 and random.randint(0, 100) < 2:  # 进一步降低火花出现概率
                    progress_width = int(self.width() * self.value() / self.maximum())
                    if progress_width > 0:  # 确保进度宽度大于0
                        sparkle['x'] = random.randint(0, progress_width)
                        sparkle['y'] = random.randint(5, self.height() - 5)
                        sparkle['size'] = random.randint(1, 3)  # 进一步减小火花尺寸
                        sparkle['alpha'] = random.randint(50, 120)  # 降低火花亮度
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

    def paintEvent(self, event):
        """重写绘制事件 - 使用单色渐变"""
        # 使用互斥锁防止重入
        if not self._draw_mutex.tryLock():
            return

        try:
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)

            # 绘制背景 - 使用浅灰色
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

                    # 创建单色蓝渐变背景
                    blue_gradient = QLinearGradient(0, 0, progress_width, 0)
                    blue_gradient.setColorAt(0, QColor(65, 105, 225))      # 皇家蓝
                    blue_gradient.setColorAt(0.5, QColor(30, 144, 255))    # 道奇蓝
                    blue_gradient.setColorAt(1, QColor(65, 105, 225))      # 皇家蓝

                    painter.setBrush(blue_gradient)
                    painter.drawRoundedRect(progress_rect, 8, 8)

                    # 添加光泽效果 - 顶部高光
                    highlight_rect = progress_rect.adjusted(0, 0, 0, -progress_rect.height() / 2)
                    highlight_gradient = QLinearGradient(0, 0, 0, highlight_rect.height())
                    highlight_gradient.setColorAt(0, QColor(255, 255, 255, 100))
                    highlight_gradient.setColorAt(1, QColor(255, 255, 255, 30))

                    painter.setBrush(highlight_gradient)
                    painter.drawRoundedRect(highlight_rect, 8, 8)

                    # 添加移动光效
                    wave_width = progress_width * 0.35
                    wave_pos = int(self._wave_position / 100.0 * progress_width)

                    if wave_pos + wave_width > 0:
                        wave_rect = progress_rect.adjusted(
                            max(0, wave_pos - wave_width / 2), 0,
                            min(0, wave_pos + wave_width / 2 - progress_width), 0
                        )

                        # 白色波浪渐变
                        wave_gradient = QLinearGradient(
                            wave_rect.left(), 0,
                            wave_rect.right(), 0
                        )
                        wave_gradient.setColorAt(0, QColor(255, 255, 255, 0))
                        wave_gradient.setColorAt(0.4, QColor(255, 255, 255, 150))
                        wave_gradient.setColorAt(0.6, QColor(255, 255, 255, 150))
                        wave_gradient.setColorAt(1, QColor(255, 255, 255, 0))

                        painter.setBrush(wave_gradient)
                        painter.drawRoundedRect(wave_rect, 8, 8)

                    # 绘制火花效果
                    for sparkle in self._sparkle_positions:
                        if sparkle['alpha'] > 0 and sparkle['x'] < progress_width:
                            # 使用蓝色火花
                            sparkle_color = QColor(255, 255, 255)
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
            print(f"绘制进度条时发生错误: {e}")
        finally:
            self._draw_mutex.unlock()

    def start_operation(self, operation_func, *args, **kwargs):
        """开始执行操作"""
        self.worker = ProgressWorker(operation_func, *args, **kwargs)
        self.worker.signals.progress_updated.connect(self.update_progress)
        self.worker.signals.title_updated.connect(self.update_title)
        self.worker.signals.finished.connect(self.on_finished)
        self.worker.signals.stopped.connect(self.on_stopped)

        # 设置为低优先级，避免阻塞UI线程
        self.worker.setAutoDelete(True)
        self.thread_pool.start(self.worker)
        return self.worker

    def update_progress(self, value, text=""):
        """更新进度条"""
        # 使用互斥锁保护进度更新
        if self._progress_mutex.tryLock():
            try:
                self.setValue(value)
                # 处理事件队列，确保UI及时更新
                QCoreApplication.processEvents()
            finally:
                self._progress_mutex.unlock()

    def update_title(self, title):
        """更新标题 - 在进度条中无实际作用，但保留以兼容接口"""
        # 使用互斥锁保护标题更新
        if self._progress_mutex.tryLock():
            try:
                # 处理事件队列，确保UI及时更新
                QCoreApplication.processEvents()
            finally:
                self._progress_mutex.unlock()

    def on_finished(self):
        """完成时的处理"""
        pass

    def on_stopped(self):
        """停止时的处理"""
        pass

    def close_worker(self):
        """关闭工作线程"""
        if self.worker and self.worker.is_running():
            self.worker.stop()


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
        self._progress_mutex = QMutex()  # 添加互斥锁保护进度更新

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
        # 使用互斥锁保护进度更新
        if self._progress_mutex.tryLock():
            try:
                self.progress_bar.update_progress(value, text)
            finally:
                self._progress_mutex.unlock()

    def update_title(self, title):
        """更新标题"""
        # 使用互斥锁保护标题更新
        if self._progress_mutex.tryLock():
            try:
                self.title_label.setText(title)
                # 处理事件队列，确保UI及时更新
                QCoreApplication.processEvents()
            finally:
                self._progress_mutex.unlock()

    def start_operation(self, operation_func, *args, **kwargs):
        """开始执行操作"""
        worker = self.progress_bar.start_operation(operation_func, *args, **kwargs)
        return worker

    def closeEvent(self, event):
        """关闭事件处理"""
        self.progress_bar.close_worker()
        event.accept()


class TheoreticalDataGenerationProgress(QDialog):
    """理论数据生成进度条窗口"""
    stop_requested = Signal()  # 定义停止信号
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
        self._progress_mutex = QMutex()  # 添加互斥锁保护进度更新

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
        # 使用互斥锁保护进度更新
        if self._progress_mutex.tryLock():
            try:
                self.progress_bar.update_progress(value, text)
                self.status_label.setText(text)
            finally:
                self._progress_mutex.unlock()

    def update_title(self, title):
        """更新标题"""
        if self._progress_mutex.tryLock():
            try:
                self.title_label.setText(title)
                QCoreApplication.processEvents()
            finally:
                self._progress_mutex.unlock()

    def request_stop(self):
        """请求停止生成"""
        self.stop_requested.emit()
        self.stop_button.setEnabled(False)
        self.status_label.setText("正在停止生成...")

    def start_operation(self, operation_func, *args, **kwargs):
        """开始执行操作"""
        worker = self.progress_bar.start_operation(operation_func, *args, **kwargs)
        return worker

    def closeEvent(self, event):
        """关闭事件处理"""
        self.progress_bar.close_worker()
        event.accept()
