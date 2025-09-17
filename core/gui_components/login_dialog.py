# core/gui_components/login_dialog.py
import os
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QPushButton, QMessageBox, QCheckBox, QGridLayout,
    QScrollArea, QWidget, QFrame, QGroupBox, QFileDialog
)
from PySide6.QtCore import Qt, Signal, QRect
from PySide6.QtGui import QPixmap, QPainter, QPen, QPainterPath, QColor

from .menu import MenuBuilder
from ..user_manager import UserManager, UserRole
from ..config import CONFIG


class PermissionUpgradeDialog(QDialog):
    """权限提升对话框"""
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.parent = parent
        self.new_role = None
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("权限提升 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(450, 400)
        self.resize(450, 400)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("权限提升")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 说明文本
        info_label = QLabel("请输入任一管理员账号和密码以进行权限提升")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                margin-bottom: 15px;
            }
        """)

        # 表单布局
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)

        # 管理员用户名输入
        admin_username_label = QLabel("管理员用户名:")
        admin_username_label.setStyleSheet("font-weight: bold;")
        self.admin_username_input = QLineEdit()
        self.admin_username_input.setPlaceholderText("请输入管理员用户名")
        self.admin_username_input.setMinimumHeight(30)

        # 管理员密码输入
        admin_password_label = QLabel("管理员密码:")
        admin_password_label.setStyleSheet("font-weight: bold;")
        self.admin_password_input = QLineEdit()
        self.admin_password_input.setPlaceholderText("请输入管理员密码")
        self.admin_password_input.setEchoMode(QLineEdit.Password)
        self.admin_password_input.setMinimumHeight(30)

        # 目标角色选择
        target_role_label = QLabel("目标角色:")
        target_role_label.setStyleSheet("font-weight: bold;")
        self.target_role_combo = QComboBox()
        self.target_role_combo.setMinimumHeight(30)

        # 根据当前用户角色设置可提升的目标角色
        current_role = self.parent.current_user_role if self.parent else None
        if current_role == UserRole.BASIC:
            # 普通用户可以提升为高级用户或管理员
            self.target_role_combo.addItem("高级用户", UserRole.ADVANCED)
            self.target_role_combo.addItem("管理员", UserRole.ADMIN)
        elif current_role == UserRole.ADVANCED:
            # 高级用户可以提升为管理员
            self.target_role_combo.addItem("管理员", UserRole.ADMIN)
        else:
            # 其他情况不允许提升
            self.target_role_combo.addItem("无可用提升选项", None)

        # 添加到表单布局
        form_layout.addWidget(admin_username_label, 0, 0)
        form_layout.addWidget(self.admin_username_input, 0, 1)
        form_layout.addWidget(admin_password_label, 1, 0)
        form_layout.addWidget(self.admin_password_input, 1, 1)
        form_layout.addWidget(target_role_label, 2, 0)
        form_layout.addWidget(self.target_role_combo, 2, 1)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.upgrade_button = QPushButton("提升权限")
        self.upgrade_button.setMinimumHeight(35)
        self.upgrade_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        button_layout.addWidget(self.upgrade_button)
        button_layout.addWidget(self.cancel_button)

        # 添加控件到布局
        layout.addWidget(title_label)
        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 设置焦点
        self.admin_username_input.setFocus()

    def setup_connections(self):
        """设置信号连接"""
        self.upgrade_button.clicked.connect(self.handle_upgrade)
        self.cancel_button.clicked.connect(self.reject)
        self.admin_username_input.returnPressed.connect(lambda: self.admin_password_input.setFocus())
        self.admin_password_input.returnPressed.connect(self.handle_upgrade)

    def handle_upgrade(self):
        """处理权限提升"""
        admin_username = self.admin_username_input.text().strip()
        admin_password = self.admin_password_input.text()
        target_role = self.target_role_combo.currentData()

        # 验证输入
        if not admin_username or not admin_password:
            QMessageBox.warning(self, "提升失败", "请填写管理员用户名和密码")
            return

        if not target_role:
            QMessageBox.warning(self, "提升失败", "请选择目标角色")
            return

        # 验管理员账号
        admin_info = self.user_manager.authenticate_user(admin_username, admin_password)
        if not admin_info:
            QMessageBox.warning(self, "提升失败", "管理员用户名或密码错误")
            return

        # 检查管理员账号是否真的具有管理员权限
        _, _, admin_role = admin_info
        if admin_role != UserRole.ADMIN:
            QMessageBox.warning(self, "提升失败", "提供的账号不是管理员账号")
            return

        # 获取当前用户名
        current_username = self.parent.current_username if self.parent else None
        if not current_username:
            QMessageBox.warning(self, "提升失败", "无法获取当前用户信息")
            return

        # 更新用户角色
        if self.user_manager.update_user_role(current_username, target_role):
            QMessageBox.information(self, "提升成功", f"用户 {current_username} 的权限已提升为 {target_role.value}")
            self.new_role = target_role
            self.accept()
        else:
            QMessageBox.warning(self, "提升失败", "权限提升失败")


class AvatarCropDialog(QDialog):
    """头像裁剪对话框"""
    def __init__(self, image_path, parent=None):
        super().__init__(parent)
        self.image_path = image_path
        self.pixmap = QPixmap(image_path)
        self.setup_ui()

    def setup_ui(self):
        """头像裁剪窗口"""
        self.setWindowTitle("裁剪头像")
        self.setMinimumSize(300, 350)
        self.resize(300, 350)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)

        # 显示图片的标签
        self.image_label = QLabel()
        self.image_label.setFixedSize(256, 256)
        self.image_label.setAlignment(Qt.AlignCenter)
        self.update_image_display()

        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)

        layout.addWidget(self.image_label)
        layout.addLayout(button_layout)

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 连接信号
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def update_image_display(self):
        """更新图片显示"""
        if self.pixmap.isNull():
            return

        # 缩放图片以适应显示区域
        scaled_pixmap = self.pixmap.scaled(
            self.image_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        # 在图片上绘制裁剪区域
        painter = QPainter(scaled_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制裁剪区域
        pen = QPen(QColor(255, 255, 255, 200))
        pen.setWidth(2)
        painter.setPen(pen)

        # 计算最大内切圆的位置和大小
        label_size = self.image_label.size()
        circle_diameter = min(label_size.width(), label_size.height())
        circle_rect = QRect(
            (label_size.width() - circle_diameter) // 2,
            (label_size.height() - circle_diameter) // 2,
            circle_diameter,
            circle_diameter
        )

        painter.drawEllipse(circle_rect)

        # 绘制半透明遮罩
        overlay = QPixmap(scaled_pixmap.size())
        overlay.fill(QColor(0, 0, 0, 100))
        painter.drawPixmap(0, 0, overlay)

        # 清除裁剪区域的遮罩
        painter.setCompositionMode(QPainter.CompositionMode_Clear)
        painter.drawEllipse(circle_rect)

        painter.end()

        self.image_label.setPixmap(scaled_pixmap)

    def get_cropped_pixmap(self):
        """获取裁剪后的图片"""
        if self.pixmap.isNull():
            return None

        # 计算在原始图片中的裁剪区域（最大内切圆）
        pixmap_size = self.pixmap.size()
        circle_diameter = min(pixmap_size.width(), pixmap_size.height())
        crop_rect = QRect(
            (pixmap_size.width() - circle_diameter) // 2,
            (pixmap_size.height() - circle_diameter) // 2,
            circle_diameter,
            circle_diameter
        )

        # 按照裁剪区域裁剪图片
        cropped = self.pixmap.copy(crop_rect)
        # 缩放到标准头像大小
        return cropped.scaled(512, 512, Qt.KeepAspectRatio, Qt.SmoothTransformation)


class UserProfileDialog(QDialog):
    """用户资料对话框"""
    def __init__(self, user_manager: UserManager, username: str, user_role: UserRole,
                 menu: MenuBuilder, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.username = username
        self.user_role = user_role
        self.menu = menu
        self.parent = parent
        self.avatar_pixmap = None

        # 获取用户资料
        self.user_profile = self.user_manager.get_user_profile(username)
        if not self.user_profile:
            self.user_profile = {
                'username': username,
                'nickname': '',
                'gender': '',
                'email': '',
                'avatar_path': ''
            }

        self.setup_ui()
        self.setup_connections()
        self.load_user_profile()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户资料 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(450, 500)
        self.resize(450, 500)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("用户资料")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 用户头像区域
        avatar_layout = QHBoxLayout()
        avatar_layout.setAlignment(Qt.AlignCenter)

        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(100, 100)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("""
            QLabel {
                border: 2px dashed #3498db;
                border-radius: 50px;
                background-color: #f8f9fa;
            }
        """)

        avatar_button_layout = QVBoxLayout()
        self.change_avatar_button = QPushButton("更改头像")
        self.change_avatar_button.setFixedSize(80, 40)
        self.change_avatar_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 5px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)

        avatar_button_layout.addStretch()
        avatar_button_layout.addWidget(self.change_avatar_button)
        avatar_button_layout.addStretch()

        avatar_layout.addWidget(self.avatar_label)
        avatar_layout.addLayout(avatar_button_layout)

        # 用户信息展示
        info_group = QFrame()
        info_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        info_group.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 15px;
            }
        """)

        info_layout = QVBoxLayout(info_group)

        # 用户名
        username_layout = QHBoxLayout()
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold;")
        self.username_value = QLabel(self.username)
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_value)
        username_layout.addStretch()

        # 昵称
        nickname_layout = QHBoxLayout()
        nickname_label = QLabel("昵称:")
        nickname_label.setStyleSheet("font-weight: bold;")
        self.nickname_input = QLineEdit()
        self.nickname_input.setPlaceholderText("请输入昵称")
        nickname_layout.addWidget(nickname_label)
        nickname_layout.addWidget(self.nickname_input)

        # 性别
        gender_layout = QHBoxLayout()
        gender_label = QLabel("性别:")
        gender_label.setStyleSheet("font-weight: bold;")
        self.gender_combo = QComboBox()
        self.gender_combo.addItems(["", "男", "女", "其他"])
        gender_layout.addWidget(gender_label)
        gender_layout.addWidget(self.gender_combo)

        # 邮箱
        email_layout = QHBoxLayout()
        email_label = QLabel("邮箱:")
        email_label.setStyleSheet("font-weight: bold;")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("请输入邮箱地址")
        email_layout.addWidget(email_label)
        email_layout.addWidget(self.email_input)

        info_layout.addLayout(username_layout)
        info_layout.addLayout(nickname_layout)
        info_layout.addLayout(gender_layout)
        info_layout.addLayout(email_layout)

        # 修改密码区域
        password_group = QGroupBox("修改密码")
        password_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 1px solid #dee2e6;
                border-radius: 8px;
                margin-top: 1ex;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                color: #495057;
            }
        """)
        password_layout = QGridLayout(password_group)
        password_layout.setVerticalSpacing(15)
        password_layout.setHorizontalSpacing(10)

        # 旧密码输入
        old_password_label = QLabel("旧密码:")
        old_password_label.setStyleSheet("font-weight: bold;")
        self.old_password_input = QLineEdit()
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.old_password_input.setMinimumHeight(30)
        self.old_password_input.setPlaceholderText("请输入当前密码")

        # 新密码输入
        new_password_label = QLabel("新密码:")
        new_password_label.setStyleSheet("font-weight: bold;")
        self.new_password_input = QLineEdit()
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setMinimumHeight(30)
        self.new_password_input.setPlaceholderText("请输入新密码（至少6个字符）")

        # 确认新密码输入
        confirm_password_label = QLabel("确认密码:")
        confirm_password_label.setStyleSheet("font-weight: bold;")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(30)
        self.confirm_password_input.setPlaceholderText("请再次输入新密码")

        # 添加到密码布局
        password_layout.addWidget(old_password_label, 0, 0)
        password_layout.addWidget(self.old_password_input, 0, 1)
        password_layout.addWidget(new_password_label, 1, 0)
        password_layout.addWidget(self.new_password_input, 1, 1)
        password_layout.addWidget(confirm_password_label, 2, 0)
        password_layout.addWidget(self.confirm_password_input, 2, 1)

        # 按钮布局
        button_layout = QHBoxLayout()

        self.save_profile_button = QPushButton("保存资料")
        self.save_profile_button.setMinimumHeight(35)
        self.save_profile_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        self.change_password_button = QPushButton("修改密码")
        self.change_password_button.setMinimumHeight(35)
        self.change_password_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)

        self.close_button = QPushButton("关闭")
        self.close_button.setMinimumHeight(35)
        self.close_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        button_layout.addWidget(self.save_profile_button)
        button_layout.addWidget(self.change_password_button)
        button_layout.addWidget(self.close_button)

        # 添加控件到主布局
        layout.addWidget(title_label)
        layout.addLayout(avatar_layout)
        layout.addWidget(info_group)
        layout.addWidget(password_group)
        layout.addLayout(button_layout)
        layout.addStretch()

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 设置焦点
        self.nickname_input.setFocus()

    def setup_connections(self):
        """设置信号连接"""
        self.change_avatar_button.clicked.connect(self.handle_change_avatar)
        self.save_profile_button.clicked.connect(self.handle_save_profile)
        self.change_password_button.clicked.connect(self.handle_change_password)
        self.close_button.clicked.connect(self.accept)

    def load_user_profile(self):
        """加载用户资料"""
        # 设置头像
        if self.user_profile.get('avatar_path') and os.path.exists(self.user_profile['avatar_path']):
            pixmap = QPixmap(self.user_profile['avatar_path'])
            if not pixmap.isNull():
                # 创建圆形头像
                circular_pixmap = self.create_circular_pixmap(pixmap, 100)
                self.avatar_label.setPixmap(circular_pixmap)
        else:
            # 默认头像
            self.avatar_label.setText("无头像")

        # 设置其他信息
        self.nickname_input.setText(self.user_profile.get('nickname', ''))
        gender = self.user_profile.get('gender', '')
        index = self.gender_combo.findText(gender)
        if index >= 0:
            self.gender_combo.setCurrentIndex(index)
        self.email_input.setText(self.user_profile.get('email', ''))

    def create_circular_pixmap(self, pixmap, size):
        """创建圆形图片"""
        # 缩放图片
        scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 创建圆形遮罩
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.transparent)

        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形路径
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)

        # 计算居中绘制位置
        x = (size - scaled_pixmap.width()) / 2
        y = (size - scaled_pixmap.height()) / 2

        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        return circular_pixmap

    def handle_change_avatar(self):
        """处理更改头像"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择头像图片",
            "",
            "图片文件 (*.png *.jpg *.jpeg *.bmp)"
        )

        if file_path:
            # 打开裁剪对话框
            crop_dialog = AvatarCropDialog(file_path, self)
            if crop_dialog.exec() == QDialog.Accepted:
                cropped_pixmap = crop_dialog.get_cropped_pixmap()
                if cropped_pixmap:
                    # 创建用户资料目录
                    user_info_dir = os.path.join(CONFIG["user_info"], self.username)
                    if not os.path.exists(user_info_dir):
                        os.makedirs(user_info_dir)

                    # 保存头像
                    avatar_path = os.path.join(user_info_dir, "avatar.png")
                    if cropped_pixmap.save(avatar_path, "PNG"):
                        self.user_profile['avatar_path'] = avatar_path
                        # 显示新头像
                        circular_pixmap = self.create_circular_pixmap(cropped_pixmap, 100)
                        self.avatar_label.setPixmap(circular_pixmap)
                        QMessageBox.information(self, "成功", "头像已更新")
                    else:
                        QMessageBox.warning(self, "失败", "保存头像失败")

    def handle_save_profile(self):
        """处理保存资料"""
        nickname = self.nickname_input.text().strip()
        gender = self.gender_combo.currentText()
        email = self.email_input.text().strip()

        # 验证邮箱格式（简单验证）
        if email and "@" not in email:
            QMessageBox.warning(self, "保存失败", "邮箱格式不正确")
            return

        # 更新用户资料
        if self.user_manager.update_user_profile(
                self.username,
                nickname=nickname if nickname else None,
                gender=gender if gender else None,
                email=email if email else None,
                avatar_path=self.user_profile.get('avatar_path') if self.user_profile.get('avatar_path') else None
        ):
            QMessageBox.information(self, "保存成功", "用户资料已保存")

            # 更新内存中的用户资料
            self.user_profile['nickname'] = nickname
            self.user_profile['gender'] = gender
            self.user_profile['email'] = email

            # 更新父窗口的用户名显示
            if self.menu:
                self.menu.update_user_avatar(self.username)
        else:
            QMessageBox.warning(self, "保存失败", "保存用户资料失败")

    def handle_change_password(self):
        """处理修改密码"""
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # 验证输入
        if not old_password or not new_password or not confirm_password:
            QMessageBox.warning(self, "修改失败", "请填写所有密码字段")
            return

        if len(new_password) < 6:
            QMessageBox.warning(self, "修改失败", "新密码至少需要6个字符")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "修改失败", "新密码和确认密码不一致")
            return

        # 尝试修改密码
        if self.user_manager.change_password(self.username, old_password, new_password):
            QMessageBox.information(self, "修改成功", "密码修改成功！")
            # 清空输入框
            self.old_password_input.clear()
            self.new_password_input.clear()
            self.confirm_password_input.clear()
            # 更新父窗口的用户名显示（如果需要）
            if self.parent:
                self.parent.update_user_avatar(self.username)
        else:
            QMessageBox.warning(self, "修改失败", "旧密码错误，请重新输入")


