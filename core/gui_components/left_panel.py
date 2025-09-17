# core/gui_components/left_panel.py
import logging
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
                               QLabel, QGroupBox, QFrame, QSpacerItem, QSizePolicy)
from PySide6.QtGui import QFont
from PySide6.QtCore import Qt


class LeftPanelBuilder:
    """左侧面板构建器"""
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app
        self.logger = logging.getLogger("LeftPanelBuilder")

    def create(self):
        """创建左侧面板"""
        # 创建主窗口部件
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(5, 5, 5, 5)
        left_layout.setSpacing(0)

        # 创建分组框
        left_group_box = QGroupBox("系统功能")
        left_group_box.setFont(QFont("Microsoft YaHei", 9))
        group_layout = QVBoxLayout(left_group_box)
        group_layout.setContentsMargins(5, 5, 5, 5)
        group_layout.setSpacing(0)

        # 创建主布局容器
        main_container = QWidget()
        main_layout = QVBoxLayout(main_container)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 根据窗口大小动态计算尺寸参数
        def calculate_sizes():
            # 获取面板尺寸
            panel_height = left_widget.height() if left_widget.height() > 0 else 600

            # 计算基础尺寸
            base_button_height = max(24, int(panel_height * 0.04))
            base_font_size = max(12, int(panel_height * 0.02))
            base_group_spacing = max(4, int(panel_height * 0.005))
            base_inner_spacing = max(3, int(panel_height * 0.005))
            base_border_radius = max(4, int(panel_height * 0.02))

            return {
                'button_height': base_button_height,
                'font_size': base_font_size,
                'group_spacing': base_group_spacing,
                'inner_spacing': base_inner_spacing,
                'border_radius': base_border_radius,
                'label_font_size': base_font_size + 1
            }

        # 应用动态尺寸到样式
        def apply_dynamic_styles():
            sizes = calculate_sizes()

            # 更新按钮样式以使用动态尺寸
            def dynamic_button_style(base_color, hover_color, pressed_color, border_color=None):
                if border_color is None:
                    border_color = base_color
                return f"""
                    QPushButton {{
                        background-color: {base_color};
                        color: white;
                        font-family: 'Microsoft YaHei';
                        font-weight: bold;
                        font-size: {sizes['font_size']}px;
                        border: 2px solid {border_color};
                        border-radius: {sizes['border_radius']}px;
                        padding: 4px 12px;
                        min-height: {sizes['button_height']}px;
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

            return dynamic_button_style, sizes

        dynamic_button_style, sizes = apply_dynamic_styles()

        # ===== 数据处理组 =====
        data_group_widget = QWidget()
        data_group_layout = QVBoxLayout(data_group_widget)
        data_group_layout.setContentsMargins(0, 0, 0, 0)
        data_group_layout.setSpacing(sizes['inner_spacing'])
        data_group_layout.setAlignment(Qt.AlignTop)

        data_group_label = QLabel("数据处理")
        data_group_font = QFont("Microsoft YaHei", sizes['label_font_size'], QFont.Bold)
        data_group_label.setFont(data_group_font)
        data_group_label.setStyleSheet(f"color: #2c3e50; margin: {sizes['inner_spacing'] * 2}px 0 {sizes['inner_spacing']}px 0;")
        data_group_layout.addWidget(data_group_label)

        # 第一行按钮
        row1_layout = QHBoxLayout()
        row1_layout.setContentsMargins(0, 0, 0, 0)
        row1_layout.setSpacing(sizes['inner_spacing'])

        self.gen_data_btn = QPushButton("生成理论数据")
        self.gen_data_btn.setStyleSheet(dynamic_button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.gen_data_btn.clicked.connect(self.app.generate_theoretical_data)
        row1_layout.addWidget(self.gen_data_btn)

        self.custom_gen_data_btn = QPushButton("自定义生成理论数据")
        self.custom_gen_data_btn.setStyleSheet(dynamic_button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.custom_gen_data_btn.clicked.connect(self.app.custom_generate_theoretical_data)
        row1_layout.addWidget(self.custom_gen_data_btn)
        data_group_layout.addLayout(row1_layout)

        # 第二行按钮
        row2_layout = QHBoxLayout()
        row2_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        row2_layout.setSpacing(sizes['inner_spacing'])

        self.data_aug_btn = QPushButton("数据增强")
        self.data_aug_btn.setStyleSheet(dynamic_button_style("#27ae60", "#2ecc71", "#1e8449"))
        self.data_aug_btn.clicked.connect(self.app.data_augmentation)
        row2_layout.addWidget(self.data_aug_btn)

        self.stop_generation_btn = QPushButton("停止生成")
        self.stop_generation_btn.setStyleSheet(dynamic_button_style("#e74c3c", "#ff6b6b", "#c0392b"))
        self.stop_generation_btn.clicked.connect(self.app.stop_generation)
        self.stop_generation_btn.setEnabled(False)
        row2_layout.addWidget(self.stop_generation_btn)
        data_group_layout.addLayout(row2_layout)

        # 第三行按钮
        row3_layout = QHBoxLayout()
        row3_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        row3_layout.setSpacing(sizes['inner_spacing'])

        self.import_original_btn = QPushButton("导入数据1(原始数据)")
        self.import_original_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.import_original_btn.clicked.connect(self.app.import_data_original)
        row3_layout.addWidget(self.import_original_btn)

        self.import_processed_btn = QPushButton("导入数据2(绘图到80度)")
        self.import_processed_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.import_processed_btn.clicked.connect(self.app.import_data_processed)
        row3_layout.addWidget(self.import_processed_btn)
        data_group_layout.addLayout(row3_layout)

        # ===== 模型操作组 =====
        model_group_widget = QWidget()
        model_group_layout = QVBoxLayout(model_group_widget)
        model_group_layout.setContentsMargins(0, 0, 0, 0)
        model_group_layout.setSpacing(sizes['inner_spacing'])

        model_group_label = QLabel("模型操作")
        model_group_label.setFont(data_group_font)
        model_group_label.setStyleSheet(
            f"color: #2c3e50; margin: {sizes['inner_spacing'] * 2}px 0 {sizes['inner_spacing']}px 0;")
        model_group_layout.addWidget(model_group_label)

        # 第四行按钮
        row4_layout = QHBoxLayout()
        row4_layout.setContentsMargins(0, 0, 0, 0)
        row4_layout.setSpacing(sizes['inner_spacing'])

        self.train_btn = QPushButton("训练模型")
        self.train_btn.setStyleSheet(dynamic_button_style("#f39c12", "#f5b041", "#d35400"))
        self.train_btn.clicked.connect(self.app.start_training)
        row4_layout.addWidget(self.train_btn)

        self.stop_train_btn = QPushButton("停止训练")
        self.stop_train_btn.setStyleSheet(dynamic_button_style("#e74c3c", "#ff6b6b", "#c0392b"))
        self.stop_train_btn.clicked.connect(self.app.stop_training)
        self.stop_train_btn.setEnabled(False)
        row4_layout.addWidget(self.stop_train_btn)
        model_group_layout.addLayout(row4_layout)

        # 第五行按钮
        row5_layout = QHBoxLayout()
        row5_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        row5_layout.setSpacing(sizes['inner_spacing'])

        self.load_btn = QPushButton("加载模型")
        self.load_btn.setStyleSheet(dynamic_button_style("#9b59b6", "#af7ac5", "#76448a"))
        self.load_btn.clicked.connect(self.app.load_model)
        row5_layout.addWidget(self.load_btn)

        self.export_btn = QPushButton("导出模型")
        self.export_btn.setStyleSheet(dynamic_button_style("#9b59b6", "#af7ac5", "#76448a"))
        self.export_btn.clicked.connect(self.app.export_model)
        row5_layout.addWidget(self.export_btn)
        model_group_layout.addLayout(row5_layout)

        # ===== 预测分析组 =====
        predict_group_widget = QWidget()
        predict_group_layout = QVBoxLayout(predict_group_widget)
        predict_group_layout.setContentsMargins(0, 0, 0, 0)
        predict_group_layout.setSpacing(sizes['inner_spacing'])

        predict_group_label = QLabel("预测分析")
        predict_group_label.setFont(data_group_font)
        predict_group_label.setStyleSheet(
            f"color: #2c3e50; margin: {sizes['inner_spacing'] * 2}px 0 {sizes['inner_spacing']}px 0;")
        predict_group_layout.addWidget(predict_group_label)

        # 第六行按钮
        row6_layout = QHBoxLayout()
        row6_layout.setContentsMargins(0, 0, 0, 0)
        row6_layout.setSpacing(sizes['inner_spacing'])

        self.predict_btn = QPushButton("预测折射率")
        self.predict_btn.setStyleSheet(dynamic_button_style("#1abc9c", "#48c9b0", "#148f77"))
        self.predict_btn.clicked.connect(self.app.predict_refractive_index)
        row6_layout.addWidget(self.predict_btn)

        self.batch_pred_btn = QPushButton("批量预测")
        self.batch_pred_btn.setStyleSheet(dynamic_button_style("#1abc9c", "#48c9b0", "#148f77"))
        self.batch_pred_btn.clicked.connect(self.app.batch_prediction)
        row6_layout.addWidget(self.batch_pred_btn)
        predict_group_layout.addLayout(row6_layout)

        # ===== 查看分析组 =====
        view_group_widget = QWidget()
        view_group_layout = QVBoxLayout(view_group_widget)
        view_group_layout.setContentsMargins(0, 0, 0, 0)
        view_group_layout.setSpacing(sizes['inner_spacing'])

        view_group_label = QLabel("查看分析")
        view_group_label.setFont(data_group_font)
        view_group_label.setStyleSheet(
            f"color: #2c3e50; margin: {sizes['inner_spacing'] * 2}px 0 {sizes['inner_spacing']}px 0;")
        view_group_layout.addWidget(view_group_label)

        # 第七行按钮
        row7_layout = QHBoxLayout()
        row7_layout.setContentsMargins(0, 0, 0, 0)
        row7_layout.setSpacing(sizes['inner_spacing'])

        self.history_btn = QPushButton("预测历史")
        self.history_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.history_btn.clicked.connect(self.app.show_prediction_history)
        row7_layout.addWidget(self.history_btn)

        self.vis_btn = QPushButton("查看可视化结果")
        self.vis_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.vis_btn.clicked.connect(self.app.show_visualizations)
        row7_layout.addWidget(self.vis_btn)
        view_group_layout.addLayout(row7_layout)

        # 第八行按钮
        row8_layout = QHBoxLayout()
        row8_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        row8_layout.setSpacing(sizes['inner_spacing'])

        self.opt_history_btn = QPushButton("查看优化历史")
        self.opt_history_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.opt_history_btn.clicked.connect(self.app.show_optimization_history)
        row8_layout.addWidget(self.opt_history_btn)

        self.compare_btn = QPushButton("模型比较")
        self.compare_btn.setStyleSheet(dynamic_button_style("#3498db", "#5dade2", "#21618c"))
        self.compare_btn.clicked.connect(self.app.compare_models)
        row8_layout.addWidget(self.compare_btn)
        view_group_layout.addLayout(row8_layout)

        # ===== 系统工具组 =====
        tools_group_widget = QWidget()
        tools_group_layout = QVBoxLayout(tools_group_widget)
        tools_group_layout.setContentsMargins(0, 0, 0, 0)
        tools_group_layout.setSpacing(sizes['inner_spacing'])

        tools_group_label = QLabel("系统工具")
        tools_group_label.setFont(data_group_font)
        tools_group_label.setStyleSheet(
            f"color: #2c3e50; margin: {sizes['inner_spacing'] * 2}px 0 {sizes['inner_spacing']}px 0;")
        tools_group_layout.addWidget(tools_group_label)

        # 第九行按钮
        row9_layout = QHBoxLayout()
        row9_layout.setContentsMargins(0, 0, 0, 0)
        row9_layout.setSpacing(sizes['inner_spacing'])

        self.monitor_btn = QPushButton("系统监控")
        self.monitor_btn.setStyleSheet(dynamic_button_style("#e67e22", "#f5b041", "#d35400"))
        self.monitor_btn.clicked.connect(self.app.toggle_system_monitor)
        row9_layout.addWidget(self.monitor_btn)

        self.refresh_btn = QPushButton("刷新页面")
        self.refresh_btn.setStyleSheet(dynamic_button_style("#e67e22", "#f5b041", "#d35400"))
        self.refresh_btn.clicked.connect(self.app.refresh_page)
        row9_layout.addWidget(self.refresh_btn)
        tools_group_layout.addLayout(row9_layout)

        # 第十行按钮
        row10_layout = QHBoxLayout()
        row10_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        row10_layout.setSpacing(sizes['inner_spacing'])

        self.clear_output_btn = QPushButton("清空输出")
        self.clear_output_btn.setStyleSheet(dynamic_button_style("#95a5a6", "#bdc3c7", "#7f8c8d"))
        self.clear_output_btn.clicked.connect(self.app.clear_output)
        row10_layout.addWidget(self.clear_output_btn)

        self.clear_plot_btn = QPushButton("清空图表")
        self.clear_plot_btn.setStyleSheet(dynamic_button_style("#95a5a6", "#bdc3c7", "#7f8c8d"))
        self.clear_plot_btn.clicked.connect(self.app.init_result_frame)
        row10_layout.addWidget(self.clear_plot_btn)
        tools_group_layout.addLayout(row10_layout)

        # 添加所有组件到主布局
        main_layout.addWidget(data_group_widget)

        # 在每组之间添加相等的弹性空间
        spacer1 = QSpacerItem(20, sizes['group_spacing'], QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer1)

        main_layout.addWidget(model_group_widget)

        spacer2 = QSpacerItem(20, sizes['group_spacing'], QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer2)

        main_layout.addWidget(predict_group_widget)

        spacer3 = QSpacerItem(20, sizes['group_spacing'], QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer3)

        main_layout.addWidget(view_group_widget)

        spacer4 = QSpacerItem(20, sizes['group_spacing'], QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer4)

        main_layout.addWidget(tools_group_widget)

        # 在系统工具组和状态指示器之间添加相等的弹性空间
        spacer5 = QSpacerItem(20, sizes['group_spacing'], QSizePolicy.Minimum, QSizePolicy.Expanding)
        main_layout.addItem(spacer5)

        # 状态指示器区域
        status_container = QFrame()
        status_layout = QVBoxLayout(status_container)
        status_layout.setContentsMargins(0, sizes['group_spacing'] * 2, 0, sizes['group_spacing'] * 2)
        status_layout.setSpacing(sizes['inner_spacing'])

        # 状态指示器行布局
        status_row_layout = QHBoxLayout()
        status_row_layout.setContentsMargins(0, 0, 0, 0)
        status_row_layout.setSpacing(sizes['group_spacing'] * 2)

        # 模型状态
        model_status_frame = QFrame()
        model_status_layout = QHBoxLayout(model_status_frame)
        model_status_layout.setContentsMargins(0, 0, 0, 0)

        model_status_label = QLabel("模型状态:")
        model_status_font = QFont("Microsoft YaHei", sizes['font_size'], QFont.Bold)
        model_status_label.setFont(model_status_font)

        self.status_var = QLabel("未加载")
        self.status_var.setFont(QFont("Microsoft YaHei", sizes['font_size'], QFont.Bold))
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
        self.model_dir_var.setFont(QFont("Microsoft YaHei", sizes['font_size']))
        self.model_dir_var.setStyleSheet("color: #3498db;")

        model_dir_layout.addWidget(model_dir_label)
        model_dir_layout.addWidget(self.model_dir_var)
        model_dir_layout.addStretch()

        status_row_layout.addWidget(model_status_frame)
        status_row_layout.addWidget(model_dir_frame)
        status_layout.addLayout(status_row_layout)

        # 第二行状态指示器
        status_row2_layout = QHBoxLayout()
        status_row2_layout.setContentsMargins(0, sizes['inner_spacing'], 0, 0)
        status_row2_layout.setSpacing(sizes['group_spacing'] * 2)

        # 数据状态显示
        data_status_frame = QFrame()
        data_status_layout = QHBoxLayout(data_status_frame)
        data_status_layout.setContentsMargins(0, 0, 0, 0)

        data_status_label = QLabel("数据状态:")
        data_status_label.setFont(model_status_font)

        self.data_status_var = QLabel("未加载")
        self.data_status_var.setFont(QFont("Microsoft YaHei", sizes['font_size']))
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
        self.sys_status_var.setFont(QFont("Microsoft YaHei", sizes['font_size']))
        self.sys_status_var.setStyleSheet("color: green;")

        sys_status_layout.addWidget(sys_status_label)
        sys_status_layout.addWidget(self.sys_status_var)
        sys_status_layout.addStretch()

        status_row2_layout.addWidget(data_status_frame)
        status_row2_layout.addWidget(sys_status_frame)
        status_layout.addLayout(status_row2_layout)

        # 添加组件到分组框布局
        group_layout.addWidget(main_container)
        group_layout.addWidget(status_container)

        # 添加分组框到左侧布局
        left_layout.addWidget(left_group_box)

        # 根据用户权限更新按钮状态
        self.update_button_permissions()

        # 连接窗口大小变化信号以重新计算尺寸
        left_widget.resizeEvent = self._create_resize_handler(left_widget, main_layout, data_group_widget,
                                                              model_group_widget, predict_group_widget, view_group_widget,
                                                              tools_group_widget, data_group_layout, model_group_layout,
                                                              predict_group_layout, view_group_layout, tools_group_layout,
                                                              status_layout, status_container, status_row_layout,
                                                              status_row2_layout, model_status_label, model_status_font,
                                                              data_group_label, model_group_label, predict_group_label,
                                                              view_group_label, tools_group_label)

        return left_widget

    def _create_resize_handler(self, widget, main_layout, data_group_widget, model_group_widget,
                               predict_group_widget, view_group_widget, tools_group_widget,
                               data_group_layout, model_group_layout, predict_group_layout,
                               view_group_layout, tools_group_layout, status_layout,
                               status_container, status_row_layout, status_row2_layout,
                               model_status_label, model_status_font, data_group_label,
                               model_group_label, predict_group_label, view_group_label, tools_group_label):
        """创建窗口大小变化处理函数"""
        def resize_event(event):
            # 重新计算尺寸
            panel_height = widget.height() if widget.height() > 0 else 600

            # 计算基础尺寸
            base_font_size = max(9, int(panel_height * 0.015))
            base_group_spacing = max(5, int(panel_height * 0.01))
            base_inner_spacing = max(3, int(panel_height * 0.005))

            # 更新布局间距
            data_group_layout.setSpacing(base_inner_spacing)
            model_group_layout.setSpacing(base_inner_spacing)
            predict_group_layout.setSpacing(base_inner_spacing)
            view_group_layout.setSpacing(base_inner_spacing)
            tools_group_layout.setSpacing(base_inner_spacing)

            # 更新标签边距
            data_group_label.setStyleSheet(
                f"color: #2c3e50; margin: {base_inner_spacing * 2}px 0 {base_inner_spacing}px 0;")
            model_group_label.setStyleSheet(
                f"color: #2c3e50; margin: {base_inner_spacing * 2}px 0 {base_inner_spacing}px 0;")
            predict_group_label.setStyleSheet(
                f"color: #2c3e50; margin: {base_inner_spacing * 2}px 0 {base_inner_spacing}px 0;")
            view_group_label.setStyleSheet(
                f"color: #2c3e50; margin: {base_inner_spacing * 2}px 0 {base_inner_spacing}px 0;")
            tools_group_label.setStyleSheet(
                f"color: #2c3e50; margin: {base_inner_spacing * 2}px 0 {base_inner_spacing}px 0;")

            # 更新状态区域布局
            status_layout.setContentsMargins(0, base_group_spacing * 2, 0, base_group_spacing * 2)
            status_layout.setSpacing(base_inner_spacing)
            status_row_layout.setSpacing(base_group_spacing * 2)
            status_row2_layout.setSpacing(base_group_spacing * 2)

            # 更新标签字体
            model_status_font.setPointSize(base_font_size)
            model_status_label.setFont(model_status_font)

            # 更新spacer尺寸
            for i in range(main_layout.count()):
                item = main_layout.itemAt(i)
                if isinstance(item, QSpacerItem):
                    main_layout.removeItem(item)

            # 重新添加spacer
            spacer1 = QSpacerItem(20, base_group_spacing, QSizePolicy.Minimum, QSizePolicy.Expanding)
            spacer2 = QSpacerItem(20, base_group_spacing, QSizePolicy.Minimum, QSizePolicy.Expanding)
            spacer3 = QSpacerItem(20, base_group_spacing, QSizePolicy.Minimum, QSizePolicy.Expanding)
            spacer4 = QSpacerItem(20, base_group_spacing, QSizePolicy.Minimum, QSizePolicy.Expanding)
            spacer5 = QSpacerItem(20, base_group_spacing, QSizePolicy.Minimum, QSizePolicy.Expanding)

            # 清除原有spacer后重新添加
            items = []
            for i in range(main_layout.count()):
                items.append(main_layout.itemAt(i))

            # 重新组织布局
            main_layout.removeItem(main_layout.itemAt(main_layout.count() - 1))  # 移除status_container
            while main_layout.count() > 0:
                main_layout.takeAt(0)

            main_layout.addWidget(data_group_widget)
            main_layout.addItem(spacer1)
            main_layout.addWidget(model_group_widget)
            main_layout.addItem(spacer2)
            main_layout.addWidget(predict_group_widget)
            main_layout.addItem(spacer3)
            main_layout.addWidget(view_group_widget)
            main_layout.addItem(spacer4)
            main_layout.addWidget(tools_group_widget)
            main_layout.addItem(spacer5)
            main_layout.addWidget(status_container)

            if hasattr(widget, '_old_resize_event') and widget._old_resize_event:
                widget._old_resize_event(event)
            else:
                QWidget.resizeEvent(widget, event)

        return resize_event

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
