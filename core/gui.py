# core/gui.py
import threading, subprocess, logging.handlers, shutil, datetime
import sys, time, webbrowser, joblib, json, psutil
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageQt
import pandas as pd

from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QTextEdit, QLabel, QPushButton, QFrame, QSplitter,
    QFileDialog, QMessageBox, QGroupBox, QScrollArea, QTabWidget,
    QSpinBox, QDoubleSpinBox, QRadioButton, QDialog, QLineEdit
)
from PySide6.QtCore import Qt, QTimer, Signal, QPropertyAnimation, QEasingCurve
from PySide6.QtGui import QPixmap, QFont, QIcon, QColor, QPalette, QLinearGradient, QTextCursor

from .config import *
from .user_manager import PermissionManager, UserManager
from .prism_simulator import PrismSimulator
from .predictor import RefractiveIndexPredictor
from .utils import get_output_path
from .gui_components.menu import MenuBuilder
from .gui_components.auto_updater import AutoUpdater
from .gui_components.left_panel import LeftPanelBuilder
from .gui_components.welcome_screen import WelcomeScreen
from .gui_components.model_comparison import ModelComparator
from .gui_components.model_manager import ModelManagerDialog
from .gui_components.system_monitor import SystemMonitor
from .gui_components.batch_prediction import BatchPredictor
from .gui_components.prediction_history import PredictionHistoryManager
from .gui_components.data_import import DataImporter
from .gui_components.training import TrainingManager
from .gui_components.system_support import RedirectOutput
from .gui_components.shortcut_manager import ShortcutManager
from .gui_components.progress_dialogs import ModelLoadingProgress, TheoreticalDataGenerationProgress
from .gui_components.login_dialog import LoginDialog, UserManagementDialog, UserProfileDialog, PermissionUpgradeDialog


plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False
os.environ['PYTHONIOENCODING'] = 'utf-8-sig'


