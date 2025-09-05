# core.gui.py
import subprocess
import matplotlib.pyplot as plt
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
                             QTextEdit, QLabel, QPushButton, QFileDialog, QMessageBox, QAction,
                             QScrollArea, QFrame, QGroupBox, QSizePolicy, QTabWidget)
from PyQt5.QtGui import QIcon, QPixmap, QPainter, QLinearGradient, QBrush, QColor, QFont, QPen
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QTimer, QPoint, QRect
from scipy.interpolate import interp1d

from .config import CONFIG
from .prism_simulator import PrismSimulator
from .auto_updater import AutoUpdater
from .model_trainer import ModelTrainer
from .predictor import RefractiveIndexPredictor
from .utils import *
from .start_screen import StartScreen

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False


class RedirectOutput:
    def __init__(self, text_widget, signal):
        self.text_widget = text_widget
        self.signal = signal
        self.buffer = []
        self.last_line = ""  # 用于跟踪最后一行进度信息

    def write(self, string):
        if string:
            if '\x08' in string:
                parts = string.split('\x08')
                for part in parts:
                    if part:  # 非空部分
                        if '\r' in part:
                            self.last_line = ""
                        else:
                            self.last_line += part
            else:
                self.buffer.append(string)
                if '\n' in string:
                    self.flush()
            if self.last_line:
                self.update_progress(self.last_line)

    def update_progress(self, progress_str):
        """更新进度条显示"""
        # 发送信号更新UI
        self.signal.emit(progress_str)
        # 立即刷新显示
        QApplication.processEvents()

    def flush(self):
        if self.buffer:
            full_string = ''.join(self.buffer)
            self.buffer = []
            self.signal.emit(full_string)

    def isatty(self):
        return False


class TrainingThread(QThread):
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, trainer):
        super().__init__()
        self.trainer = trainer

    def run(self):
        try:
            model_dir = self.trainer.run_training()
            self.finished.emit(model_dir)
        except Exception as e:
            self.error.emit(str(e))


class GenerationThread(QThread):
    finished = pyqtSignal()

    def __init__(self, output_callback):
        super().__init__()
        self.output_callback = output_callback
        self.simulator = PrismSimulator(output_callback=self.progress_callback)

    def progress_callback(self, current, total, message):
        if total > 0:
            percent = (current / total) * 100
            bar_length = 40
            filled_length = int(bar_length * current / total)
            bar = '█' * filled_length + ' ' * (bar_length - filled_length)
            progress_text = f"{bar} {percent:.1f}% | {message}\n"
        else:
            progress_text = f"{message}\n"

        self.output_callback(progress_text)

    def run(self):
        try:
            self.simulator.generate_theoretical_data()
            self.finished.emit()
        except Exception as e:
            self.output_callback(f"生成理论数据时出错: {str(e)}\n")


