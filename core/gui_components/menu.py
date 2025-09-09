# core/gui_components/menu.py
import logging, os
from PySide6.QtWidgets import (QMenuBar, QMenu, QLabel, QToolBar, QSizePolicy, QHBoxLayout,
                               QWidget, QDialog, QVBoxLayout, QPushButton, QTableWidget,
                               QTableWidgetItem, QAbstractItemView, QHeaderView, QTabWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import (QFont, QPixmap, QPainter, QBrush, QColor,
                           QRadialGradient, QAction, QIcon, QPainterPath)

from ..config import CONFIG


class MenuBuilder:
    """菜单构建器"""
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.menu_items = {}
        self.logger = logging.getLogger("MenuBuilder")
        self.avatar_button = None
        self.avatar_toolbar = None
        self.menu_permissions = {
            "生成理论数据": "generate_data",
            "自定义生成理论数据": "generate_data",
            "数据增强": "data_augmentation",
            "导入数据1(原始数据)": "import_data",
            "导入数据2(绘图到80度)": "import_data",
            "训练模型": "train_model",
            "加载模型": "import_model",
            "导出模型": "export_model",
            "模型管理": "manage_models",
            "模型比较": "compare_model",
            "预测折射率": "run_prediction",
            "批量预测": "run_prediction",
            "查看优化历史": "view_prediction",
            "查看可视化结果": "view_prediction",
            "查看预测历史": "view_prediction",
            "保存当前系统输出内容": "export_data",
            "系统监控": "system_monitor",
            "查看监控日志": "show_monitoring_logs",
            "用户管理": "user_management",
            "自定义快捷键": "customize_shortcuts",
        }

    def build_menu(self):
        """构建菜单"""
        self.menu_bar = QMenuBar(self.main_window)

        # 设置菜单样式
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2c3e50, stop:1 #1a2530);
                color: #ecf0f1;
                border-bottom: 1px solid #34495e;
                padding: 2px 0;
                spacing: 2px;
            }
            QMenuBar::item {
                background: transparent;
                padding: 7px 15px;
                margin: 0 3px;
                border-radius: 5px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
                border: 1px solid transparent;
            }
            QMenuBar::item:selected {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #3498db, stop:1 #2980b9);
                border: 1px solid #5dade2;
                color: #ffffff;
            }
            QMenuBar::item:pressed {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2980b9, stop:1 #3498db);
                border: 1px solid #5dade2;
            }
            QMenu {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 8px;
                padding: 6px 0;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);
            }
            QMenu::item {
                padding: 10px 35px 10px 30px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                font-weight: normal;
            }
            QMenu::item:selected {
                background-color: #3498db;
                border-radius: 5px;
                margin: 0 5px;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #34495e;
                margin: 5px 10px;
            }
            QMenu::icon {
                padding-left: 10px;
            }
            QMenu::item:disabled {
                color: #7f8c8d;
            }
        """)

        # 文件菜单
        file_menu = QMenu("文件", self.menu_bar)
        file_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        import_original_action = file_menu.addAction("导入数据1(原始数据) (O)", self.app.import_data_original)
        import_processed_action = file_menu.addAction("导入数据2(绘图到80度) (Ctrl+Shift+O)",
                                                      self.app.import_data_processed)
        file_menu.addSeparator()
        save_results_action = file_menu.addAction("保存当前系统输出内容 (S)", self.app.save_current_results)
        file_menu.addSeparator()
        file_menu.addAction("退出 (Q)", self.app.on_close)
        self.menu_bar.addMenu(file_menu)

        # 数据处理菜单
        data_menu = QMenu("数据处理", self.menu_bar)
        data_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        gen_data_action = data_menu.addAction("生成理论数据 (G)", self.app.generate_theoretical_data)
        custom_gen_data_action = data_menu.addAction("自定义生成理论数据(Ctrl+Shift+G)",
                                                     self.app.custom_generate_theoretical_data)
        stop_gen_action = data_menu.addAction("停止生成(Z)", self.app.stop_generation)
        data_menu.addSeparator()
        data_aug_action = data_menu.addAction("数据增强(Ctrl+Shift+U)", self.app.data_augmentation)
        self.menu_bar.addMenu(data_menu)

        # 模型操作菜单
        model_menu = QMenu("模型操作", self.menu_bar)
        model_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        train_model_action = model_menu.addAction("训练模型(T)", self.app.start_training)
        stop_train_action = model_menu.addAction("停止训练(X)", self.app.stop_training)
        model_menu.addSeparator()
        load_model_action = model_menu.addAction("加载模型(L)", self.app.load_model)
        export_model_action = model_menu.addAction("导出模型(E)", self.app.export_model)
        # 添加模型管理功能
        model_menu.addSeparator()
        manage_models_action = model_menu.addAction("模型管理(M)", self.app.manage_models)
        self.menu_bar.addMenu(model_menu)

        # 预测分析菜单
        predict_menu = QMenu("预测分析", self.menu_bar)
        predict_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        predict_action = predict_menu.addAction("预测折射率(P)", self.app.predict_refractive_index)
        batch_predict_action = predict_menu.addAction("批量预测(B)", self.app.batch_prediction)
        self.menu_bar.addMenu(predict_menu)

        # 查看分析菜单
        view_menu = QMenu("查看分析", self.menu_bar)
        view_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        opt_history_action = view_menu.addAction("查看优化历史(O)", self.app.show_optimization_history)
        vis_results_action = view_menu.addAction("查看可视化结果(V)", self.app.show_visualizations)
        view_menu.addSeparator()
        compare_models_action = view_menu.addAction("模型比较(Ctrl+shift+M)", self.app.compare_models)
        self.menu_bar.addMenu(view_menu)

        # 历史记录菜单
        history_menu = QMenu("历史记录", self.menu_bar)
        history_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        pred_history_action = history_menu.addAction("查看预测历史(H)", self.app.show_prediction_history)
        monitor_logs_action = history_menu.addAction("查看监控日志(N)", self.app.show_monitoring_logs)
        self.menu_bar.addMenu(history_menu)

        # 系统工具菜单
        tools_menu = QMenu("系统工具", self.menu_bar)
        tools_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        refresh_action = tools_menu.addAction("刷新界面(F5)", self.app.refresh_page)
        clear_chart_action = tools_menu.addAction("清空图表(D)", self.app.init_result_frame)
        clear_output_action = tools_menu.addAction("清空输出(Ctrl+Shift+D)", self.app.clear_output)
        tools_menu.addSeparator()
        sys_monitor_action = tools_menu.addAction("系统监控(Y)", self.app.toggle_system_monitor)
        tools_menu.addSeparator()
        user_management_action = tools_menu.addAction("用户管理(Ctrl+shift+P)", self.app.open_user_management)
        self.menu_bar.addMenu(tools_menu)

        # 帮助菜单
        help_menu = QMenu("帮助", self.menu_bar)
        help_menu.setFont(QFont("Microsoft YaHei", 11, QFont.Bold))
        help_menu.addAction("切换主题(Alt+D)", self.app.toggle_theme)
        help_menu.addAction("使用指南(F1)", self.app.show_usage_guide)
        help_menu.addAction("快捷键列表(K)", self.app.show_shortcuts_dialog)
        customize_shortcuts = help_menu.addAction("自定义快捷键(Ctrl+Shift+K)",
                                                  self.app.show_customize_shortcuts_dialog)
        help_menu.addSeparator()
        help_menu.addAction("检查更新(U)", self.app.check_for_updates)  # 添加检查更新选项
        help_menu.addAction("关于(A)", self.app.show_about)
        self.menu_bar.addMenu(help_menu)

        # 创建用户头像工具栏
        self.create_avatar_toolbar()

        self.main_window.setMenuBar(self.menu_bar)

        # 保存菜单项引用
        self.menu_items = {
            # 数据处理菜单项
            "生成理论数据": (data_menu, gen_data_action),
            "自定义生成理论数据": (data_menu, custom_gen_data_action),
            "停止生成": (data_menu, stop_gen_action),
            "数据增强": (data_menu, data_aug_action),

            # 模型操作菜单项
            "训练模型": (model_menu, train_model_action),
            "停止训练": (model_menu, stop_train_action),
            "加载模型": (model_menu, load_model_action),
            "导出模型": (model_menu, export_model_action),
            "模型管理": (model_menu, manage_models_action),

            # 预测分析菜单项
            "预测折射率": (predict_menu, predict_action),
            "批量预测": (predict_menu, batch_predict_action),

            # 查看分析菜单项
            "查看优化历史": (view_menu, opt_history_action),
            "查看可视化结果": (view_menu, vis_results_action),
            "模型比较": (view_menu, compare_models_action),

            # 历史记录菜单项
            "查看预测历史": (history_menu, pred_history_action),
            "查看监控日志": (history_menu, monitor_logs_action),

            # 系统工具菜单项
            "刷新界面": (tools_menu, refresh_action),
            "清空图表": (tools_menu, clear_chart_action),
            "清空输出": (tools_menu, clear_output_action),
            "系统监控": (tools_menu, sys_monitor_action),
            "用户管理": (tools_menu, user_management_action),

            # 文件菜单项
            "导入数据1(原始数据)": (file_menu, import_original_action),
            "导入数据2(绘图到80度)": (file_menu, import_processed_action),
            "保存当前系统输出内容": (file_menu, save_results_action),

            # 帮助菜单项
            "自定义快捷键": (help_menu, customize_shortcuts),
        }

        # 根据用户权限更新菜单项状态
        self.update_menu_permissions()

    def update_menu_permissions(self):
        """根据当前用户权限更新菜单项的可用性"""
        if not hasattr(self.app, 'current_user_role') or not self.app.current_user_role:
            # 如果没有用户角色信息，默认禁用所有菜单项
            for item_name, (menu, action) in self.menu_items.items():
                action.setEnabled(False)
            return

        # 根据权限启用/禁用菜单项
        for item_name, (menu, action) in self.menu_items.items():
            if item_name in self.menu_permissions:
                permission = self.menu_permissions[item_name]
                action.setEnabled(self.app.check_permission(permission))
            elif item_name in ["刷新界面", "清空图表", "清空输出"]:
                action.setEnabled(True)
            else:
                # 默认情况下禁用
                action.setEnabled(False)

    def load_user_avatar(self, username):
        """加载用户头像"""
        if not username:
            return None

        try:
            # 构建头像路径
            avatar_path = os.path.join(CONFIG["user_info"], username, "avatar.png")

            # 检查头像文件是否存在
            if os.path.exists(avatar_path):
                pixmap = QPixmap(avatar_path)
                if not pixmap.isNull():
                    # 缩放到合适的大小并保持圆形
                    scaled_pixmap = pixmap.scaled(26, 26, Qt.KeepAspectRatio, Qt.SmoothTransformation)

                    # 创建圆形遮罩
                    circular_pixmap = QPixmap(26, 26)
                    circular_pixmap.fill(Qt.transparent)

                    painter = QPainter(circular_pixmap)
                    painter.setRenderHint(QPainter.Antialiasing)

                    # 绘制圆形路径
                    path = QPainterPath()
                    path.addEllipse(0, 0, 26, 26)
                    painter.setClipPath(path)

                    # 居中绘制图片
                    x = (26 - scaled_pixmap.width()) / 2
                    y = (26 - scaled_pixmap.height()) / 2
                    painter.drawPixmap(x, y, scaled_pixmap)
                    painter.end()

                    return circular_pixmap
        except Exception as e:
            self.logger.error(f"加载用户头像失败: {str(e)}")

        return None

    def create_circular_avatar(self, text, size=26):
        """创建圆形头像"""
        pixmap = QPixmap(size, size)
        pixmap.fill(Qt.transparent)

        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 创建径向渐变
        gradient = QRadialGradient(size / 2, size / 2, size / 2)
        gradient.setColorAt(0, QColor("#5dade2"))
        gradient.setColorAt(0.8, QColor("#3498db"))
        gradient.setColorAt(1, QColor("#2980b9"))

        # 绘制圆形背景，留出1像素边距防止被切掉
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(1, 1, size - 2, size - 2)

        # 绘制文字
        painter.setPen(QColor("white"))
        font = QFont("Microsoft YaHei", 10, QFont.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignCenter, text)

        painter.end()
        return pixmap

    def create_avatar_toolbar(self):
        """创建用于显示用户头像的工具栏并放置在菜单栏右边"""
        self.avatar_toolbar = QToolBar("User Info")
        self.avatar_toolbar.setObjectName("userAvatarToolbar")
        self.avatar_toolbar.setMovable(False)  # 固定工具栏位置
        self.avatar_toolbar.setFloatable(False)  # 禁止浮动

        # 设置工具栏样式
        self.avatar_toolbar.setStyleSheet("""
            QToolBar {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #2c3e50, stop:1 #1a2530);
                border: none;
                spacing: 8px;
                padding: 2px 10px;
            }
            QLabel {
                color: #ecf0f1;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
                padding: 0 5px;
            }
        """)

        # 获取当前用户名
        current_username = getattr(self.app, 'current_username', None)

        # 创建头像标签
        self.avatar_label = QLabel()
        self.avatar_label.setObjectName("avatarLabel")
        self.avatar_label.setFixedSize(34, 34)

        # 设置头像标签为圆形
        self.avatar_label.setStyleSheet("""
            #avatarLabel {
                border-radius: 17px;
                background-color: transparent;
                border: none;
            }
            #avatarLabel:hover {
                background-color: rgba(52, 152, 219, 0.3);
            }
        """)

        # 尝试加载用户头像，如果没有则使用默认头像
        avatar_pixmap = self.load_user_avatar(current_username)
        if avatar_pixmap:
            # 如果有用户头像，直接使用
            self.avatar_label.setPixmap(avatar_pixmap)
        else:
            # 否则使用默认头像
            if current_username:
                avatar_text = current_username[0].upper()
            else:
                avatar_text = "访"  # 访客显示"访"字

            # 创建圆形头像
            avatar_pixmap = self.create_circular_avatar(avatar_text)
            self.avatar_label.setPixmap(avatar_pixmap)

        self.avatar_label.setAlignment(Qt.AlignCenter)

        # 创建悬停菜单
        self.avatar_menu = QMenu(self.avatar_label)
        self.avatar_menu.setStyleSheet("""
            QMenu {
                background-color: #2c3e50;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 8px;
                padding: 6px 0;
                box-shadow: 2px 2px 5px rgba(0, 0, 0, 0.3);
            }
            QMenu::item {
                padding: 10px 35px 10px 30px;
                font-family: "Microsoft YaHei";
                font-size: 11px;
                font-weight: normal;
            }
            QMenu::item:selected {
                background-color: #3498db;
                border-radius: 5px;
                margin: 0 5px;
                color: #ffffff;
            }
            QMenu::separator {
                height: 1px;
                background: #34495e;
                margin: 5px 10px;
            }
        """)

        # 添加菜单项
        edit_profile_action = QAction("编辑资料", self.avatar_menu)
        edit_profile_action.triggered.connect(self.app.show_user_profile)
        self.avatar_menu.addAction(edit_profile_action)

        upgrade_permission_action = QAction("权限提升", self.avatar_menu)
        upgrade_permission_action.triggered.connect(self.app.upgrade_permission)
        self.avatar_menu.addAction(upgrade_permission_action)

        self.avatar_menu.addSeparator()

        # 添加权限说明选项
        permission_info_action = QAction("权限说明", self.avatar_menu)
        permission_info_action.triggered.connect(self.show_permission_info)
        self.avatar_menu.addAction(permission_info_action)

        self.avatar_menu.addSeparator()

        logout_action = QAction("退出登录", self.avatar_menu)
        logout_action.triggered.connect(self.app.logout)
        self.avatar_menu.addAction(logout_action)

        # 连接点击事件
        self.avatar_label.mousePressEvent = self.show_avatar_menu

        # 创建一个容器widget来水平排列用户名和头像
        avatar_container = QWidget()
        avatar_container_layout = QHBoxLayout(avatar_container)
        avatar_container_layout.setContentsMargins(0, 0, 0, 0)
        avatar_container_layout.setSpacing(5)
        avatar_container_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # 添加用户名标签到容器
        if current_username:
            username_label = QLabel(current_username)
            username_label.setObjectName("usernameLabel")
            username_label.setStyleSheet("""
                QLabel {
                    color: #ecf0f1;
                    font-family: "Microsoft YaHei";
                    font-size: 12px;
                    font-weight: bold;
                    padding: 0 5px;
                    background: transparent;
                }
            """)

            # 设置固定最大宽度并启用省略号显示
            username_label.setMaximumWidth(500)
            username_label.setMinimumWidth(150)
            username_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

            # 启用省略号显示
            username_label.setTextFormat(Qt.PlainText)
            username_label.setWordWrap(False)

            # 根据文本长度决定对齐方式
            font_metrics = username_label.fontMetrics()
            text_width = font_metrics.horizontalAdvance(current_username)

            if text_width > 500:  # 如果文本过长，使用左对齐并显示省略号
                username_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                username_label.setToolTip(current_username)  # 添加完整用户名的提示
            else:  # 否则使用右对齐
                username_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            # 启用文本省略
            username_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

            avatar_container_layout.addWidget(username_label)

        # 添加头像标签到容器
        avatar_container_layout.addWidget(self.avatar_label)

        # 添加组件到工具栏
        self.avatar_toolbar.addWidget(avatar_container)

        # 将工具栏添加到菜单栏的右边
        self.menu_bar.setCornerWidget(self.avatar_toolbar, Qt.TopRightCorner)

    def show_avatar_menu(self, event):
        """显示头像菜单"""
        if event.button() == Qt.LeftButton:
            # 在头像标签下方显示菜单
            pos = self.avatar_label.mapToGlobal(self.avatar_label.rect().bottomLeft())
            self.avatar_menu.exec(pos)

    def show_permission_info(self):
        """显示权限说明窗口"""
        # 创建权限说明对话框
        permission_dialog = QDialog()
        permission_dialog.setWindowTitle("权限说明 - OptiSVR分光计折射率预测系统")
        permission_dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        permission_dialog.setMinimumSize(900, 600)
        permission_dialog.resize(900, 600)
        permission_dialog.setModal(True)

        # 设置窗口图标
        icon_path = os.path.join(CONFIG["img"], 'icon.ico')
        permission_dialog.setWindowIcon(QIcon(icon_path))

        # 创建标签页控件
        tab_widget = QTabWidget()
        tab_widget.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #3498db;
                border-radius: 5px;
                background-color: white;
            }
            QTabBar::tab {
                background: #ecf0f1;
                color: #2c3e50;
                padding: 10px 20px;
                margin: 2px;
                border: 1px solid #3498db;
                border-radius: 5px;
                font-family: "Microsoft YaHei";
                font-size: 12px;
                font-weight: bold;
            }
            QTabBar::tab:selected {
                background: #3498db;
                color: white;
                border-color: #2980b9;
            }
            QTabBar::tab:hover:!selected {
                background: #d6eaf8;
            }
        """)

        # 创建权限说明标签页
        permission_widget = QWidget()
        permission_layout = QVBoxLayout(permission_widget)
        permission_layout.setSpacing(15)
        permission_layout.setContentsMargins(20, 20, 20, 20)

        # 权限说明标题
        permission_title_label = QLabel("权限说明")
        permission_title_label.setAlignment(Qt.AlignCenter)
        permission_title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)
        permission_layout.addWidget(permission_title_label)

        # 创建权限表格
        permission_table = QTableWidget()
        permission_table.setColumnCount(5)
        permission_table.setRowCount(23)
        permission_table.setHorizontalHeaderLabels(["功能", "管理员", "高级用户", "基础用户", "访客"])
        permission_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        permission_table.setSelectionMode(QAbstractItemView.NoSelection)
        permission_table.setStyleSheet("""
            QTableWidget {
                font-family: "Microsoft YaHei";
                font-size: 11px;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                QAbstractItemView::item { padding: 5px; }
            }
            QTableWidget::item {
                padding: 5px;
                border: none;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border: 1px solid #2980b9;
            }
            QTableWidget::item {
                text-align: center;
            }
        """)

        # 设置表格内容
        permissions_data = [
            ("导入数据1(原始数据)", True, True, True, True),
            ("导入数据2(绘图到80度)", True, True, True, True),
            ("刷新界面/清空图表/清空输出", True, True, True, True),
            ("加载模型", True, True, True, True),
            ("预测折射率", True, True, True, True),
            ("查看可视化结果", True, True, True, True),
            ("查看预测历史", True, True, True, True),
            ("保存当前系统输出内容", True, True, True, True),
            ("生成理论数据", True, True, True, False),
            ("自定义生成理论数据", True, True, True, False),
            ("停止生成", True, True, True, False),
            ("训练模型", True, True, True, False),
            ("停止训练", True, True, True, False),
            ("导出模型", True, True, True, False),
            ("模型比较", True, True, True, False),
            ("批量预测", True, True, True, False),
            ("查看优化历史", True, True, True, False),
            ("数据增强", True, True, False, False),
            ("模型管理", True, True, False, False),
            ("自定义快捷键", True, True, False, False),
            ("系统监控", True, False, False, False),
            ("查看监控日志", True, False, False, False),
            ("用户管理", True, False, False, False),
        ]

        for row, (function, admin, advanced, basic, guest) in enumerate(permissions_data):
            permission_table.setItem(row, 0, QTableWidgetItem(function))
            permission_table.setItem(row, 1, QTableWidgetItem("✓" if admin else "✗"))
            permission_table.setItem(row, 2, QTableWidgetItem("✓" if advanced else "✗"))
            permission_table.setItem(row, 3, QTableWidgetItem("✓" if basic else "✗"))
            permission_table.setItem(row, 4, QTableWidgetItem("✓" if guest else "✗"))

        # 设置表格样式
        permission_table.verticalHeader().setVisible(False)
        permission_table.setAlternatingRowColors(True)
        permission_table.setStyleSheet(permission_table.styleSheet() + """
            QTableWidget {
                alternate-background-color: #f8f9fa;
                background-color: white;
            }
            QTableWidget::item {
                text-align: center;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)

        # 设置列宽相等
        permission_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 设置特定列的文本对齐方式和颜色
        for row in range(permission_table.rowCount()):
            for col in range(1, 5):  # 权限列
                item = permission_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
                    if item.text() == "✓":
                        item.setForeground(QColor("#27ae60"))  # 绿色
                        item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
                    else:
                        item.setForeground(QColor("#e74c3c"))  # 红色
                        item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))

        # 设置第一列（功能列）的文本对齐方式
        for row in range(permission_table.rowCount()):
            item = permission_table.item(row, 0)  # 功能列
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        permission_layout.addWidget(permission_table)

        # 添加权限说明标签页
        tab_widget.addTab(permission_widget, "权限说明")

        # 创建模型训练方式说明标签页
        training_widget = QWidget()
        training_layout = QVBoxLayout(training_widget)
        training_layout.setSpacing(15)
        training_layout.setContentsMargins(20, 20, 20, 20)

        # 模型训练方式说明标题
        training_methods_label = QLabel("模型训练方式说明")
        training_methods_label.setAlignment(Qt.AlignCenter)
        training_methods_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin: 10px 0;
            }
        """)
        training_layout.addWidget(training_methods_label)

        # 创建训练方式说明表格
        training_methods_table = QTableWidget()
        training_methods_table.setColumnCount(5)
        training_methods_table.setRowCount(6)
        training_methods_table.setHorizontalHeaderLabels(["训练方式", "管理员", "高级用户", "基础用户", "访客用户"])
        training_methods_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        training_methods_table.setSelectionMode(QAbstractItemView.NoSelection)
        training_methods_table.setStyleSheet("""
            QTableWidget {
                font-family: "Microsoft YaHei";
                font-size: 11px;
                gridline-color: #dee2e6;
                border: 1px solid #dee2e6;
                border-radius: 5px;
                margin-bottom: 20px;
                QAbstractItemView::item { padding: 5px; }
            }
            QTableWidget::item {
                padding: 5px;
                border: none;
            }
            QHeaderView::section {
                background-color: #9b59b6;
                color: white;
                font-weight: bold;
                font-size: 11px;
                padding: 8px;
                border: 1px solid #8e44ad;
            }
            QTableWidget::item {
                text-align: center;
            }
        """)

        # 设置训练方式表格内容
        training_methods_data = [
            ("K-Means聚类 + Optuna优化", True, True, True, False),
            ("SOM聚类 + Optuna优化", True, True, False, False),
            ("K-Means聚类 + 贝叶斯优化", True, True, False, False),
            ("SOM聚类 + 贝叶斯优化", True, True, False, False),
            ("K-Means聚类 + 混合优化", True, True, False, False),
            ("SOM聚类 + 混合优化", True, True, False, False),
        ]

        for row, (method, admin, advanced, basic, guest) in enumerate(training_methods_data):
            training_methods_table.setItem(row, 0, QTableWidgetItem(method))
            training_methods_table.setItem(row, 1, QTableWidgetItem("✓" if admin else "✗"))
            training_methods_table.setItem(row, 2, QTableWidgetItem("✓" if advanced else "✗"))
            training_methods_table.setItem(row, 3, QTableWidgetItem("✓" if basic else "✗"))
            training_methods_table.setItem(row, 4, QTableWidgetItem("✓" if guest else "✗"))

        # 设置训练方式表格样式
        training_methods_table.verticalHeader().setVisible(False)
        training_methods_table.setAlternatingRowColors(True)
        training_methods_table.setStyleSheet(training_methods_table.styleSheet() + """
            QTableWidget {
                alternate-background-color: #f8f9fa;
                background-color: white;
            }
            QTableWidget::item {
                text-align: center;
            }
            QTableWidget::item:selected {
                background-color: #9b59b6;
                color: white;
            }
        """)

        # 设置列宽
        training_methods_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)

        # 设置特定列的文本对齐方式和颜色
        for row in range(training_methods_table.rowCount()):
            for col in range(1, 5):  # 权限列
                item = training_methods_table.item(row, col)
                if item:
                    item.setTextAlignment(Qt.AlignCenter)
                    if item.text() == "✓":
                        item.setForeground(QColor("#27ae60"))  # 绿色
                        item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))
                    else:
                        item.setForeground(QColor("#e74c3c"))  # 红色
                        item.setFont(QFont("Microsoft YaHei", 12, QFont.Bold))

        # 设置第一列（功能列）的文本对齐方式
        for row in range(training_methods_table.rowCount()):
            item = training_methods_table.item(row, 0)  # 功能列
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        training_layout.addWidget(training_methods_table)

        # 添加模型训练方式说明标签页
        tab_widget.addTab(training_widget, "模型训练方式")

        # 创建主布局并添加标签页控件
        main_layout = QVBoxLayout(permission_dialog)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.addWidget(tab_widget)

        # 添加确定按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        ok_button = QPushButton("确定")
        ok_button.setObjectName("primary")
        ok_button.clicked.connect(permission_dialog.accept)
        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                font-size: 14px;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 20px;
                min-width: 80px;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)
        button_layout.addWidget(ok_button)

        main_layout.addLayout(button_layout)

        permission_dialog.exec()

    def update_user_avatar(self, new_username):
        """更新用户头像显示"""
        if self.avatar_label:
            # 尝试加载用户头像
            avatar_pixmap = self.load_user_avatar(new_username)

            if avatar_pixmap:
                # 如果有用户头像，直接使用
                self.avatar_label.setPixmap(avatar_pixmap)
            else:
                # 否则使用默认头像
                avatar_text = new_username[0].upper() if new_username else "访"

                # 创建新的圆形头像
                avatar_pixmap = self.create_circular_avatar(avatar_text)
                self.avatar_label.setPixmap(avatar_pixmap)

            # 更新或创建用户名标签
            if self.avatar_toolbar:
                username_label = None
                avatar_container = self.avatar_toolbar.widgetForAction(
                    self.avatar_toolbar.actions()[0]) if self.avatar_toolbar.actions() else None
                if avatar_container and avatar_container.layout():
                    for i in range(avatar_container.layout().count()):
                        item = avatar_container.layout().itemAt(i)
                        if item and item.widget() and isinstance(item.widget(),
                                                                 QLabel) and item.widget().objectName() == "usernameLabel":
                            username_label = item.widget()
                            break

                # 如果没有找到用户名标签但有新用户名，创建新标签
                if not username_label and new_username:
                    new_username_label = QLabel(new_username)
                    new_username_label.setObjectName("usernameLabel")
                    new_username_label.setStyleSheet("""
                        QLabel {
                            color: #ecf0f1;
                            font-family: "Microsoft YaHei";
                            font-size: 12px;
                            font-weight: bold;
                            padding: 0 5px;
                            background: transparent;
                        }
                    """)

                    # 设置固定最大宽度并启用省略号显示
                    new_username_label.setMaximumWidth(500)
                    new_username_label.setMinimumWidth(150)
                    new_username_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

                    # 启用省略号显示
                    new_username_label.setTextFormat(Qt.PlainText)
                    new_username_label.setWordWrap(False)

                    # 根据文本长度决定对齐方式
                    font_metrics = new_username_label.fontMetrics()
                    text_width = font_metrics.horizontalAdvance(new_username)

                    if text_width > 500:
                        new_username_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        new_username_label.setToolTip(new_username)
                    else:
                        new_username_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        new_username_label.setToolTip("")

                    # 启用文本省略
                    new_username_label.setTextInteractionFlags(Qt.TextSelectableByMouse)

                    # 添加到容器中
                    avatar_container = self.avatar_toolbar.widgetForAction(self.avatar_toolbar.actions()[0])
                    if avatar_container and avatar_container.layout():
                        avatar_container.layout().insertWidget(0, new_username_label)
                elif username_label and new_username:
                    font_metrics = username_label.fontMetrics()
                    text_width = font_metrics.horizontalAdvance(new_username)

                    # 如果文本过长，使用左对齐并显示省略号
                    if text_width > 500:
                        username_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        username_label.setToolTip(new_username)
                    else:
                        username_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter) # 使用右对齐
                        username_label.setToolTip("")

                    username_label.setText(new_username)
                # 如果是访客状态，移除标签
                elif username_label and not new_username:
                    username_label.setParent(None)
                    username_label.deleteLater()

    def enable_all_buttons_except_stop(self):
        """启用所有功能按钮和菜单项"""
        if not hasattr(self.app, 'current_user_role') or not self.app.current_user_role:
            # 如果没有用户角色信息，默认禁用所有菜单项
            for item_name, (menu, action) in self.menu_items.items():
                action.setEnabled(False)
            return

        # 根据权限启用/禁用菜单项
        for item_name, (menu, action) in self.menu_items.items():
            # 停止相关按钮特殊处理
            if item_name in ["停止训练", "停止生成"]:
                action.setEnabled(False)
            elif item_name in self.menu_permissions:
                permission = self.menu_permissions[item_name]
                action.setEnabled(self.app.check_permission(permission))
            elif item_name in ["刷新界面", "清空图表", "清空输出"]:
                action.setEnabled(True)
            else:
                action.setEnabled(False)

    def disable_all_buttons_except_stop(self):
        """禁用除停止训练按钮外的所有功能按钮和菜单项"""
        if not hasattr(self.app, 'current_user_role') or not self.app.current_user_role:
            # 如果没有用户角色信息，默认禁用所有菜单项
            for item_name, (menu, action) in self.menu_items.items():
                action.setEnabled(False)
            return

        # 根据权限启用/禁用菜单项
        for item_name, (menu, action) in self.menu_items.items():
            if item_name in ["停止训练", "停止生成"]:
                action.setEnabled(True)
            else:
                action.setEnabled(False)