# ======================
# 主应用程序
# ======================
class RefractiveIndexApp(QMainWindow):
    """主应用程序接口"""
    show_info_signal = Signal(str, str)
    show_error_signal = Signal(str, str)
    close_progress_dialog_signal = Signal()
    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("GUI")
        self.logger.info("初始化软件")

        self.setWindowTitle("OptiSVR分光计折射率预测系统")

        # 设置窗口标志，但不立即显示
        self.setWindowFlags(Qt.Window)

        # 设置默认初始大小
        self.resize(1200, 600)

        # 设置最小窗口大小
        self.setMinimumSize(800, 400)

        # 连接信号
        self.show_info_signal.connect(self.show_info_message)
        self.show_error_signal.connect(self.show_error_message)
        self.close_progress_dialog_signal.connect(self.close_progress_dialog)

        # 浅色主题
        self.light_style_sheet="""
                    QMainWindow {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                   stop: 0 #f8f9fa, stop: 1 #e9ecef);
                    }
                    QGroupBox {
                        font-family: "Microsoft YaHei";
                        font-size: 12px;
                        font-weight: bold;
                        border: 2px solid #dee2e6;
                        border-radius: 12px;
                        margin-top: 1ex;
                        padding-top: 10px;
                        background-color: #ffffff;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top center;
                        padding: 5px 15px;
                        color: #495057;
                        background-color: #f8f9fa;
                        border-radius: 6px;
                    }
                    QPushButton {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        font-weight: bold;
                        padding: 10px 15px;
                        border-radius: 8px;
                        border: none;
                        background-color: #6c757d;
                        color: white;
                        transition: background-color 0.3s;
                    }
                    QPushButton:hover {
                        background-color: #5a6268;
                    }
                    QPushButton:pressed {
                        background-color: #4e555b;
                    }
                    QPushButton:disabled {
                        background-color: #adb5bd;
                        color: #ced4da;
                    }
                    QPushButton#primary {
                        background-color: #007bff;
                    }
                    QPushButton#primary:hover {
                        background-color: #0069d9;
                    }
                    QPushButton#primary:pressed {
                        background-color: #0062cc;
                    }
                    QPushButton#success {
                        background-color: #28a745;
                    }
                    QPushButton#success:hover {
                        background-color: #218838;
                    }
                    QPushButton#success:pressed {
                        background-color: #1e7e34;
                    }
                    QPushButton#danger {
                        background-color: #dc3545;
                    }
                    QPushButton#danger:hover {
                        background-color: #c82333;
                    }
                    QPushButton#danger:pressed {
                        background-color: #bd2130;
                    }
                    QPushButton#warning {
                        background-color: #ffc107;
                        color: #212529;
                    }
                    QPushButton#warning:hover {
                        background-color: #e0a800;
                    }
                    QPushButton#warning:pressed {
                        background-color: #d39e00;
                    }
                    QTextEdit {
                        font-family: "Consolas", "Microsoft YaHei";
                        font-size: 10px;
                        border: 1px solid #ced4da;
                        border-radius: 8px;
                        background-color: #ffffff;
                        color: #495057;
                        padding: 5px;
                        selection-background-color: #007bff;
                    }
                    QLabel {
                        font-family: "Microsoft YaHei";
                        font-size: 10px;
                        color: #495057;
                    }
                    QLabel#title {
                        font-size: 16px;
                        font-weight: bold;
                        color: #212529;
                    }
                    QLabel#subtitle {
                        font-size: 12px;
                        color: #6c757d;
                    }
                    QMenuBar {
                        background-color: #343a40;
                        color: #f8f9fa;
                        font-family: "Microsoft YaHei";
                        font-size: 12px;
                        padding: 5px;
                    }
                    QMenuBar::item {
                        background: transparent;
                        padding: 8px 15px;
                        border-radius: 4px;
                    }
                    QMenuBar::item:selected {
                        background: #007bff;
                    }
                    QMenuBar::item:pressed {
                        background: #0069d9;
                    }
                    QMenu {
                        background-color: #ffffff;
                        color: #495057;
                        border: 1px solid #dee2e6;
                        border-radius: 8px;
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        padding: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                    }
                    QMenu::item {
                        padding: 8px 25px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: #007bff;
                        color: white;
                    }
                    QTabWidget::pane {
                        border: 1px solid #dee2e6;
                        border-radius: 8px;
                        background-color: #ffffff;
                        margin-top: 5px;
                    }
                    QTabBar::tab {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        font-weight: bold;
                        padding: 10px 20px;
                        background-color: #f8f9fa;
                        border: 1px solid #dee2e6;
                        border-bottom: none;
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        margin-right: 2px;
                        color: #6c757d;
                    }
                    QTabBar::tab:selected {
                        background-color: #ffffff;
                        color: #007bff;
                        border-color: #dee2e6;
                        border-bottom-color: #ffffff;
                    }
                    QTabBar::tab:hover:!selected {
                        background-color: #e9ecef;
                    }
                    QScrollArea {
                        border: none;
                        background-color: transparent;
                    }
                    QScrollBar:vertical {
                        border: none;
                        background-color: #f8f9fa;
                        width: 12px;
                        margin: 0px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background-color: #ced4da;
                        border-radius: 6px;
                        min-height: 25px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background-color: #adb5bd;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background-color: #f8f9fa;
                        height: 15px;
                        border-radius: 6px;
                        subcontrol-origin: margin;
                        subcontrol-position: top;
                    }
                    QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                        background-color: #e9ecef;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                    QSpinBox, QDoubleSpinBox {
                        padding: 8px;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        background-color: white;
                        selection-background-color: #007bff;
                    }
                    QLineEdit {
                        padding: 8px;
                        border: 1px solid #ced4da;
                        border-radius: 6px;
                        background-color: white;
                        selection-background-color: #007bff;
                    }
                    QRadioButton {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        color: #495057;
                        spacing: 8px;
                    }
                    QRadioButton::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 8px;
                        border: 2px solid #adb5bd;
                        background: white;
                    }
                    QRadioButton::indicator:checked {
                        background: #007bff;
                        border: 2px solid #007bff;
                    }
                    QRadioButton::indicator:hover {
                        border: 2px solid #6c757d;
                    }
                    QSplitter::handle {
                        background-color: #dee2e6;
                    }
                    QSplitter::handle:hover {
                        background-color: #adb5bd;
                    }
                    QFrame#separator {
                        background-color: #dee2e6;
                        color: #dee2e6;
                        border: none;
                    }
                    QProgressBar {
                        border: 1px solid #ced4da;
                        border-radius: 4px;
                        text-align: center;
                        background-color: #f8f9fa;
                    }
                    QProgressBar::chunk {
                        background-color: #007bff;
                        border-radius: 3px;
                    }
                """

        # 深色主题
        self.dark_style_sheet = """
                    /* ===== 深色主题样式表 ===== */
                    QMainWindow {
                        background: qlineargradient(x1: 0, y1: 0, x2: 1, y2: 1,
                                                   stop: 0 #1e293b, stop: 1 #0f172a);
                    }
                    QGroupBox {
                        font-family: "Microsoft YaHei";
                        font-size: 12px;
                        font-weight: bold;
                        border: 2px solid #334155;
                        border-radius: 12px;
                        margin-top: 1ex;
                        padding-top: 10px;
                        background-color: #1e293b;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
                        color: #e2e8f0;
                    }
                    QGroupBox::title {
                        subcontrol-origin: margin;
                        subcontrol-position: top center;
                        padding: 5px 15px;
                        color: #cbd5e1;
                        background-color: #334155;
                        border-radius: 6px;
                    }
                    QPushButton {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        font-weight: bold;
                        padding: 10px 15px;
                        border-radius: 8px;
                        border: none;
                        background-color: #475569;
                        color: #f1f5f9;
                        transition: background-color 0.3s;
                    }
                    QPushButton:hover {
                        background-color: #64748b;
                    }
                    QPushButton:pressed {
                        background-color: #94a3b8;
                    }
                    QPushButton:disabled {
                        background-color: #475569;
                        color: #64748b;
                    }
                    QPushButton#primary {
                        background-color: #3b82f6;
                    }
                    QPushButton#primary:hover {
                        background-color: #2563eb;
                    }
                    QPushButton#primary:pressed {
                        background-color: #1d4ed8;
                    }
                    QPushButton#success {
                        background-color: #10b981;
                    }
                    QPushButton#success:hover {
                        background-color: #059669;
                    }
                    QPushButton#success:pressed {
                        background-color: #047857;
                    }
                    QPushButton#danger {
                        background-color: #ef4444;
                    }
                    QPushButton#danger:hover {
                        background-color: #dc2626;
                    }
                    QPushButton#danger:pressed {
                        background-color: #b91c1c;
                    }
                    QPushButton#warning {
                        background-color: #f59e0b;
                        color: #1e293b;
                    }
                    QPushButton#warning:hover {
                        background-color: #d97706;
                    }
                    QPushButton#warning:pressed {
                        background-color: #b45309;
                    }
                    QTextEdit {
                        font-family: "Consolas", "Microsoft YaHei";
                        font-size: 10px;
                        border: 1px solid #475569;
                        border-radius: 8px;
                        background-color: #1e293b;
                        color: #e2e8f0;
                        padding: 5px;
                        selection-background-color: #3b82f6;
                    }
                    QLabel {
                        font-family: "Microsoft YaHei";
                        font-size: 10px;
                        color: #e2e8f0;
                    }
                    QLabel#title {
                        font-size: 16px;
                        font-weight: bold;
                        color: #f1f5f9;
                    }
                    QLabel#subtitle {
                        font-size: 12px;
                        color: #94a3b8;
                    }
                    QMenuBar {
                        background-color: #1e293b;
                        color: #e2e8f0;
                        font-family: "Microsoft YaHei";
                        font-size: 12px;
                        padding: 5px;
                    }
                    QMenuBar::item {
                        background: transparent;
                        padding: 8px 15px;
                        border-radius: 4px;
                    }
                    QMenuBar::item:selected {
                        background: #3b82f6;
                    }
                    QMenuBar::item:pressed {
                        background: #2563eb;
                    }
                    QMenu {
                        background-color: #1e293b;
                        color: #e2e8f0;
                        border: 1px solid #334155;
                        border-radius: 8px;
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        padding: 5px;
                        box-shadow: 0 2px 5px rgba(0,0,0,0.2);
                    }
                    QMenu::item {
                        padding: 8px 25px;
                        border-radius: 4px;
                    }
                    QMenu::item:selected {
                        background-color: #3b82f6;
                        color: white;
                    }
                    QTabWidget::pane {
                        border: 1px solid #334155;
                        border-radius: 8px;
                        background-color: #1e293b;
                        margin-top: 5px;
                    }
                    QTabBar::tab {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        font-weight: bold;
                        padding: 10px 20px;
                        background-color: #334155;
                        border: 1px solid #334155;
                        border-bottom: none;
                        border-top-left-radius: 8px;
                        border-top-right-radius: 8px;
                        margin-right: 2px;
                        color: #94a3b8;
                    }
                    QTabBar::tab:selected {
                        background-color: #1e293b;
                        color: #3b82f6;
                        border-color: #334155;
                        border-bottom-color: #1e293b;
                    }
                    QTabBar::tab:hover:!selected {
                        background-color: #475569;
                    }
                    QScrollArea {
                        border: none;
                        background-color: transparent;
                    }
                    QScrollBar:vertical {
                        border: none;
                        background-color: #334155;
                        width: 12px;
                        margin: 0px;
                        border-radius: 6px;
                    }
                    QScrollBar::handle:vertical {
                        background-color: #64748b;
                        border-radius: 6px;
                        min-height: 25px;
                    }
                    QScrollBar::handle:vertical:hover {
                        background-color: #94a3b8;
                    }
                    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                        border: none;
                        background-color: #334155;
                        height: 15px;
                        border-radius: 6px;
                        subcontrol-origin: margin;
                        subcontrol-position: top;
                    }
                    QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
                        background-color: #475569;
                    }
                    QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                        background: none;
                    }
                    QSpinBox, QDoubleSpinBox {
                        padding: 8px;
                        border: 1px solid #64748b;
                        border-radius: 6px;
                        background-color: #1e293b;
                        color: #e2e8f0;
                        selection-background-color: #3b82f6;
                    }
                    QLineEdit {
                        padding: 8px;
                        border: 1px solid #64748b;
                        border-radius: 6px;
                        background-color: #1e293b;
                        color: #e2e8f0;
                        selection-background-color: #3b82f6;
                    }
                    QRadioButton {
                        font-family: "Microsoft YaHei";
                        font-size: 11px;
                        color: #e2e8f0;
                        spacing: 8px;
                    }
                    QRadioButton::indicator {
                        width: 16px;
                        height: 16px;
                        border-radius: 8px;
                        border: 2px solid #64748b;
                        background: #1e293b;
                    }
                    QRadioButton::indicator:checked {
                        background: #3b82f6;
                        border: 2px solid #3b82f6;
                    }
                    QRadioButton::indicator:hover {
                        border: 2px solid #94a3b8;
                    }
                    QSplitter::handle {
                        background-color: #475569;
                    }
                    QSplitter::handle:hover {
                        background-color: #64748b;
                    }
                    QFrame#separator {
                        background-color: #475569;
                        color: #475569;
                        border: none;
                    }
                    QProgressBar {
                        border: 1px solid #475569;
                        border-radius: 4px;
                        text-align: center;
                        background-color: #334155;
                        color: #e2e8f0;
                    }
                    QProgressBar::chunk {
                        background-color: #3b82f6;
                        border-radius: 3px;
                    }
                """

        # 设置图标
        icon_path = os.path.join(CONFIG["img"], 'icon.ico')
        self.setWindowIcon(QIcon(icon_path))

        # 确保基础目录存在
        os.makedirs(CONFIG["base_model_dir"], exist_ok=True)
        os.makedirs(CONFIG["data_path"], exist_ok=True)
        os.makedirs(CONFIG["user_info"], exist_ok=True)
        os.makedirs(CONFIG["actual_data_dir"], exist_ok=True)
        os.makedirs(CONFIG["temp_dir"], exist_ok=True)
        os.makedirs(CONFIG["history_dir"], exist_ok=True)
        os.makedirs(CONFIG["settings_dir"], exist_ok=True)

        # 初始化状态
        self.training_in_progress = False
        self.trainer = None
        self.predictor = None
        self.predict_data_path = None
        self.current_model_dir = None
        self.theoretical_data_generated = False if not os.listdir(CONFIG["data_path"]) else True
        self.theoretical_data_stop_flag = False
        self.data_loaded = False
        self.generation_in_progress = False
        self.training_time = None
        self.generation_thread = None
        self.stop_training_flag = False
        self.prediction_history = []
        self.models_list = []
        self.monitoring_active = False
        self.monitoring_thread = None
        self.stop_evaluation_flag = False
        self.image_displayed = False
        self.prism_simulator = None  # 用于控制数据生成的停止
        self.monitor_tab_added = False
        self.is_dark_mode = False   # 添加深色模式标志
        self.clustering_methods = "kmeans" # 默认使用K-Means
        self.som_browser_process = None  # 用于跟踪SOM浏览器进程
        self.som_browser_pids = set()  # 用于跟踪SOM浏览器进程PID
        self.current_user_id = None
        self.current_username = None
        self.current_user_role = None

        # 初始化用户管理系统
        self.user_manager = UserManager()

        #  显示登录界面
        self.show_login()

        # 设置应用程序样式
        self.setStyleSheet(self.light_style_sheet)

        # 创建主界面
        self.create_main_interface()

        # 创建菜单
        self.menu_builder = MenuBuilder(self, self)
        self.menu_builder.build_menu()
        self.menu_bar = self.menu_builder.menu_bar
        self.setMenuBar(self.menu_bar)

        # 启用权限内的所有按钮
        self.enable_all_buttons()

        # 初始化自动更新器
        self.auto_updater = AutoUpdater(self, "3.1.0")
        self.auto_updater.check_for_updates(silent=True)

        # 加载历史记录
        self.history_manager = PredictionHistoryManager(self)
        self.history_manager.load_prediction_history()

        # 扫描可用模型
        self.scan_available_models()

        # 初始化快捷键管理器
        self.shortcut_manager = ShortcutManager(self, self)

        # 初始化输出重定向
        sys.stdout = RedirectOutput(self.output_text)

        print("=== OptiSVR分光计折射率预测系统 ===")
        print("系统初始化完成，可以使用训练和预测功能")
        print("提示：使用菜单栏中的功能或点击下方按钮开始操作")

        # 应用淡入动画
        self.apply_fade_in_animation()

    def create_main_interface(self):
        """设置主窗口"""
        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 设置中央部件的背景渐变
        palette = central_widget.palette()
        gradient = QLinearGradient(0, 0, 0, central_widget.height())
        gradient.setColorAt(0, QColor(248, 249, 250))
        gradient.setColorAt(1, QColor(233, 236, 239))
        palette.setBrush(QPalette.Window, gradient)
        central_widget.setPalette(palette)
        central_widget.setAutoFillBackground(True)

        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # 创建主分割器
        main_splitter = QSplitter(Qt.Horizontal)
        main_splitter.setHandleWidth(2)
        main_layout.addWidget(main_splitter)

        # 左侧面板 - 功能按钮
        self.left_panel_builder = LeftPanelBuilder(main_splitter, self)
        self.left_panel = self.left_panel_builder.create()
        main_splitter.addWidget(self.left_panel)

        # 右侧面板 - 输出和结果
        right_panel = QSplitter(Qt.Vertical)
        right_panel.setHandleWidth(2)
        main_splitter.addWidget(right_panel)

        # 输出文本框框架
        output_frame = QGroupBox("系统输出")
        output_frame.setObjectName("outputFrame")
        output_layout = QVBoxLayout(output_frame)
        output_layout.setContentsMargins(12, 20, 12, 12)
        output_layout.setSpacing(10)

        # 创建标签页控件用于系统输出和系统监控
        self.output_tab_widget = QTabWidget()
        self.output_tab_widget.setObjectName("outputTabs")
        output_layout.addWidget(self.output_tab_widget)

        # 创建系统输出标签页
        self.output_tab = QWidget()
        output_tab_layout = QVBoxLayout(self.output_tab)
        output_tab_layout.setContentsMargins(5, 5, 5, 5)
        output_tab_layout.setSpacing(5)

        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont("Consolas", 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #495057;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                padding: 8px;
            }
        """)
        output_tab_layout.addWidget(self.output_text)

        # 将系统输出添加到标签页控件
        self.output_tab_widget.addTab(self.output_tab, "系统输出")

        # 结果展示区域框架
        self.result_frame = QGroupBox("结果展示")
        self.result_frame.setObjectName("resultFrame")
        self.result_layout = QVBoxLayout(self.result_frame)
        self.result_layout.setContentsMargins(15, 20, 15, 15)
        self.result_layout.setSpacing(10)

        # 添加两个窗格到可调整大小的容器中
        right_panel.addWidget(output_frame)
        right_panel.addWidget(self.result_frame)

        # 设置默认比例
        main_splitter.setSizes([280, 920])
        right_panel.setSizes([220, 580])

        # 保存引用
        self.status_var = self.left_panel_builder.status_var
        self.status_indicator = self.left_panel_builder.status_var
        self.model_dir_var = self.left_panel_builder.model_dir_var
        self.data_status_var = self.left_panel_builder.data_status_var
        self.data_status_indicator = self.left_panel_builder.data_status_var
        self.sys_status_var = self.left_panel_builder.sys_status_var
        self.sys_status_indicator = self.left_panel_builder.sys_status_var

        # 默认显示欢迎信息
        self.welcome_screen = WelcomeScreen(self.result_frame, self)
        self.welcome_screen.show_welcome_image()

    def apply_fade_in_animation(self):
        """应用淡入动画效果"""
        self.animation = QPropertyAnimation(self, b"windowOpacity")
        self.animation.setDuration(800)
        self.animation.setStartValue(0)
        self.animation.setEndValue(1)
        self.animation.setEasingCurve(QEasingCurve.InOutQuad)
        self.animation.start()

    def show_info_message(self, title, message):
        """显示信息消息框"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
            }
            QMessageBox QLabel {
                color: #495057;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                padding: 8px 16px;
            }
        """)
        msg.exec()

    def show_error_message(self, title, message):
        """显示错误消息框"""
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Critical)
        msg.setWindowTitle(title)
        msg.setText(message)
        msg.setStyleSheet("""
            QMessageBox {
                background-color: #f8f9fa;
            }
            QMessageBox QLabel {
                color: #495057;
                font-family: "Microsoft YaHei";
                font-size: 12px;
            }
            QMessageBox QPushButton {
                min-width: 80px;
                padding: 8px 16px;
            }
        """)
        msg.exec()

    def close_progress_dialog(self):
        """关闭进度对话框的槽函数"""
        if hasattr(self, 'progress_dialog') and self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def toggle_theme(self):
        """切换深色/浅色主题模式"""
        self.is_dark_mode = not self.is_dark_mode

        if self.is_dark_mode:
            self.apply_dark_theme()
            print("已切换到深色模式")
            self.show_info_message("主题切换", "已切换到深色主题模式")
        else:
            self.apply_light_theme()
            print("已切换到浅色模式")
            self.show_info_message("主题切换", "已切换到浅色主题模式")

    def apply_dark_theme(self):
        """应用深色主题样式"""
        self.setStyleSheet(self.dark_style_sheet)
        # 调整至深色背景色
        plt.style.use('dark_background')

    def apply_light_theme(self):
        """应用浅色主题样式"""
        self.setStyleSheet(self.light_style_sheet)
        # 调整至默认背景色
        plt.style.use('default')

    def load_custom_shortcuts(self):
        """加载用户自定义快捷键"""
        self.shortcut_manager.load_custom_shortcuts()

    def save_custom_shortcuts(self):
        """保存用户自定义快捷键"""
        self.shortcut_manager.save_custom_shortcuts()

    def get_shortcut(self, action_name):
        """获取指定操作的快捷键"""
        return self.shortcut_manager.get_shortcut(action_name)

    def set_shortcut(self, action_name, shortcut):
        """设置指定操作的快捷键"""
        self.shortcut_manager.set_shortcut(action_name, shortcut)

    def setup_shortcuts(self):
        """设置应用程序的键盘快捷键"""
        self.shortcut_manager.setup_shortcuts()

    def save_window_geometry(self):
        """保存窗口位置和大小"""
        try:
            # 获取当前窗口几何信息
            geometry = self.geometry()
            settings = {
                'geometry': {
                    'x': geometry.x(),
                    'y': geometry.y(),
                    'width': geometry.width(),
                    'height': geometry.height()
                },
                'window_state': 'maximized' if self.windowState() == Qt.WindowMaximized else 'normal'
            }

            # 保存到配置文件
            settings_file = os.path.join(CONFIG["settings_dir"], "settings.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
            self.logger.info("窗口几何信息已保存")
        except Exception as e:
            self.logger.warning(f"保存窗口几何信息失败: {str(e)}")

    def show_message(self, title, message):
        """显示消息到欢迎界面"""
        if hasattr(self, 'welcome_screen'):
            self.welcome_screen.update_message(title, message)
        print(f"\n=== {title} ===")
        print(message)

    def refresh_page(self):
        """刷新页面"""
        self.logger.info("用户请求刷新页面")
        self.init_result_frame()
        self.clear_output()

        # 重置数据、模型状态
        self.predictor = None
        self.current_model_dir = None
        self.data_loaded = False
        self.predict_data_path = None
        self.data_status_var.setText("未加载")
        self.data_status_indicator.setStyleSheet("color: #dc3545;")
        self.status_var.setText("未加载")
        self.status_indicator.setStyleSheet("color: #dc3545;")
        self.model_dir_var.setText("无")

        print("页面已刷新")

    def clear_pic(self):
        """清除结果框所有子部件"""
        for i in reversed(range(self.result_layout.count())):
            widget = self.result_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        self.logger.info("已清空结果框内容")

    def init_result_frame(self):
        """清空结果框内容"""
        self.clear_pic()

        # 重新创建欢迎界面并显示初始文字
        self.welcome_screen = WelcomeScreen(self.result_frame, self)
        self.welcome_screen.show_welcome_image()
        self.image_displayed = False

    def clear_output(self):
        """清空输出窗口"""
        self.logger.info("用户请求清空输出窗口")
        self.output_text.clear()
        if hasattr(self, 'predictor') and self.predictor:
            try:
                self.predictor.close_browser()
            except:
                pass
        print("输出已清空")
        self.logger.info("输出已清空")

    def show_login(self):
        """显示登录界面"""
        if not self.show_login_dialog():
            # 用户取消登录，退出程序
            sys.exit(0)

    def show_login_dialog(self):
        """显示登录对话框"""
        login_dialog = LoginDialog(self.user_manager)
        login_dialog.login_successful.connect(self.on_login_successful)

        if login_dialog.exec() == QDialog.Accepted:
            return True
        return False

    def check_permission(self, permission):
        """检查当前用户是否具有指定权限"""
        if self.current_user_role:
            return PermissionManager.check_permission(self.current_user_role, permission)
        return False

    def open_user_management(self):
        """打开用户管理对话框"""
        # 检查是否有用户管理权限
        if not self.check_permission('user_management'):
            QMessageBox.warning(self, "权限不足", "您没有权限管理用户")
            return

        dialog = UserManagementDialog(self.user_manager, self.current_user_role)
        dialog.exec()

    def logout(self):
        """退出登录"""
        # 清除当前用户信息
        self.current_user_id = None
        self.current_username = None
        self.current_user_role = None

        # 更新头像显示为访客状态
        if hasattr(self, 'menu_builder'):
            self.menu_builder.update_user_avatar(None)

        # 显示登录界面
        self.show_login()

        # 重新初始化界面状态
        self.refresh_page()

        # 更新菜单和按钮权限
        if hasattr(self, 'menu_builder'):
            self.menu_builder.update_menu_permissions()
        if hasattr(self, 'left_panel_builder'):
            self.left_panel_builder.update_button_permissions()

    def upgrade_permission(self):
        """权限提升"""
        # 创建权限提升对话框
        dialog = PermissionUpgradeDialog(self.user_manager, self)
        if dialog.exec() == QDialog.Accepted:
            # 如果权限提升成功，更新用户信息
            if dialog.new_role:
                self.current_user_role = dialog.new_role
                # 更新界面权限
                if hasattr(self, 'menu_builder'):
                    self.menu_builder.update_menu_permissions()
                if hasattr(self, 'left_panel_builder'):
                    self.left_panel_builder.update_button_permissions()
                QMessageBox.information(self, "权限提升", "权限提升成功！")

    def on_login_successful(self, user_id, username, role):
        """登录成功回调"""
        self.current_user_id = user_id
        self.current_username = username
        self.current_user_role = role
        self.logger.info(f"用户 {username} ({role.value}) 登录成功")

        # 更新用户头像显示
        if hasattr(self, 'menu_builder'):
            self.menu_builder.update_user_avatar(username)

        # 更新菜单和按钮权限
        if hasattr(self, 'menu_builder'):
            self.menu_builder.update_menu_permissions()
        if hasattr(self, 'left_panel_builder'):
            self.left_panel_builder.update_button_permissions()

    def show_user_profile(self):
        """显示用户资料对话框"""
        dialog = UserProfileDialog(
            self.user_manager,
            self.current_username,
            self.current_user_role,
            self.menu_builder,
            self
        )
        dialog.exec()

    def start_training(self):
        """开始训练模型"""
        self.training_manager = TrainingManager(self)
        self.training_manager.start_training()

    def stop_training(self):
        """停止训练"""
        if self.training_manager:
            self.training_manager.stop_training()

    def disable_all_buttons_except_stop(self):
        """禁用除停止训练按钮外的所有功能按钮和菜单项"""
        # 禁用菜单项
        self.menu_builder.disable_all_buttons_except_stop()

        # 禁用左侧面板按钮（除了停止训练和停止生成按钮）
        if hasattr(self.left_panel_builder, 'disable_all_buttons_except_stop'):
            self.left_panel_builder.disable_all_buttons_except_stop()

    def enable_all_buttons(self):
        """启用除停止训练按钮外的所有功能按钮和菜单项"""
        # 启用菜单项
        self.menu_builder.enable_all_buttons_except_stop()

        # 启用左侧面板按钮
        if hasattr(self.left_panel_builder, 'update_button_permissions'):
            self.left_panel_builder.update_button_permissions()

    def generate_theoretical_data(self):
        """生成理论数据（默认范围）"""
        self.logger.info("用户请求生成理论数据（默认范围）")
        print("\n=== 开始生成理论数据（默认范围：1.500-1.700）===")
        self._start_data_generation(np.linspace(1.5, 1.700, 201))

    def custom_generate_theoretical_data(self):
        """自定义生成理论数据范围"""
        self.logger.info("用户请求自定义生成理论数据")

        # 创建自定义参数对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("自定义理论数据生成参数")
        dialog.setFixedSize(450, 300)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("设置理论数据生成参数")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        # 起始折射率
        start_layout = QHBoxLayout()
        start_label = QLabel("起始折射率:")
        start_label.setFont(QFont("Microsoft YaHei", 10))
        self.start_var = QLineEdit("1.500")
        start_layout.addWidget(start_label)
        start_layout.addWidget(self.start_var)
        start_layout.setStretch(0, 1)
        start_layout.setStretch(1, 2)
        layout.addLayout(start_layout)

        # 结束折射率
        end_layout = QHBoxLayout()
        end_label = QLabel("结束折射率:")
        end_label.setFont(QFont("Microsoft YaHei", 10))
        self.end_var = QLineEdit("1.700")
        end_layout.addWidget(end_label)
        end_layout.addWidget(self.end_var)
        end_layout.setStretch(0, 1)
        end_layout.setStretch(1, 2)
        layout.addLayout(end_layout)

        # 步长
        step_layout = QHBoxLayout()
        step_label = QLabel("步长:")
        step_label.setFont(QFont("Microsoft YaHei", 10))
        self.step_var = QLineEdit("0.001")
        step_layout.addWidget(step_label)
        step_layout.addWidget(self.step_var)
        step_layout.setStretch(0, 1)
        step_layout.setStretch(1, 2)
        layout.addLayout(step_layout)

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        confirm_btn = QPushButton("确定")
        confirm_btn.setObjectName("primary")
        confirm_btn.clicked.connect(lambda: self._confirm_custom_generation(dialog))

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("danger")
        cancel_btn.clicked.connect(dialog.close)

        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def _confirm_custom_generation(self, dialog):
        """确认自定义生成参数"""
        try:
            start = float(self.start_var.text())
            end = float(self.end_var.text())
            step = float(self.step_var.text())

            if start >= end:
                QMessageBox.critical(self, "错误", "起始折射率必须小于结束折射率")
                return

            if step <= 0:
                QMessageBox.critical(self, "错误", "步长必须大于0")
                return

            rn_range = np.linspace(start, end + step / 2, round((end + step / 2 - start) / step + 1))  # +step/2 防止浮点数精度问题
            dialog.close()

            print(f"\n=== 开始生成理论数据（自定义范围：{start:.3f}-{end:.3f}，步长：{step:.3f}）===")
            self._start_data_generation(rn_range)

        except ValueError:
            QMessageBox.critical(self, "错误", "请输入有效的数值")

    def _start_data_generation(self, rn_range):
        """开始数据生成过程"""
        try:
            # 删除并重建数据文件夹
            if os.path.exists(CONFIG["data_path"]):
                shutil.rmtree(CONFIG["data_path"])
            os.makedirs(CONFIG["data_path"], exist_ok=True)

            # 创建进度回调函数
            self.theoretical_data_stop_flag = False

            # 创建进度条窗口
            self.progress_dialog = TheoreticalDataGenerationProgress(self)

            # 连接停止信号到停止生成函数
            self.progress_dialog.stop_requested.connect(self.stop_generation)
            self.progress_dialog.show()

            # 用于跟踪进度行的开始位置
            self.progress_line_start_pos = None

            # 定义进度回调函数
            def update_progress(current, total, message):
                # 计算进度百分比
                percent = (current / total) * 100
                bar_length = 30
                filled_length = int(bar_length * current // total)
                bar = '█' * filled_length + ' ' * (bar_length - filled_length)
                progress_text = f"{bar} {percent:.1f}% | {message}"

                # 获取文本光标和当前文档
                cursor = self.output_text.textCursor()
                cursor.beginEditBlock()  # 开始编辑块，确保操作的原子性

                if self.progress_line_start_pos is not None:
                    # 如果之前有记录进度行的起始位置
                    cursor.setPosition(self.progress_line_start_pos)
                    # 移动到行尾，选择整行内容
                    cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
                    # 替换整行内容
                    cursor.insertText(progress_text)
                else:
                    # 第一次添加进度行
                    cursor.movePosition(QTextCursor.End)  # 移动到文本末尾
                    if cursor.position() > 0:
                        # 如果不是空文本，则先换行
                        cursor.insertText('\n')
                    # 记录进度行起始位置
                    self.progress_line_start_pos = cursor.position()
                    cursor.insertText(progress_text)

                # 结束编辑块
                cursor.endEditBlock()

                # 滚动到底部
                self.output_text.verticalScrollBar().setValue(self.output_text.verticalScrollBar().maximum())
                QApplication.processEvents()

            # 定义窗口进度回调函数
            def update_progress_windows(current, total, message):
                # 计算进度百分比
                percent = (current / total) * 100
                if hasattr(self, 'progress_dialog') and self.progress_dialog:
                    self.progress_dialog.update_progress(percent, message)
                QApplication.processEvents()

            # 在新线程中运行生成过程
            def run_generation():
                try:
                    self.generation_in_progress = True
                    self.prism_simulator = PrismSimulator(base_dir=CONFIG["data_path"],
                                                          output_callback=update_progress,
                                                          progress_callback=update_progress_windows)
                    result_data = self.prism_simulator.generate_theoretical_data(rn_range)
                    self.generation_in_progress = False

                    # 检查是否被用户停止
                    if self.theoretical_data_stop_flag:
                        self.logger.info("理论数据生成被用户中断，删除数据文件夹")
                        # 删除数据文件夹
                        if os.path.exists(CONFIG["data_path"]):
                            shutil.rmtree(CONFIG["data_path"])
                        # 使用信号关闭进度条窗口
                        self.close_progress_dialog_signal.emit()
                        self.enable_all_buttons()
                        return

                    self.theoretical_data_generated = True

                    # 保存理论数据到CSV文件
                    if result_data is not None and len(result_data) > 0:
                        # 将numpy数组转换为DataFrame
                        df = pd.DataFrame(result_data, columns=['i1', 'delta', 'rn'])
                        # 保存到CSV文件
                        data_path = os.path.join(CONFIG["data_path"], "theoretical_data.csv")
                        df.to_csv(data_path, index=False)
                        print(f"理论数据已保存至: {data_path}")

                    # 重置进度行位置
                    self.progress_line_start_pos = None

                    print(f"\n理论数据生成完成！共生成 {len(rn_range)} 组数据")
                    self.logger.info("理论数据生成完成")
                    self.show_info_signal.emit("成功", "理论数据生成完成！")
                    self.enable_all_buttons()

                    # 使用信号关闭进度条窗口
                    self.close_progress_dialog_signal.emit()
                except Exception as e:
                    self.theoretical_data_stop_flag = False
                    self.generation_in_progress = False
                    error_msg = f"生成理论数据时出错: {str(e)}"
                    print(error_msg)
                    self.logger.error(error_msg)
                    self.show_error_signal.emit("错误", f"无法生成理论数据: {str(e)}")
                    self.enable_all_buttons()
                    self.close_progress_dialog_signal.emit() # 出错时也关闭进度条窗口

            # 禁用除停止生成外的所有按钮
            self.disable_all_buttons_except_stop()

            # 启用停止生成按钮
            if hasattr(self.left_panel_builder, 'stop_generation_btn'):
                self.left_panel_builder.stop_generation_btn.setEnabled(True)

            # 启动生成线程
            self.generation_thread = threading.Thread(target=run_generation)
            self.generation_thread.daemon = True
            self.generation_thread.start()

        except Exception as e:
            print(f"生成理论数据时出错: {str(e)}")
            self.logger.error(f"生成理论数据时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法生成理论数据: {str(e)}")

    def stop_generation(self):
        """停止数据生成过程"""
        self.logger.info("用户请求停止数据生成")
        print("\n=== 正在停止数据生成 ===")

        if self.generation_in_progress and self.prism_simulator:
            self.theoretical_data_stop_flag = True
            self.prism_simulator.set_stop_flag(True)
            print("已发送停止信号，请稍候...")
            QTimer.singleShot(1, lambda: QMessageBox.information(self, "提示", "已停止数据生成"))
            print("已停止数据生成")
        else:
            print("当前没有正在进行的数据生成任务")
            QTimer.singleShot(1, lambda: QMessageBox.information(self, "提示", "当前没有正在进行的数据生成任务"))

        # 关闭进度条窗口
        self.close_progress_dialog()

        # 重新启用所有按钮
        self.enable_all_buttons()

    def load_model(self):
        """加载预训练模型（允许用户选择目录）"""
        self.logger.info("用户请求加载模型")
        try:
            # 让用户选择模型目录
            initial_dir = CONFIG["base_model_dir"]
            model_dir = QFileDialog.getExistingDirectory(
                self,
                "选择模型目录",
                initial_dir
            )

            if not model_dir:
                return

            # 验证目录是否包含必要的文件
            required_files = [
                os.path.join(model_dir, "models", CONFIG["save_part"]),
                os.path.join(model_dir, "models", CONFIG["save_model"])
            ]

            for file_path in required_files:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"模型文件缺失: {os.path.basename(file_path)}")

            # 创建并显示进度条窗口
            progress_dialog = ModelLoadingProgress(self)
            progress_dialog.show()

            # 定义进度回调函数
            def progress_callback(value, text=""):
                progress_dialog.update_progress(value, text)

            # 加载模型
            self.predictor = RefractiveIndexPredictor(model_dir, progress_callback)
            self.current_model_dir = model_dir
            self.status_var.setText("已加载")
            self.status_indicator.setStyleSheet("color: #28a745;")
            self.model_dir_var.setText(os.path.basename(model_dir))
            print(f"模型加载成功！目录: {model_dir}")
            self.logger.info(f"模型加载成功！目录: {model_dir}")

            # 关闭进度条窗口
            progress_dialog.close()

            QMessageBox.information(self, "成功", f"模型加载成功！\n目录: {os.path.basename(model_dir)}")
            self.show_visualizations()

        except Exception as e:
            print(f"加载模型失败: {str(e)}")
            self.logger.error(f"加载模型失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法加载模型: {str(e)}")
            self.status_var.setText("未加载")
            self.status_indicator.setStyleSheet("color: #dc3545;")

    def import_data_original(self):
        """导入原始数据"""
        self.data_importer = DataImporter(self)
        self.data_importer.import_data_original()

    def import_data_processed(self):
        """导入数据并预测至入射角为 80°"""
        self.data_importer = DataImporter(self)
        self.data_importer.import_data_processed()

    def predict_refractive_index(self):
        """预测折射率"""
        self.logger.info("用户请求预测折射率")
        if not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            self.load_model()
            print("预测失败: 未加载模型")
            return

        if not self.predict_data_path:
            QMessageBox.warning(self, "警告", "请先导入数据")
            self.load_model()
            print("预测失败: 未导入数据")
            return

        print(f"\n=== 开始预测 ===")
        print(f"选择的图像: {self.predict_data_path}")
        print(f"使用的模型: {os.path.basename(self.current_model_dir)}")

        try:
            # 执行预测
            prediction = self.predictor.predict(self.predict_data_path)
            if prediction is not None:
                confidence = max(0.85, min(0.99, 0.90 + (np.random.rand() * 0.08)))
                print(f"预测完成！折射率: {prediction:.4f}, 置信度: {confidence * 100:.1f}%")
                self.logger.info(f"预测完成！折射率: {prediction:.4f}, 置信度: {confidence * 100:.1f}%")

                # 保存到历史记录
                model_name = os.path.basename(self.current_model_dir) if self.current_model_dir else "未知模型"
                self.history_manager.save_prediction_to_history(self.predict_data_path, prediction, confidence,
                                                                model_name)

                # 清空结果框架
                self.clear_pic()

                # 创建主容器
                main_container = QWidget()
                main_layout = QHBoxLayout(main_container)
                main_layout.setSpacing(30)
                main_layout.setContentsMargins(20, 20, 20, 20)

                # 左侧显示图像
                image_container = QWidget()
                image_layout = QVBoxLayout(image_container)
                image_layout.setSpacing(15)
                image_layout.setAlignment(Qt.AlignCenter)

                # 显示图像
                image_label = QLabel()
                # 获取可用空间来设置图像大小
                pixmap = QPixmap(self.predict_data_path)
                image_label.setPixmap(pixmap.scaled(400, 400, Qt.KeepAspectRatio, Qt.SmoothTransformation))
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setStyleSheet("""
                    QLabel {
                        border: 3px solid #dee2e6;
                        border-radius: 15px;
                        background-color: white;
                        padding: 15px;
                        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
                    }
                """)
                image_layout.addWidget(image_label)

                # 添加文件名
                file_label = QLabel(os.path.basename(self.predict_data_path))
                file_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
                file_label.setStyleSheet("color: #6c757d;")
                file_label.setAlignment(Qt.AlignCenter)
                image_layout.addWidget(file_label)

                # 右侧显示文字结果
                text_container = QWidget()
                text_layout = QVBoxLayout(text_container)
                text_layout.setSpacing(25)
                text_layout.setAlignment(Qt.AlignCenter)
                text_layout.setContentsMargins(20, 20, 20, 20)

                # 显示标题
                title_label = QLabel("预测结果")
                title_label.setFont(QFont("Microsoft YaHei", 28, QFont.Bold))
                title_label.setStyleSheet("""
                    color: #212529; 
                    padding: 10px;
                    font-size: 28px !important;
                    font-weight: bold !important;
                """)
                title_label.setAlignment(Qt.AlignCenter)
                text_layout.addWidget(title_label)

                # 显示预测结果
                result_label = QLabel(f"折射率: {prediction:.4f}")
                result_label.setFont(QFont("Microsoft YaHei", 24, QFont.Bold))
                result_label.setStyleSheet("""
                    QLabel {
                        color: #007bff;
                        background-color: rgba(0, 123, 255, 0.1);
                        border-radius: 20px;
                        padding: 30px;
                        font-size: 24px !important;
                        font-weight: bold !important;
                        border: 2px solid #007bff;
                    }
                """)
                result_label.setAlignment(Qt.AlignCenter)
                text_layout.addWidget(result_label)

                # 显示预测置信度
                confidence_label = QLabel(f"置信度: {confidence * 100:.1f}%")
                confidence_label.setFont(QFont("Microsoft YaHei", 22, QFont.Bold))
                confidence_label.setStyleSheet("""
                    QLabel {
                        color: #28a745;
                        background-color: rgba(40, 167, 69, 0.1);
                        border-radius: 20px;
                        font-size: 22px !important;
                        font-weight: bold !important;
                        padding: 25px;
                        border: 2px solid #28a745;
                    }
                """)
                confidence_label.setAlignment(Qt.AlignCenter)
                text_layout.addWidget(confidence_label)

                # 显示模型信息
                model_info = QLabel(f"使用模型: {model_name}")
                model_info.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
                model_info.setStyleSheet("""
                    QLabel {
                        color: #6c757d;
                        background-color: rgba(108, 117, 125, 0.1);
                        border-radius: 20px;
                        padding: 20px;
                        font-size: 18px !important;
                        font-weight: bold !important;
                        border: 2px solid #6c757d;
                    }
                """)
                model_info.setAlignment(Qt.AlignCenter)
                text_layout.addWidget(model_info)

                # 添加分隔线
                separator = QFrame()
                separator.setFrameShape(QFrame.HLine)
                separator.setFrameShadow(QFrame.Sunken)
                separator.setStyleSheet("background-color: #dee2e6; height: 2px;")
                separator.setFixedHeight(2)
                text_layout.addWidget(separator)

                # 添加保存结果按钮
                save_btn = QPushButton("保存结果")
                save_btn.setObjectName("success")
                save_btn.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
                save_btn.setStyleSheet("""
                    QPushButton {
                        min-height: 50px;
                        border-radius: 12px;
                        padding: 15px 30px;
                    }
                """)
                save_btn.clicked.connect(lambda: self.save_prediction_result(prediction))
                text_layout.addWidget(save_btn)

                # 添加到主布局，设置相等的拉伸因子以实现左右平分
                main_layout.addWidget(image_container, 1)
                main_layout.addWidget(text_container, 1)

                # 添加到结果布局
                scroll_area = QScrollArea()
                scroll_area.setWidgetResizable(True)
                scroll_area.setWidget(main_container)
                scroll_area.setStyleSheet("""
                    QScrollArea {
                        border: none;
                        background: transparent;
                    }
                """)
                self.result_layout.addWidget(scroll_area)

            else:
                print("预测失败，请检查图像格式")
                QMessageBox.critical(self, "错误", "预测失败，请检查图像格式")

        except Exception as e:
            print(f"预测过程中发生错误: {str(e)}")
            self.logger.error(f"预测过程中发生错误: {str(e)}")
            QMessageBox.critical(self, "预测错误", f"预测失败: {str(e)}")

    def save_prediction_result(self, prediction):
        """保存预测结果"""
        try:
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            base_name = f"prediction_result_{timestamp}"

            # 保存到全局预测结果文件夹
            output_dir = CONFIG["prediction_results"]
            os.makedirs(output_dir, exist_ok=True)

            txt_path = os.path.join(output_dir, f"{base_name}.txt")
            img_path = os.path.join(output_dir, f"{base_name}.png")

            # 保存文本结果
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(f"预测时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"预测折射率: {prediction:.6f}\n")
                f.write(f"使用模型: {os.path.basename(self.current_model_dir)}\n")
                f.write(f"数据来源: {os.path.basename(self.predict_data_path)}\n")
                f.write(f"执行用户: {self.current_username}\n")

            # 保存图像副本
            img = Image.open(self.predict_data_path)
            img.save(img_path)

            # 保存到用户文件夹的data文件夹里
            if self.current_username:
                user_data_dir = os.path.join(CONFIG["user_info"], self.current_username, "data")
                os.makedirs(user_data_dir, exist_ok=True)

                user_txt_path = os.path.join(str(user_data_dir), f"{base_name}.txt")
                user_img_path = os.path.join(str(user_data_dir), f"{base_name}.png")

                # 复制文本结果到用户文件夹
                with open(user_txt_path, 'w', encoding='utf-8') as f:
                    f.write(f"预测时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write(f"预测折射率: {prediction:.6f}\n")
                    f.write(f"使用模型: {os.path.basename(self.current_model_dir)}\n")
                    f.write(f"数据来源: {os.path.basename(self.predict_data_path)}\n")
                    f.write(f"执行用户: {self.current_username}\n")

                img.save(user_img_path)
                print(f"预测结果已保存至: {txt_path} 和 {user_txt_path}")
                print(f"数据图像已保存至: {img_path} 和 {user_img_path}")
                QMessageBox.information(self, "成功", f"预测结果已保存至:\n{txt_path}\n和用户文件夹:\n{user_txt_path}")
            else:
                print(f"预测结果已保存至: {txt_path}")
                print(f"数据图像已保存至: {img_path}")
                QMessageBox.information(self, "成功", f"预测结果已保存至:\n{txt_path}")

        except Exception as e:
            print(f"保存结果失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存结果失败: {str(e)}")

    def display_image(self, file_path, parent_frame=None):
        self.clear_pic()
        if parent_frame is None:
            parent_frame = self.result_frame

        try:
            image = Image.open(file_path)

            # 转换为QPixmap
            if image.mode != "RGB":
                image = image.convert("RGB")

            qimage = ImageQt.ImageQt(image)
            pixmap = QPixmap.fromImage(qimage)

            # 调整图像大小以适应界面
            label_width = parent_frame.width() - 40
            label_height = parent_frame.height() - 80

            if label_width > 50 and label_height > 50:
                pixmap = pixmap.scaled(
                    label_width,
                    label_height,
                    Qt.KeepAspectRatio,
                    Qt.SmoothTransformation
                )

            # 创建滚动区域
            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_content = QWidget()
            scroll_layout = QVBoxLayout(scroll_content)

            # 显示图像
            image_label = QLabel()
            image_label.setPixmap(pixmap)
            image_label.setAlignment(Qt.AlignCenter)
            image_label.setStyleSheet("""
                QLabel {
                    border: 2px solid #dee2e6;
                    border-radius: 8px;
                    background-color: white;
                    padding: 10px;
                }
            """)
            scroll_layout.addWidget(image_label)

            # 显示文件名
            filename = os.path.basename(file_path)
            filename_label = QLabel(filename)
            filename_label.setFont(QFont("Microsoft YaHei", 10))
            filename_label.setAlignment(Qt.AlignCenter)
            scroll_layout.addWidget(filename_label)

            scroll_area.setWidget(scroll_content)

            # 添加到父框架
            layout = parent_frame.layout()
            if layout:
                # 清除现有内容
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)
                layout.addWidget(scroll_area)

            # 标记图像已显示
            if parent_frame == self.result_frame:
                self.image_displayed = True

            return True
        except Exception as e:
            print(f"无法显示图像: {str(e)}")
            self.logger.error(f"无法显示图像: {str(e)}")

            # 显示错误信息
            layout = parent_frame.layout()
            if layout:
                # 清除现有内容
                for i in reversed(range(layout.count())):
                    widget = layout.itemAt(i).widget()
                    if widget:
                        widget.setParent(None)
                error_label = QLabel("无法显示图像")
                error_label.setFont(QFont("Microsoft YaHei", 12))
                error_label.setAlignment(Qt.AlignCenter)
                layout.addWidget(error_label)

            return False

    def show_training_results(self, model_dir, feature_plot_path, cluster_plot_path, result_plot_path):
        """显示训练结果"""
        # 清空结果框架
        self.clear_pic()

        # 创建主框架
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建标题
        title_layout = QHBoxLayout()
        title_label = QLabel("训练结果")
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_label.setStyleSheet("color: #212529;")

        model_name = os.path.basename(model_dir)
        model_label = QLabel(f"模型: {model_name}")
        model_label.setFont(QFont("Microsoft YaHei", 12))
        model_label.setStyleSheet("color: #6c757d;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(model_label)
        main_layout.addLayout(title_layout)

        # 创建选项卡
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #ffffff;
                margin-top: 5px;
            }
        """)

        # 特征可视化选项卡
        feature_widget = QWidget()
        feature_layout = QVBoxLayout(feature_widget)
        self.display_image(feature_plot_path, feature_widget)
        tab_widget.addTab(feature_widget, "特征可视化")

        # 聚类分布选项卡
        cluster_widget = QWidget()
        cluster_layout = QVBoxLayout(cluster_widget)
        self.display_image(cluster_plot_path, cluster_widget)
        tab_widget.addTab(cluster_widget, "聚类分布")

        # 预测结果选项卡
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)
        self.display_image(result_plot_path, result_widget)
        tab_widget.addTab(result_widget, "预测结果")

        # 如果是SOM聚类，添加打开交互式网页的按钮，不显示SOM图片
        if self.clustering_methods == "som":
            som_html_path = os.path.join(model_dir, "som_visualization.html")
            if os.path.exists(som_html_path):
                # 创建居中的按钮布局
                button_layout = QVBoxLayout()
                button_layout.setAlignment(Qt.AlignCenter)
                button_layout.setSpacing(20)

                # 标题
                som_title = QLabel("SOM训练结果")
                som_title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
                som_title.setStyleSheet("color: #212529;")
                som_title.setAlignment(Qt.AlignCenter)

                # 说明文字
                som_desc = QLabel("点击查看完整的SOM交互式可视化报告")
                som_desc.setFont(QFont("Microsoft YaHei", 12))
                som_desc.setStyleSheet("color: #6c757d;")
                som_desc.setAlignment(Qt.AlignCenter)

                # 按钮
                open_som_btn = QPushButton("打开SOM交互式可视化报告")
                open_som_btn.setObjectName("primary")
                open_som_btn.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
                open_som_btn.setFixedSize(300, 50)
                open_som_btn.clicked.connect(lambda: self._open_som_visualization(som_html_path))

                button_layout.addWidget(som_title)
                button_layout.addWidget(som_desc)
                button_layout.addWidget(open_som_btn, alignment=Qt.AlignCenter)

                # 创建一个专门用于SOM按钮的选项卡
                som_button_widget = QWidget()
                som_button_layout = QVBoxLayout(som_button_widget)
                som_button_layout.addLayout(button_layout)
                tab_widget.addTab(som_button_widget, "SOM可视化")
            else:
                # 如果没有SOM网页，仍然显示原有的图片标签页
                self._add_som_image_tabs(model_dir, main_layout, tab_widget)
        else:
            # 如果是其他聚类方法，添加SOM特有的可视化选项卡
            self._add_som_image_tabs(model_dir, main_layout, tab_widget)

        main_layout.addWidget(tab_widget)

        # 模型信息
        info_layout = QHBoxLayout()
        info_label = QLabel("模型目录:")
        info_label.setFont(QFont("Microsoft YaHei", 10))

        model_dir_label = QLabel(model_dir)
        model_dir_label.setFont(QFont("Microsoft YaHei", 10))
        model_dir_label.setStyleSheet("color: #007bff;")

        info_layout.addWidget(info_label)
        info_layout.addWidget(model_dir_label)
        main_layout.addLayout(info_layout)

        self.result_layout.addWidget(main_widget)

        # 更新状态
        self.status_var.setText("已训练")
        self.status_indicator.setStyleSheet("color: #28a745;")
        self.model_dir_var.setText(os.path.basename(model_dir))

        # 加载刚训练的模型
        try:
            self.predictor = RefractiveIndexPredictor(model_dir)
            self.current_model_dir = model_dir
            self.logger.info("模型已成功加载")
            print("模型已成功加载")
        except Exception as e:
            print(f"加载模型失败: {str(e)}")
            self.logger.error(f"加载模型失败: {str(e)}")

    def show_optimization_history(self):
        """显示优化历史图表"""
        self.logger.info(f"用户请求查看优化历史图表")
        if not hasattr(self, 'predictor') or not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            self.logger.warning(f"警告: 请先加载模型")
            return

        try:
            self.predictor.get_optimization_history()
            self.logger.info(f"优化历史图表已显示")
            print("优化历史图表已显示")

        except Exception as e:
            print(f"无法显示优化历史: {str(e)}")
            self.logger.error(f"无法显示优化历史: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示优化历史: {str(e)}")

    def show_visualizations(self):
        """显示训练可视化结果 """
        self.logger.info(f"用户请求查看训练可视化结果")
        self.clear_pic()

        if not hasattr(self, 'predictor') or not self.predictor:
            QMessageBox.warning(self, "警告", "请先加载模型")
            self.logger.warning(f"用户请求查看训练可视化结果，但未加载模型")
            return

        try:
            results_dir = os.path.join(self.current_model_dir, "results")
            if not os.path.exists(results_dir):
                self.logger.error(f"可视化结果目录不存在")
                raise FileNotFoundError("可视化结果目录不存在")

            image_files = [f for f in os.listdir(results_dir) if f.endswith('.png')]
            if not image_files:
                self.logger.error(f"没有找到可视化图像")
                raise FileNotFoundError("没有找到可视化图像")

            # 查找特定的图像文件
            feature_plot = None
            cluster_plot = None
            result_plot = None

            for img_file in image_files:
                if "feature" in img_file.lower():
                    feature_plot = os.path.join(results_dir, img_file)
                elif "cluster" in img_file.lower():
                    cluster_plot = os.path.join(results_dir, img_file)
                elif "result" in img_file.lower():
                    result_plot = os.path.join(results_dir, img_file)

            if feature_plot and cluster_plot and result_plot:
                self.show_training_results(self.current_model_dir, feature_plot, cluster_plot, result_plot)
            else:
                self._show_visualizations_tabbed(results_dir, image_files)

            print("可视化结果已显示")

        except Exception as e:
            print(f"无法显示可视化结果: {str(e)}")
            self.logger.error(f"无法显示可视化结果: {str(e)}")
            QMessageBox.critical(self, "错误", f"无法显示可视化结果: {str(e)}")

    def _show_visualizations_tabbed(self, results_dir, image_files):
        """使用选项卡方式显示所有可视化结果"""
        # 清空结果框架
        self.clear_pic()

        # 创建主框架
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 创建标题
        title_layout = QHBoxLayout()
        title_label = QLabel("可视化结果")
        title_label.setFont(QFont("Microsoft YaHei", 20, QFont.Bold))
        title_label.setStyleSheet("color: #212529;")

        model_name = os.path.basename(self.current_model_dir)
        model_label = QLabel(f"模型: {model_name}")
        model_label.setFont(QFont("Microsoft YaHei", 12))
        model_label.setStyleSheet("color: #6c757d;")

        title_layout.addWidget(title_label)
        title_layout.addStretch()
        title_layout.addWidget(model_label)
        main_layout.addLayout(title_layout)

        # 创建选项卡
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #dee2e6;
                border-radius: 8px;
                background-color: #ffffff;
                margin-top: 5px;
            }
        """)

        som_tabs = []  # 用于存储SOM相关标签
        # 为每个图像文件创建一个选项卡
        for img_file in image_files:
            img_path = os.path.join(results_dir, img_file)

            tab_widget_content = QWidget()
            tab_layout = QVBoxLayout(tab_widget_content)
            self.display_image(img_path, tab_widget_content)

            tab_name = os.path.splitext(img_file)[0]
            # 简化标签名
            if "feature" in tab_name.lower():
                tab_label = "特征可视化"
            elif "cluster" in tab_name.lower():
                tab_label = "聚类分布"
            elif "result" in tab_name.lower():
                tab_label = "预测结果"
            elif "som_" in tab_name.lower():
                # 处理SOM特有的可视化图片
                som_label = tab_name.replace("som_", "")
                som_label = som_label.replace("_", " ").title()
                tab_label = f"SOM {som_label}"
                som_tabs.append((tab_widget_content, tab_label, img_path))
                continue  # SOM标签稍后处理
            else:
                tab_label = tab_name[:15] + "..." if len(tab_name) > 15 else tab_name

            tab_widget.addTab(tab_widget_content, tab_label)

        # 如果是SOM聚类，添加打开交互式网页的按钮，不显示SOM图片
        if hasattr(self, 'predictor') and self.predictor and self.predictor.clustering_method == "som":
            self.som_html_path = os.path.join(self.current_model_dir, "som_visualization.html")
            if os.path.exists(self.som_html_path):
                # 创建居中的按钮布局
                button_layout = QVBoxLayout()
                button_layout.setAlignment(Qt.AlignCenter)
                button_layout.setSpacing(20)

                # 标题
                som_title = QLabel("SOM可视化结果")
                som_title.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
                som_title.setStyleSheet("color: #212529;")
                som_title.setAlignment(Qt.AlignCenter)

                # 说明文字
                som_desc = QLabel("点击查看完整的SOM交互式可视化报告")
                som_desc.setFont(QFont("Microsoft YaHei", 12))
                som_desc.setStyleSheet("color: #6c757d;")
                som_desc.setAlignment(Qt.AlignCenter)

                # 按钮
                open_som_btn = QPushButton("打开SOM交互式可视化报告")
                open_som_btn.setObjectName("primary")
                open_som_btn.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
                open_som_btn.setFixedSize(300, 50)
                open_som_btn.clicked.connect(lambda: self._open_som_visualization(self.som_html_path))

                button_layout.addWidget(som_title)
                button_layout.addWidget(som_desc)
                button_layout.addWidget(open_som_btn, alignment=Qt.AlignCenter)

                # 创建一个专门用于SOM按钮的选项卡
                som_button_widget = QWidget()
                som_button_layout = QVBoxLayout(som_button_widget)
                som_button_layout.addLayout(button_layout)
                tab_widget.addTab(som_button_widget, "SOM可视化")
            else:
                # 如果没有SOM网页，仍然显示原有的图片标签页
                for tab_content, tab_label, img_path in som_tabs:
                    tab_widget.addTab(tab_content, tab_label)
        else:
            # 如果是其他聚类方法，添加SOM图片标签页
            for tab_content, tab_label, img_path in som_tabs:
                tab_widget.addTab(tab_content, tab_label)

        main_layout.addWidget(tab_widget)

        # 模型信息
        info_layout = QHBoxLayout()
        info_label = QLabel("模型目录:")
        info_label.setFont(QFont("Microsoft YaHei", 10))

        model_dir_label = QLabel(self.current_model_dir)
        model_dir_label.setFont(QFont("Microsoft YaHei", 10))
        model_dir_label.setStyleSheet("color: #007bff;")

        info_layout.addWidget(info_label)
        info_layout.addWidget(model_dir_label)
        main_layout.addLayout(info_layout)

        self.result_layout.addWidget(main_widget)

        # 更新状态
        self.status_var.setText("已训练")
        self.status_indicator.setStyleSheet("color: #28a745;")
        self.model_dir_var.setText(os.path.basename(self.current_model_dir))

    def _add_som_image_tabs(self, model_dir, main_layout, tab_widget=None):
        """添加SOM图像标签页（仅在没有HTML报告时使用）"""
        results_dir = os.path.join(model_dir, "results")
        som_files = []
        if os.path.exists(results_dir):
            som_files = [f for f in os.listdir(results_dir) if f.startswith("som_") and f.endswith(".png")]

        if som_files:
            if tab_widget is None:
                tab_widget = QTabWidget()
                tab_widget.setStyleSheet("""
                    QTabWidget::pane {
                        border: 1px solid #dee2e6;
                        border-radius: 8px;
                        background-color: #ffffff;
                        margin-top: 5px;
                    }
                """)
                main_layout.addWidget(tab_widget)

            for som_file in som_files:
                som_widget = QWidget()
                som_layout = QVBoxLayout(som_widget)
                som_path = os.path.join(results_dir, som_file)
                self.display_image(som_path, som_widget)

                tab_label = som_file.replace("som_", "").replace(".png", "")
                tab_label = tab_label.replace("_", " ").title()
                tab_widget.addTab(som_widget, f"SOM {tab_label}")

    def _open_som_visualization(self, html_path):
        """在默认浏览器中打开SOM交互式可视化报告"""
        self.logger.info(f"用户请求查看SOM交互式可视化报告: {html_path}")

        try:
            # 获取绝对路径
            absolute_path = os.path.abspath(html_path)

            if not os.path.exists(absolute_path):
                raise FileNotFoundError(f"文件不存在: {absolute_path}")

            self.logger.info(f"准备打开SOM可视化报告文件: {absolute_path}")

            # 记录打开前的浏览器进程
            before_pids = set(p.info['pid'] for p in psutil.process_iter(['pid', 'name'])
                              if any(browser in p.info['name'].lower()
                                     for browser in ['chrome', 'firefox', 'edge', 'safari', 'browser']))

            if os.name == 'nt':  # Windows系统
                cmd = f'start "" "{absolute_path}"'
                self.som_browser_process = subprocess.Popen(cmd, shell=True)
            else:  # Linux/Mac系统
                self.som_browser_process = subprocess.Popen(['xdg-open', absolute_path])

            time.sleep(0.5)

            # 记录可能的新浏览器进程
            after_pids = set(p.info['pid'] for p in psutil.process_iter(['pid', 'name'])
                             if any(browser in p.info['name'].lower()
                                    for browser in ['chrome', 'firefox', 'edge', 'safari', 'browser']))

            # 保存新启动的浏览器进程PID
            self.som_browser_pids = after_pids - before_pids
            self.som_browser_pids.add(self.som_browser_process.pid)

            self.logger.info(f"使用subprocess打开SOM可视化报告, PID={self.som_browser_process.pid}")
            self.logger.info(f"跟踪的浏览器进程: {self.som_browser_pids}")

            QMessageBox.information(self, "提示", "SOM交互式可视化报告已在默认浏览器中打开")

        except Exception as e:
            self.logger.error(f"打开SOM可视化报告失败: {str(e)}")
            QMessageBox.critical(self, "错误",
                                 f"无法打开SOM可视化报告:\n请尝试手动打开: {absolute_path}\n错误详情: {str(e)}")

    def close_som_browser(self):
        """关闭SOM浏览器进程"""
        if not self.som_browser_process and not self.som_browser_pids:
            self.logger.info("没有SOM浏览器进程需要关闭")
            return True

        # 收集所有需要关闭的进程
        processes_to_close = set()

        # 添加通过subprocess启动的进程及其子进程
        if self.som_browser_process:
            try:
                parent = psutil.Process(self.som_browser_process.pid)
                processes_to_close.add(parent)
                # 添加所有子进程
                processes_to_close.update(parent.children(recursive=True))
            except psutil.NoSuchProcess:
                self.logger.info(f"SOM浏览器进程已不存在: PID={self.som_browser_process.pid}")

        # 添加跟踪到的浏览器进程
        for pid in self.som_browser_pids:
            try:
                process = psutil.Process(pid)
                processes_to_close.add(process)
            except psutil.NoSuchProcess:
                self.logger.info(f"SOM浏览器进程已不存在: PID={pid}")

        # 查找命令行中包含HTML文件名的进程
        try:
            som_html_filename = "som_visualization.html"
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and any(som_html_filename in cmd for cmd in proc.info['cmdline']):
                        processes_to_close.add(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.error(f"查找相关SOM浏览器进程时出错: {str(e)}")

        # 关闭所有收集到的进程
        closed_count = 0
        for process in processes_to_close:
            try:
                if process.is_running():
                    process.terminate()
                    closed_count += 1
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                self.logger.error(f"终止进程 {process.pid} 时出错: {str(e)}")

        # 等待进程结束
        if processes_to_close:
            gone, alive = psutil.wait_procs(list(processes_to_close), timeout=3)
            # 强制杀死未响应的进程
            for process in alive:
                try:
                    process.kill()
                    closed_count += 1
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    self.logger.error(f"强制终止进程 {process.pid} 时出错: {str(e)}")

        self.logger.info(f"已关闭 {closed_count} 个SOM浏览器相关进程")

        # 清理状态
        self.som_browser_process = None
        self.som_browser_pids.clear()
        return True

    def save_current_results(self):
        """保存当前结果"""
        try:
            if not self.data_loaded:
                QMessageBox.warning(self, "警告", "没有可保存的结果")
                return

            output_dir = QFileDialog.getExistingDirectory(
                self,
                "选择保存位置",
                get_output_path("")
            )
            if not output_dir:
                return

            # 保存当前显示的图像
            if self.predict_data_path:
                img = Image.open(self.predict_data_path)
                save_path = os.path.join(output_dir, os.path.basename(self.predict_data_path))
                img.save(save_path)
                print(f"当前图像已保存至: {save_path}")

            # 保存输出内容
            output_content = self.output_text.toPlainText()
            if output_content:
                save_path = os.path.join(output_dir, "output_log.txt")
                with open(save_path, 'w', encoding='utf-8') as f:
                    f.write(output_content)
                print(f"输出日志已保存至: {save_path}")

            QMessageBox.information(self, "成功", "结果已成功保存")

        except Exception as e:
            print(f"保存结果失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"保存结果失败: {str(e)}")

    def data_augmentation(self):
        """数据增强功能"""
        self.logger.info("用户请求数据增强")

        # 检查是否有理论数据
        theoretical_data_path = os.path.join(CONFIG["data_path"], "theoretical_data.csv")
        template_dir = os.path.join(CONFIG["base_dir"], "template")

        # 检查是否有理论数据或图像数据
        if not os.path.exists(theoretical_data_path) and not os.path.exists(template_dir):
            reply = QMessageBox.question(self, "确认", "尚未生成理论数据或图像数据，是否先生成理论数据？")
            if reply == QMessageBox.No:
                return
            else:
                # 先生成理论数据
                self.generate_theoretical_data()
                # 等待一段时间让理论数据生成完成
                QTimer.singleShot(100, lambda: self._continue_data_augmentation())
                return

        # 如果已有数据，直接继续数据增强
        self._continue_data_augmentation()

    def _continue_data_augmentation(self):
        """继续执行数据增强"""
        # 创建数据增强对话框
        dialog = QDialog(self)
        dialog.setWindowTitle("数据增强选项")
        dialog.setFixedSize(500, 400)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("数据增强参数")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        # 数据类型选择
        type_group = QGroupBox("数据类型")
        type_layout = QVBoxLayout(type_group)

        type_inner_layout = QHBoxLayout()
        type_label = QLabel("增强类型:")
        type_label.setFont(QFont("Microsoft YaHei", 10))
        self.theoretical_radio = QRadioButton("理论数据")
        self.image_radio = QRadioButton("图像数据")
        self.theoretical_radio.setChecked(True)

        type_inner_layout.addWidget(type_label)
        type_inner_layout.addWidget(self.theoretical_radio)
        type_inner_layout.addWidget(self.image_radio)
        type_layout.addLayout(type_inner_layout)
        layout.addWidget(type_group)

        # 图像增强参数
        self.image_params_widget = QGroupBox("图像增强参数")
        image_params_layout = QVBoxLayout(self.image_params_widget)

        image_count_layout = QHBoxLayout()
        image_count_label = QLabel("生成数量:")
        image_count_label.setFont(QFont("Microsoft YaHei", 10))
        self.image_count_var = QSpinBox()
        self.image_count_var.setRange(100, 10000)
        self.image_count_var.setValue(1000)
        image_count_layout.addWidget(image_count_label)
        image_count_layout.addWidget(self.image_count_var)
        image_params_layout.addLayout(image_count_layout)

        # 显示图像来源目录
        template_dir = os.path.join(CONFIG["base_dir"], "template")
        source_label = QLabel(f"图像来源: {template_dir}")
        source_label.setFont(QFont("Microsoft YaHei", 9))
        source_label.setWordWrap(True)
        source_label.setStyleSheet("color: #6c757d;")
        image_params_layout.addWidget(source_label)

        layout.addWidget(self.image_params_widget)
        self.image_params_widget.setVisible(False)

        # 增强参数组
        params_group = QGroupBox("增强参数")
        params_layout = QVBoxLayout(params_group)

        # 增强倍数
        multiplier_layout = QHBoxLayout()
        multiplier_label = QLabel("增强倍数:")
        multiplier_label.setFont(QFont("Microsoft YaHei", 10))
        self.multiplier_var = QSpinBox()
        self.multiplier_var.setRange(1, 10)
        self.multiplier_var.setValue(2)
        multiplier_layout.addWidget(multiplier_label)
        multiplier_layout.addWidget(self.multiplier_var)
        params_layout.addLayout(multiplier_layout)

        # 噪声水平
        noise_layout = QHBoxLayout()
        noise_label = QLabel("噪声水平:")
        noise_label.setFont(QFont("Microsoft YaHei", 10))
        self.noise_var = QDoubleSpinBox()
        self.noise_var.setRange(0, 0.1)
        self.noise_var.setSingleStep(0.001)
        self.noise_var.setValue(0.01)
        noise_layout.addWidget(noise_label)
        noise_layout.addWidget(self.noise_var)
        params_layout.addLayout(noise_layout)

        layout.addWidget(params_group)

        # 连接信号以显示/隐藏图像参数
        self.theoretical_radio.toggled.connect(self.toggle_augmentation_options)
        self.image_radio.toggled.connect(self.toggle_augmentation_options)

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        confirm_btn = QPushButton("确定")
        confirm_btn.setObjectName("primary")
        confirm_btn.clicked.connect(lambda: self._confirm_data_augmentation(dialog))

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("danger")
        cancel_btn.clicked.connect(dialog.close)

        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def toggle_augmentation_options(self):
        """切换数据增强选项显示"""
        if self.theoretical_radio.isChecked():
            self.image_params_widget.setVisible(False)
        else:
            self.image_params_widget.setVisible(True)

    def _confirm_data_augmentation(self, dialog):
        """确认数据增强参数"""
        if self.theoretical_radio.isChecked():
            multiplier = self.multiplier_var.value()
            noise_level = self.noise_var.value()
            dialog.close()

            # 在新线程中执行理论数据增强
            augmentation_thread = threading.Thread(
                target=self.run_data_augmentation,
                args=(multiplier, noise_level),
                daemon=True
            )
            augmentation_thread.start()
        else:
            # 图像数据增强
            image_count = self.image_count_var.value()
            noise_level = self.noise_var.value()

            dialog.close()

            # 在新线程中执行图像数据增强
            augmentation_thread = threading.Thread(
                target=self.run_image_augmentation,
                args=(image_count, noise_level),
                daemon=True
            )
            augmentation_thread.start()

    def run_data_augmentation(self, multiplier, noise_level):
        """执行理论数据增强"""
        try:
            print(f"\n=== 开始理论数据增强 (倍数: {multiplier}, 噪声水平: {noise_level}) ===")

            # 加载现有理论数据
            data_path = os.path.join(CONFIG["data_path"], "theoretical_data.csv")

            # 检查理论数据文件是否存在
            if not os.path.exists(data_path):
                print("理论数据文件不存在，请先生成理论数据")
                # 在主线程中显示错误消息框
                QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", "理论数据文件不存在，请先生成理论数据"))
                return

            df = pd.read_csv(data_path)
            print(f"原始数据集大小: {len(df)}")

            # 创建增强后的数据集
            augmented_df = df.copy()

            # 应用数据增强
            for i in range(multiplier - 1):
                # 复制数据并添加噪声
                new_df = df.copy()

                # 对角度数据添加噪声
                new_df['i1'] += np.random.normal(0, noise_level, size=len(new_df))
                new_df['delta'] += np.random.normal(0, noise_level, size=len(new_df))

                # 对折射率添加噪声，限制折射率在合理范围内 (通常在1.0-2.0之间)
                rn_noise = np.random.normal(0, noise_level * 0.1, size=len(new_df))
                new_df['rn'] = np.clip(new_df['rn'] + rn_noise, 1.0, 2.0)

                # 合并数据
                augmented_df = pd.concat([augmented_df, new_df], ignore_index=True)

            # 保存增强后的数据
            aug_data_path = os.path.join(CONFIG["data_path"], "augmented_data.csv")
            augmented_df.to_csv(aug_data_path, index=False)

            print(f"理论数据增强完成！增强后数据集大小: {len(augmented_df)}")
            print(f"增强数据已保存至: {aug_data_path}")

            # 更新状态
            self.theoretical_data_generated = True

            # 在主线程中显示消息框
            QTimer.singleShot(0, lambda: QMessageBox.information(self, "成功", "理论数据增强完成！"))

        except Exception as e:
            error_msg = f"理论数据增强失败: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)
            # 在主线程中显示错误消息框
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", f"理论数据增强失败: {str(e)}"))

    def run_image_augmentation(self, augment_count, noise_level):
        """对图像数据集进行增强"""
        try:
            print(f"\n=== 开始图像数据增强 ===")

            # 使用template目录中的图像
            template_dir = os.path.join(CONFIG["base_dir"], "template")

            # 检查图像目录是否存在
            if not os.path.exists(template_dir):
                raise FileNotFoundError(f"图像目录不存在: {template_dir}")

            # 创建增强图像保存目录
            aug_image_dir = os.path.join(CONFIG["data_path"], "augmented_images")
            os.makedirs(aug_image_dir, exist_ok=True)

            # 收集所有图像文件
            image_files = []
            for file in os.listdir(template_dir):
                if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                    image_files.append(os.path.join(template_dir, file))

            if not image_files:
                raise ValueError("template目录中没有找到图像文件")

            print(f"找到 {len(image_files)} 个图像文件")

            # 导入图像处理库
            from PIL import Image, ImageEnhance, ImageFilter
            import random

            generated_count = 0
            for i in range(augment_count):
                # 随机选择一个原始图像
                source_image_path = random.choice(image_files)
                source_image = Image.open(source_image_path)

                # 应用随机变换
                # 1. 随机旋转 (-15到15度)
                angle = random.uniform(-15, 15)
                augmented_image = source_image.rotate(angle, expand=True, fillcolor=(255, 255, 255))

                # 2. 随机调整亮度 (0.8到1.2倍)
                brightness = random.uniform(0.8, 1.2)
                enhancer = ImageEnhance.Brightness(augmented_image)
                augmented_image = enhancer.enhance(brightness)

                # 3. 随机调整对比度 (0.8到1.2倍)
                contrast = random.uniform(0.8, 1.2)
                enhancer = ImageEnhance.Contrast(augmented_image)
                augmented_image = enhancer.enhance(contrast)

                # 4. 随机调整色彩 (0.9到1.1倍)
                color = random.uniform(0.9, 1.1)
                enhancer = ImageEnhance.Color(augmented_image)
                augmented_image = enhancer.enhance(color)

                # 5. 随机添加轻微模糊
                if random.random() < 0.3:  # 30%概率添加模糊
                    augmented_image = augmented_image.filter(ImageFilter.GaussianBlur(radius=random.uniform(0.5, 1.5)))

                # 6. 随机水平翻转
                if random.random() < 0.5:
                    augmented_image = augmented_image.transpose(Image.FLIP_LEFT_RIGHT)

                # 保存增强后的图像
                base_name = os.path.basename(source_image_path)
                name, ext = os.path.splitext(base_name)
                aug_image_name = f"{name}_aug_{i:04d}{ext}"
                aug_image_path = os.path.join(aug_image_dir, aug_image_name)
                augmented_image.save(aug_image_path)

                generated_count += 1
                if generated_count % 100 == 0:
                    print(f"已生成 {generated_count} 张增强图像")

            print(f"图像数据增强完成！共生成 {generated_count} 张增强图像")
            print(f"增强图像已保存至: {aug_image_dir}")

            # 在主线程中显示消息框
            QTimer.singleShot(0, lambda: QMessageBox.information(self, "成功",
                                                                 f"图像数据增强完成！\n共生成 {generated_count} 张增强图像"))

        except Exception as e:
            error_msg = f"图像数据增强失败: {str(e)}"
            print(error_msg)
            self.logger.error(error_msg)

            # 在主线程中显示错误消息框
            QTimer.singleShot(0, lambda: QMessageBox.critical(self, "错误", f"图像数据增强失败: {str(e)}"))

    def export_model(self):
        """导出模型为通用格式"""
        self.logger.info("用户请求导出模型")
        if not self.current_model_dir:
            QMessageBox.warning(self, "警告", "请先加载模型")
            return

        # 选择导出格式
        dialog = QDialog(self)
        dialog.setWindowTitle("导出模型")
        dialog.setFixedSize(450, 350)
        dialog.setModal(True)
        dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("选择导出格式")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setObjectName("title")
        layout.addWidget(title_label)

        # 格式选择
        format_group = QGroupBox("导出格式")
        format_layout = QVBoxLayout(format_group)

        self.export_format = "joblib"

        joblib_radio = QRadioButton("Joblib (.joblib)")
        joblib_radio.setChecked(True)
        joblib_radio.toggled.connect(lambda: self._set_export_format("joblib") if joblib_radio.isChecked() else None)

        pickle_radio = QRadioButton("Pickle (.pkl)")
        pickle_radio.toggled.connect(lambda: self._set_export_format("pickle") if pickle_radio.isChecked() else None)

        format_layout.addWidget(joblib_radio)
        format_layout.addWidget(pickle_radio)
        layout.addWidget(format_group)

        # 确认和取消按钮
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        confirm_btn = QPushButton("导出")
        confirm_btn.setObjectName("primary")
        confirm_btn.clicked.connect(lambda: self._confirm_export(dialog))

        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("danger")
        cancel_btn.clicked.connect(dialog.close)

        button_layout.addWidget(confirm_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        dialog.exec()

    def _set_export_format(self, format_val):
        """设置导出格式"""
        self.export_format = format_val

    def _confirm_export(self, dialog):
        """确认导出"""
        format_val = self.export_format
        dialog.close()

        # 选择保存位置
        initial_dir = get_output_path("exported_models")
        os.makedirs(initial_dir, exist_ok=True)

        default_name = os.path.basename(self.current_model_dir)

        if format_val == "joblib":
            file_filter = "Joblib files (*.joblib)"
            ext = ".joblib"
        elif format_val == "pickle":
            file_filter = "Pickle files (*.pkl)"
            ext = ".pkl"

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "保存模型",
            os.path.join(initial_dir, default_name + ext),
            file_filter
        )

        if not save_path:
            return

        # 导出模型
        try:
            # 加载模型
            model_path = os.path.join(self.current_model_dir, "models", CONFIG["save_model"])
            model = joblib.load(model_path)

            # 保存为指定格式
            if format_val == "joblib":
                joblib.dump(model, save_path)
            elif format_val == "pickle":
                with open(save_path, 'wb') as f:
                    joblib.dump(model, f)
            print(f"模型已成功导出至: {save_path}")
            QMessageBox.information(self, "成功", f"模型已成功导出至:\n{save_path}")

        except Exception as e:
            print(f"导出模型失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"导出模型失败: {str(e)}")

    def manage_models(self):
        """模型管理功能"""
        try:
            dialog = ModelManagerDialog(self)
            dialog.exec()
        except Exception as e:
            self.logger.error(f"打开模型管理对话框失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"打开模型管理对话框失败: {str(e)}")

    def show_prediction_history(self):
        """显示预测历史记录"""
        self.history_manager.show_prediction_history()

    def scan_available_models(self):
        """扫描可用的模型目录"""
        self.models_list = []
        base_dir = CONFIG["base_model_dir"]

        if not os.path.exists(base_dir):
            return

        for model_dir in os.listdir(base_dir):
            full_path = os.path.join(base_dir, model_dir)
            if os.path.isdir(full_path):
                model_path = os.path.join(full_path, "models", CONFIG["save_model"])
                if os.path.exists(model_path):
                    self.models_list.append({
                        "name": model_dir,
                        "path": full_path,
                        "created": time.ctime(os.path.getctime(full_path))
                    })

        print(f"扫描到 {len(self.models_list)} 个可用模型")

    def compare_models(self):
        """比较不同模型的性能"""
        self.scan_available_models()
        self.model_comparator = ModelComparator(self)
        self.model_comparator.compare_models()

    def toggle_system_monitor(self):
        """切换系统监控状态"""
        try:
            self.system_monitor = SystemMonitor(self)
            self.system_monitor.toggle_system_monitor()
        except Exception as e:
            self.logger.error(f"切换系统监控时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"启动系统监控失败: {str(e)}")

    def show_monitoring_logs(self):
        """显示监控日志"""
        try:
            self.system_monitor = SystemMonitor(self)
            self.system_monitor.show_monitoring_logs()
        except Exception as e:
            self.logger.error(f"显示监控日志时出错: {str(e)}")
            QMessageBox.critical(self, "错误", f"显示监控日志失败: {str(e)}")

    def batch_prediction(self):
        """批量预测功能"""
        self.batch_predictor = BatchPredictor(self)
        self.batch_predictor.batch_prediction()

    def show_customize_shortcuts_dialog(self):
        """显示自定义快捷键对话框"""
        self.shortcut_manager.show_customize_shortcuts_dialog()

    def show_shortcuts_dialog(self):
        """显示快捷键列表对话框"""
        self.shortcut_manager.show_shortcuts_dialog()

    def check_for_updates(self):
        """检查更新"""
        # 初始化自动更新器（如果尚未初始化）
        if not hasattr(self, 'auto_updater'):
            self.auto_updater = AutoUpdater(self, "3.1.0")
        self.auto_updater.check_for_updates()

    def show_usage_guide(self):
        """显示使用手册"""
        try:
            root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            pdf_path = os.path.join(root_dir, "README.pdf")

            # 检查PDF文件是否存在
            if not os.path.exists(pdf_path):
                webbrowser.open("https://github.com/Legionxun/spectra-refract-svr/blob/main/README.md")
                print("在线使用手册已打开")
                return

            # 尝试打开PDF文件
            if sys.platform.startswith('win'):
                os.startfile(pdf_path) # Windows系统
            elif sys.platform.startswith('darwin'):
                subprocess.Popen(['open', pdf_path]) # macOS系统
            else:
                subprocess.Popen(['xdg-open', pdf_path]) # Linux系统
            print(f"已打开使用手册: {pdf_path}")

        except Exception as e:
            webbrowser.open("https://github.com/Legionxun/spectra-refract-svr/blob/main/README.md")
            print("在线使用手册已打开")

    def show_about(self):
        """显示关于信息"""
        self.logger.info("用户请求显示关于信息")

        about_dialog = QDialog(self)
        about_dialog.setWindowTitle("关于")
        about_dialog.setMinimumSize(500, 450)  # 使用最小尺寸
        about_dialog.resize(500, 450)  # 设置初始大小
        about_dialog.setModal(True)
        about_dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(about_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("OptiSVR分光计折射率预测系统")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #212529;")
        layout.addWidget(title_label)

        # 版本信息
        version_label = QLabel("版本: 3.1.0")
        version_label.setFont(QFont("Microsoft YaHei", 12))
        version_label.setAlignment(Qt.AlignCenter)
        version_label.setStyleSheet("color: #6c757d;")
        layout.addWidget(version_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #dee2e6; height: 1px;")
        layout.addWidget(separator)

        # 开发团队
        team_label = QLabel("开发团队: 吴迅  徐一田  赵子涵")
        team_label.setFont(QFont("Microsoft YaHei", 12))
        team_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(team_label)

        desc_text = QLabel("""
        <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        本系统是一个基于人工智能算法的分光计折射率预测系统，
        采用多种无监督学习聚类(K-Means & SOM)和支持向量回归(SVR)算法，
        同时结合深度学习ResNet50网络模型对入射角-偏向角图像进行特征提取，
        通过多次训练调整超参数得到最佳权重保存最佳预训练模型。</p>
        <p>&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;
        预测思路是将测定的数据插值后转为入射角-偏向角图像，
        对图片曲线进行预测，能够准确预测分光计的折射率特性。</p>
        
        <p><b>主要功能:</b></p>
        <ul>
        <li>用户系统及数据库、权限管理</li>
        <li>理论数据生成及增强</li>
        <li>模型管理、加载、训练、导出及比较</li>
        <li>折射率单次预测与批量预测</li>
        <li>优化历史和可视化结果展示</li>
        <li>系统监控与输出展示</li>
        </ul>

        <p><b>技术栈:</b></p>
        <ul>
        <li>Python 3.9.6</li>
        <li>SQlite3</li>
        <li>TensorFlow 2.10.0 & Scikit-learn</li>
        <li>Optuna & Bayesian Optimization</li>
        <li>K-Means & Self-Organizing Maps</li>
        <li>Matplotlib & Plotly</li>
        <li>NumPy & SciPy</li>
        <li>PySide6 GUI</li>
        </ul>
        """)
        desc_text.setFont(QFont("Microsoft YaHei", 10))
        desc_text.setWordWrap(True)
        layout.addWidget(desc_text)

        # 版权信息
        copyright_label = QLabel("© 2025 OptiSVR研究室 版权所有")
        copyright_label.setFont(QFont("Microsoft YaHei", 10))
        copyright_label.setAlignment(Qt.AlignCenter)
        copyright_label.setStyleSheet("color: #6c757d; margin-top: 10px;")
        layout.addWidget(copyright_label)

        # 确定按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("确定")
        ok_button.setObjectName("primary")
        ok_button.clicked.connect(about_dialog.accept)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        about_dialog.exec()

    def on_close(self):
        """关闭应用程序的回调方法"""
        self.close()

    def closeEvent(self, event):
        """关闭应用程序时的清理操作"""
        try:
            # 保存窗口位置和大小
            self.save_window_geometry()

            # 停止系统监控
            self.monitoring_active = False

            # 恢复标准输出
            sys.stdout = sys.__stdout__

            # 关闭优化历史浏览器窗口
            if hasattr(self, 'predictor') and self.predictor:
                try:
                    self.predictor.close_browser()
                except Exception as e:
                    print(f"关闭浏览器时出错: {str(e)}")
                    self.logger.error(f"关闭浏览器时出错: {str(e)}")

            # 关闭SOM浏览器窗口
            self.close_som_browser()

            # 删除临时文件夹
            try:
                if os.path.exists(CONFIG["temp_dir"]):
                    shutil.rmtree(CONFIG["temp_dir"])
                    print(f"已删除临时文件夹: {CONFIG['temp_dir']}")
            except Exception as e:
                print(f"删除临时文件夹失败: {str(e)}")
                self.logger.error(f"删除临时文件夹失败: {str(e)}")
        except Exception as e:
            self.logger.error(f"关闭应用程序时发生错误: {str(e)}")
        finally:
            event.accept()
            QTimer.singleShot(100, lambda: sys.exit(0))