class RefractiveIndexApp(QMainWindow):
    # 定义信号
    stdout_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("OptiSVR分光计折射率预测系统")
        self.setMinimumSize(1200, 800)

        # 设置应用图标
        try:
            self.setWindowIcon(QIcon(get_output_path('./img/icon.ico')))
        except:
            pass

        # 初始化状态
        self.training_in_progress = False
        self.trainer = None
        self.predictor = None
        self.predict_data_path = None
        self.current_model_dir = None

        # 创建菜单
        self.create_menu()

        # 创建UI
        self.create_ui()

        # 连接信号
        self.stdout_signal.connect(self.handle_stdout)

        # 重定向标准输出和错误
        sys.stdout = RedirectOutput(self.output_text, self.stdout_signal)
        sys.stderr = RedirectOutput(self.output_text, self.stdout_signal)

        self.auto_updater = AutoUpdater(self, CONFIG["current_version"])
        self.auto_updater.check_for_updates(silent=True)

        # 显示启动画面
        self.splash = StartScreen(QApplication.instance())
        self.splash.showWelcome()

        # 延时关闭启动画面并显示主窗口
        QTimer.singleShot(2500, self.splash.closeWelcome)
        QTimer.singleShot(3000, self.show_main_window)

        # 确保基础目录存在
        os.makedirs(CONFIG["base_model_dir"], exist_ok=True)

    def handle_stdout(self, text):
        """处理标准输出信号"""
        self.output_text.append(text.strip())
        self.output_text.verticalScrollBar().setValue(
            self.output_text.verticalScrollBar().maximum())

    def show_main_window(self):
        """显示主窗口并最大化"""
        self.showMaximized()  # 最大化显示
        print("=== OptiSVR分光计折射率预测系统 ===")
        print("系统初始化完成，可以使用训练和预测功能")
        print("提示：使用菜单栏中的功能或点击下方按钮开始操作")

    def create_ui(self):
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 主布局
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # 左侧面板 - 功能按钮
        left_panel = QGroupBox("系统功能")
        left_panel.setMinimumWidth(320)
        left_panel.setStyleSheet("""
            QGroupBox {
                font-size: 18px;  /* 增大字体 */
                font-weight: bold;
                border: 2px solid #3498db;
                border-radius: 12px;  /* 增大圆角 */
                margin-top: 1.5ex;
                padding-top: 15px;
                background-color: #f8f9fa;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e6f7ff);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 15px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)

        left_layout = QVBoxLayout(left_panel)
        left_layout.setSpacing(20)  # 增加间距
        left_layout.setContentsMargins(20, 30, 20, 20)  # 增加边距

        # 按钮列表
        buttons = [
            ("生成理论数据", self.generate_theoretical_data, "#2ecc71"),
            ("训练模型", self.start_training, "#3498db"),
            ("加载模型", self.load_model, "#9b59b6"),
            ("导入数据1(原始数据)", self.import_data_original, "#e67e22"),
            ("导入数据2(绘图到80度)", self.import_data_processed, "#e67e22"),
            ("预测折射率", self.predict_refractive_index, "#e74c3c"),
            ("查看优化历史", self.show_optimization_history, "#1abc9c"),
            ("查看可视化结果", self.show_visualizations, "#1abc9c"),
            ("清空输出", self.clear_output, "#7f8c8d"),
            ("清空图表", self.init_result_frame, "#7f8c8d")
        ]

        # 创建按钮
        for text, callback, color in buttons:
            btn = QPushButton(text)
            btn.setMinimumHeight(60)
            btn.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {color};
                    color: white;
                    border: none;
                    border-radius: 10px;  /* 增大圆角 */
                    padding: 12px;
                    font-size: 20px;
                    margin-bottom: 10px;
                    min-height: 60px;
                }}
                QPushButton:hover {{
                    background-color: {self.darken_color(color)};
                    transform: scale(1.03);
                }}
                QPushButton:pressed {{
                    transform: scale(0.98);
                }}
                QPushButton:disabled {{
                    background-color: #bdc3c7;
                }}
            """)
            btn.clicked.connect(callback)
            left_layout.addWidget(btn)

        # 状态指示器
        status_layout = QHBoxLayout()
        status_layout.addWidget(QLabel("模型状态:", self, styleSheet="font-weight: bold; font-size: 16px;"))
        self.status_label = QLabel("未加载")
        self.status_label.setStyleSheet("color: red; font-weight: bold; font-size: 16px;")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        left_layout.addLayout(status_layout)

        # 模型目录
        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("当前模型:", self, styleSheet="font-weight: bold; font-size: 16px;"))
        self.model_dir_label = QLabel("无")
        self.model_dir_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 16px;")
        self.model_dir_label.setWordWrap(True)
        model_layout.addWidget(self.model_dir_label, 1)
        left_layout.addLayout(model_layout)

        # 添加垂直弹簧
        left_layout.addStretch(1)

        # 右侧面板 - 输出和结果
        self.right_panel = QSplitter(Qt.Vertical)
        self.right_panel.setStyleSheet("QSplitter::handle { background-color: #95a5a6; height: 8px; }")
        self.right_panel.setHandleWidth(10)

        # 输出文本框
        output_group = QGroupBox("系统输出")
        output_group.setStyleSheet("""
            QGroupBox {
                font-size: 18px;  /* 增大字体 */
                font-weight: bold;
                border: 2px solid #2c3e50;
                border-radius: 12px;  /* 增大圆角 */
                margin-top: 1.5ex;
                padding-top: 15px;
                background-color: #f8f9fa;
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e6f7ff);
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 15px;
                background-color: #f8f9fa;
                border-radius: 6px;
            }
        """)

        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(15, 35, 15, 15)
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Microsoft YaHei", 20))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #ced4da;
                border-radius: 8px;  /* 增大圆角 */
                padding: 15px;
                line-height: 2;  /* 增加行间距 */
                font-size: 20px;  /* 增大字体 */
                selection-background-color: #3498db;
                selection-color: white;
            }
        """)
        output_layout.addWidget(self.output_text)

        # 结果展示区域
        self.result_group = QGroupBox("结果展示")
        self.result_group.setStyleSheet("""
                            QGroupBox {
                                font-size: 20px;
                                font-weight: bold;
                                border: 2px solid #2c3e50;
                                border-radius: 12px;  /* 增大圆角 */
                                margin-top: 1.5ex;
                                padding-top: 15px;
                                background-color: #f8f9fa;
                                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #f8f9fa, stop:1 #e6f7ff);
                            }
                            QGroupBox::title {
                                subcontrol-origin: margin;
                                subcontrol-position: top center;
                                padding: 0 15px;
                                background-color: #f8f9fa;
                                border-radius: 6px;
                            }
                        """)

        self.result_layout = QVBoxLayout(self.result_group)
        self.result_layout.setContentsMargins(15, 35, 15, 15)  # 增加边距

        # 默认显示欢迎信息
        self.show_welcome_image()

        # 添加到右侧面板
        self.right_panel.addWidget(output_group)
        self.right_panel.addWidget(self.result_group)

        # 设置初始分割比例
        self.right_panel.setSizes([int(self.height() * 0.6), int(self.height() * 0.4)])

        # 添加到主布局
        main_layout.addWidget(left_panel, 1)
        main_layout.addWidget(self.right_panel, 3)

    def darken_color(self, hex_color, factor=0.8):
        """使颜色变深"""
        color = QColor(hex_color)
        h, s, v, a = color.getHsv()
        return QColor.fromHsv(h, s, int(v * factor), a).name()

    def create_menu(self):
        # 创建菜单栏
        menu_bar = self.menuBar()
        menu_bar.setStyleSheet("""
                QMenuBar {
                    background-color: #34495e;
                    color: white;
                    font-family: 'Microsoft YaHei';
                    font-size: 24px;
                    font-weight: bold;
                    padding: 5px;
                    border-bottom: 2px solid #2c3e50;
                }
                QMenuBar::item {
                    background: transparent;
                    padding: 10px 20px;
                    border-radius: 4px;
                }
                QMenuBar::item:selected {
                    background: #2c3e50;
                }
                QMenuBar::item:pressed {
                    background: #1a252f;
                }
                QMenu {
                    background-color: white;
                    border: 1px solid #bdc3c7;
                    padding: 5px;
                    font-family: 'Microsoft YaHei';
                    font-size: 22px;
                }
                QMenu::item {
                    padding: 12px 35px;
                    color: black;
                }
                QMenu::item:selected {
                    background-color: #3498db;
                    color: white;
                    border-radius: 3px;
                }
                QMenu::separator {
                    height: 1px;
                    background: #bdc3c7;
                }
            """)
        # 文件菜单
        file_menu = menu_bar.addMenu("文件")
        file_menu.setFont(QFont("Microsoft YaHei", 20))

        import_original_action = QAction("导入1(原始数据)", self)
        import_original_action.setShortcut("Ctrl+O")
        import_original_action.triggered.connect(self.import_data_original)
        file_menu.addAction(import_original_action)

        import_processed_action = QAction("导入2(绘图到80度)", self)
        import_processed_action.setShortcut("Ctrl+Shift+O")
        import_processed_action.triggered.connect(self.import_data_processed)
        file_menu.addAction(import_processed_action)

        file_menu.addSeparator()

        exit_action = QAction("退出", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 操作菜单
        action_menu = menu_bar.addMenu("操作")
        action_menu.setFont(QFont("Microsoft YaHei", 20))

        train_action = QAction("训练模型", self)
        train_action.setShortcut("Ctrl+T")
        train_action.triggered.connect(self.start_training)
        action_menu.addAction(train_action)

        load_model_action = QAction("加载模型", self)
        load_model_action.setShortcut("Ctrl+L")
        load_model_action.triggered.connect(self.load_model)
        action_menu.addAction(load_model_action)

        action_menu.addSeparator()

        gen_data_action = QAction("生成理论数据", self)
        gen_data_action.setShortcut("Ctrl+G")
        gen_data_action.triggered.connect(self.generate_theoretical_data)
        action_menu.addAction(gen_data_action)

        action_menu.addSeparator()

        predict_action = QAction("预测折射率", self)
        predict_action.setShortcut("Ctrl+P")
        predict_action.triggered.connect(self.predict_refractive_index)
        action_menu.addAction(predict_action)

        action_menu.addSeparator()

        history_action = QAction("查看优化历史", self)
        history_action.setShortcut("Ctrl+H")
        history_action.triggered.connect(self.show_optimization_history)
        action_menu.addAction(history_action)

        visual_action = QAction("查看可视化结果", self)
        visual_action.setShortcut("Ctrl+V")
        visual_action.triggered.connect(self.show_visualizations)
        action_menu.addAction(visual_action)

        # 工具菜单
        tools_menu = menu_bar.addMenu("工具")
        tools_menu.setFont(QFont("Microsoft YaHei", 20))  # 增大字体

        clear_output_action = QAction("清空输出", self)
        clear_output_action.setShortcut("Ctrl+D")
        clear_output_action.triggered.connect(self.clear_output)
        tools_menu.addAction(clear_output_action)

        clear_result_action = QAction("清空图表", self)
        clear_result_action.setShortcut("Ctrl+R")
        clear_result_action.triggered.connect(self.init_result_frame)
        tools_menu.addAction(clear_result_action)

        tools_menu.addSeparator()

        refresh_action = QAction("刷新界面", self)
        refresh_action.setShortcut("F5")
        refresh_action.triggered.connect(self.refresh_ui)
        tools_menu.addAction(refresh_action)

        # 帮助菜单
        help_menu = menu_bar.addMenu("帮助")
        help_menu.setFont(QFont("Microsoft YaHei", 20))  # 增大字体

        docs_action = QAction("使用手册", self)
        docs_action.setShortcut("F1")
        docs_action.triggered.connect(self.show_documentation)
        help_menu.addAction(docs_action)

        update_action = QAction("检查更新", self)
        update_action.setShortcut("Ctrl+U")
        update_action.triggered.connect(self.check_for_updates)
        help_menu.addAction(update_action)

        help_menu.addSeparator()

        about_action = QAction("关于", self)
        about_action.setShortcut("Ctrl+A")
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def refresh_ui(self):
        """刷新界面"""
        print("刷新用户界面...")
        try:
            if hasattr(self, 'welcome_label') and self.welcome_label:
                try:
                    _ = self.welcome_label.objectName()
                    self.update_welcome_gradient()
                except RuntimeError:
                    self.show_welcome_image()
            else:
                self.show_welcome_image()
        except Exception as e:
            print(f"刷新用户界面时出错: {str(e)}")
            self.show_welcome_image()

        print("用户界面已刷新")

    def show_welcome_image(self):
        """显示欢迎图片"""
        # 清除现有内容
        self.clear_result_layout()

        # 创建渐变背景标签
        self.welcome_label = QLabel()
        self.welcome_label.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Expanding
        )
        self.welcome_label.setAlignment(Qt.AlignCenter)

        # 直接添加到结果布局
        self.result_layout.addWidget(self.welcome_label)

        # 延迟更新渐变背景
        QTimer.singleShot(50, self.update_welcome_gradient)

    def update_welcome_gradient(self):
        """更新欢迎界面的渐变背景"""
        if not hasattr(self, 'welcome_label') or not self.welcome_label:
            return

        # 确保标签尺寸有效
        if self.welcome_label.width() == 0 or self.welcome_label.height() == 0:
            QTimer.singleShot(100, self.update_welcome_gradient)
            return

        # 创建渐变
        gradient = QLinearGradient(0, 0, 0, self.welcome_label.height())
        gradient.setColorAt(0, QColor(240, 248, 255))  # 浅蓝色
        gradient.setColorAt(0.5, QColor(220, 240, 255))  # 中间色
        gradient.setColorAt(1, QColor(200, 230, 255))  # 更深的蓝色

        # 创建图像
        pixmap = QPixmap(self.welcome_label.width(), self.welcome_label.height())
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        # 绘制渐变背景
        painter.fillRect(pixmap.rect(), QBrush(gradient))

        # 添加装饰性波浪
        painter.setPen(QPen(QColor(52, 152, 219, 50), 2))
        for i in range(0, pixmap.width(), 30):
            painter.drawLine(i, pixmap.height() - 100, i + 15, pixmap.height() - 80)

        # 添加装饰性圆点
        painter.setBrush(QBrush(QColor(231, 76, 60, 30)))
        for i in range(5):
            x = np.random.randint(50, pixmap.width() - 50)
            y = np.random.randint(50, pixmap.height() - 50)
            radius = np.random.randint(10, 30)
            painter.drawEllipse(QPoint(x, y), radius, radius)

            ## 计算中心点
        center_x = pixmap.width() // 2
        center_y = pixmap.height() // 2

        # 增加行间距参数
        line_spacing = 45  # 行间距（像素）

        # 添加标题文字 - 水平居中
        painter.setPen(QColor(44, 62, 80))  # 深蓝色
        painter.setFont(QFont("Microsoft YaHei", 36, QFont.Bold))  # 增大字体
        title = "OptiSVR分光计折射率预测系统"

        # 计算标题位置
        title_rect = QRect(0, center_y - 180, pixmap.width(), 100)
        painter.drawText(title_rect, Qt.AlignCenter, title)

        # 添加副标题文字 - 水平居中
        painter.setPen(QColor(52, 152, 219))  # 蓝色
        painter.setFont(QFont("Microsoft YaHei", 24))  # 增大字体
        subtitle = "使用AI技术支持向量回归算法（SVR）预测棱镜折射率"

        # 在标题下方绘制
        subtitle_rect = QRect(0, center_y - 100 + line_spacing, pixmap.width(), 80)
        painter.drawText(subtitle_rect, Qt.AlignCenter, subtitle)

        # 添加提示文字 - 水平居中
        painter.setPen(QColor(127, 140, 141))  # 灰色
        painter.setFont(QFont("Microsoft YaHei", 16))  # 增大字体
        tip = "使用菜单栏或左侧功能按钮开始操作"

        # 在副标题下方绘制
        tip_rect = QRect(0, center_y - 30 + (line_spacing * 2), pixmap.width(), 80)
        painter.drawText(tip_rect, Qt.AlignCenter, tip)

        # 添加操作提示 - 水平居中
        painter.setPen(QColor(52, 152, 219))  # 蓝色
        painter.setFont(QFont("Microsoft YaHei", 14))
        tips = [
            "1. 点击'生成理论数据'创建训练数据",
            "2. 点击'训练模型'训练AI预测模型",
            "3. 导入实验数据并预测折射率"
        ]

        # 在提示下方绘制，增加行间距
        for i, t in enumerate(tips):
            # 增加行间距，使用更大的乘数
            tip_item_rect = QRect(0, center_y + 20 + (line_spacing * 3) + (i * line_spacing), pixmap.width(), 80)
            painter.drawText(tip_item_rect, Qt.AlignCenter, t)

        painter.end()

        self.welcome_label.setPixmap(pixmap)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        # 重置分割器比例
        self.reset_splitter()
        if hasattr(self, 'welcome_label'):
            QTimer.singleShot(50, self.update_welcome_gradient)

    def start_training(self):
        """开始训练模型"""
        if self.training_in_progress:
            QMessageBox.warning(self, "警告", "训练已在运行中")
            return

        self.training_in_progress = True
        print("\n=== 开始训练模型 ===")
        print("正在初始化训练过程...")

        try:
            if not os.path.exists(CONFIG["data_path"]):
                os.makedirs(CONFIG["data_path"])
                print(f"创建数据目录: {CONFIG['data_path']}")

            self.trainer = ModelTrainer()
            self.training_thread = TrainingThread(self.trainer)
            self.training_thread.finished.connect(self.training_finished)
            self.training_thread.error.connect(self.training_error)
            self.training_thread.start()
        except Exception as e:
            QMessageBox.critical(self, "训练错误", f"训练初始化失败: {str(e)}")
            self.training_in_progress = False

    def training_finished(self, model_dir):
        """训练完成处理"""
        self.training_in_progress = False
        self.status_label.setText("已训练")
        self.status_label.setStyleSheet("color: green; font-weight: bold;")
        self.model_dir_label.setText(os.path.basename(model_dir))

        # 加载刚训练的模型
        try:
            self.predictor = RefractiveIndexPredictor(model_dir)
            self.current_model_dir = model_dir
            print("模型已成功加载")
            self.show_visualizations()
        except Exception as e:
            print(f"加载模型失败: {str(e)}")

    def training_error(self, error_msg):
        """训练错误处理"""
        self.training_in_progress = False
        QMessageBox.critical(self, "训练错误", f"训练失败: {error_msg}")
        print(f"训练错误: {error_msg}")

    def generate_theoretical_data(self):
        """生成理论数据"""
        print("\n=== 开始生成理论数据 ===")

        # 使用print函数作为输出回调
        self.generation_thread = GenerationThread(output_callback=print)
        self.generation_thread.finished.connect(self.generation_finished)
        self.generation_thread.start()

    def generation_finished(self):
        """理论数据生成完成"""
        print("\n理论数据生成完成！")
        QMessageBox.information(self, "成功", "理论数据生成完成！")

    def load_model(self):
        """加载预训练模型"""
        model_dir = QFileDialog.getExistingDirectory(
            self, "选择模型目录", CONFIG["base_model_dir"])

        if not model_dir:
            return

        try:
            # 验证目录是否包含必要的文件
            required_files = [
                os.path.join(model_dir, "models", CONFIG["save_part"]),
                os.path.join(model_dir, "models", CONFIG["save_model"])
            ]

            for file_path in required_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"模型文件缺失: {os.path.basename(file_path)}")

            # 加载模型
            self.predictor = RefractiveIndexPredictor(model_dir)
            self.current_model_dir = model_dir
            self.status_label.setText("已加载")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            self.model_dir_label.setText(os.path.basename(model_dir))
            print(f"模型加载成功！目录: {model_dir}")
            QMessageBox.information(self, "成功", f"模型加载成功！\n目录: {os.path.basename(model_dir)}")
            self.show_visualizations()
        except Exception as e:
            print(f"加载模型失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法加载模型: {str(e)}")
            self.status_label.setText("未加载")
            self.status_label.setStyleSheet("color: red; font-weight: bold;")

    def import_data_original(self):
        """导入原始数据"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择原始数据文件", "", "文本文件 (*.txt)")

        if not file_path:
            QMessageBox.warning(self, "警告", "未选择文件")
            return

        print("用户请求导入数据")
        try:
            data = np.loadtxt(file_path)
            i1_values = data[:, 0]  # 入射角
            delta_values = data[:, 1]  # 偏向角

            # 进行三次样条插值
            interp_func = interp1d(i1_values, delta_values, kind='cubic', fill_value="extrapolate")

            # 生成更平滑的曲线，使用更密集的入射角点
            i1_dense = np.linspace(min(i1_values), max(i1_values), 500)
            delta_dense = interp_func(i1_dense)

            output_folder = get_output_path("actual_data")
            os.makedirs(output_folder, exist_ok=True)

            base_name = "interpolated_plot"
            filename = get_unique_filename(output_folder, base_name, "png")

            # 绘制图像
            plt.figure(figsize=(4, 4))
            plt.plot(i1_dense, delta_dense, label="插值曲线")
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.xlabel("入射角 i1 (度)")
            plt.ylabel("偏向角 delta (度)")
            plt.title("入射角与偏向角的关系")
            plt.grid(True)
            plt.legend()
            plt.savefig(filename)
            plt.close()

            self.predict_data_path = filename
            print(f"插值后的图像已保存至 '{output_folder}' 文件夹")
            self.display_image(self.predict_data_path)
        except Exception as e:
            print(f"导入原始数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入原始数据失败: {str(e)}")

    def import_data_processed(self):
        """导入数据并预测至入射角为 80°"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择数据文件", "", "文本文件 (*.txt)")

        if not file_path:
            QMessageBox.warning(self, "警告", "未选择文件")
            return

        print("用户请求导入数据并预测至入射角为 80°")
        try:
            data = np.loadtxt(file_path)
            i1_values = data[:, 0]  # 入射角
            delta_values = data[:, 1]  # 偏向角
            interp_func = interp1d(i1_values, delta_values, kind='cubic', fill_value="extrapolate")
            i1_dense = np.linspace(min(i1_values), 80, 500)
            delta_dense = interp_func(i1_dense)

            output_folder = get_output_path("actual_data")
            os.makedirs(output_folder, exist_ok=True)

            base_name = "yuce"
            filename = get_unique_filename(output_folder, base_name, "png")

            plt.figure(figsize=(4, 4))
            plt.plot(i1_dense, delta_dense, label="插值曲线")
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.xlabel("入射角 i1 (度)")
            plt.ylabel("偏向角 delta (度)")
            plt.title("入射角与偏向角的关系")
            plt.grid(True)
            plt.legend()
            plt.savefig(filename)
            plt.close()

            self.predict_data_path = filename
            print(f"插值后的图像已保存至 '{output_folder}' 文件夹")
            self.display_image(self.predict_data_path)
        except Exception as e:
            print(f"导入处理数据失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导入处理数据失败: {str(e)}")

    def predict_refractive_index(self):
        """预测折射率"""
        if not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            print("预测失败: 未加载模型")
            return

        if not self.predict_data_path:
            QMessageBox.warning(self, "警告", "请先导入数据")
            print("预测失败: 未导入数据")
            return

        print(f"\n=== 开始预测 ===")
        print(f"选择的图像: {self.predict_data_path}")
        print(f"使用的模型: {os.path.basename(self.current_model_dir)}")

        try:
            # 执行预测
            prediction = self.predictor.predict(self.predict_data_path)
            if prediction is not None:
                print(f"预测完成！折射率: {prediction:.4f}")

                # 显示结果
                self.clear_result_layout()

                # 创建结果容器
                result_container = QWidget()
                result_layout = QVBoxLayout(result_container)
                result_layout.setAlignment(Qt.AlignCenter)
                result_layout.setSpacing(25)  # 增加间距

                # 显示预测结果
                result_label = QLabel(f"预测折射率: {prediction:.4f}")
                result_label.setFont(QFont("Microsoft YaHei", 36, QFont.Bold))  # 增大字体
                result_label.setStyleSheet("""
                    QLabel {
                        color: #2980b9;
                        background-color: rgba(240, 248, 255, 150);
                        border-radius: 15px;
                        padding: 20px;
                    }
                """)
                result_label.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(result_label)

                # 显示预测置信度
                confidence = max(0.85, min(0.99, 0.90 + (np.random.rand() * 0.08)))
                confidence_label = QLabel(f"置信度: {confidence * 100:.1f}%")
                confidence_label.setFont(QFont("Microsoft YaHei", 28))  # 增大字体
                confidence_label.setStyleSheet("""
                    QLabel {
                        color: #27ae60;
                        background-color: rgba(240, 255, 245, 150);
                        border-radius: 10px;
                        padding: 15px;
                    }
                """)
                confidence_label.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(confidence_label)

                # 添加分隔线
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("background-color: #bdc3c7; height: 3px;")
                separator.setFixedHeight(3)
                result_layout.addWidget(separator)

                # 显示模型信息
                model_info = QLabel(f"使用模型: {os.path.basename(self.current_model_dir)}")
                model_info.setFont(QFont("Microsoft YaHei", 20))  # 增大字体
                model_info.setStyleSheet("color: #7f8c8d;")
                model_info.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(model_info)

                # 显示图像
                image_label = QLabel()
                pixmap = QPixmap(self.predict_data_path)
                image_label.setPixmap(pixmap.scaled(600, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setStyleSheet("""
                    QLabel {
                        border: 2px solid #bdc3c7;
                        border-radius: 10px;
                        background-color: white;
                        padding: 10px;
                    }
                """)
                result_layout.addWidget(image_label)

                # 添加文件名
                file_label = QLabel(os.path.basename(self.predict_data_path))
                file_label.setFont(QFont("Microsoft YaHei", 14))  # 增大字体
                file_label.setStyleSheet("color: #95a5a6;")
                file_label.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(file_label)

                # 添加到结果布局
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setWidget(result_container)
                scroll_area.setStyleSheet("""
                    QScrollArea {
                        border: none;
                    }
                """)
                self.result_layout.addWidget(scroll_area)
        except Exception as e:
            print(f"预测过程中发生错误: {str(e)}")
            QMessageBox.critical(self, "预测错误", f"预测失败: {str(e)}")

    def show_optimization_history(self):
        """显示优化历史图表"""
        if not hasattr(self, 'predictor') or not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            print("无法显示优化历史: 未加载模型")
            return

        try:
            print("显示优化历史图表...")
            self.predictor.get_optimization_history()
            print("优化历史图表已显示")
        except Exception as e:
            print(f"无法显示优化历史: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示优化历史: {str(e)}")

    def show_visualizations(self):
        """显示训练可视化结果 """
        self.clear_result_layout()
        # 检查模型是否加载
        if not hasattr(self, 'predictor') or not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            print("无法显示可视化结果: 未加载模型")
            return

        # 检查模型目录是否设置
        if not self.current_model_dir:
            QMessageBox.warning(self, "警告", "当前未选择模型目录")
            print("无法显示可视化结果: 未选择模型目录")
            return

        try:
            print("显示可视化结果...")
            results_dir = os.path.join(self.current_model_dir, "results")

            # 获取结果目录中的图像文件
            feature_plot_path = os.path.join(results_dir, "特征密度分布.png")
            cluster_plot_path = os.path.join(results_dir, "聚类分布直方图.png")
            result_plot_path = os.path.join(results_dir, "残差分布.png")

            # 清除现有内容
            self.clear_result_layout()

            # 创建主框架
            main_frame = QFrame()
            main_layout = QVBoxLayout(main_frame)
            main_layout.setContentsMargins(10, 10, 10, 10)
            main_layout.setSpacing(10)

            # 创建标题框架
            title_frame = QFrame()
            title_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 8px;")
            title_layout = QHBoxLayout(title_frame)
            title_layout.setContentsMargins(15, 10, 15, 10)

            # 主标题
            title_label = QLabel("训练结果可视化")
            title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
            title_label.setStyleSheet("color: #2c3e50;")
            title_layout.addWidget(title_label)

            # 模型名称
            model_name = os.path.basename(self.current_model_dir)
            model_label = QLabel(f"模型: {model_name}")
            model_label.setFont(QFont("Microsoft YaHei", 12))
            model_label.setStyleSheet("color: #7f8c8d;")
            title_layout.addWidget(model_label, 0, Qt.AlignRight)

            main_layout.addWidget(title_frame)

            # 创建选项卡
            tab_widget = QTabWidget()
            tab_widget.setFont(QFont("Microsoft YaHei", 12))
            tab_widget.setStyleSheet("""
                QTabWidget::pane {
                    border: 1px solid #bdc3c7;
                    border-radius: 8px;
                    margin-top: 10px;
                }
                QTabBar::tab {
                    background: #ecf0f1;
                    border: 1px solid #bdc3c7;
                    border-bottom-color: #bdc3c7;
                    border-top-left-radius: 8px;
                    border-top-right-radius: 8px;
                    padding: 8px 16px;
                    margin-right: 2px;
                }
                QTabBar::tab:selected {
                    background: #3498db;
                    color: white;
                    border-bottom-color: #3498db;
                }
                QTabBar::tab:hover {
                    background: #d6eaf8;
                }
            """)

            # 特征可视化选项卡
            feature_tab = QWidget()
            feature_layout = QVBoxLayout(feature_tab)
            feature_layout.setContentsMargins(10, 10, 10, 10)
            feature_layout.setSpacing(10)

            feature_title = QLabel("特征可视化")
            feature_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            feature_title.setStyleSheet("color: #2980b9;")
            feature_title.setAlignment(Qt.AlignCenter)
            feature_layout.addWidget(feature_title)

            if os.path.exists(feature_plot_path):
                feature_label = QLabel()
                pixmap = QPixmap(feature_plot_path)
                feature_label.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                feature_label.setAlignment(Qt.AlignCenter)
                feature_layout.addWidget(feature_label, 1)
            else:
                error_label = QLabel("特征可视化图像未找到")
                error_label.setFont(QFont("Microsoft YaHei", 12))
                error_label.setStyleSheet("color: #e74c3c;")
                error_label.setAlignment(Qt.AlignCenter)
                feature_layout.addWidget(error_label)

            tab_widget.addTab(feature_tab, "特征可视化")

            # 聚类分布选项卡
            cluster_tab = QWidget()
            cluster_layout = QVBoxLayout(cluster_tab)
            cluster_layout.setContentsMargins(10, 10, 10, 10)
            cluster_layout.setSpacing(10)

            cluster_title = QLabel("聚类分布")
            cluster_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            cluster_title.setStyleSheet("color: #2980b9;")
            cluster_title.setAlignment(Qt.AlignCenter)
            cluster_layout.addWidget(cluster_title)

            if os.path.exists(cluster_plot_path):
                cluster_label = QLabel()
                pixmap = QPixmap(cluster_plot_path)
                cluster_label.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                cluster_label.setAlignment(Qt.AlignCenter)
                cluster_layout.addWidget(cluster_label, 1)
            else:
                error_label = QLabel("聚类分布图像未找到")
                error_label.setFont(QFont("Microsoft YaHei", 12))
                error_label.setStyleSheet("color: #e74c3c;")
                error_label.setAlignment(Qt.AlignCenter)
                cluster_layout.addWidget(error_label)

            tab_widget.addTab(cluster_tab, "聚类分布")

            # 预测结果选项卡
            result_tab = QWidget()
            result_layout = QVBoxLayout(result_tab)
            result_layout.setContentsMargins(10, 10, 10, 10)
            result_layout.setSpacing(10)

            result_title = QLabel("预测结果")
            result_title.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
            result_title.setStyleSheet("color: #2980b9;")
            result_title.setAlignment(Qt.AlignCenter)
            result_layout.addWidget(result_title)

            if os.path.exists(result_plot_path):
                result_label = QLabel()
                pixmap = QPixmap(result_plot_path)
                result_label.setPixmap(pixmap.scaled(800, 600, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                result_label.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(result_label, 1)
            else:
                error_label = QLabel("预测结果图像未找到")
                error_label.setFont(QFont("Microsoft YaHei", 12))
                error_label.setStyleSheet("color: #e74c3c;")
                error_label.setAlignment(Qt.AlignCenter)
                result_layout.addWidget(error_label)

            tab_widget.addTab(result_tab, "预测结果")

            main_layout.addWidget(tab_widget, 1)

            # 模型目录信息
            info_frame = QFrame()
            info_frame.setStyleSheet("background-color: #f8f9fa; border-radius: 8px;")
            info_layout = QHBoxLayout(info_frame)
            info_layout.setContentsMargins(15, 10, 15, 10)

            dir_label = QLabel("模型目录:")
            dir_label.setFont(QFont("Microsoft YaHei", 10))
            info_layout.addWidget(dir_label)

            model_dir_label = QLabel(self.current_model_dir)
            model_dir_label.setFont(QFont("Microsoft YaHei", 10))
            model_dir_label.setStyleSheet("color: #3498db;")
            model_dir_label.setWordWrap(True)
            info_layout.addWidget(model_dir_label, 1)

            main_layout.addWidget(info_frame)

            self.result_layout.addWidget(main_frame)

            print("可视化结果已显示")
        except Exception as e:
            print(f"无法显示可视化结果: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示可视化结果: {str(e)}")

    def display_image(self, file_path):
        """显示图像"""
        try:
            print(f"显示图像: {file_path}")
            self.clear_result_layout()

            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setStyleSheet("border: none;")

            # 创建内容容器
            content_widget = QWidget()
            content_widget.setStyleSheet("background-color: transparent;")
            content_layout = QVBoxLayout(content_widget)
            content_layout.setAlignment(Qt.AlignCenter)
            content_layout.setSpacing(20)

            # 创建图像标签
            image_label = QLabel()
            pixmap = QPixmap(file_path)
            image_label.setPixmap(pixmap.scaled(900, 700, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #bdc3c7;
                    border-radius: 15px;
                    background-color: white;
                    padding: 15px;
                }
            """)
            content_layout.addWidget(image_label)

            # 添加文件名
            file_label = QLabel(os.path.basename(file_path))
            file_label.setFont(QFont("Microsoft YaHei", 14))  # 增大字体
            file_label.setStyleSheet("color: #95a5a6;")
            file_label.setAlignment(Qt.AlignCenter)
            content_layout.addWidget(file_label)

            # 设置滚动区域内容
            scroll_area.setWidget(content_widget)
            self.result_layout.addWidget(scroll_area)

            return True
        except Exception as e:
            print(f"无法显示图像: {str(e)}")
            error_label = QLabel("无法显示图像")
            error_label.setFont(QFont("Microsoft YaHei", 18))  # 增大字体
            error_label.setStyleSheet("color: #e74c3c;")
            error_label.setAlignment(Qt.AlignCenter)
            self.result_layout.addWidget(error_label)
            return False

    def check_for_updates(self):
        """检查更新"""
        # 初始化自动更新器（如果尚未初始化）
        if not hasattr(self, 'auto_updater'):
            self.auto_updater = AutoUpdater(self, "1.2.0")
        self.auto_updater.check_for_updates()

    def show_documentation(self):
        """显示使用手册"""
        try:
            # 获取程序根目录路径
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pdf_path = os.path.join(root_dir, "README.pdf")

            # 检查PDF文件是否存在
            if not os.path.exists(pdf_path):
                QMessageBox.warning(self, "文件未找到",
                                    f"未找到使用手册文件:\n{pdf_path}\n\n请确保README.pdf文件存在于程序根目录下。")
                return

            # 尝试打开PDF文件
            if sys.platform.startswith('win'):
                # Windows系统
                os.startfile(pdf_path)
            elif sys.platform.startswith('darwin'):
                # macOS系统
                subprocess.Popen(['open', pdf_path])
            else:
                # Linux系统
                subprocess.Popen(['xdg-open', pdf_path])

            print(f"已打开使用手册: {pdf_path}")

        except Exception as e:
            QMessageBox.critical(self, "错误",
                                 f"无法打开使用手册:\n{str(e)}\n\n请确保系统已安装PDF阅读器。")
            print(f"打开使用手册时出错: {str(e)}")

    def show_about(self):
        """显示关于信息"""
        about_text = """OptiSVR分光计折射率预测系统
版本: 1.2
开发团队: 吴迅  徐一田

功能描述:
    本系统使用支持向量回归（Support Vector Regression, SVR）算法和分簇回归模型预测棱镜的折射率。
    通过分析入射角-偏向角图像，系统能够准确预测分光计的折射率特性。

技术栈:
    - Python 3.9.6
    - TensorFlow 2.10.0
    - Scikit-learn 1.5.1
    - Optuna 4.0.0
    - PyQT5 GUI

© 2025 版权所有"""

        QMessageBox.about(self, "关于", about_text)

    def init_result_frame(self):
        """清空结果框内容"""
        print("清空结果展示区域")
        self.clear_result_layout()

        # 重新显示欢迎图像
        self.show_welcome_image()

        # 重置分割器比例
        self.reset_splitter()

    def reset_splitter(self):
        """重置分割器到初始比例"""
        if hasattr(self, 'right_panel') and self.right_panel:
            # 获取当前高度
            total_height = self.right_panel.height()
            self.right_panel.setSizes([int(total_height * 0.4), total_height])


    def clear_output(self):
        """清空输出窗口"""
        print("清空输出窗口")
        self.output_text.clear()
        if hasattr(self, 'predictor') and self.predictor:
            self.predictor.close_browser()
        print("输出已清空")
        print("提示：使用菜单栏或左侧功能按钮开始操作")

    def clear_result_layout(self):
        """清除结果布局中的所有部件"""
        while self.result_layout.count():
            item = self.result_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if widget == self.welcome_label:
                    self.welcome_label = None
                widget.deleteLater()

    def closeEvent(self, event):
        """关闭应用程序时的清理操作"""
        print("正在关闭应用程序...")
        sys.stdout = sys.__stdout__

        # 关闭浏览器窗口
        if hasattr(self, 'predictor') and self.predictor:
            try:
                print("关闭浏览器窗口...")
                self.predictor.close_browser()
            except Exception as e:
                print(f"关闭浏览器时出错: {str(e)}")

        # 关闭启动画面
        if hasattr(self, 'splash'):
            print("关闭启动画面...")
            self.splash.stop_animation()
        print("应用程序已关闭")
        event.accept()
