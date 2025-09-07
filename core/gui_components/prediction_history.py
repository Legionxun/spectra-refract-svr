# core/gui_components/prediction_history.py
import csv, os, logging, datetime
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QFileDialog, QMessageBox, QApplication
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont

from ..config import CONFIG


class PredictionHistoryManager:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("PredictionHistoryManager")

    def save_prediction_to_history(self, filename, prediction, confidence, model_name):
        """保存预测结果到历史记录"""
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.app.prediction_history.append({
            "timestamp": timestamp,
            "filename": filename,
            "prediction": prediction,
            "confidence": confidence,
            "model": model_name
        })

        # 保存到文件
        history_path = os.path.join(CONFIG["history_dir"], "prediction_history.csv")
        try:
            with open(history_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)

                # 如果文件为空，写入标题
                if os.stat(history_path).st_size == 0:
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称"])
                writer.writerow([timestamp, os.path.basename(filename), prediction, confidence, model_name])
        except Exception as e:
            print(f"保存预测历史记录失败: {str(e)}")
            self.logger.error(f"保存预测历史记录失败: {str(e)}")

    def load_prediction_history(self):
        """加载预测历史记录"""
        history_path = os.path.join(CONFIG["history_dir"], "prediction_history.csv")
        if os.path.exists(history_path):
            encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
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
                            if len(row) >= 5:
                                self.app.prediction_history.append({
                                    "timestamp": row[0],
                                    "filename": row[1],
                                    "prediction": float(row[2]),
                                    "confidence": float(row[3]),
                                    "model": row[4]
                                })
                    print(f"已加载 {len(self.app.prediction_history)} 条历史记录 (编码: {used_encoding})")
                except Exception as e:
                    print(f"解析历史记录失败: {str(e)}")
                    self.logger.error(f"解析历史记录失败: {str(e)}")
        else:
            print("未找到历史记录文件")

    def show_prediction_history(self):
        """显示预测历史记录"""
        if not self.app.prediction_history:
            QMessageBox.information(self.app, "提示", "暂无预测历史记录")
            return

        # 创建历史记录窗口
        dialog = PredictionHistoryDialog(self.app)
        dialog.exec()


class PredictionHistoryDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.setWindowTitle("预测历史记录")
        self.resize(800, 600)

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

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["时间", "文件名", "折射率", "置信度", "模型"])

        # 设置列宽
        self.table.setColumnWidth(0, 150)
        self.table.setColumnWidth(1, 200)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 200)

        # 设置表格属性
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        # 填充数据
        self.populate_table()

        layout.addWidget(self.table)

        # 添加按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

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

    def populate_table(self):
        """填充表格数据"""
        self.table.setRowCount(len(self.app.prediction_history))
        for i, record in enumerate(self.app.prediction_history):
            self.table.setItem(i, 0, QTableWidgetItem(record["timestamp"]))
            self.table.setItem(i, 1, QTableWidgetItem(os.path.basename(record["filename"])))
            self.table.setItem(i, 2, QTableWidgetItem(f"{record['prediction']:.4f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{record['confidence'] * 100:.1f}"))
            self.table.setItem(i, 4, QTableWidgetItem(record["model"]))

        # 设置单元格对齐方式
        for i in range(self.table.rowCount()):
            # 时间列居中
            item = self.table.item(i, 0)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 文件名列左对齐
            item = self.table.item(i, 1)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

            # 折射率列居中
            item = self.table.item(i, 2)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 置信度列居中
            item = self.table.item(i, 3)
            if item:
                item.setTextAlignment(Qt.AlignCenter)

            # 模型列左对齐
            item = self.table.item(i, 4)
            if item:
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

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
                with open(save_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerow(["时间戳", "文件名", "预测折射率", "置信度", "模型名称"])
                    for record in self.app.prediction_history:
                        writer.writerow([
                            record["timestamp"],
                            record["filename"],
                            record["prediction"],
                            record["confidence"],
                            record["model"]
                        ])
                QMessageBox.information(self, "成功", f"历史记录已导出至:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")