class LoginDialog(QDialog):
    """登录对话框"""
    login_successful = Signal(int, str, object)  # user_id, username, role
    def __init__(self, user_manager: UserManager):
        super().__init__()
        self.user_manager = user_manager
        self.setup_ui()
        self.setup_connections()
        self.populate_remembered_users()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户登录 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(450, 500)
        self.resize(450, 500)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()

        # 主布局
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("OptiSVR分光计折射率预测系统")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        subtitle_label = QLabel("用户登录")
        subtitle_label.setAlignment(Qt.AlignCenter)
        subtitle_label.setStyleSheet("""
            QLabel {
                font-size: 16px;
                color: #7f8c8d;
                margin-bottom: 20px;
            }
        """)

        # 用户头像显示区域
        self.avatar_layout = QVBoxLayout()
        self.avatar_layout.setAlignment(Qt.AlignCenter)
        self.avatar_label = QLabel()
        self.avatar_label.setFixedSize(80, 80)
        self.avatar_label.setAlignment(Qt.AlignCenter)
        self.avatar_label.setStyleSheet("""
            QLabel {
                border-radius: 40px;
                background-color: #3498db;
                color: white;
                font-size: 24px;
                font-weight: bold;
            }
        """)
        self.avatar_layout.addWidget(self.avatar_label)

        # 登录表单
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)

        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold;")
        self.username_input = QComboBox()
        self.username_input.setEditable(True)
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(30)

        # 密码输入
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)

        # 添加到表单布局
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)

        # 记住我和修改密码布局
        bottom_layout = QHBoxLayout()

        self.remember_checkbox = QCheckBox("记住密码")
        self.forgot_password_button = QPushButton("忘记密码")
        self.forgot_password_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.forgot_password_button.setFixedSize(80, 30)

        self.change_password_button = QPushButton("修改密码")
        self.change_password_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
                padding: 5px 10px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.change_password_button.setFixedSize(80, 30)

        bottom_layout.addWidget(self.remember_checkbox)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.forgot_password_button)
        bottom_layout.addWidget(self.change_password_button)

        # 登录按钮
        self.login_button = QPushButton("登录")
        self.login_button.setMinimumHeight(40)
        self.login_button.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #21618c;
            }
        """)

        # 注册和访客按钮布局
        button_layout = QHBoxLayout()
        self.register_button = QPushButton("注册")
        self.register_button.setMinimumHeight(35)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        self.guest_button = QPushButton("以访客身份进入")
        self.guest_button.setMinimumHeight(35)
        self.guest_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        button_layout.addWidget(self.register_button)
        button_layout.addWidget(self.guest_button)

        # 添加控件到主布局
        main_layout.addWidget(title_label)
        main_layout.addWidget(subtitle_label)
        main_layout.addLayout(self.avatar_layout)
        main_layout.addLayout(form_layout)
        main_layout.addLayout(bottom_layout)
        main_layout.addWidget(self.login_button)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(scroll_area)

        # 设置焦点
        self.username_input.setFocus()

    def populate_remembered_users(self):
        """填充记住的用户列表"""
        remembered_users = self.user_manager.get_remembered_users()
        if remembered_users:
            # 添加所有记住的用户名到下拉列表
            for username, _ in remembered_users:
                self.username_input.addItem(username)

            # 默认选中第一个用户
            first_username, first_password = remembered_users[0]
            self.username_input.setCurrentText(first_username)
            self.password_input.setText(first_password)
            self.remember_checkbox.setChecked(True)

            # 显示第一个用户的头像
            self.update_avatar_display(first_username)
        else:
            # 没有记住的用户时隐藏头像
            self.avatar_label.hide()

    def setup_connections(self):
        """设置信号连接"""
        self.login_button.clicked.connect(self.handle_login)
        self.register_button.clicked.connect(self.handle_register)
        self.guest_button.clicked.connect(self.handle_guest_login)
        self.username_input.lineEdit().returnPressed.connect(self.handle_login)
        self.password_input.returnPressed.connect(self.handle_login)
        self.change_password_button.clicked.connect(self.handle_change_password)
        self.forgot_password_button.clicked.connect(self.handle_forgot_password)
        self.remember_checkbox.stateChanged.connect(self.handle_remember_password)
        self.username_input.currentTextChanged.connect(self.on_username_changed)

    def on_username_changed(self, text):
        """当用户名改变时自动填充密码"""
        remembered_users = self.user_manager.get_remembered_users()
        for username, password in remembered_users:
            if username == text:
                self.password_input.setText(password)
                self.remember_checkbox.setChecked(True)
                self.update_avatar_display(username)
                return

        # 如果没有匹配的记住用户，清空密码字段
        self.password_input.clear()
        self.remember_checkbox.setChecked(False)
        # 隐藏头像显示
        self.avatar_label.hide()

    def update_avatar_display(self, username):
        """更新头像显示"""
        # 获取用户资料
        user_profile = self.user_manager.get_user_profile(username)

        if user_profile and user_profile.get('avatar_path') and os.path.exists(user_profile['avatar_path']):
            # 如果有头像图片，则显示图片
            pixmap = QPixmap(user_profile['avatar_path'])
            if not pixmap.isNull():
                circular_pixmap = self.create_circular_pixmap(pixmap, 80)
                self.avatar_label.setPixmap(circular_pixmap)
                self.avatar_label.show()
            else:
                # 图片加载失败，显示默认头像
                self.show_default_avatar(username)
        else:
            # 没有头像图片，显示默认头像（蓝底首字母）
            self.show_default_avatar(username)

    def create_circular_pixmap(self, pixmap, size):
        """创建圆形图片"""
        # 缩放图片
        scaled_pixmap = pixmap.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)

        # 创建圆形遮罩
        circular_pixmap = QPixmap(size, size)
        circular_pixmap.fill(Qt.transparent)

        painter = QPainter(circular_pixmap)
        painter.setRenderHint(QPainter.Antialiasing)

        # 绘制圆形路径
        path = QPainterPath()
        path.addEllipse(0, 0, size, size)
        painter.setClipPath(path)

        # 计算居中绘制位置
        x = (size - scaled_pixmap.width()) / 2
        y = (size - scaled_pixmap.height()) / 2

        painter.drawPixmap(x, y, scaled_pixmap)
        painter.end()

        return circular_pixmap

    def show_default_avatar(self, username):
        """显示默认头像（蓝底首字母）"""
        if username:
            # 获取用户名首字母
            first_letter = username[0].upper() if username else ""

            # 设置样式
            self.avatar_label.setText(first_letter)
            self.avatar_label.setStyleSheet("""
                QLabel {
                    border-radius: 40px;
                    background-color: #3498db;
                    color: white;
                    font-size: 24px;
                    font-weight: bold;
                }
            """)
            self.avatar_label.show()
        else:
            # 没有用户名时隐藏头像
            self.avatar_label.hide()

    def handle_remember_password(self, state):
        """处理记住密码复选框状态变化"""
        if state == Qt.Checked:
            # 如果有记住的用户信息，则填充当前选中的用户名和密码
            current_username = self.username_input.currentText()
            remembered_users = self.user_manager.get_remembered_users()
            for username, password in remembered_users:
                if username == current_username:
                    self.username_input.setCurrentText(username)
                    self.password_input.setText(password)
                    self.update_avatar_display(username)
                    return
        else:
            # 取消选中时不自动清空输入框，让用户自己决定是否清空
            pass

    def handle_login(self):
        """处理登录"""
        username = self.username_input.currentText().strip()
        password = self.password_input.text()
        remember = self.remember_checkbox.isChecked()

        if not username or not password:
            QMessageBox.warning(self, "登录失败", "请输入用户名和密码")
            return

        user_info = self.user_manager.authenticate_user(username, password)
        if user_info:
            user_id, username, role = user_info
            # 保存记住的用户
            self.user_manager.save_remembered_user(username, password, remember)
            self.login_successful.emit(user_id, username, role)
            self.accept()
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")

    def handle_register(self):
        """处理注册"""
        # 创建注册对话框
        register_dialog = RegisterDialog(self.user_manager, self)
        register_dialog.registration_successful.connect(self.on_registration_successful)
        register_dialog.exec()

    def handle_guest_login(self):
        """处理访客登录"""
        # 以访客身份登录
        self.login_successful.emit(-1, "Guest", UserRole.GUEST)
        self.accept()

    def handle_change_password(self):
        """处理修改密码"""
        # 创建修改密码对话框
        change_password_dialog = ChangePasswordDialog(self.user_manager, self)
        change_password_dialog.exec()

    def handle_forgot_password(self):
        """处理忘记密码"""
        # 创建忘记密码对话框
        forgot_password_dialog = ForgotPasswordDialog(self.user_manager, self)
        forgot_password_dialog.exec()

    def on_registration_successful(self, username):
        """注册成功回调"""
        QMessageBox.information(self, "注册成功", f"用户 {username} 注册成功！\n请使用您的用户名和密码登录。")
        # 自动填充用户名
        self.username_input.setCurrentText(username)
        self.password_input.setFocus()

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if event.key() == Qt.Key_Escape:
            # 允许用户通过ESC键关闭对话框
            self.reject()
        else:
            super().keyPressEvent(event)


class RegisterDialog(QDialog):
    """注册对话框"""
    registration_successful = Signal(str)  # username
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户注册 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(400, 300)
        self.resize(400, 300)
        self.setModal(True)

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("用户注册")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 表单布局
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)

        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名（至少2个字符）")
        self.username_input.setMinimumHeight(30)

        # 密码输入
        password_label = QLabel("密码:")
        password_label.setStyleSheet("font-weight: bold;")
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("请输入密码（至少6个字符）")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setMinimumHeight(30)

        # 确认密码输入
        confirm_password_label = QLabel("确认密码:")
        confirm_password_label.setStyleSheet("font-weight: bold;")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请再次输入密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(30)

        # 添加到表单布局
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        form_layout.addWidget(password_label, 1, 0)
        form_layout.addWidget(self.password_input, 1, 1)
        form_layout.addWidget(confirm_password_label, 2, 0)
        form_layout.addWidget(self.confirm_password_input, 2, 1)

        # 注册按钮
        self.register_button = QPushButton("注册")
        self.register_button.setMinimumHeight(40)
        self.register_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)

        # 添加控件到布局
        layout.addWidget(title_label)
        layout.addLayout(form_layout)
        layout.addWidget(self.register_button)
        layout.addStretch()

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 设置焦点
        self.username_input.setFocus()

    def setup_connections(self):
        """设置信号连接"""
        self.register_button.clicked.connect(self.handle_register)
        self.username_input.returnPressed.connect(self.handle_register)
        self.password_input.returnPressed.connect(self.handle_register)
        self.confirm_password_input.returnPressed.connect(self.handle_register)

    def handle_register(self):
        """处理注册"""
        username = self.username_input.text().strip()
        password = self.password_input.text()
        confirm_password = self.confirm_password_input.text()

        # 验证输入
        if not username or not password or not confirm_password:
            QMessageBox.warning(self, "注册失败", "请填写所有字段")
            return

        if len(username) < 2:
            QMessageBox.warning(self, "注册失败", "用户名至少需要2个字符")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "注册失败", "密码至少需要6个字符")
            return

        if password != confirm_password:
            QMessageBox.warning(self, "注册失败", "两次输入的密码不一致")
            return

        # 尝试创建用户
        if self.user_manager.create_user(username, password, UserRole.BASIC):
            self.registration_successful.emit(username)
            self.accept()
        else:
            QMessageBox.warning(self, "注册失败", f"用户名 {username} 已存在，请选择其他用户名")


class ChangePasswordDialog(QDialog):
    """修改密码对话框"""
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("修改密码 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(400, 250)
        self.resize(400, 250)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("修改密码")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 表单布局
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)

        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(30)

        # 旧密码输入
        old_password_label = QLabel("旧密码:")
        old_password_label.setStyleSheet("font-weight: bold;")
        self.old_password_input = QLineEdit()
        self.old_password_input.setPlaceholderText("请输入旧密码")
        self.old_password_input.setEchoMode(QLineEdit.Password)
        self.old_password_input.setMinimumHeight(30)

        # 新密码输入
        new_password_label = QLabel("新密码:")
        new_password_label.setStyleSheet("font-weight: bold;")
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码（至少6个字符）")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setMinimumHeight(30)

        # 添加到表单布局
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        form_layout.addWidget(old_password_label, 1, 0)
        form_layout.addWidget(self.old_password_input, 1, 1)
        form_layout.addWidget(new_password_label, 2, 0)
        form_layout.addWidget(self.new_password_input, 2, 1)

        # 修改密码按钮
        self.change_password_button = QPushButton("修改密码")
        self.change_password_button.setMinimumHeight(40)
        self.change_password_button.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                font-size: 16px;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
            QPushButton:pressed {
                background-color: #d35400;
            }
        """)

        # 添加控件到布局
        layout.addWidget(title_label)
        layout.addLayout(form_layout)
        layout.addWidget(self.change_password_button)
        layout.addStretch()

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 设置焦点
        self.username_input.setFocus()

    def setup_connections(self):
        """设置信号连接"""
        self.change_password_button.clicked.connect(self.handle_change_password)
        self.username_input.returnPressed.connect(lambda: self.old_password_input.setFocus())
        self.old_password_input.returnPressed.connect(lambda: self.new_password_input.setFocus())
        self.new_password_input.returnPressed.connect(self.handle_change_password)

    def handle_change_password(self):
        """处理修改密码"""
        username = self.username_input.text().strip()
        old_password = self.old_password_input.text()
        new_password = self.new_password_input.text()

        # 验证输入
        if not username or not old_password or not new_password:
            QMessageBox.warning(self, "修改失败", "请填写所有字段")
            return

        if len(new_password) < 6:
            QMessageBox.warning(self, "修改失败", "新密码至少需要6个字符")
            return

        # 尝试修改密码
        if self.user_manager.change_password(username, old_password, new_password):
            QMessageBox.information(self, "修改成功", "密码修改成功！")
            self.accept()
        else:
            QMessageBox.warning(self, "修改失败", "用户名或旧密码错误")


