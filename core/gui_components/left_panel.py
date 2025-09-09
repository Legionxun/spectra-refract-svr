# core/gui_components/left_panel.py
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QGroupBox, QFrame)
from PySide6.QtGui import QFont
import logging


class LeftPanelBuilder:
    """左侧面板构建器"""
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.logger = logging.getLogger("LeftPanelBuilder")

    def create(self):
        # 创建主窗口部件
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 10, 0)

        # 创建分组框
        left_group_box = QGroupBox("系统功能")
        left_group_box.setFont(QFont("Microsoft YaHei", 9))
        group_layout = QVBoxLayout(left_group_box)
        group_layout.setSpacing(5)

        # 创建按钮区域
        button_frame = QWidget()
        button_layout = QVBoxLayout(button_frame)
        button_layout.setSpacing(2)

        # ===== 按钮样式模板 =====
        # 定义样式模板函数
        def button_style(base_color, hover_color, pressed_color, border_color=None):
            if border_color is None:
                border_color = base_color
            return f"""
                QPushButton {{
                    background-color: {base_color};
                    color: white;
                    font-family: 'Microsoft YaHei';
                    font-weight: bold;
                    font-size: 12px;
                    border: 2px solid {border_color};
                    border-radius: 6px;
                    padding: 4px 12px;
                    min-height: 28px;
                    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
                }}
                QPushButton:hover {{
                    background-color: {hover_color};
                    border: 2px solid {hover_color};
                    box-shadow: 0 2px 5px rgba(0, 0, 0, 0.3);
                }}
                QPushButton:pressed {{
                    background-color: {pressed_color};
                    border: 2px solid {pressed_color};
                    box-shadow: inset 0 1px 2px rgba(0, 0, 0, 0.3);
                    padding: 5px 11px 3px 13px;  /* 模拟按压效果 */
                }}
                QPushButton:disabled {{
                    background-color: #bdc3c7;
                    border: 2px solid #95a5a6;
                    color: #ecf0f1;
                    box-shadow: none;
                }}
            """

        # ===== 数据处理组 =====
        data_group_label = QLabel("数据处理")
        data_group_font = QFont("Microsoft YaHei", 10, QFont.Bold)
        data_group_label.setFont(data_group_font)
        data_group_label.setStyleSheet("color: #2c3e50; margin-top: 6px; margin-bottom: 3px;")
        button_layout.addWidget(data_group_label)

        # 第一行按钮
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)

        self.gen_data_btn = QPushButton("生成理论数据")
        self.gen_data_btn.setStyleSheet(button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.gen_data_btn.clicked.connect(self.app.generate_theoretical_data)
        row1_layout.addWidget(self.gen_data_btn)

        self.custom_gen_data_btn = QPushButton("自定义生成理论数据")
        self.custom_gen_data_btn.setStyleSheet(button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.custom_gen_data_btn.clicked.connect(self.app.custom_generate_theoretical_data)
        row1_layout.addWidget(self.custom_gen_data_btn)
        button_layout.addLayout(row1_layout)

        # 第二行按钮
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)
        self.data_aug_btn = QPushButton("数据增强")
        self.data_aug_btn.setStyleSheet(button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.data_aug_btn.clicked.connect(self.app.data_augmentation)
        row2_layout.addWidget(self.data_aug_btn)

        self.stop_generation_btn = QPushButton("停止生成")
        self.stop_generation_btn.setStyleSheet(button_style("#e74c3c", "#ff6b6b", "#c0392b"))
        self.stop_generation_btn.clicked.connect(self.app.stop_generation)
        self.stop_generation_btn.setEnabled(False)
        row2_layout.addWidget(self.stop_generation_btn)
        button_layout.addLayout(row2_layout)

        # 第三行按钮
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(4)
        self.import_original_btn = QPushButton("导入数据1(原始数据)")
        self.import_original_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.import_original_btn.clicked.connect(self.app.import_data_original)
        row3_layout.addWidget(self.import_original_btn)

        self.import_processed_btn = QPushButton("导入数据2(绘图到80度)")
        self.import_processed_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.import_processed_btn.clicked.connect(self.app.import_data_processed)
        row3_layout.addWidget(self.import_processed_btn)
        button_layout.addLayout(row3_layout)

        # ===== 模型操作组 =====
        model_group_label = QLabel("模型操作")
        model_group_label.setFont(data_group_font)
        model_group_label.setStyleSheet("color: #2c3e50; margin-top: 8px; margin-bottom: 3px;")
        button_layout.addWidget(model_group_label)

        # 第四行按钮
        row4_layout = QHBoxLayout()
        row4_layout.setSpacing(4)
        self.train_btn = QPushButton("训练模型")
        self.train_btn.setStyleSheet(button_style("#f39c12", "#f5b041", "#d35400"))
        self.train_btn.clicked.connect(self.app.start_training)
        row4_layout.addWidget(self.train_btn)

        self.stop_train_btn = QPushButton("停止训练")
        self.stop_train_btn.setStyleSheet(button_style("#e74c3c", "#ff6b6b", "#c0392b"))
        self.stop_train_btn.clicked.connect(self.app.stop_training)
        self.stop_train_btn.setEnabled(False)
        row4_layout.addWidget(self.stop_train_btn)
        button_layout.addLayout(row4_layout)

        # 第五行按钮
        row5_layout = QHBoxLayout()
        row5_layout.setSpacing(4)
        self.load_btn = QPushButton("加载模型")
        self.load_btn.setStyleSheet(button_style("#9b59b6", "#af7ac5", "#76448a"))
        self.load_btn.clicked.connect(self.app.load_model)
        row5_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("导出模型")
        self.export_btn.setStyleSheet(button_style("#9b59b6", "#af7ac5", "#76448a"))
        self.export_btn.clicked.connect(self.app.export_model)
        row5_layout.addWidget(self.export_btn)
        button_layout.addLayout(row5_layout)

        # ===== 预测分析组 =====
        predict_group_label = QLabel("预测分析")
        predict_group_label.setFont(data_group_font)
        predict_group_label.setStyleSheet("color: #2c3e50; margin-top: 8px; margin-bottom: 3px;")
        button_layout.addWidget(predict_group_label)

        # 第六行按钮
        row6_layout = QHBoxLayout()
        row6_layout.setSpacing(4)
        self.predict_btn = QPushButton("预测折射率")
        self.predict_btn.setStyleSheet(button_style("#1abc9c", "#48c9b0", "#148f77"))
        self.predict_btn.clicked.connect(self.app.predict_refractive_index)
        row6_layout.addWidget(self.predict_btn)

        self.batch_pred_btn = QPushButton("批量预测")
        self.batch_pred_btn.setStyleSheet(button_style("#1abc9c", "#48c9b0", "#148f77"))
        self.batch_pred_btn.clicked.connect(self.app.batch_prediction)
        row6_layout.addWidget(self.batch_pred_btn)
        button_layout.addLayout(row6_layout)

        # ===== 查看分析组 =====
        view_group_label = QLabel("查看分析")
        view_group_label.setFont(data_group_font)
        view_group_label.setStyleSheet("color: #2c3e50; margin-top: 8px; margin-bottom: 3px;")
        button_layout.addWidget(view_group_label)

        # 第七行按钮
        row7_layout = QHBoxLayout()
        row7_layout.setSpacing(4)
        self.history_btn = QPushButton("预测历史")
        self.history_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.history_btn.clicked.connect(self.app.show_prediction_history)
        row7_layout.addWidget(self.history_btn)

        self.vis_btn = QPushButton("查看可视化结果")
        self.vis_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.vis_btn.clicked.connect(self.app.show_visualizations)
        row7_layout.addWidget(self.vis_btn)
        button_layout.addLayout(row7_layout)

        # 第八行按钮
        row8_layout = QHBoxLayout()
        row8_layout.setSpacing(4)
        self.opt_history_btn = QPushButton("查看优化历史")
        self.opt_history_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.opt_history_btn.clicked.connect(self.app.show_optimization_history)
        row8_layout.addWidget(self.opt_history_btn)

        self.compare_btn = QPushButton("模型比较")
        self.compare_btn.setStyleSheet(button_style("#3498db", "#5dade2", "#21618c"))
        self.compare_btn.clicked.connect(self.app.compare_models)
        row8_layout.addWidget(self.compare_btn)
        button_layout.addLayout(row8_layout)

        # ===== 系统工具组 =====
        tools_group_label = QLabel("系统工具")
        tools_group_label.setFont(data_group_font)
        tools_group_label.setStyleSheet("color: #2c3e50; margin-top: 8px; margin-bottom: 3px;")
        button_layout.addWidget(tools_group_label)

        # 第九行按钮
        row9_layout = QHBoxLayout()
        row9_layout.setSpacing(4)
        self.monitor_btn = QPushButton("系统监控")
        self.monitor_btn.setStyleSheet(button_style("#e67e22", "#f5b041", "#d35400"))
        self.monitor_btn.clicked.connect(self.app.toggle_system_monitor)
        row9_layout.addWidget(self.monitor_btn)

        self.refresh_btn = QPushButton("刷新页面")
        self.refresh_btn.setStyleSheet(button_style("#e67e22", "#f5b041", "#d35400"))
        self.refresh_btn.clicked.connect(self.app.refresh_page)
        row9_layout.addWidget(self.refresh_btn)
        button_layout.addLayout(row9_layout)

        # 第十行按钮
        row10_layout = QHBoxLayout()
        row10_layout.setSpacing(4)
        self.clear_output_btn = QPushButton("清空输出")
        self.clear_output_btn.setStyleSheet(button_style("#95a5a6", "#bdc3c7", "#7f8c8d"))
        self.clear_output_btn.clicked.connect(self.app.clear_output)
        row10_layout.addWidget(self.clear_output_btn)

        self.clear_plot_btn = QPushButton("清空图表")
        self.clear_plot_btn.setStyleSheet(button_style("#95a5a6", "#bdc3c7", "#7f8c8d"))
        self.clear_plot_btn.clicked.connect(self.app.init_result_frame)
        row10_layout.addWidget(self.clear_plot_btn)
        button_layout.addLayout(row10_layout)

        # 添加按钮区域到分组框
        group_layout.addWidget(button_frame)

        # 状态指示器区域
        status_container = QFrame()
        status_layout = QVBoxLayout(status_container)
        status_layout.setSpacing(3)

        # 状态指示器行布局
        status_row_layout = QHBoxLayout()
        status_row_layout.setSpacing(5)

        # 模型状态
        model_status_frame = QFrame()
        model_status_layout = QHBoxLayout(model_status_frame)
        model_status_layout.setContentsMargins(0, 0, 0, 0)

        model_status_label = QLabel("模型状态:")
        model_status_font = QFont("Microsoft YaHei", 9, QFont.Bold)
        model_status_label.setFont(model_status_font)

        self.status_var = QLabel("未加载")
        self.status_var.setFont(QFont("Microsoft YaHei", 9, QFont.Bold))
        self.status_var.setStyleSheet("color: red;")

        model_status_layout.addWidget(model_status_label)
        model_status_layout.addWidget(self.status_var)
        model_status_layout.addStretch()

        # 模型目录显示
        model_dir_frame = QFrame()
        model_dir_layout = QHBoxLayout(model_dir_frame)
        model_dir_layout.setContentsMargins(0, 0, 0, 0)

        model_dir_label = QLabel("当前模型:")
        model_dir_label.setFont(model_status_font)

        self.model_dir_var = QLabel("无")
        self.model_dir_var.setFont(QFont("Microsoft YaHei", 9))
        self.model_dir_var.setStyleSheet("color: #3498db;")

        model_dir_layout.addWidget(model_dir_label)
        model_dir_layout.addWidget(self.model_dir_var)
        model_dir_layout.addStretch()

        status_row_layout.addWidget(model_status_frame)
        status_row_layout.addWidget(model_dir_frame)
        status_layout.addLayout(status_row_layout)

        # 第二行状态指示器
        status_row2_layout = QHBoxLayout()
        status_row2_layout.setSpacing(5)

        # 数据状态显示
        data_status_frame = QFrame()
        data_status_layout = QHBoxLayout(data_status_frame)
        data_status_layout.setContentsMargins(0, 0, 0, 0)

        data_status_label = QLabel("数据状态:")
        data_status_label.setFont(model_status_font)

        self.data_status_var = QLabel("未加载")
        self.data_status_var.setFont(QFont("Microsoft YaHei", 9))
        self.data_status_var.setStyleSheet("color: red;")

        data_status_layout.addWidget(data_status_label)
        data_status_layout.addWidget(self.data_status_var)
        data_status_layout.addStretch()

        # 系统状态显示
        sys_status_frame = QFrame()
        sys_status_layout = QHBoxLayout(sys_status_frame)
        sys_status_layout.setContentsMargins(0, 0, 0, 0)

        sys_status_label = QLabel("系统状态:")
        sys_status_label.setFont(model_status_font)

        self.sys_status_var = QLabel("正常")
        self.sys_status_var.setFont(QFont("Microsoft YaHei", 9))
        self.sys_status_var.setStyleSheet("color: green;")

        sys_status_layout.addWidget(sys_status_label)
        sys_status_layout.addWidget(self.sys_status_var)
        sys_status_layout.addStretch()

        status_row2_layout.addWidget(data_status_frame)
        status_row2_layout.addWidget(sys_status_frame)
        status_layout.addLayout(status_row2_layout)

        group_layout.addWidget(status_container)
        group_layout.addStretch()

        left_layout.addWidget(left_group_box)

        # 根据用户权限更新按钮状态
        self.update_button_permissions()

        return left_widget

    def update_button_permissions(self):
        """根据当前用户权限更新按钮的可用性"""
        if not hasattr(self.app, 'current_user_role') or not self.app.current_user_role:
            # 如果没有用户角色信息，默认禁用所有按钮
            self.gen_data_btn.setEnabled(False)
            self.custom_gen_data_btn.setEnabled(False)
            self.data_aug_btn.setEnabled(False)
            self.import_original_btn.setEnabled(False)
            self.import_processed_btn.setEnabled(False)
            self.train_btn.setEnabled(False)
            self.load_btn.setEnabled(False)
            self.export_btn.setEnabled(False)
            self.predict_btn.setEnabled(False)
            self.batch_pred_btn.setEnabled(False)
            self.history_btn.setEnabled(False)
            self.vis_btn.setEnabled(False)
            self.opt_history_btn.setEnabled(False)
            self.compare_btn.setEnabled(False)
            self.monitor_btn.setEnabled(False)
            self.clear_output_btn.setEnabled(False)
            self.clear_plot_btn.setEnabled(False)
            return

        # 根据权限启用/禁用按钮
        self.gen_data_btn.setEnabled(self.app.check_permission('generate_data'))
        self.custom_gen_data_btn.setEnabled(self.app.check_permission('generate_data'))
        self.import_original_btn.setEnabled(self.app.check_permission('import_data'))
        self.import_processed_btn.setEnabled(self.app.check_permission('import_data'))
        self.data_aug_btn.setEnabled(self.app.check_permission('data_augmentation'))
        self.train_btn.setEnabled(self.app.check_permission('train_model'))
        self.load_btn.setEnabled(self.app.check_permission('import_model'))
        self.export_btn.setEnabled(self.app.check_permission('export_model'))
        self.predict_btn.setEnabled(self.app.check_permission('run_prediction'))
        self.batch_pred_btn.setEnabled(self.app.check_permission('run_prediction'))
        self.history_btn.setEnabled(self.app.check_permission('view_prediction'))
        self.vis_btn.setEnabled(self.app.check_permission('view_prediction'))
        self.opt_history_btn.setEnabled(self.app.check_permission('view_prediction'))
        self.compare_btn.setEnabled(self.app.check_permission('compare_model'))
        self.monitor_btn.setEnabled(self.app.check_permission('system_monitor'))

        # 这些操作对所有用户都可用
        self.refresh_btn.setEnabled(True)
        self.clear_output_btn.setEnabled(True)
        self.clear_plot_btn.setEnabled(True)

        # 特殊处理停止按钮
        self.stop_train_btn.setEnabled(False)
        self.stop_generation_btn.setEnabled(False)

    def disable_all_buttons_except_stop(self):
        """禁用除停止训练按钮外的所有功能按钮"""
        # 禁用所有按钮
        self.gen_data_btn.setEnabled(False)
        self.custom_gen_data_btn.setEnabled(False)
        self.data_aug_btn.setEnabled(False)
        self.import_original_btn.setEnabled(False)
        self.import_processed_btn.setEnabled(False)
        self.train_btn.setEnabled(False)
        self.load_btn.setEnabled(False)
        self.export_btn.setEnabled(False)
        self.predict_btn.setEnabled(False)
        self.batch_pred_btn.setEnabled(False)
        self.history_btn.setEnabled(False)
        self.vis_btn.setEnabled(False)
        self.opt_history_btn.setEnabled(False)
        self.compare_btn.setEnabled(False)
        self.monitor_btn.setEnabled(False)
        self.refresh_btn.setEnabled(False)
        self.clear_output_btn.setEnabled(False)
        self.clear_plot_btn.setEnabled(False)

        # 启用停止按钮
        self.stop_train_btn.setEnabled(True)
        self.stop_generation_btn.setEnabled(True)
