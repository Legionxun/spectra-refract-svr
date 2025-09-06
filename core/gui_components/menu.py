# core/gui_components/menu.py
from PySide6.QtWidgets import QMenuBar, QMenu
import logging


class MenuBuilder:
    def __init__(self, main_window, app):
        self.main_window = main_window
        self.app = app
        self.menu_items = {}
        self.logger = logging.getLogger("MenuBuilder")

    def build_menu(self):
        self.menu_bar = QMenuBar(self.main_window)
        self.menu_bar.setStyleSheet("""
            QMenuBar {
                background-color: #2c3e50;
                color: #ecf0f1;
            }
            QMenuBar::item {
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #3498db;
            }
            QMenuBar::item:pressed {
                background: #3498db;
            }
            QMenu {
                background-color: #34495e;
                color: #ecf0f1;
            }
            QMenu::item:selected {
                background-color: #3498db;
            }
        """)

        # 文件菜单
        file_menu = QMenu("文件", self.menu_bar)
        file_menu.addAction("导入数据1(原始数据)", self.app.import_data_original)
        file_menu.addAction("导入数据2(绘图到80度)", self.app.import_data_processed)
        file_menu.addSeparator()
        file_menu.addAction("保存当前系统输出内容", self.app.save_current_results)
        file_menu.addSeparator()
        file_menu.addAction("退出", self.app.on_close)
        self.menu_bar.addMenu(file_menu)

        # 数据处理菜单
        data_menu = QMenu("数据处理", self.menu_bar)
        data_menu.addAction("生成理论数据", self.app.generate_theoretical_data)
        data_menu.addAction("自定义生成理论数据", self.app.custom_generate_theoretical_data)
        data_menu.addAction("停止生成", self.app.stop_generation)
        data_menu.addSeparator()
        data_menu.addAction("数据增强", self.app.data_augmentation)
        self.menu_bar.addMenu(data_menu)

        # 模型操作菜单
        model_menu = QMenu("模型操作", self.menu_bar)
        model_menu.addAction("训练模型", self.app.start_training)
        model_menu.addAction("停止训练", self.app.stop_training)
        model_menu.addSeparator()
        model_menu.addAction("加载模型", self.app.load_model)
        model_menu.addSeparator()
        model_menu.addAction("导出模型", self.app.export_model)
        self.menu_bar.addMenu(model_menu)

        # 预测分析菜单
        predict_menu = QMenu("预测分析", self.menu_bar)
        predict_menu.addAction("预测折射率", self.app.predict_refractive_index)
        predict_menu.addAction("批量预测", self.app.batch_prediction)
        self.menu_bar.addMenu(predict_menu)

        # 查看分析菜单
        view_menu = QMenu("查看分析", self.menu_bar)
        view_menu.addAction("查看优化历史", self.app.show_optimization_history)
        view_menu.addAction("查看可视化结果", self.app.show_visualizations)
        view_menu.addSeparator()
        view_menu.addAction("模型比较", self.app.compare_models)
        self.menu_bar.addMenu(view_menu)

        # 历史记录菜单
        history_menu = QMenu("历史记录", self.menu_bar)
        history_menu.addAction("查看预测历史", self.app.show_prediction_history)
        self.menu_bar.addMenu(history_menu)

        # 系统工具菜单
        tools_menu = QMenu("系统工具", self.menu_bar)
        tools_menu.addAction("系统监控", self.app.toggle_system_monitor)
        tools_menu.addAction("查看监控日志", self.app.show_monitoring_logs)
        self.menu_bar.addMenu(tools_menu)

        # 帮助菜单
        help_menu = QMenu("帮助", self.menu_bar)
        help_menu.addAction("使用指南", self.app.show_usage_guide)
        help_menu.addAction("检查更新", self.app.check_for_updates)
        help_menu.addAction("关于", self.app.show_about)
        self.menu_bar.addMenu(help_menu)

        self.main_window.setMenuBar(self.menu_bar)

        # 保存菜单项索引以便后续禁用/启用
        # 获取所有菜单项
        menus = [
            data_menu,  # 0 - 数据处理
            model_menu,  # 1 - 模型操作
            predict_menu,  # 2 - 预测分析
            view_menu,  # 3 - 查看分析
            history_menu,  # 4 - 历史记录
            tools_menu  # 5 - 系统工具
        ]

        # 保存菜单项引用
        self.menu_items = {
            # 数据处理菜单项
            "生成理论数据": (menus[0], menus[0].actions()[0]),
            "自定义生成理论数据": (menus[0], menus[0].actions()[1]),
            "停止生成": (menus[0], menus[0].actions()[2]),
            "数据增强": (menus[0], menus[0].actions()[4]),

            # 模型操作菜单项
            "训练模型": (menus[1], menus[1].actions()[0]),
            "停止训练": (menus[1], menus[1].actions()[1]),
            "加载模型": (menus[1], menus[1].actions()[3]),
            "导出模型": (menus[1], menus[1].actions()[5]),

            # 预测分析菜单项
            "预测折射率": (menus[2], menus[2].actions()[0]),
            "批量预测": (menus[2], menus[2].actions()[1]),

            # 查看分析菜单项
            "查看优化历史": (menus[3], menus[3].actions()[0]),
            "查看可视化结果": (menus[3], menus[3].actions()[1]),
            "模型比较": (menus[3], menus[3].actions()[3]),

            # 历史记录菜单项
            "查看预测历史": (menus[4], menus[4].actions()[0]),

            # 系统工具菜单项
            "系统监控": (menus[5], menus[5].actions()[0]),
            "查看监控日志": (menus[5], menus[5].actions()[1])
        }

    def enable_all_buttons(self):
        """启用所有功能按钮和菜单项"""
        for item_name, (menu, action) in self.menu_items.items():
            action.setEnabled(True)

        # 禁用"停止训练"和"停止生成"菜单项
        _, stop_train_action = self.menu_items["停止训练"]
        stop_train_action.setEnabled(False)

        _, stop_generation_action = self.menu_items["停止生成"]
        stop_generation_action.setEnabled(False)

    def disable_all_buttons_except_stop(self):
        """禁用除停止训练按钮外的所有功能按钮和菜单项"""
        for item_name, (menu, action) in self.menu_items.items():
            if item_name != "停止训练" and item_name != "停止生成":
                action.setEnabled(False)

        # 启用"停止训练"和"停止生成"菜单项
        _, stop_train_action = self.menu_items["停止训练"]
        stop_train_action.setEnabled(True)

        _, stop_generation_action = self.menu_items["停止生成"]
        stop_generation_action.setEnabled(True)