class ForgotPasswordDialog(QDialog):
    """忘记密码对话框"""
    def __init__(self, user_manager: UserManager, parent=None):
        super().__init__(parent)
        self.user_manager = user_manager
        self.setup_ui()
        self.setup_connections()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("忘记密码 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(400, 300)
        self.resize(400, 300)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)

        # 标题
        title_label = QLabel("重置密码")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 说明文本
        info_label = QLabel("请输入您的用户名，系统将为您重置密码")
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("""
            QLabel {
                color: #7f8c8d;
                margin-bottom: 15px;
            }
        """)

        # 表单布局
        form_layout = QGridLayout()
        form_layout.setVerticalSpacing(15)

        # 用户名输入
        username_label = QLabel("用户名:")
        username_label.setStyleSheet("font-weight: bold;")
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("请输入用户名")
        self.username_input.setMinimumHeight(30)

        # 新密码输入
        new_password_label = QLabel("新密码:")
        new_password_label.setStyleSheet("font-weight: bold;")
        self.new_password_input = QLineEdit()
        self.new_password_input.setPlaceholderText("请输入新密码（至少6个字符）")
        self.new_password_input.setEchoMode(QLineEdit.Password)
        self.new_password_input.setMinimumHeight(30)

        # 确认新密码输入
        confirm_password_label = QLabel("确认密码:")
        confirm_password_label.setStyleSheet("font-weight: bold;")
        self.confirm_password_input = QLineEdit()
        self.confirm_password_input.setPlaceholderText("请再次输入新密码")
        self.confirm_password_input.setEchoMode(QLineEdit.Password)
        self.confirm_password_input.setMinimumHeight(30)

        # 添加到表单布局
        form_layout.addWidget(username_label, 0, 0)
        form_layout.addWidget(self.username_input, 0, 1)
        form_layout.addWidget(new_password_label, 1, 0)
        form_layout.addWidget(self.new_password_input, 1, 1)
        form_layout.addWidget(confirm_password_label, 2, 0)
        form_layout.addWidget(self.confirm_password_input, 2, 1)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.reset_button = QPushButton("重置密码")
        self.reset_button.setMinimumHeight(35)
        self.reset_button.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)

        self.cancel_button = QPushButton("取消")
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        button_layout.addWidget(self.reset_button)
        button_layout.addWidget(self.cancel_button)

        # 添加控件到布局
        layout.addWidget(title_label)
        layout.addWidget(info_label)
        layout.addLayout(form_layout)
        layout.addLayout(button_layout)

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

        # 设置焦点
        self.username_input.setFocus()

    def setup_connections(self):
        """设置信号连接"""
        self.reset_button.clicked.connect(self.handle_reset_password)
        self.cancel_button.clicked.connect(self.reject)
        self.username_input.returnPressed.connect(lambda: self.new_password_input.setFocus())
        self.new_password_input.returnPressed.connect(lambda: self.confirm_password_input.setFocus())
        self.confirm_password_input.returnPressed.connect(self.handle_reset_password)

    def handle_reset_password(self):
        """处理重置密码"""
        username = self.username_input.text().strip()
        new_password = self.new_password_input.text()
        confirm_password = self.confirm_password_input.text()

        # 验证输入
        if not username:
            QMessageBox.warning(self, "重置失败", "请输入用户名")
            return

        if not new_password or not confirm_password:
            QMessageBox.warning(self, "重置失败", "请输入新密码和确认密码")
            return

        if len(new_password) < 6:
            QMessageBox.warning(self, "重置失败", "新密码至少需要6个字符")
            return

        if new_password != confirm_password:
            QMessageBox.warning(self, "重置失败", "新密码和确认密码不一致")
            return

        # 检查用户是否存在
        if not self.user_manager.user_exists(username):
            QMessageBox.warning(self, "重置失败", "用户不存在")
            return

        # 重置密码
        if self.user_manager.reset_password(username, new_password):
            QMessageBox.information(self, "重置成功", f"用户 {username} 的密码已重置成功！")
            self.accept()
        else:
            QMessageBox.warning(self, "重置失败", "密码重置失败")


