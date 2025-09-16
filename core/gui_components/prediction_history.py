# core/gui_components/prediction_history.py
import csv, os, logging, datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem, QWidget,
    QHeaderView, QPushButton, QFileDialog, QMessageBox, QApplication, QTabWidget, QAbstractItemView,
    QScrollArea, QFrame
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap

from ..config import CONFIG


class PredictionHistoryManager:
    """预测历史记录管理器"""
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("PredictionHistoryManager")

    def save_prediction_to_history(self, filename, prediction, confidence, model_name):
        """保存预测结果到历史记录"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 获取当前用户名
        current_user = getattr(self.app, 'current_user', None)
        if current_user is None:
            current_user = getattr(self.app, 'current_username', None)
            if current_user:
                username = current_user
            else:
                username = 'guest'
        else:
            username = current_user['username'] if isinstance(current_user, dict) else current_user

        record = {
            "timestamp": timestamp,
            "filename": filename,
            "prediction": prediction,
            "confidence": confidence,
            "model": model_name,
            "username": username
        }

        self.app.prediction_history.append(record)

        # 保存到总的历史记录文件
        history_path = os.path.join(CONFIG["history_dir"], "prediction_history.csv")
        try:
            with open(history_path, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if os.stat(history_path).st_size == 0:
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称", "用户名"])
                writer.writerow([timestamp, os.path.basename(filename), prediction, confidence, model_name, username])
        except Exception as e:
            print(f"保存预测历史记录失败: {str(e)}")
            self.logger.error(f"保存预测历史记录失败: {str(e)}")

        # 保存到用户特定的历史记录文件
        user_history_dir = os.path.join(CONFIG["user_info"], username, "history")
        if not os.path.exists(user_history_dir):
            os.makedirs(user_history_dir)

        user_history_path = os.path.join(str(user_history_dir), "prediction_history.csv")
        try:
            with open(user_history_path, 'a', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                if os.stat(user_history_path).st_size == 0:
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称"])
                writer.writerow([timestamp, os.path.basename(filename), prediction, confidence, model_name])
        except Exception as e:
            print(f"保存用户预测历史记录失败: {str(e)}")
            self.logger.error(f"保存用户预测历史记录失败: {str(e)}")

    def load_prediction_history(self):
        """加载预测历史记录"""
        # 清空现有历史记录
        self.app.prediction_history.clear()

        # 加载总的历史记录
        history_path = os.path.join(CONFIG["history_dir"], "prediction_history.csv")
        if os.path.exists(history_path):
            encodings = ['utf-8-sig', 'utf-8', 'gbk', 'gb2312', 'latin-1']
            content = None
            used_encoding = None

            for encoding in encodings:
                try:
                    with open(history_path, 'r', encoding=encoding) as f:
                        content = f.read()
                        used_encoding = encoding
                        break
                except UnicodeDecodeError:
                    continue

            if content is None:
                try:
                    with open(history_path, 'rb') as f:
                        content = f.read().decode('utf-8', errors='ignore')
                    used_encoding = 'utf-8 (with errors ignored)'
                except Exception as e:
                    print(f"加载历史记录失败: {str(e)}")
                    self.logger.error(f"加载历史记录失败: {str(e)}")
                    return

            if content:
                try:
                    with open(history_path, 'r', encoding=used_encoding) as f:
                        reader = csv.reader(f)
                        # 跳过标题行
                        next(reader)
                        for row in reader:
                            if len(row) >= 6:  # 现在有6列包括用户名
                                self.app.prediction_history.append({
                                    "timestamp": row[0],
                                    "filename": row[1],
                                    "prediction": float(row[2]),
                                    "confidence": float(row[3]),
                                    "model": row[4],
                                    "username": row[5]
                                })
                    print(f"已加载 {len(self.app.prediction_history)} 条历史记录 (编码: {used_encoding})")
                except Exception as e:
                    print(f"解析历史记录失败: {str(e)}")
                    self.logger.error(f"解析历史记录失败: {str(e)}")
        else:
            print("未找到历史记录文件")

    def show_prediction_history(self):
        """显示预测历史记录"""
        self._ensure_user_history_file()

        if not self.app.prediction_history:
            QMessageBox.information(self.app, "提示", "暂无预测历史记录")
            return

        # 创建历史记录窗口
        dialog = PredictionHistoryDialog(self.app)
        dialog.exec()

    def _ensure_user_history_file(self):
        """确保当前用户的历史记录文件存在"""
        # 获取当前用户名
        current_user = getattr(self.app, 'current_user', None)
        if current_user is None:
            current_user = getattr(self.app, 'current_username', None)
            if current_user:
                username = current_user
            else:
                username = 'guest'
        else:
            username = current_user['username'] if isinstance(current_user, dict) else current_user

        # 检查用户历史记录文件是否存在
        user_history_dir = os.path.join(CONFIG["user_info"], username, "history")
        user_history_path = os.path.join(user_history_dir, "prediction_history.csv")

        # 如果用户历史记录文件不存在，从总历史记录中筛选并创建
        if not os.path.exists(user_history_path):
            if not os.path.exists(user_history_dir):
                os.makedirs(user_history_dir)

            # 筛选属于当前用户的历史记录
            user_records = [record for record in self.app.prediction_history if
                            record.get("username", "guest") == username]

            # 如果有属于该用户的历史记录，则保存到用户文件中
            if user_records:
                try:
                    with open(user_history_path, 'w', newline='', encoding='utf-8-sig') as f:
                        writer = csv.writer(f)
                        writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称"])
                        for record in user_records:
                            writer.writerow([
                                record["timestamp"],
                                os.path.basename(record["filename"]),
                                record["prediction"],
                                record["confidence"],
                                record["model"]
                            ])
                    print(f"已为用户 {username} 创建历史记录文件，包含 {len(user_records)} 条记录")
                except Exception as e:
                    print(f"创建用户历史记录文件失败: {str(e)}")
                    self.logger.error(f"创建用户历史记录文件失败: {str(e)}")

    def delete_history_records(self, indices_to_delete):
        """删除指定索引的历史记录"""
        # 按降序排列索引
        indices_to_delete.sort(reverse=True)

        # 删除应用中的历史记录
        for index in indices_to_delete:
            if 0 <= index < len(self.app.prediction_history):
                del self.app.prediction_history[index]

        # 保存更新后的总历史记录
        self._save_all_history()

        # 更新所有用户的历史记录文件
        self._update_user_history_files()

    def _save_all_history(self):
        """保存所有历史记录到总文件"""
        history_path = os.path.join(CONFIG["history_dir"], "prediction_history.csv")

        try:
            # 确保目录存在
            os.makedirs(CONFIG["history_dir"], exist_ok=True)

            with open(history_path, 'w', newline='', encoding='utf-8-sig') as f:
                writer = csv.writer(f)
                # 写入标题
                writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称", "用户名"])
                # 写入数据
                for record in self.app.prediction_history:
                    writer.writerow([
                        record["timestamp"],
                        record["filename"],
                        record["prediction"],
                        record["confidence"],
                        record["model"],
                        record["username"]
                    ])
            print(f"已更新总历史记录文件，剩余 {len(self.app.prediction_history)} 条记录")
        except Exception as e:
            print(f"保存总历史记录失败: {str(e)}")
            self.logger.error(f"保存总历史记录失败: {str(e)}")

    def _update_user_history_files(self):
        """更新所有用户的历史记录文件"""
        user_records = {}
        for record in self.app.prediction_history:
            username = record.get("username", "guest")
            if username not in user_records:
                user_records[username] = []
            user_records[username].append(record)

        # 为每个用户更新历史记录文件
        for username, records in user_records.items():
            user_history_dir = os.path.join(CONFIG["user_info"], username, "history")
            user_history_path = os.path.join(user_history_dir, "prediction_history.csv")

            try:
                # 确保目录存在
                os.makedirs(user_history_dir, exist_ok=True)

                with open(user_history_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    # 写入标题
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称"])
                    # 写入数据
                    for record in records:
                        writer.writerow([
                            record["timestamp"],
                            os.path.basename(record["filename"]),
                            record["prediction"],
                            record["confidence"],
                            record["model"]
                        ])
                print(f"已更新用户 {username} 的历史记录文件，包含 {len(records)} 条记录")
            except Exception as e:
                print(f"更新用户 {username} 的历史记录文件失败: {str(e)}")
                self.logger.error(f"更新用户 {username} 的历史记录文件失败: {str(e)}")


class DeletePNGFilesDialog(QDialog):
    """删除预测图片对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("删除预测图片")
        self.resize(700, 500)
        self.png_files = []
        self.image_containers = []  # 保存图片容器的引用
        self.init_ui()
        self.refresh_png_list()  # 初始化时加载图片列表

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("删除预测图片")
        title_font = QFont("Microsoft YaHei", 14, QFont.Bold)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # 说明文字
        desc_label = QLabel("选择要删除的PNG文件:")
        layout.addWidget(desc_label)

        # 创建滚动区域用于显示图片
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)

        # 创建内容容器
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_layout.setSpacing(5)
        self.content_layout.setAlignment(Qt.AlignTop)

        self.scroll_area.setWidget(self.content_widget)
        layout.addWidget(self.scroll_area)

        # 按钮布局
        button_layout = QHBoxLayout()

        # 全选/取消全选按钮
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all_files)
        button_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all_files)
        button_layout.addWidget(deselect_all_btn)

        # 刷新按钮
        refresh_btn = QPushButton("刷新列表")
        refresh_btn.clicked.connect(self.refresh_png_list)
        button_layout.addWidget(refresh_btn)

        layout.addLayout(button_layout)

        # 操作按钮布局
        action_layout = QHBoxLayout()
        action_layout.addStretch()

        # 删除选中文件按钮
        delete_selected_btn = QPushButton("删除选中文件")
        delete_selected_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                    QPushButton:pressed {
                        background-color: #a93226;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        delete_selected_btn.clicked.connect(self.delete_selected_files)
        action_layout.addWidget(delete_selected_btn)

        # 删除所有文件按钮
        delete_all_btn = QPushButton("删除所有文件")
        delete_all_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f39c12;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #d35400;
                    }
                    QPushButton:pressed {
                        background-color: #ba4a00;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        delete_all_btn.clicked.connect(self.delete_all_files)
        action_layout.addWidget(delete_all_btn)

        # 关闭按钮
        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #7f8c8d;
                    }
                    QPushButton:pressed {
                        background-color: #6c757d;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        close_btn.clicked.connect(self.close)
        action_layout.addWidget(close_btn)

        layout.addLayout(action_layout)

    def refresh_png_list(self):
        """刷新PNG文件列表"""
        # 清除现有的图片显示
        for i in reversed(range(self.content_layout.count())):
            item = self.content_layout.takeAt(i)
            if item.widget():
                item.widget().deleteLater()

        self.image_containers = []  # 清空容器引用列表

        # 获取所有PNG文件
        try:
            if not os.path.exists(CONFIG["actual_data_dir"]):
                os.makedirs(CONFIG["actual_data_dir"], exist_ok=True)

            png_files = [f for f in os.listdir(CONFIG["actual_data_dir"]) if f.lower().endswith('.png')]
            if not png_files:
                no_files_label = QLabel("没有找到PNG文件")
                no_files_label.setAlignment(Qt.AlignCenter)
                self.content_layout.addWidget(no_files_label)
                return

            # 创建网格布局显示图片，每行4个
            row_widget = None
            row_layout = None

            for i, png_file in enumerate(sorted(png_files)):
                # 每行4个图片
                if i % 4 == 0:
                    row_widget = QWidget()
                    row_layout = QHBoxLayout(row_widget)
                    row_layout.setSpacing(10)
                    self.content_layout.addWidget(row_widget)

                # 创建图片容器
                image_container = QFrame()
                image_container.setFrameStyle(QFrame.StyledPanel)
                image_container.setLineWidth(1)
                image_container.setProperty("fileName", png_file)  # 保存文件名
                image_layout = QVBoxLayout(image_container)
                image_layout.setContentsMargins(5, 5, 5, 5)
                image_layout.setSpacing(3)

                # 创建文件名标签
                file_label = QLabel(png_file)
                file_label.setWordWrap(True)
                file_label.setMaximumWidth(150)
                file_label.setObjectName("fileLabel")

                # 创建图片显示
                image_label = QLabel()
                image_label.setAlignment(Qt.AlignCenter)
                image_label.setFixedSize(150, 150)
                image_label.setScaledContents(False)

                # 加载图片
                image_path = os.path.join(CONFIG["actual_data_dir"], png_file)
                if os.path.exists(image_path):
                    pixmap = QPixmap(image_path)
                    if not pixmap.isNull():
                        # 缩放图片以适应标签
                        pixmap = pixmap.scaled(150, 150, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        image_label.setPixmap(pixmap)
                else:
                    image_label.setText("图片不存在")

                # 创建选择标记
                selection_indicator = QLabel("☐")
                selection_indicator.setAlignment(Qt.AlignCenter)
                selection_indicator.setStyleSheet("font-size: 20px; color: #666;")
                selection_indicator.setProperty("selected", False)
                selection_indicator.setProperty("filePath", image_path)
                selection_indicator.setCursor(Qt.PointingHandCursor)
                selection_indicator.setFixedHeight(30)

                # 连接点击事件
                def toggle_selection_wrapper(label):
                    def toggle(event):
                        self.toggle_selection(label)

                    return toggle

                selection_indicator.mousePressEvent = toggle_selection_wrapper(selection_indicator)

                image_layout.addWidget(image_label)
                image_layout.addWidget(file_label)
                image_layout.addWidget(selection_indicator, 0, Qt.AlignCenter)

                row_layout.addWidget(image_container)
                self.image_containers.append({
                    'container': image_container,
                    'indicator': selection_indicator,
                    'file_path': image_path,
                    'file_name': png_file
                })

            # 如果最后一行不满4个，添加弹性空间
            if row_layout and len(png_files) % 4 != 0:
                row_layout.addStretch()

        except Exception as e:
            error_label = QLabel(f"读取PNG文件列表失败: {str(e)}")
            error_label.setAlignment(Qt.AlignCenter)
            self.content_layout.addWidget(error_label)

    def toggle_selection(self, label):
        """切换选择状态"""
        is_selected = label.property("selected")
        if is_selected:
            label.setText("☐")
            label.setStyleSheet("font-size: 20px; color: #666;")
            label.setProperty("selected", False)
        else:
            label.setText("☑")
            label.setStyleSheet("font-size: 20px; color: #e74c3c;")
            label.setProperty("selected", True)

    def select_all_files(self):
        """全选所有文件"""
        for container_info in self.image_containers:
            label = container_info['indicator']
            if not label.property("selected"):
                label.setText("☑")
                label.setStyleSheet("font-size: 20px; color: #e74c3c;")
                label.setProperty("selected", True)

    def deselect_all_files(self):
        """取消全选所有文件"""
        for container_info in self.image_containers:
            label = container_info['indicator']
            if label.property("selected"):
                label.setText("☐")
                label.setStyleSheet("font-size: 20px; color: #666;")
                label.setProperty("selected", False)

    def get_selected_files(self):
        """获取选中的文件路径列表"""
        selected_files = []
        for container_info in self.image_containers:
            if container_info['indicator'].property("selected"):
                selected_files.append(container_info['file_path'])
        return selected_files

    def delete_selected_files(self):
        """删除选中的PNG文件"""
        selected_files = self.get_selected_files()

        if not selected_files:
            QMessageBox.information(self, "提示", "请先选择要删除的PNG文件")
            return

        # 确认删除操作
        file_names = [os.path.basename(f) for f in selected_files]
        file_list = "\n".join(file_names[:10])
        if len(file_names) > 10:
            file_list += f"\n... 和其他 {len(file_names) - 10} 个文件"

        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除以下 {len(file_names)} 个PNG文件吗？此操作不可撤销。\n\n{file_list}",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        # 执行删除操作
        deleted_count = 0
        failed_files = []
        for file_path in selected_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")

        # 刷新列表显示
        self.refresh_png_list()

        # 显示结果
        if failed_files:
            QMessageBox.warning(self, "部分失败",
                                f"成功删除 {deleted_count} 个文件\n\n删除失败的文件:\n" + "\n".join(failed_files))
        else:
            QMessageBox.information(self, "成功", f"已成功删除 {deleted_count} 个PNG文件")

    def delete_all_files(self):
        """删除所有PNG文件"""
        all_files = [container_info['file_path'] for container_info in self.image_containers]

        total_count = len(all_files)

        if total_count == 0:
            QMessageBox.information(self, "提示", "没有PNG文件可删除")
            return

        # 确认删除操作
        reply = QMessageBox.question(self, "确认删除",
                                     f"确定要删除所有 {total_count} 个PNG文件吗？此操作不可撤销。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        # 执行删除操作
        deleted_count = 0
        failed_files = []
        for file_path in all_files:
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    deleted_count += 1
            except Exception as e:
                failed_files.append(f"{os.path.basename(file_path)}: {str(e)}")

        # 刷新列表显示
        self.refresh_png_list()

        # 显示结果
        if failed_files:
            QMessageBox.warning(self, "部分失败",
                                f"成功删除 {deleted_count} 个文件\n\n删除失败的文件:\n" + "\n".join(failed_files))
        else:
            QMessageBox.information(self, "成功", f"已成功删除 {deleted_count} 个PNG文件")


class PredictionHistoryDialog(QDialog):
    """预测历史记录窗口"""
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("预测历史记录")
        self.resize(850, 600)

        # 居中显示
        self.center_window()

        self.init_ui()

    def center_window(self):
        """居中显示窗口"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        title_label = QLabel("预测历史记录")
        title_font = QFont("Microsoft YaHei", 16, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 创建标签页
        self.tab_widget = QTabWidget()

        # 按用户分组历史记录
        user_histories = {}
        all_history = []

        for record in self.app.prediction_history:
            all_history.append(record)
            username = record.get("username", "guest")
            if username not in user_histories:
                user_histories[username] = []
            user_histories[username].append(record)

        # 创建总的历史记录标签页
        all_history_tab = QWidget()
        all_history_layout = QVBoxLayout(all_history_tab)

        all_table = QTableWidget()
        all_table.setColumnCount(6)
        all_table.setHorizontalHeaderLabels(["时间", "文件名", "折射率", "置信度", "模型", "用户"])
        all_table.setSelectionMode(QAbstractItemView.ExtendedSelection)  # 允许多选
        all_table.setSelectionBehavior(QAbstractItemView.SelectRows)  # 选择整行

        # 设置列宽
        all_table.setColumnWidth(0, 150)
        all_table.setColumnWidth(1, 150)
        all_table.setColumnWidth(2, 100)
        all_table.setColumnWidth(3, 100)
        all_table.setColumnWidth(4, 150)
        all_table.setColumnWidth(5, 100)

        # 设置表格属性
        all_table.setEditTriggers(QTableWidget.NoEditTriggers)
        all_table.setSelectionBehavior(QTableWidget.SelectRows)
        all_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 填充总的历史记录数据
        self.populate_table_with_users(all_table, all_history)
        all_history_layout.addWidget(all_table)

        self.tab_widget.addTab(all_history_tab, "所有记录")

        # 为每个用户创建标签页
        self.user_tables = {}
        for username, history in user_histories.items():
            user_tab = QWidget()
            user_layout = QVBoxLayout(user_tab)

            user_table = QTableWidget()
            user_table.setColumnCount(5)
            user_table.setHorizontalHeaderLabels(["时间", "文件名", "折射率", "置信度", "模型"])
            user_table.setSelectionMode(QAbstractItemView.ExtendedSelection)
            user_table.setSelectionBehavior(QAbstractItemView.SelectRows)

            # 设置列宽
            user_table.setColumnWidth(0, 150)
            user_table.setColumnWidth(1, 200)
            user_table.setColumnWidth(2, 100)
            user_table.setColumnWidth(3, 100)
            user_table.setColumnWidth(4, 200)

            # 设置表格属性
            user_table.setEditTriggers(QTableWidget.NoEditTriggers)
            user_table.setSelectionBehavior(QTableWidget.SelectRows)
            user_table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

            # 填充用户历史记录数据
            self.populate_table(user_table, history)
            user_layout.addWidget(user_table)

            # 保存用户表格引用
            self.user_tables[username] = user_table

            self.tab_widget.addTab(user_tab, f"用户: {username}")

        layout.addWidget(self.tab_widget)

        # 添加按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        # 删除选中记录按钮
        delete_btn = QPushButton("删除选中记录")
        delete_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #e74c3c;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #c0392b;
                    }
                    QPushButton:pressed {
                        background-color: #a93226;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        delete_btn.clicked.connect(self.delete_selected_records)
        button_layout.addWidget(delete_btn)

        # 删除预测图片按钮
        delete_png_btn = QPushButton("删除预测图片")
        delete_png_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #f39c12;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #d35400;
                    }
                    QPushButton:pressed {
                        background-color: #ba4a00;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        delete_png_btn.clicked.connect(self.show_delete_png_dialog)
        button_layout.addWidget(delete_png_btn)

        export_btn = QPushButton("导出历史")
        export_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #3498db;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #2980b9;
                    }
                    QPushButton:pressed {
                        background-color: #21618c;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        export_btn.clicked.connect(self.export_history)
        button_layout.addWidget(export_btn)

        close_btn = QPushButton("关闭")
        close_btn.setStyleSheet("""
                    QPushButton {
                        background-color: #95a5a6;
                        color: white;
                        font-weight: bold;
                        border: none;
                        padding: 8px 16px;
                        border-radius: 4px;
                    }
                    QPushButton:hover {
                        background-color: #7f8c8d;
                    }
                    QPushButton:pressed {
                        background-color: #6c757d;
                        padding: 9px 15px 7px 17px;
                    }
                """)
        close_btn.clicked.connect(self.close)
        button_layout.addWidget(close_btn)

        layout.addLayout(button_layout)

    def show_delete_png_dialog(self):
        """显示删除PNG文件对话框"""
        dialog = DeletePNGFilesDialog(self)
        dialog.exec()

    def populate_table(self, table, history):
        """填充表格数据"""
        table.setRowCount(len(history))
        for i, record in enumerate(history):
            table.setItem(i, 0, QTableWidgetItem(record["timestamp"]))
            table.setItem(i, 1, QTableWidgetItem(os.path.basename(record["filename"])))
            table.setItem(i, 2, QTableWidgetItem(f"{record['prediction']:.4f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{record['confidence'] * 100:.1f}"))
            table.setItem(i, 4, QTableWidgetItem(record["model"]))

        # 设置单元格对齐方式
        for i in range(table.rowCount()):
            # 时间列居中
            item = table.item(i, 0)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 文件名列左对齐
            item = table.item(i, 1)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # 折射率列居中
            item = table.item(i, 2)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 置信度列居中
            item = table.item(i, 3)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 模型列左对齐
            item = table.item(i, 4)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def populate_table_with_users(self, table, history):
        """填充表格数据"""
        table.setRowCount(len(history))
        for i, record in enumerate(history):
            table.setItem(i, 0, QTableWidgetItem(record["timestamp"]))
            table.setItem(i, 1, QTableWidgetItem(os.path.basename(record["filename"])))
            table.setItem(i, 2, QTableWidgetItem(f"{record['prediction']:.4f}"))
            table.setItem(i, 3, QTableWidgetItem(f"{record['confidence'] * 100:.1f}"))
            table.setItem(i, 4, QTableWidgetItem(record["model"]))
            table.setItem(i, 5, QTableWidgetItem(record.get("username", "guest")))

        # 设置单元格对齐方式
        for i in range(table.rowCount()):
            # 时间列居中
            item = table.item(i, 0)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 文件名列左对齐
            item = table.item(i, 1)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # 折射率列居中
            item = table.item(i, 2)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 置信度列居中
            item = table.item(i, 3)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 模型列左对齐
            item = table.item(i, 4)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # 用户名列左对齐
            item = table.item(i, 5)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def delete_selected_records(self):
        """删除选中的记录"""
        current_tab_index = self.tab_widget.currentIndex()
        current_tab_text = self.tab_widget.tabText(current_tab_index)

        # 确认删除操作
        reply = QMessageBox.question(self, "确认删除", "确定要删除选中的记录吗？此操作不可撤销。",
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        if reply == QMessageBox.No:
            return

        # 获取当前选中的表格
        if current_tab_text == "所有记录":
            # 处理总记录表格
            table = self.tab_widget.widget(current_tab_index).findChildren(QTableWidget)[0]
            selected_rows = sorted(set(index.row() for index in table.selectionModel().selectedRows()), reverse=True)

            if not selected_rows:
                QMessageBox.information(self, "提示", "请先选择要删除的记录")
                return

            # 获取要删除的记录索引
            indices_to_delete = []
            for row in selected_rows:
                # 在所有历史记录中查找匹配的记录
                record_timestamp = table.item(row, 0).text()
                record_filename = table.item(row, 1).text()

                for i, record in enumerate(self.app.prediction_history):
                    if record["timestamp"] == record_timestamp and os.path.basename(
                            record["filename"]) == record_filename:
                        indices_to_delete.append(i)
                        break

            # 调用历史记录管理器删除记录
            self.app.history_manager.delete_history_records(indices_to_delete)

            # 重新加载界面
            self.refresh_tables()
            QMessageBox.information(self, "成功", f"已删除 {len(selected_rows)} 条记录")
        else:
            # 处理用户特定记录表格
            username = current_tab_text.replace("用户: ", "")
            if username in self.user_tables:
                table = self.user_tables[username]
                selected_rows = sorted(set(index.row() for index in table.selectionModel().selectedRows()),
                                       reverse=True)

                if not selected_rows:
                    QMessageBox.information(self, "提示", "请先选择要删除的记录")
                    return

                # 获取要删除的记录索引
                indices_to_delete = []
                for row in selected_rows:
                    record_timestamp = table.item(row, 0).text()
                    record_filename = table.item(row, 1).text()

                    for i, record in enumerate(self.app.prediction_history):
                        if (record["timestamp"] == record_timestamp and
                                os.path.basename(record["filename"]) == record_filename and
                                record.get("username", "guest") == username):
                            indices_to_delete.append(i)
                            break

                # 调用历史记录管理器删除记录
                self.app.history_manager.delete_history_records(indices_to_delete)

                # 重新加载界面
                self.refresh_tables()
                QMessageBox.information(self, "成功", f"已删除 {len(selected_rows)} 条记录")
            else:
                QMessageBox.warning(self, "错误", "无法找到对应的用户记录")

    def refresh_tables(self):
        """刷新所有表格"""
        # 清空现有表格
        for i in range(self.tab_widget.count()):
            tab_widget = self.tab_widget.widget(i)
            table = tab_widget.findChildren(QTableWidget)[0]
            table.clearContents()
            table.setRowCount(0)

        user_histories = {}
        all_history = []

        for record in self.app.prediction_history:
            all_history.append(record)
            username = record.get("username", "guest")
            if username not in user_histories:
                user_histories[username] = []
            user_histories[username].append(record)

        # 更新总的历史记录标签页
        all_table = self.tab_widget.widget(0).findChildren(QTableWidget)[0]
        self.populate_table_with_users(all_table, all_history)

        # 更新用户标签页
        self.user_tables.clear()
        for i in range(1, self.tab_widget.count()):
            tab_text = self.tab_widget.tabText(i)
            if tab_text.startswith("用户: "):
                username = tab_text.replace("用户: ", "")
                if username in user_histories:
                    user_tab = self.tab_widget.widget(i)
                    user_table = user_tab.findChildren(QTableWidget)[0]
                    self.populate_table(user_table, user_histories[username])
                    self.user_tables[username] = user_table

    def export_history(self):
        """导出历史记录"""
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出历史记录",
            "prediction_history.csv",
            "CSV files (*.csv)"
        )

        if save_path:
            try:
                # 使用UTF-8编码保存，确保中文字符正确处理
                with open(save_path, 'w', newline='', encoding='utf-8-sig') as f:
                    writer = csv.writer(f)
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称", "用户名"])
                    for record in self.app.prediction_history:
                        writer.writerow([
                            record["timestamp"],
                            record["filename"],
                            record["prediction"],
                            record["confidence"],
                            record["model"],
                            record.get("username", "guest")
                        ])
                QMessageBox.information(self, "成功", f"历史记录已导出至:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
