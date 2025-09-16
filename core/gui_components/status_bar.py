# core/gui_components/status_bar.py
from PySide6.QtWidgets import QStatusBar, QLabel, QProgressBar, QWidget
from PySide6.QtCore import Qt, QTimer, QRect
from PySide6.QtGui import QPainter, QPen, QColor


class LoadingIndicator(QWidget):
    """加载指示器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate)
        self.setVisible(False)

        # 设置窗口属性，移除外框
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)

    def rotate(self):
        """旋转动画"""
        self.angle = (self.angle - 3) % 360
        self.update()

    def start(self):
        """启动动画"""
        self.setVisible(True)
        self.timer.start(10)  # 每100毫秒更新一次

    def stop(self):
        """停止动画"""
        self.timer.stop()
        self.setVisible(False)

    def paintEvent(self, event):
        """绘制加载指示器"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # 设置画笔
        pen = QPen(QColor("#007bff"))  # 使用蓝色
        pen.setWidth(3)
        pen.setCapStyle(Qt.RoundCap)  # 设置线帽为圆形
        painter.setPen(pen)

        # 获取控件中心和半径
        center_x = self.width() // 2
        center_y = self.height() // 2
        radius = min(center_x, center_y) - 4

        # 绘制圆弧
        rect = QRect(center_x - radius, center_y - radius, 2 * radius, 2 * radius)
        start_angle = self.angle * 16  # Qt中角度以1/16度为单位
        span_angle = 270 * 16  # 绘制270度的弧线
        painter.drawArc(rect, start_angle, span_angle)


class StatusBarManager:
    """状态栏管理器"""
    def __init__(self, main_window):
        self.main_window = main_window
        self.status_bar = None
        self.status_label = None
        self.sync_loading_label = None
        self.sync_progress_bar = None
        self.sync_status_label = None
        self.sync_in_progress = False

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.main_window.setStatusBar(self.status_bar)

        # 创建状态栏标签
        self.status_label = QLabel("就绪")
        self.status_bar.addPermanentWidget(self.status_label)

        # 创建同步加载动画标签
        self.sync_loading_label = LoadingIndicator()
        self.sync_loading_label.setVisible(False)
        self.sync_loading_label.setFixedSize(20, 20)
        self.status_bar.addPermanentWidget(self.sync_loading_label)

        # 创建同步进度条
        self.sync_progress_bar = QProgressBar()
        self.sync_progress_bar.setVisible(False)
        self.sync_progress_bar.setMaximumWidth(200)
        self.sync_progress_bar.setMinimum(0)
        self.sync_progress_bar.setMaximum(100)
        self.sync_progress_bar.setValue(0)

        # 设置进度条样式，与对话框中保持一致
        self.sync_progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 1px solid grey;
                        border-radius: 3px;
                        background-color: #f0f0f0;
                        height: 4px;
                        text-align: center;
                    }
                    QProgressBar::chunk {
                        background-color: #4CAF50;
                        border-radius: 2px;
                    }
                """)

        self.status_bar.addPermanentWidget(self.sync_progress_bar)

        # 同步状态标签
        self.sync_status_label = QLabel("")
        self.sync_status_label.setVisible(False)
        self.status_bar.addPermanentWidget(self.sync_status_label)

    def update_sync_progress(self, current, total):
        """更新同步进度"""
        try:
            # 确保 current 和 total 是整数
            current = int(current)
            total = int(total)

            if total > 0:
                progress = int((current / total) * 100)
                self.sync_progress_bar.setValue(progress)
                self.sync_status_label.setText(f"同步中: {progress}% ({current}/{total})")

                # 在系统托盘显示进度
                if hasattr(self.main_window, 'tray_icon') and self.main_window.tray_icon:
                    self.main_window.tray_icon.show_message("云同步", f"同步进度: {progress}%",
                                                            self.main_window.tray_icon.icon(), 2000)
            else:
                # 始终使用确定模式，即使total为0也显示0%进度，与对话框保持一致
                self.sync_progress_bar.setValue(0)
                self.sync_status_label.setText("同步中...")
        except (ValueError, TypeError):
            # 始终使用确定模式，即使出现异常也显示0%进度，与对话框保持一致
            self.sync_progress_bar.setValue(0)
            self.sync_status_label.setText("同步中...")

    def update_file_sync_progress(self, filename, current, total):
        """更新文件同步进度"""
        try:
            # 确保 current 和 total 是整数
            current = int(current)
            total = int(total)

            if total > 0:
                progress = int((current / total) * 100)
                self.sync_progress_bar.setValue(progress)
                self.sync_status_label.setText(f"同步中: {progress}% ({current}/{total}) [{filename}]")
            else:
                # 始终使用确定模式，即使total为0也显示0%进度，与对话框保持一致
                self.sync_progress_bar.setValue(0)
                self.sync_status_label.setText(f"同步中... [{filename}]")
        except (ValueError, TypeError):
            # 始终使用确定模式，即使出现异常也显示0%进度，与对话框保持一致
            self.sync_progress_bar.setValue(0)
            self.sync_status_label.setText(f"同步中... [{filename}]")

    def show_sync_progress(self, show=True):
        """显示或隐藏同步进度条"""
        self.sync_in_progress = show
        self.sync_progress_bar.setVisible(show)
        self.sync_status_label.setVisible(show)
        self.sync_loading_label.setVisible(show)

        if show:
            self.status_label.setText("云同步进行中...")
            self.sync_progress_bar.setRange(0, 100)
            self.sync_progress_bar.setValue(0)
            # 启动加载动画
            self.sync_loading_label.start()
        else:
            # 停止加载动画
            self.sync_loading_label.stop()
            self.sync_status_label.setText("")
            self.status_label.setText("就绪")