class UserManagementDialog(QDialog):
    """用户管理对话框"""
    def __init__(self, user_manager: UserManager, current_user_role: UserRole):
        super().__init__()
        self.user_manager = user_manager
        self.current_user_role = current_user_role
        self.setup_ui()
        self.setup_connections()
        self.load_users()

    def setup_ui(self):
        """设置界面"""
        self.setWindowTitle("用户管理 - OptiSVR分光计折射率预测系统")
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        self.setMinimumSize(700, 500)
        self.resize(700, 500)
        self.setModal(True)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建滚动区域
        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容部件
        content_widget = QWidget()
        layout = QVBoxLayout(content_widget)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 标题
        title_label = QLabel("用户管理")
        title_label.setAlignment(Qt.AlignCenter)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 18px;
                font-weight: bold;
                color: #2c3e50;
                margin-bottom: 10px;
            }
        """)

        # 用户创建区域
        create_group = QFrame()
        create_group.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        create_group.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        create_layout = QGridLayout()
        create_layout.setVerticalSpacing(15)
        create_layout.setHorizontalSpacing(10)

        create_layout.addWidget(QLabel("用户名:"), 0, 0)
        self.new_username_input = QLineEdit()
        self.new_username_input.setMinimumHeight(30)
        create_layout.addWidget(self.new_username_input, 0, 1)

        create_layout.addWidget(QLabel("密码:"), 1, 0)
        self.new_password_input = QLineEdit()
        self.new_password_input.setMinimumHeight(30)
        self.new_password_input.setEchoMode(QLineEdit.Password)
        create_layout.addWidget(self.new_password_input, 1, 1)

        create_layout.addWidget(QLabel("角色:"), 2, 0)
        self.role_combo = QComboBox()
        self.role_combo.setMinimumHeight(30)
        # 根据当前用户角色限制可分配的角色
        if self.current_user_role == UserRole.ADMIN:
            roles = [UserRole.ADMIN, UserRole.ADVANCED, UserRole.BASIC, UserRole.GUEST]
        elif self.current_user_role == UserRole.ADVANCED:
            roles = [UserRole.BASIC, UserRole.GUEST]  # 高级用户只能创建基础用户和访客
        else:
            roles = []

        for role in roles:
            self.role_combo.addItem(role.value, role)
        create_layout.addWidget(self.role_combo, 2, 1)

        self.create_button = QPushButton("创建用户")
        self.create_button.setMinimumHeight(35)
        self.create_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        create_layout.addWidget(self.create_button, 3, 0, 1, 2)

        create_group.setLayout(create_layout)

        # 用户列表标题
        list_title = QLabel("用户列表:")
        list_title.setStyleSheet("font-weight: bold; font-size: 14px;")

        # 用户列表区域
        self.user_list = QGridLayout()
        self.user_list.setHorizontalSpacing(10)
        self.user_list.setVerticalSpacing(5)

        # 滚动区域用于用户列表
        list_scroll_area = QScrollArea()
        list_scroll_widget = QWidget()
        list_scroll_widget.setLayout(self.user_list)
        list_scroll_area.setWidget(list_scroll_widget)
        list_scroll_area.setWidgetResizable(True)
        list_scroll_area.setMinimumHeight(250)
        list_scroll_area.setStyleSheet("""
            QScrollArea {
                border: 1px solid #dee2e6;
                border-radius: 5px;
            }
        """)

        # 添加控件到布局
        layout.addWidget(title_label)
        layout.addWidget(create_group)
        layout.addWidget(list_title)
        layout.addWidget(list_scroll_area)

        # 将内容部件设置到滚动区域
        scroll_area.setWidget(content_widget)

        # 创建主布局并添加滚动区域
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll_area)

    def setup_connections(self):
        """设置信号连接"""
        self.create_button.clicked.connect(self.create_user)

    def create_user(self):
        """创建新用户"""
        username = self.new_username_input.text().strip()
        password = self.new_password_input.text()
        role = self.role_combo.currentData()

        if not username or not password:
            QMessageBox.warning(self, "创建失败", "请填写用户名和密码")
            return

        if len(password) < 6:
            QMessageBox.warning(self, "创建失败", "密码长度至少为6位")
            return

        if not role:
            QMessageBox.warning(self, "创建失败", "请选择用户角色")
            return

        if self.user_manager.create_user(username, password, role):
            QMessageBox.information(self, "创建成功", f"用户 {username} 创建成功")
            self.new_username_input.clear()
            self.new_password_input.clear()
            self.load_users()
        else:
            QMessageBox.warning(self, "创建失败", f"用户 {username} 已存在或创建失败")

    def load_users(self):
        """加载用户列表"""
        # 清除现有用户列表
        for i in reversed(range(self.user_list.count())):
            widget = self.user_list.itemAt(i).widget()
            if widget:
                widget.setParent(None)

        users = self.user_manager.get_all_users()

        # 添加表头
        headers = ["用户名", "角色", "创建时间", "最后登录", "状态", "操作"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setStyleSheet("font-weight: bold; padding: 5px;")
            self.user_list.addWidget(label, 0, col)

        # 添加用户信息
        for row, user in enumerate(users, start=1):
            user_id, username, role, created_at, last_login, is_active = user

            # 用户名
            username_label = QLabel(username)
            self.user_list.addWidget(username_label, row, 0)

            # 角色
            role_label = QLabel(role)
            self.user_list.addWidget(role_label, row, 1)

            # 创建时间
            created_label = QLabel(created_at)
            self.user_list.addWidget(created_label, row, 2)

            # 最后登录
            last_login_label = QLabel(last_login or "从未登录")
            self.user_list.addWidget(last_login_label, row, 3)

            # 状态
            status_label = QLabel("启用" if is_active else "停用")
            status_label.setStyleSheet("color: green;" if is_active else "color: red; font-weight: bold;")
            self.user_list.addWidget(status_label, row, 4)

            # 操作按钮
            button_layout = QHBoxLayout()
            button_layout.setSpacing(5)

            # 只有管理员可以管理所有用户
            can_manage = (self.current_user_role == UserRole.ADMIN)

            if can_manage and is_active:
                # 添加更改角色按钮
                change_role_btn = QPushButton("更改角色")
                change_role_btn.setFixedSize(80, 25)
                change_role_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #007bff;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background-color: #0069d9;
                    }
                """)
                # 使用默认参数修复闭包问题
                change_role_btn.clicked.connect(lambda checked, u=username, r=role: self.change_user_role(u, r))
                button_layout.addWidget(change_role_btn)

                deactivate_btn = QPushButton("停用")
                deactivate_btn.setFixedSize(60, 25)
                deactivate_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #dc3545;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background-color: #c82333;
                    }
                """)
                # 使用默认参数修复闭包问题
                deactivate_btn.clicked.connect(lambda checked, u=username: self.deactivate_user(u))
                button_layout.addWidget(deactivate_btn)
            elif can_manage and not is_active:
                delete_btn = QPushButton("删除")
                delete_btn.setFixedSize(60, 25)
                delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #6c757d;
                        color: white;
                        border: none;
                        border-radius: 3px;
                        font-size: 10px;
                    }
                    QPushButton:hover {
                        background-color: #5a6268;
                    }
                """)
                delete_btn.clicked.connect(lambda checked, u=username: self.delete_user(u))
                button_layout.addWidget(delete_btn)

            button_widget = QWidget()
            button_widget.setLayout(button_layout)
            self.user_list.addWidget(button_widget, row, 5)

    def change_user_role(self, username, current_role):
        """更改用户角色"""
        # 创建角色选择对话框
        dialog = QDialog(self)
        dialog.setWindowTitle(f"更改 {username} 的角色")
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint)
        dialog.setMinimumSize(300, 150)
        dialog.setModal(True)

        # 设置窗口图标
        dialog.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 创建布局
        layout = QVBoxLayout(dialog)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)

        # 说明标签
        info_label = QLabel(f"选择 {username} 的新角色:")
        info_label.setAlignment(Qt.AlignCenter)
        info_label.setStyleSheet("font-weight: bold;")

        # 角色选择组合框
        role_combo = QComboBox()
        role_combo.setMinimumHeight(30)

        # 添加所有可能的角色
        roles = [UserRole.ADMIN, UserRole.ADVANCED, UserRole.BASIC, UserRole.GUEST]
        current_role_enum = None

        # 找到当前角色的枚举值
        for role in UserRole:
            if role.value == current_role:
                current_role_enum = role
                break

        # 添加角色选项
        for role in roles:
            role_combo.addItem(role.value, role)
            if role == current_role_enum:
                role_combo.setCurrentIndex(role_combo.count() - 1)

        # 按钮布局
        button_layout = QHBoxLayout()
        ok_button = QPushButton("确定")
        cancel_button = QPushButton("取消")

        ok_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)

        cancel_button.setStyleSheet("""
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                font-weight: bold;
                border-radius: 5px;
                padding: 8px 16px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
        """)

        button_layout.addWidget(ok_button)
        button_layout.addWidget(cancel_button)

        # 添加控件到布局
        layout.addWidget(info_label)
        layout.addWidget(role_combo)
        layout.addLayout(button_layout)

        # 连接信号
        ok_button.clicked.connect(dialog.accept)
        cancel_button.clicked.connect(dialog.reject)

        # 显示对话框
        if dialog.exec() == QDialog.Accepted:
            new_role = role_combo.currentData()
            # 检查角色是否更改
            if new_role != current_role_enum:
                # 更新用户角色
                if self.user_manager.update_user_role(username, new_role):
                    QMessageBox.information(self, "成功", f"用户 {username} 的角色已更新为 {new_role.value}")
                    self.load_users()  # 重新加载用户列表
                else:
                    QMessageBox.warning(self, "失败", f"更新用户 {username} 的角色失败")

    def deactivate_user(self, username):
        """停用用户"""
        reply = QMessageBox.question(self, "确认", f"确定要停用用户 {username} 吗？",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.user_manager.deactivate_user(username):
                QMessageBox.information(self, "成功", f"用户 {username} 已停用")
                self.load_users()
            else:
                QMessageBox.warning(self, "失败", f"停用用户 {username} 失败")

    def delete_user(self, username):
        """删除用户"""
        reply = QMessageBox.question(self, "确认", f"确定要删除用户 {username} 吗？此操作不可恢复！",
                                     QMessageBox.Yes | QMessageBox.No)

        if reply == QMessageBox.Yes:
            if self.user_manager.delete_user(username):
                QMessageBox.information(self, "成功", f"用户 {username} 已删除")
                self.load_users()
            else:
                QMessageBox.warning(self, "失败", f"删除用户 {username} 失败")
