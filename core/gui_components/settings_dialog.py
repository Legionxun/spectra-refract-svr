# core/gui_components/settings_dialog.py
import json, os
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSpinBox, 
                               QPushButton, QGroupBox, QFormLayout, QMessageBox)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..config import CONFIG


class SettingsDialog(QDialog):
    """系统设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("系统设置")
        self.setModal(True)
        self.resize(400, 300)
        self.init_ui()
        self.load_settings()

    def init_ui(self):
        """初始化UI界面"""
        layout = QVBoxLayout()
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("系统设置")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        layout.addWidget(title_label)

        # 折射率显示设置组
        refractive_index_group = QGroupBox("折射率显示设置")
        refractive_index_layout = QFormLayout()
        refractive_index_layout.setLabelAlignment(Qt.AlignRight)
        refractive_index_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)

        # 小数位数设置
        self.decimal_places_spinbox = QSpinBox()
        self.decimal_places_spinbox.setRange(1, 10)
        self.decimal_places_spinbox.setValue(4)
        refractive_index_layout.addRow("小数位数:", self.decimal_places_spinbox)

        refractive_index_group.setLayout(refractive_index_layout)
        layout.addWidget(refractive_index_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 确定按钮
        ok_button = QPushButton("确定")
        ok_button.setObjectName("primary")
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)

        # 取消按钮
        cancel_button = QPushButton("取消")
        cancel_button.setObjectName("danger")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(cancel_button)

        # 重置按钮
        reset_button = QPushButton("重置")
        reset_button.clicked.connect(self.reset_settings)
        button_layout.addWidget(reset_button)

        layout.addLayout(button_layout)
        self.setLayout(layout)

    def load_settings(self):
        """加载设置"""
        settings_file = os.path.join(CONFIG["settings_dir"], "settings.json")
        try:
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                    decimal_places = settings.get("refractive_index_decimal_places", 4)
                    self.decimal_places_spinbox.setValue(decimal_places)
        except Exception as e:
            print(f"加载设置时出错: {e}")

    def save_settings(self):
        """保存设置"""
        settings_file = os.path.join(CONFIG["settings_dir"], "settings.json")
        try:
            # 读取现有设置
            settings = {}
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
            
            # 更新设置
            settings["refractive_index_decimal_places"] = self.decimal_places_spinbox.value()
            
            # 保存设置
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=4)
                
            # 更新全局配置
            CONFIG["refractive_index_decimal_places"] = self.decimal_places_spinbox.value()
            
            return True
        except Exception as e:
            print(f"保存设置时出错: {e}")
            QMessageBox.critical(self, "错误", f"保存设置失败: {str(e)}")
            return False

    def reset_settings(self):
        """重置设置"""
        reply = QMessageBox.question(self, "确认", "确定要重置所有设置吗？")
        if reply == QMessageBox.Yes:
            self.decimal_places_spinbox.setValue(4)

    def accept(self):
        """确认设置"""
        if self.save_settings():
            super().accept()
            QMessageBox.information(self, "成功", "设置已保存！")
