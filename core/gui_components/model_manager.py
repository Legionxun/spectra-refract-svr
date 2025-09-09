# core/gui_components/model_manager.py
import os, shutil
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
                               QListWidget, QListWidgetItem, QLabel, QMessageBox,
                               QAbstractItemView, QFrame)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..config import CONFIG


class ModelManagerDialog(QDialog):
    """模型管理对话框"""
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("模型管理")
        self.setModal(True)
        self.resize(600, 400)
        self.models_path = CONFIG.get("base_model_dir", "saved_models")
        self.setup_ui()
        self.load_models()

    def setup_ui(self):
        """设置用户界面"""
        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("模型管理")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 添加分隔线
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # 模型列表
        self.model_list = QListWidget()
        self.model_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        layout.addWidget(self.model_list)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 刷新按钮
        refresh_btn = QPushButton("刷新")
        refresh_btn.clicked.connect(self.load_models)
        button_layout.addWidget(refresh_btn)

        # 删除选中按钮
        self.delete_btn = QPushButton("删除选中模型")
        self.delete_btn.clicked.connect(self.delete_selected_models)
        self.delete_btn.setEnabled(False)
        button_layout.addWidget(self.delete_btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 连接模型列表选择信号
        self.model_list.itemSelectionChanged.connect(self.on_selection_changed)

    def load_models(self):
        """加载模型列表"""
        self.model_list.clear()

        if not os.path.exists(self.models_path):
            return

        try:
            model_dirs = [d for d in os.listdir(self.models_path)
                          if os.path.isdir(os.path.join(self.models_path, d))]

            for model_dir in sorted(model_dirs, reverse=True):
                item = QListWidgetItem(model_dir)
                item.setToolTip(f"模型路径: {os.path.join(self.models_path, model_dir)}")
                self.model_list.addItem(item)

            # 检查当前加载的模型是否还存在
            current_model_name = None
            if (hasattr(self.app, 'current_model_dir') and
                    self.app.current_model_dir):
                current_model_name = os.path.basename(self.app.current_model_dir)

            # 如果当前加载的模型已被删除，则卸载它
            if current_model_name and current_model_name not in model_dirs:
                self.app.predictor = None
                self.app.current_model_dir = None
                self.app.status_var.setText("未加载")
                self.app.status_indicator.setStyleSheet("color: #dc3545;")
                self.app.model_dir_var.setText("无")

                # 清空结果区域
                self.app.init_result_frame()

                QMessageBox.information(
                    self,
                    "模型已卸载",
                    f"当前加载的模型 '{current_model_name}' 已被删除，模型已自动卸载。"
                )

        except Exception as e:
            QMessageBox.critical(self, "错误", f"加载模型列表失败: {str(e)}")

    def on_selection_changed(self):
        """当选择项改变时"""
        selected_count = len(self.model_list.selectedItems())
        self.delete_btn.setEnabled(selected_count > 0)
        if selected_count > 0:
            self.delete_btn.setText(f"删除选中模型({selected_count})")
        else:
            self.delete_btn.setText("删除选中模型")

    def delete_selected_models(self):
        """删除选中模型"""
        selected_items = self.model_list.selectedItems()
        if not selected_items:
            return

        # 确认删除
        model_names = [item.text() for item in selected_items]
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"确定要删除以下 {len(model_names)} 个模型及其所有文件吗?\n\n" +
            "\n".join(model_names),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success_count = 0
            failed_models = []

            # 检查当前加载的模型是否在删除列表中
            current_model_name = None
            if (hasattr(self.parent(), 'current_model_dir') and
                    self.app.current_model_dir):
                current_model_name = os.path.basename(self.app.current_model_dir)

            need_unload = current_model_name in model_names

            for model_name in model_names:
                model_path = os.path.join(self.models_path, model_name)
                try:
                    if os.path.exists(model_path):
                        shutil.rmtree(model_path)
                        success_count += 1
                except Exception as e:
                    failed_models.append(f"{model_name}: {str(e)}")

            # 更新界面
            for item in selected_items:
                self.model_list.takeItem(self.model_list.row(item))

            # 如果删除了当前加载的模型，则卸载它
            if need_unload:
                self.app.predictor = None
                self.app.current_model_dir = None
                self.app.status_var.setText("未加载")
                self.app.status_indicator.setStyleSheet("color: #dc3545;")
                self.app.model_dir_var.setText("无")

                # 清空结果区域
                self.app.init_result_frame()
                QMessageBox.information(
                    self,
                    "模型已卸载",
                    f"已删除当前加载的模型 '{current_model_name}'，模型已自动卸载。"
                )

            # 显示结果
            if failed_models:
                QMessageBox.warning(
                    self,
                    "删除完成",
                    f"成功删除 {success_count} 个模型。\n\n以下模型删除失败:\n" +
                    "\n".join(failed_models)
                )
            else:
                if not need_unload:
                    QMessageBox.information(
                        self,
                        "删除完成",
                        f"成功删除 {success_count} 个模型。"
                    )

            # 重新加载模型列表
            self.on_selection_changed()
