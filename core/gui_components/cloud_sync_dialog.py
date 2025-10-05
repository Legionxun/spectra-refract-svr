# core/gui_components/cloud_sync_dialog.py
from PySide6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
                               QLineEdit, QCheckBox, QMessageBox, QGroupBox, QProgressBar)
from PySide6.QtCore import Qt, Signal, QTimer
from PySide6.QtGui import QFont, QPalette
from cryptography.fernet import Fernet

from ..cloud_sync import CloudSyncManager
from ..config import CONFIG


class CloudSyncSettingsDialog(QDialog):
    """云同步设置对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.cloud_sync_manager = CloudSyncManager()
        self.setup_ui()
        self.load_settings()

    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("云同步设置")
        self.setFixedSize(500, 400)
        self.setModal(True)

        layout = QVBoxLayout()

        # 标题
        title_label = QLabel("云同步设置")
        title_label.setFont(QFont("Microsoft YaHei", 16, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 同步开关
        self.enable_sync_checkbox = QCheckBox("启用云同步")
        self.enable_sync_checkbox.setFont(QFont("Microsoft YaHei", 12))
        layout.addWidget(self.enable_sync_checkbox)

        # GitHub设置组
        github_group = QGroupBox("GitHub配置")
        github_layout = QVBoxLayout()

        # GitHub令牌
        token_layout = QHBoxLayout()
        token_label = QLabel("个人访问令牌:")
        token_label.setFont(QFont("Microsoft YaHei", 10))
        self.token_input = QLineEdit()
        self.token_input.setFont(QFont("Microsoft YaHei", 10))
        self.token_input.setEchoMode(QLineEdit.Password)

        # 设置为只读并显示为灰色
        palette = self.token_input.palette()
        palette.setColor(QPalette.Base, Qt.lightGray)
        self.token_input.setPalette(palette)
        self.token_input.setReadOnly(True)
        token_layout.addWidget(token_label)
        token_layout.addWidget(self.token_input)
        github_layout.addLayout(token_layout)

        # GitHub用户名
        username_layout = QHBoxLayout()
        username_label = QLabel("GitHub用户名:")
        username_label.setFont(QFont("Microsoft YaHei", 10))
        self.username_input = QLineEdit()
        self.username_input.setFont(QFont("Microsoft YaHei", 10))

        # 设置为只读并显示为灰色
        palette = self.username_input.palette()
        palette.setColor(QPalette.Base, Qt.lightGray)
        self.username_input.setPalette(palette)
        self.username_input.setReadOnly(True)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        github_layout.addLayout(username_layout)

        # 仓库名称
        repo_layout = QHBoxLayout()
        repo_label = QLabel("仓库名称:")
        repo_label.setFont(QFont("Microsoft YaHei", 10))
        self.repo_input = QLineEdit()
        self.repo_input.setFont(QFont("Microsoft YaHei", 10))
        repo_layout.addWidget(repo_label)
        repo_layout.addWidget(self.repo_input)
        github_layout.addLayout(repo_layout)

        github_group.setLayout(github_layout)
        layout.addWidget(github_group)

        # 状态信息
        status_group = QGroupBox("同步状态")
        status_layout = QVBoxLayout()

        self.status_label = QLabel("状态: 未配置")
        self.status_label.setFont(QFont("Microsoft YaHei", 10))
        status_layout.addWidget(self.status_label)

        self.last_sync_label = QLabel("最后同步时间: 从未")
        self.last_sync_label.setFont(QFont("Microsoft YaHei", 10))
        status_layout.addWidget(self.last_sync_label)

        status_group.setLayout(status_layout)
        layout.addWidget(status_group)

        # 操作按钮
        button_layout = QHBoxLayout()

        self.test_button = QPushButton("测试连接")
        self.test_button.setFont(QFont("Microsoft YaHei", 10))
        self.test_button.clicked.connect(self.test_connection)
        button_layout.addWidget(self.test_button)

        self.sync_button = QPushButton("立即同步")
        self.sync_button.setFont(QFont("Microsoft YaHei", 10))
        self.sync_button.clicked.connect(self.sync_now)
        button_layout.addWidget(self.sync_button)

        button_layout.addStretch()

        self.save_button = QPushButton("保存")
        self.save_button.setFont(QFont("Microsoft YaHei", 10))
        self.save_button.clicked.connect(self.save_settings)
        self.save_button.setDefault(True)
        button_layout.addWidget(self.save_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFont(QFont("Microsoft YaHei", 10))
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_settings(self):
        """加载现有设置"""
        if self.cloud_sync_manager.is_sync_enabled():
            self.enable_sync_checkbox.setChecked(True)
            config = self.cloud_sync_manager.sync_config
            self.token_input.setText(
                Fernet(CONFIG["key"]).decrypt(config.get("github_token").encode("utf-8")).decode("utf-8"))
            self.username_input.setText(config.get("github_username", CONFIG.get("repo_username", "")))
            self.repo_input.setText(config.get("github_repo", CONFIG.get("cloud_sync_name", "")))

            # 更新状态显示
            self.status_label.setText("状态: 已启用")
            last_sync = self.cloud_sync_manager.get_last_sync_time()
            if last_sync:
                self.last_sync_label.setText(f"最后同步时间: {last_sync}")
            else:
                self.last_sync_label.setText("最后同步时间: 从未")
        else:
            self.enable_sync_checkbox.setChecked(False)
            self.status_label.setText("状态: 未启用")

            # 加载默认配置信息
            self.token_input.setText(Fernet(CONFIG["key"]).decrypt(CONFIG["repo_token_bytes"]).decode("utf-8"))
            self.username_input.setText(CONFIG.get("repo_username", ""))
            self.repo_input.setText(CONFIG.get("cloud_sync_name", ""))

    def test_connection(self):
        """测试GitHub连接"""
        token = self.token_input.text().strip()
        username = self.username_input.text().strip()
        repo = self.repo_input.text().strip()

        if not token or not username or not repo:
            QMessageBox.warning(self, "配置不完整", "请填写所有GitHub配置信息")
            return

        # 创建临时同步管理器进行测试
        temp_manager = CloudSyncManager()
        if temp_manager.configure_sync(token, username, repo):
            QMessageBox.information(self, "连接成功", "已成功连接到GitHub仓库")
        else:
            QMessageBox.critical(self, "连接失败", "无法连接到GitHub仓库，请检查配置信息")

    def sync_now(self):
        """立即同步"""
        if not self.cloud_sync_manager.is_sync_enabled():
            QMessageBox.warning(self, "未启用", "请先启用云同步功能")
            return

        # 停止自动同步
        if self.parent_app:
            self.parent_app.cloud_sync_manager.stop_sync()

        # 创建并显示进度对话框
        self.progress_dialog = CloudSyncProgressDialog(self, self.parent_app)
        self.progress_dialog.sync_completed.connect(self.on_sync_completed)

        # 连接云同步管理器的信号到进度对话框
        try:
            self.cloud_sync_manager.sync_progress.connect(self.progress_dialog.update_progress)
            self.cloud_sync_manager.sync_file_progress.connect(self.progress_dialog.update_file_progress)
            self.cloud_sync_manager.sync_finished.connect(self.progress_dialog.on_sync_finished)
        except Exception as e:
            pass

        # 显示进度对话框
        self.progress_dialog.show()
        self.cloud_sync_manager.trigger_sync(self.parent_app)

        # 关闭设置对话框
        self.accept()

    def on_sync_completed(self, success, message):
        """同步完成回调"""
        if self.parent_app:
            self.parent_app.show_sync_progress(False)

            # 重启自动同步定时器
            self.parent_app.cloud_sync_manager.setup_auto_sync(self.parent_app)

        if success:
            QMessageBox.information(self, "同步成功", message)

            # 更新最后同步时间显示
            last_sync = self.cloud_sync_manager.get_last_sync_time()
            if last_sync:
                self.last_sync_label.setText(f"最后同步时间: {last_sync}")
        else:
            QMessageBox.critical(self, "同步失败", message)

    def save_settings(self):
        """保存设置"""
        if self.enable_sync_checkbox.isChecked():
            token = self.token_input.text().strip()
            username = self.username_input.text().strip()
            repo = self.repo_input.text().strip()

            if not token or not username or not repo:
                QMessageBox.warning(self, "配置不完整", "请填写所有GitHub配置信息")
                return

            if self.cloud_sync_manager.configure_sync(token, username, repo):
                QMessageBox.information(self, "保存成功", "云同步设置已保存并启用")
                self.status_label.setText("状态: 已启用")

                # 如果是首次同步，立即触发一次同步
                if self.cloud_sync_manager.is_auto_sync_needed():
                    self.parent_app.status_label.setText("首次同步中...")
                    self.cloud_sync_manager.trigger_sync(self.parent_app)

                self.accept()
            else:
                QMessageBox.critical(self, "保存失败", "无法保存设置，请检查配置信息")
        else:
            self.cloud_sync_manager.disable_sync()
            self.status_label.setText("状态: 已禁用")
            QMessageBox.information(self, "保存成功", "云同步已禁用")
            self.accept()


class CloudSyncProgressDialog(QDialog):
    """云同步进度对话框"""
    sync_completed = Signal(bool, str)  # (success, message)
    def __init__(self, parent=None, main_window=None):
        super().__init__(parent)
        self.parent_dialog = parent
        self.main_window = main_window
        if main_window:
            self.cloud_sync_manager = main_window.cloud_sync_manager
        else:
            self.cloud_sync_manager = CloudSyncManager()
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.setup_ui()

    def setup_ui(self):
        """设置用户界面"""
        self.setWindowTitle("云同步")
        self.setFixedSize(400, 230)

        layout = QVBoxLayout()

        self.status_label = QLabel("正在同步数据...")
        self.status_label.setFont(QFont("Microsoft YaHei", 12))
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)

        self.file_status_label = QLabel("")
        self.file_status_label.setFont(QFont("Microsoft YaHei", 10))
        self.file_status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.file_status_label)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)

        self.file_progress_bar = QProgressBar()
        self.file_progress_bar.setRange(0, 100)
        self.file_progress_bar.setValue(0)
        layout.addWidget(self.file_progress_bar)

        # 添加按钮布局
        button_layout = QHBoxLayout()

        self.background_button = QPushButton("后台运行")
        self.background_button.setFont(QFont("Microsoft YaHei", 10))
        self.background_button.clicked.connect(self.run_in_background)
        button_layout.addWidget(self.background_button)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setFont(QFont("Microsoft YaHei", 10))
        self.cancel_button.clicked.connect(self.cancel_sync)
        button_layout.addWidget(self.cancel_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

    def update_progress(self, current, total):
        """更新进度条"""
        try:
            current = int(current)
            total = int(total)

            if total > 0:
                progress = int((current / total) * 100)
                self.progress_bar.setValue(progress)
                self.status_label.setText(f"正在同步阶段... ({current}/{total})")
            else:
                self.progress_bar.setValue(0)
                self.status_label.setText("正在同步数据...")
        except (ValueError, TypeError):
            self.progress_bar.setValue(0)
            self.status_label.setText("正在同步数据...")

    def update_file_progress(self, filename, current, total):
        """更新文件进度条"""
        try:
            current = int(current)
            total = int(total)

            if total > 0:
                progress = int((current / total) * 100)
                self.file_progress_bar.setValue(progress)
                self.file_status_label.setText(f"正在处理: {filename} ({current}/{total})")
            else:
                self.file_progress_bar.setValue(0)
                self.file_status_label.setText(f"正在处理: {filename}")
        except (ValueError, TypeError):
            self.file_progress_bar.setValue(0)
            self.file_status_label.setText(f"正在处理: {filename}")

    def on_sync_finished(self, success, message):
        """同步完成处理"""
        try:
            if self.main_window:
                self.main_window.show_sync_progress(False)

            if not hasattr(self, 'is_background_sync') or not self.is_background_sync:
                self.sync_completed.emit(success, message)
                QTimer.singleShot(0, self.accept)
            else:
                self.sync_completed.emit(success, message)
        except RuntimeError:
            pass

    def cancel_sync(self):
        """取消同步"""
        try:
            self.cloud_sync_manager.sync_in_progress = False
            self.reject()
        except RuntimeError:
            pass

    def run_in_background(self):
        """后台运行同步"""
        try:
            self.is_background_sync = True
            if self.main_window:
                QMessageBox.information(self, "后台同步", "同步将在后台继续运行，您可以在状态栏查看进度。")
                self.main_window.show_sync_progress(True)
            self.hide()
            if self.parent_dialog:
                self.parent_dialog.hide()
        except RuntimeError:
            pass
