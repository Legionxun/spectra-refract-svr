# core/gui_components/shortcut_manager.py
import json, os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QFrame, QScrollArea, QWidget,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QMessageBox
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QColor, QShortcut, QKeySequence

from ..config import CONFIG, DEFAULT_SHORTCUTS


class ShortcutManager:
    """快捷键管理器"""
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.logger = self.app.logger
        self.shortcuts = {}
        self.custom_shortcuts = {}

        # 加载用户自定义快捷键
        self.load_custom_shortcuts()
        self.setup_shortcuts()

    def load_custom_shortcuts(self):
        """加载用户自定义快捷键"""
        try:
            shortcuts_file = os.path.join(CONFIG["settings_dir"], "shortcuts.json")
            if os.path.exists(shortcuts_file):
                with open(shortcuts_file, 'r', encoding='utf-8') as f:
                    self.custom_shortcuts = json.load(f)
            else:
                # 创建默认快捷键文件
                self.custom_shortcuts = DEFAULT_SHORTCUTS.copy()
                self.save_custom_shortcuts()
        except Exception as e:
            self.logger.error(f"加载自定义快捷键失败: {str(e)}")
            self.custom_shortcuts = DEFAULT_SHORTCUTS.copy()

    def save_custom_shortcuts(self):
        """保存用户自定义快捷键"""
        try:
            shortcuts_file = os.path.join(CONFIG["settings_dir"], "shortcuts.json")
            with open(shortcuts_file, 'w', encoding='utf-8') as f:
                json.dump(self.custom_shortcuts, f, ensure_ascii=False, indent=4)
            self.logger.info("自定义快捷键已保存")
        except Exception as e:
            self.logger.error(f"保存自定义快捷键失败: {str(e)}")

    def get_shortcut(self, action_name):
        """获取指定操作的快捷键"""
        return self.custom_shortcuts.get(action_name, "")

    def set_shortcut(self, action_name, shortcut):
        """设置指定操作的快捷键"""
        self.custom_shortcuts[action_name] = shortcut
        self.save_custom_shortcuts()

    def clear_shortcuts(self):
        """清除所有快捷键连接"""
        for shortcut in self.shortcuts.values():
            try:
                shortcut.activated.disconnect()
            except:
                pass  # 忽略断开连接时的错误
            shortcut.setEnabled(False)
            shortcut.deleteLater()
        self.shortcuts.clear()

    def setup_shortcuts(self):
        """设置应用程序的键盘快捷键"""
        # 清除现有的快捷键
        self.clear_shortcuts()

        # 创建快捷操作对象
        self.shortcuts["generate_theoretical_data"] = QShortcut(
            QKeySequence(self.get_shortcut("generate_theoretical_data")), self.main_window)
        self.shortcuts["generate_theoretical_data"].activated.connect(self.app.generate_theoretical_data)

        self.shortcuts["custom_generate_theoretical_data"] = QShortcut(
            QKeySequence(self.get_shortcut("custom_generate_theoretical_data")), self.main_window)
        self.shortcuts["custom_generate_theoretical_data"].activated.connect(self.app.custom_generate_theoretical_data)

        self.shortcuts["stop_generation"] = QShortcut(QKeySequence(self.get_shortcut("stop_generation")),
                                                      self.main_window)
        self.shortcuts["stop_generation"].activated.connect(self.app.stop_generation)

        self.shortcuts["data_augmentation"] = QShortcut(QKeySequence(self.get_shortcut("data_augmentation")),
                                                        self.main_window)
        self.shortcuts["data_augmentation"].activated.connect(self.app.data_augmentation)

        self.shortcuts["save_results"] = QShortcut(QKeySequence(self.get_shortcut("save_results")), self.main_window)
        self.shortcuts["save_results"].activated.connect(self.app.save_current_results)

        self.shortcuts["predict_refractive_index"] = QShortcut(
            QKeySequence(self.get_shortcut("predict_refractive_index")), self.main_window)
        self.shortcuts["predict_refractive_index"].activated.connect(self.app.predict_refractive_index)

        self.shortcuts["batch_prediction"] = QShortcut(QKeySequence(self.get_shortcut("batch_prediction")),
                                                       self.main_window)
        self.shortcuts["batch_prediction"].activated.connect(self.app.batch_prediction)

        self.shortcuts["show_optimization_history"] = QShortcut(
            QKeySequence(self.get_shortcut("show_optimization_history")), self.main_window)
        self.shortcuts["show_optimization_history"].activated.connect(self.app.show_optimization_history)

        self.shortcuts["show_prediction_history"] = QShortcut(
            QKeySequence(self.get_shortcut("show_prediction_history")), self.main_window)
        self.shortcuts["show_prediction_history"].activated.connect(self.app.show_prediction_history)

        self.shortcuts["start_training"] = QShortcut(QKeySequence(self.get_shortcut("start_training")),
                                                     self.main_window)
        self.shortcuts["start_training"].activated.connect(self.app.start_training)

        self.shortcuts["stop_training"] = QShortcut(QKeySequence(self.get_shortcut("stop_training")), self.main_window)
        self.shortcuts["stop_training"].activated.connect(self.app.stop_training)

        self.shortcuts["compare_models"] = QShortcut(QKeySequence(self.get_shortcut("compare_models")),
                                                     self.main_window)
        self.shortcuts["compare_models"].activated.connect(self.app.compare_models)

        self.shortcuts["load_model"] = QShortcut(QKeySequence(self.get_shortcut("load_model")), self.main_window)
        self.shortcuts["load_model"].activated.connect(self.app.load_model)

        self.shortcuts["export_model"] = QShortcut(QKeySequence(self.get_shortcut("export_model")), self.main_window)
        self.shortcuts["export_model"].activated.connect(self.app.export_model)

        self.shortcuts["manage_models"] = QShortcut(QKeySequence(self.get_shortcut("manage_models")), self.main_window)
        self.shortcuts["manage_models"].activated.connect(self.app.manage_models)

        self.shortcuts["system_monitor"] = QShortcut(QKeySequence(self.get_shortcut("system_monitor")),
                                                     self.main_window)
        self.shortcuts["system_monitor"].activated.connect(self.app.toggle_system_monitor)

        self.shortcuts["show_monitoring_logs"] = QShortcut(QKeySequence(self.get_shortcut("show_monitoring_logs")),
                                                           self.main_window)
        self.shortcuts["show_monitoring_logs"].activated.connect(self.app.show_monitoring_logs)

        self.shortcuts["init_result_frame"] = QShortcut(QKeySequence(self.get_shortcut("clear_chart")),
                                                        self.main_window)
        self.shortcuts["init_result_frame"].activated.connect(self.app.init_result_frame)

        self.shortcuts["clear_output"] = QShortcut(QKeySequence(self.get_shortcut("clear_output")), self.main_window)
        self.shortcuts["clear_output"].activated.connect(self.app.clear_output)

        self.shortcuts["refresh_page"] = QShortcut(QKeySequence(self.get_shortcut("refresh_page")), self.main_window)
        self.shortcuts["refresh_page"].activated.connect(self.app.refresh_page)

        self.shortcuts["user_management"] = QShortcut(QKeySequence(self.get_shortcut("user_management")), self.main_window)
        self.shortcuts["user_management"].activated.connect(self.app.open_user_management)

        self.shortcuts["toggle_theme"] = QShortcut(QKeySequence(self.get_shortcut("toggle_theme")), self.main_window)
        self.shortcuts["toggle_theme"].activated.connect(self.app.toggle_theme)

        self.shortcuts["show_usage_guide"] = QShortcut(QKeySequence(self.get_shortcut("show_usage_guide")),
                                                       self.main_window)
        self.shortcuts["show_usage_guide"].activated.connect(self.app.show_usage_guide)

        self.shortcuts["show_shortcuts_dialog"] = QShortcut(QKeySequence(self.get_shortcut("show_shortcuts_dialog")),
                                                            self.main_window)
        self.shortcuts["show_shortcuts_dialog"].activated.connect(self.app.show_shortcuts_dialog)

        self.shortcuts["customize_shortcuts"] = QShortcut(QKeySequence(self.get_shortcut("customize_shortcuts")),
                                                          self.main_window)
        self.shortcuts["customize_shortcuts"].activated.connect(self.app.show_customize_shortcuts_dialog)

        self.shortcuts["check_for_updates"] = QShortcut(QKeySequence(self.get_shortcut("check_for_updates")),
                                                          self.main_window)
        self.shortcuts["check_for_updates"].activated.connect(self.app.check_for_updates)

        self.shortcuts["show_about"] = QShortcut(QKeySequence(self.get_shortcut("show_about")), self.main_window)
        self.shortcuts["show_about"].activated.connect(self.app.show_about)

        self.shortcuts["close_app"] = QShortcut(QKeySequence(self.get_shortcut("exit_app")), self.main_window)
        self.shortcuts["close_app"].activated.connect(self.app.close)

    def show_customize_shortcuts_dialog(self):
        """显示自定义快捷键对话框"""
        self.logger.info("用户请求自定义快捷键")

        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("自定义快捷键")
        dialog.resize(800, 600)
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
        title_label = QLabel("自定义快捷键")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #212529; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # 创建说明标签
        info_label = QLabel("点击快捷键列中的单元格来修改快捷键，按Delete键清除快捷键")
        info_label.setFont(QFont("Microsoft YaHei", 10))
        info_label.setStyleSheet("color: #6c757d; margin-bottom: 10px;")
        layout.addWidget(info_label)

        # 创建表格
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(3)
        self.shortcuts_table.setHorizontalHeaderLabels(["功能", "当前快捷键", "默认快捷键"])
        self.shortcuts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.shortcuts_table.setSelectionMode(QTableWidget.SingleSelection)
        self.shortcuts_table.setSelectionBehavior(QTableWidget.SelectRows)

        # 设置表格样式
        self.shortcuts_table.setStyleSheet("""
            QTableWidget {
                background-color: white;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                gridline-color: #dee2e6;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #dee2e6;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
            QHeaderView::section {
                background-color: #3498db;
                color: white;
                padding: 10px;
                border: none;
                font-weight: bold;
            }
        """)

        # 设置列宽
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.shortcuts_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)

        # 隐藏网格线
        self.shortcuts_table.setShowGrid(False)

        # 填充表格数据
        self.populate_shortcuts_table()

        layout.addWidget(self.shortcuts_table)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # 恢复默认按钮
        restore_defaults_btn = QPushButton("恢复默认")
        restore_defaults_btn.setObjectName("warning")
        restore_defaults_btn.clicked.connect(self.restore_default_shortcuts)
        button_layout.addWidget(restore_defaults_btn)

        button_layout.addStretch()

        # 确定按钮
        ok_btn = QPushButton("确定")
        ok_btn.setObjectName("primary")
        ok_btn.clicked.connect(lambda: self.save_custom_shortcuts_from_dialog(dialog))
        button_layout.addWidget(ok_btn)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.setObjectName("danger")
        cancel_btn.clicked.connect(dialog.close)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # 连接表格的点击事件
        self.shortcuts_table.cellClicked.connect(self.on_shortcut_cell_clicked)

        dialog.exec()

    def populate_shortcuts_table(self):
        """填充快捷键表格数据"""
        # 清空现有数据
        self.shortcuts_table.setRowCount(0)

        # 快捷键分类和对应的功能
        shortcut_categories = {
            "数据处理": [
                ("生成理论数据", "generate_theoretical_data"),
                ("自定义生成理论数据", "custom_generate_theoretical_data"),
                ("停止生成", "stop_generation"),
                ("数据增强", "data_augmentation")
            ],
            "文件操作": [
                ("导入数据1(原始数据)", "import_original"),
                ("导入数据2(绘图到80度)", "import_processed"),
                ("保存当前系统输出内容", "save_results"),
                ("退出", "exit_app")
            ],
            "模型操作": [
                ("训练模型", "start_training"),
                ("停止训练", "stop_training"),
                ("加载模型", "load_model"),
                ("导出模型", "export_model"),
                ("模型管理", "manage_models")
            ],
            "预测分析": [
                ("预测折射率", "predict_refractive_index"),
                ("批量预测", "batch_prediction")
            ],
            "查看分析": [
                ("查看优化历史", "show_optimization_history"),
                ("查看可视化结果", "show_visualizations"),
                ("模型比较", "compare_models")
            ],
            "历史记录": [
                ("查看预测历史", "show_prediction_history"),
                ("查看监控日志", "show_monitoring_logs")
            ],
            "系统工具": [
                ("系统监控", "system_monitor"),
                ("刷新界面", "refresh_page"),
                ("清空图表", "clear_chart"),
                ("清空输出", "clear_output"),
                ("用户管理", "user_management"),
            ],
            "帮助": [
                ("切换主题", "toggle_theme"),
                ("使用指南", "show_usage_guide"),
                ("快捷键列表", "show_shortcuts_dialog"),
                ("自定义快捷键", "customize_shortcuts"),
                ("检查更新", "check_for_updates"),
                ("关于", "show_about")
            ]
        }

        row = 0
        for category, shortcuts in shortcut_categories.items():
            # 为每个分类添加标题行
            self.shortcuts_table.insertRow(row)
            category_item = QTableWidgetItem(category)
            category_item.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
            category_item.setFlags(Qt.ItemIsEnabled)  # 不可选择
            self.shortcuts_table.setItem(row, 0, category_item)
            self.shortcuts_table.setSpan(row, 0, 1, 3)  # 合并三列
            category_item.setBackground(QColor(200, 200, 200))
            row += 1

            # 添加该分类下的快捷键
            for display_name, action_name in shortcuts:
                self.shortcuts_table.insertRow(row)

                # 功能名称
                name_item = QTableWidgetItem(display_name)
                name_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                self.shortcuts_table.setItem(row, 0, name_item)

                # 当前快捷键
                current_shortcut = self.custom_shortcuts.get(action_name, "")
                current_item = QTableWidgetItem(current_shortcut)
                current_item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                current_item.setData(Qt.UserRole, action_name)  # 存储动作名称
                self.shortcuts_table.setItem(row, 1, current_item)

                # 默认快捷键
                default_shortcut = DEFAULT_SHORTCUTS.get(action_name, "")
                default_item = QTableWidgetItem(default_shortcut)
                default_item.setFlags(Qt.ItemIsEnabled)
                self.shortcuts_table.setItem(row, 2, default_item)

                row += 1

    def on_shortcut_cell_clicked(self, row, column):
        """处理快捷键单元格点击事件"""
        # 只处理快捷键列（第2列）的点击
        if column != 1:
            return

        item = self.shortcuts_table.item(row, column)
        if not item or not item.data(Qt.UserRole):
            return

        # 显示快捷键设置对话框
        action_name = item.data(Qt.UserRole)
        current_shortcut = item.text()

        shortcut_dialog = QDialog(self.main_window)
        shortcut_dialog.setWindowTitle("设置快捷键")
        shortcut_dialog.setFixedSize(300, 150)
        shortcut_dialog.setModal(True)

        layout = QVBoxLayout(shortcut_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 说明标签
        label = QLabel(f"请按下要设置的快捷键组合\n当前: {current_shortcut if current_shortcut else '无'}")
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 清除按钮
        clear_btn = QPushButton("清除")
        clear_btn.setObjectName("danger")
        clear_btn.clicked.connect(lambda: self.clear_shortcut(row, shortcut_dialog))
        button_layout.addWidget(clear_btn)

        # 取消按钮
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(shortcut_dialog.close)
        button_layout.addWidget(cancel_btn)

        layout.addLayout(button_layout)

        # 设置按键事件处理器
        shortcut_dialog.key_pressed = lambda event: self.handle_key_press(event, row, shortcut_dialog)
        shortcut_dialog.keyPressEvent = shortcut_dialog.key_pressed

        shortcut_dialog.exec()

    def handle_key_press(self, event, row, dialog):
        """处理按键事件以设置快捷键"""
        # 检查是否按下了Delete或Backspace键来清除快捷键
        if event.key() in (Qt.Key_Delete, Qt.Key_Backspace):
            # 清除快捷键
            item = self.shortcuts_table.item(row, 1)
            if item:
                item.setText("")
            dialog.close()
            event.accept()
            return

        # 获取按键组合
        key = event.key()
        modifiers = event.modifiers()

        # 忽略单独的功能键（如Shift、Ctrl、Alt）
        if key in (Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_Meta):
            return

        # 构建快捷键字符串
        key_sequence_parts = []

        # 添加修饰键
        if modifiers & Qt.ControlModifier:
            key_sequence_parts.append("Ctrl")
        if modifiers & Qt.AltModifier:
            key_sequence_parts.append("Alt")
        if modifiers & Qt.ShiftModifier:
            key_sequence_parts.append("Shift")
        if modifiers & Qt.MetaModifier:
            key_sequence_parts.append("Meta")

        # 添加主键
        key_enum = Qt.Key(key)
        key_string = QKeySequence(key_enum).toString()

        # 过滤掉单独的修饰键名称
        if key_string and not key_string.startswith("Ctrl+") and not key_string.startswith(
                "Alt+") and not key_string.startswith("Shift+") and not key_string.startswith("Meta+"):
            key_sequence_parts.append(key_string)

        # 组合快捷键
        if key_sequence_parts:
            shortcut_text = "+".join(key_sequence_parts)
        else:
            shortcut_text = ""

        # 检查快捷键是否有效
        if not shortcut_text:
            return

        # 更新表格中的快捷键显示
        item = self.shortcuts_table.item(row, 1)
        if item:
            item.setText(shortcut_text)

        dialog.close()
        event.accept()

    def clear_shortcut(self, row, dialog):
        """清除指定行的快捷键"""
        item = self.shortcuts_table.item(row, 1)
        if item:
            item.setText("")
        dialog.close()

    def save_custom_shortcuts_from_dialog(self, dialog):
        """从对话框保存自定义快捷键"""
        # 更新自定义快捷键字典
        for row in range(self.shortcuts_table.rowCount()):
            action_item = self.shortcuts_table.item(row, 1)
            if action_item and action_item.data(Qt.UserRole):
                action_name = action_item.data(Qt.UserRole)
                shortcut = action_item.text()
                self.custom_shortcuts[action_name] = shortcut

        # 保存到文件
        self.save_custom_shortcuts()

        # 重新设置快捷键
        self.setup_shortcuts()

        dialog.close()

        # 显示成功消息
        QMessageBox.information(self.main_window, "成功", "快捷键设置已保存并应用")

    def restore_default_shortcuts(self):
        """恢复默认快捷键"""
        self.custom_shortcuts = DEFAULT_SHORTCUTS.copy()
        self.populate_shortcuts_table()
        QMessageBox.information(self.main_window, "成功", "已恢复默认快捷键设置")

    def show_shortcuts_dialog(self):
        """显示快捷键列表对话框"""
        self.logger.info("用户请求查看快捷键列表")
        shortcuts_dialog = QDialog(self.main_window)
        shortcuts_dialog.setWindowTitle("快捷键列表")
        shortcuts_dialog.resize(600, 500)
        shortcuts_dialog.setModal(True)
        shortcuts_dialog.setStyleSheet("""
            QDialog {
                background-color: #f8f9fa;
            }
        """)

        layout = QVBoxLayout(shortcuts_dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("快捷键列表")
        title_label.setFont(QFont("Microsoft YaHei", 18, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("color: #212529;")
        layout.addWidget(title_label)

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("background-color: #dee2e6; height: 1px;")
        layout.addWidget(separator)

        # 创建滚动区域和容器
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_area.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                border: none;
                background: #e9ecef;
                width: 12px;
                border-radius: 4px;
                margin: 0px 0px 0px 0px;
            }
            QScrollBar::handle:vertical {
                background: #adb5bd;
                border-radius: 4px;
                min-height: 20px;
            }
            QScrollBar::handle:vertical:hover {
                background: #6c757d;
            }
        """)

        # 创建滚动区域的内容容器
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        scroll_layout.setContentsMargins(10, 10, 10, 10)

        # 快捷键列表
        shortcuts_text = QLabel("""
        <p><b>文件操作:</b></p>
        <ul>
        <li>导入数据1(原始数据) - {}</li>
        <li>导入数据2(绘图到80度) - {}</li>
        <li>保存当前系统输出内容 - {}</li>
        <li>退出 - {}</li>
        </ul>

        <p><b>数据处理:</b></p>
        <ul>
        <li>生成理论数据 - {}</li>
        <li>自定义生成理论数据 - {}</li>
        <li>停止生成 - {}</li>
        <li>数据增强 - {}</li>
        </ul>

        <p><b>模型操作:</b></p>
        <ul>
        <li>训练模型 - {}</li>
        <li>停止训练 - {}</li>
        <li>加载模型 - {}</li>
        <li>导出模型 - {}</li>
        <li>模型管理 - {}</li>
        </ul>

        <p><b>预测分析:</b></p>
        <ul>
        <li>预测折射率 - {}</li>
        <li>批量预测 - {}</li>
        </ul>

        <p><b>查看分析:</b></p>
        <ul>
        <li>查看优化历史 - {}</li>
        <li>查看可视化结果 - {}</li>
        <li>模型比较 - {}</li>
        </ul>

        <p><b>历史记录:</b></p>
        <ul>
        <li>查看预测历史 - {}</li>
        <li>查看监控日志 - {}</li>
        </ul>

        <p><b>系统工具:</b></p>
        <ul>
        <li>系统监控 - {}</li>
        <li>刷新界面 - {}</li>
        <li>清空图表 - {}</li>
        <li>清空输出 - {}</li>
        <li>用户管理 - {}</li>
        </ul>

        <p><b>帮助:</b></p>
        <ul>
        <li>切换主题 - {}</li>
        <li>使用指南 - {}</li>
        <li>快捷键列表 - {}</li>
        <li>自定义快捷键 - {}</li>
        <li>检查更新 - {}</li>
        <li>关于 - {}</li>
        </ul>
        """.format(
            self.get_shortcut("import_original"),
            self.get_shortcut("import_processed"),
            self.get_shortcut("save_results"),
            self.get_shortcut("exit_app"),

            self.get_shortcut("generate_theoretical_data"),
            self.get_shortcut("custom_generate_theoretical_data"),
            self.get_shortcut("stop_generation"),
            self.get_shortcut("data_augmentation"),

            self.get_shortcut("start_training"),
            self.get_shortcut("stop_training"),
            self.get_shortcut("load_model"),
            self.get_shortcut("export_model"),
            self.get_shortcut("manage_models"),

            self.get_shortcut("predict_refractive_index"),
            self.get_shortcut("batch_prediction"),

            self.get_shortcut("show_optimization_history"),
            self.get_shortcut("show_visualizations"),
            self.get_shortcut("compare_models"),

            self.get_shortcut("show_prediction_history"),
            self.get_shortcut("show_monitoring_logs"),

            self.get_shortcut("system_monitor"),
            self.get_shortcut("refresh_page"),
            self.get_shortcut("clear_chart"),
            self.get_shortcut("clear_output"),
            self.get_shortcut("user_management"),

            self.get_shortcut("toggle_theme"),
            self.get_shortcut("show_usage_guide"),
            self.get_shortcut("show_shortcuts_dialog"),
            self.get_shortcut("customize_shortcuts"),
            self.get_shortcut("check_for_updates"),
            self.get_shortcut("show_about")
        ))

        shortcuts_text.setFont(QFont("Microsoft YaHei", 10))
        shortcuts_text.setWordWrap(True)
        shortcuts_text.setAlignment(Qt.AlignTop)
        scroll_layout.addWidget(shortcuts_text)

        # 添加弹性空间
        scroll_layout.addStretch()

        # 将内容容器设置为滚动区域的widget
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 自定义快捷键按钮
        customize_btn = QPushButton("自定义快捷键")
        customize_btn.setObjectName("warning")
        customize_btn.clicked.connect(lambda: [shortcuts_dialog.close(), self.show_customize_shortcuts_dialog()])
        button_layout.addWidget(customize_btn)

        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.setObjectName("primary")
        ok_button.clicked.connect(shortcuts_dialog.accept)
        button_layout.addWidget(ok_button)
        layout.addLayout(button_layout)

        shortcuts_dialog.exec()
