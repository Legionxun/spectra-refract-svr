# core/gui_components/model_comparison.py
import os, logging, traceback, csv, json, math
from threading import Thread
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTableWidget, QTableWidgetItem,
    QHeaderView, QPushButton, QTabWidget, QFileDialog, QMessageBox,
    QApplication, QWidget, QScrollArea, QToolBar
)
from PySide6.QtCore import Qt, QTimer, Signal, QObject, QPoint
from PySide6.QtGui import QFont, QPixmap, QAction, QMouseEvent
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from ..config import CONFIG
from ..predictor import RefractiveIndexPredictor
from .progress_dialogs import AnimatedProgressBar, ModelLoadingProgress

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False


class ModelEvaluationWorker(QObject):
    """模型评估工作线程"""
    progress_updated = Signal(int, str)  # 进度值, 描述文本
    evaluation_finished = Signal(list)  # 评估结果数据
    evaluation_stopped = Signal()
    error_occurred = Signal(str)  # 错误信息
    model_evaluated = Signal(dict)  # 单个模型评估完成信号
    def __init__(self, app, models_list, template_images):
        super().__init__()
        self.app = app
        self.models_list = models_list
        self.template_images = template_images
        self.stop_flag = False

    def stop_evaluation(self):
        """停止评估"""
        self.stop_flag = True

    def run_evaluation(self, force_recalculate=False):
        """运行模型评估"""
        try:
            model_data = []
            total_models = len(self.models_list)

            # 检查是否需要停止
            if self.stop_flag:
                self.evaluation_stopped.emit()
                return

            # 检查是否已存在模型比较结果文件且不需要强制重新计算
            comparison_csv_path = os.path.join(CONFIG["history_dir"], "model_comparison_results.csv")
            if not force_recalculate and os.path.exists(comparison_csv_path):
                self.progress_updated.emit(100, "已存在模型比较结果")
                try:
                    # 尝试从已有的CSV文件加载数据
                    df = pd.read_csv(comparison_csv_path)
                    if len(df) >= len(self.models_list):
                        for _, row in df.iterrows():
                            # 检查是否需要停止
                            if self.stop_flag:
                                self.evaluation_stopped.emit()
                                return

                            model_result = {
                                "name": row["模型名称"],
                                "training_time": row.get("训练时长(s)", 0),
                                "mae": row["MAE"],
                                "rmse": row["RMSE"],
                                "median_ae": row.get("MedAE", 0),
                                "sse": row.get("SSE", 0),
                                "r2": row.get("R²", 0),
                                "accuracy": row.get("准确度(±0.001)(%)", 0),
                                "model_size": row.get("模型大小(MB)", 0)
                            }
                            model_data.append(model_result)
                            self.model_evaluated.emit(model_result)
                        self.evaluation_finished.emit(model_data)
                        return
                except Exception as e:
                    print(f"加载现有评估数据失败: {str(e)}")

            # 用于存储所有模型的预测结果
            actual_values = []
            # 首先解析所有图片的实际值（只做一次）
            for img_path in self.template_images:
                # 检查是否需要停止
                if self.stop_flag:
                    self.evaluation_stopped.emit()
                    return

                # 从文件名中提取实际折射率值
                filename = os.path.basename(img_path)
                try:
                    name_str = filename.split('_')[1]
                    actual_rn = float(name_str.split('.')[0]) + float(name_str.split('.')[1]) * round(math.pow(0.1, len(name_str.split('.')[1])), len(name_str.split('.')[1]))
                    actual_values.append(actual_rn)
                except Exception as e:
                    print(f"解析文件名失败: {filename}, 错误: {str(e)}")
                    actual_values.append(0)
            actual_values = np.array(actual_values)

            # 定义准确度计算的±
            ACCURACY_THRESHOLD = 0.001

            # 计算总的进度单位
            total_units = total_models * (2 + len(self.template_images))  # 2表示加载和计算步骤，每个模板图像一个步骤
            completed_units = 0

            for i, model_info in enumerate(self.models_list):
                # 检查是否需要停止
                if self.stop_flag:
                    self.evaluation_stopped.emit()
                    return

                # 更新进度
                progress = int((completed_units / total_units) * 100)
                self.progress_updated.emit(progress, f"正在加载模型: {model_info['name']} ({i + 1}/{total_models})")

                # 加载模型性能数据
                metrics_path = os.path.join(model_info["path"], "metrics.json")
                metrics = {}
                # 如果存在metrics.json文件，先加载它
                if os.path.exists(metrics_path):
                    try:
                        with open(metrics_path, 'r') as f:
                            metrics = json.load(f)
                    except Exception as e:
                        print(f"加载模型 {model_info['name']} 的指标失败: {str(e)}")

                completed_units += 1
                progress = int((completed_units / total_units) * 100)
                self.progress_updated.emit(progress, f"加载模型 {model_info['name']} 完成")

                # 使用template图片评估模型
                try:
                    # 检查是否需要停止
                    if self.stop_flag:
                        self.evaluation_stopped.emit()
                        return

                    predictor = RefractiveIndexPredictor(model_info["path"])
                    # 存储该模型对所有图片的预测结果
                    predictions = []
                    # 对每张图片进行预测
                    for j, img_path in enumerate(self.template_images):
                        # 检查是否需要停止
                        if self.stop_flag:
                            predictor.close_browser()
                            self.evaluation_stopped.emit()
                            return

                        # 更新进度
                        completed_units += 1
                        progress = int((completed_units / total_units) * 100)
                        self.progress_updated.emit(progress,
                                                   f"模型 {model_info['name']} 正在预测第 {j + 1}/{len(self.template_images)} 张图片")

                        # 使用模型预测
                        predicted_rn = predictor.predict(img_path)
                        if predicted_rn is not None:
                            predictions.append(predicted_rn)
                        else:
                            predictions.append(actual_values[j] if j < len(actual_values) else 0)
                            print(f"警告: 模型 {model_info['name']} 对 {img_path} 预测失败")

                    # 如果评估被停止，跳出循环
                    if self.stop_flag:
                        predictor.close_browser()
                        self.evaluation_stopped.emit()
                        return

                    # 更新进度
                    completed_units += 1
                    progress = int((completed_units / total_units) * 100)
                    self.progress_updated.emit(progress, f"正在计算 {model_info['name']} 的评估指标")

                    # 计算评估指标
                    predictions = np.array(predictions)
                    # 确保数组长度一致
                    if len(predictions) != len(actual_values):
                        # 如果长度不一致，截取较短的长度
                        min_len = min(len(predictions), len(actual_values))
                        predictions = predictions[:min_len]
                        actual_values_subset = actual_values[:min_len]
                        print(f"警告: 预测值和实际值长度不一致，已截取为{min_len}")
                    else:
                        actual_values_subset = actual_values

                    # 计算各种评估指标
                    mae = np.mean(np.abs(predictions - actual_values_subset))  # 平均绝对误差
                    rmse = np.sqrt(np.mean((predictions - actual_values_subset) ** 2))  # 均方根误差
                    median_ae = np.median(np.abs(predictions - actual_values_subset))  # 中位数绝对误差
                    # 计算SSE (残差平方和)
                    sse = np.sum((actual_values_subset - predictions) ** 2)
                    # 计算SST (总平方和)
                    sst = np.sum((actual_values_subset - np.mean(actual_values_subset)) ** 2)
                    # 计算R² (决定系数)
                    r2 = 1 - (sse / sst) if sst != 0 else 0
                    # 计算绝对误差百分比
                    abs_error_percentage = np.abs((predictions - actual_values_subset) / actual_values_subset)
                    # 统计在±内的样本数
                    correct_count = np.sum(abs_error_percentage <= ACCURACY_THRESHOLD)
                    # 计算准确度百分比
                    accuracy = (correct_count / len(actual_values_subset)) * 100
                    # 获取模型文件大小
                    model_file_path = os.path.join(model_info["path"], "models", CONFIG["save_model"])
                    model_size = os.path.getsize(model_file_path) / (1024 * 1024) if os.path.exists(
                        model_file_path) else 0  # MB
                    # 获取训练时长
                    training_time = predictor.training_time

                    # 更新指标
                    metrics["mae"] = float(mae)
                    metrics["rmse"] = float(rmse)
                    metrics["median_ae"] = float(median_ae)
                    metrics["sse"] = float(sse)
                    metrics["r2"] = float(r2)
                    metrics["accuracy"] = float(accuracy)
                    metrics["model_size"] = float(model_size)
                    metrics["training_time"] = float(training_time)

                    # 保存更新后的指标
                    with open(metrics_path, 'w') as f:
                        json.dump(metrics, f, indent=2)

                    # 关闭预测器
                    predictor.close_browser()

                    # 添加调试信息
                    print(f"模型 {model_info['name']} 评估结果:")
                    print(f"  预测值范围: {np.min(predictions):.4f} - {np.max(predictions):.4f}")
                    print(f"  实际值范围: {np.min(actual_values_subset):.4f} - {np.max(actual_values_subset):.4f}")
                    print(f"  MAE: {mae:.4f}, RMSE: {rmse:.4f}")
                    print(f"  SSE: {sse:.4f}, R²: {r2:.4f}")
                    print(f"  准确度(±0.001): {accuracy:.2f}%")
                    print(f"  训练时长: {training_time:.2f}s")

                except Exception as e:
                    print(f"评估模型 {model_info['name']} 失败: {str(e)}")
                    traceback.print_exc()
                    # 使用默认值或从metrics.json中读取的值
                    if "mae" not in metrics:
                        metrics["mae"] = 0
                    if "rmse" not in metrics:
                        metrics["rmse"] = 0
                    if "median_ae" not in metrics:
                        metrics["median_ae"] = 0
                    if "sse" not in metrics:
                        metrics["sse"] = 0
                    if "r2" not in metrics:
                        metrics["r2"] = 0
                    if "accuracy" not in metrics:
                        metrics["accuracy"] = 0
                    if "model_size" not in metrics:
                        metrics["model_size"] = 0
                    if "training_time" not in metrics:
                        metrics["training_time"] = 0

                # 保存数据用于绘图
                model_result = {
                    "name": model_info["name"],
                    "training_time": metrics.get("training_time", 0),
                    "mae": metrics.get("mae", 0),
                    "rmse": metrics.get("rmse", 0),
                    "median_ae": metrics.get("median_ae", 0),
                    "sse": metrics.get("sse", 0),
                    "r2": metrics.get("r2", 0),
                    "accuracy": metrics.get("accuracy", 0),
                    "model_size": metrics.get("model_size", 0)
                }
                model_data.append(model_result)

                # 发送单个模型评估完成信号
                self.model_evaluated.emit(model_result)

            # 如果评估被停止，不发送完成信号
            if self.stop_flag:
                self.evaluation_stopped.emit()
                return

            self.progress_updated.emit(100, "评估完成")
            self.evaluation_finished.emit(model_data)

        except Exception as e:
            if not self.stop_flag:  # 只有在非主动停止的情况下才发送错误信号
                self.error_occurred.emit(f"模型评估过程中发生错误: {str(e)}")
                traceback.print_exc()


class DraggableScrollArea(QScrollArea):
    """可拖拽的滚动区域"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_position = QPoint()
        self.setDragMode()

    def setDragMode(self):
        """设置拖拽模式"""
        self.setMouseTracking(True)
        self.viewport().setCursor(Qt.OpenHandCursor)
        self.setWidgetResizable(False)  # 保持原始尺寸

    def mousePressEvent(self, event: QMouseEvent):
        """鼠标按下事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint()
            self.viewport().setCursor(Qt.ClosedHandCursor)
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent):
        """鼠标移动事件"""
        if event.buttons() & Qt.LeftButton and not self.drag_position.isNull():
            # 计算鼠标移动的偏移量
            delta = event.globalPosition().toPoint() - self.drag_position

            # 更新滚动条位置
            h_bar = self.horizontalScrollBar()
            v_bar = self.verticalScrollBar()
            h_bar.setValue(h_bar.value() - delta.x())
            v_bar.setValue(v_bar.value() - delta.y())

            # 更新拖拽起始位置
            self.drag_position = event.globalPosition().toPoint()
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent):
        """鼠标释放事件"""
        if event.button() == Qt.LeftButton:
            self.drag_position = QPoint()
            self.viewport().setCursor(Qt.OpenHandCursor)
            event.accept()
        else:
            super().mouseReleaseEvent(event)

class ScrollableFigureCanvas(FigureCanvas):
    """可滚动的图表画布，支持拖拽"""
    def __init__(self, figure, parent=None):
        super().__init__(figure)
        self.parent_scroll_area = parent
        self.setParent(parent)
        self.setMouseTracking(True)

    def mousePressEvent(self, event):
        """重写鼠标按下事件，传递给父滚动区域"""
        if self.parent_scroll_area and event.button() == Qt.LeftButton:
            self.parent_scroll_area.mousePressEvent(event)
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """重写鼠标移动事件，传递给父滚动区域"""
        if self.parent_scroll_area and event.buttons() & Qt.LeftButton:
            self.parent_scroll_area.mouseMoveEvent(event)
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """重写鼠标释放事件，传递给父滚动区域"""
        if self.parent_scroll_area and event.button() == Qt.LeftButton:
            self.parent_scroll_area.mouseReleaseEvent(event)
        else:
            super().mouseReleaseEvent(event)


class ModelComparisonDialog(QDialog):
    """模型性能比较对话框"""
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.logger = logging.getLogger("ModelComparator")
        self.model_data = []
        self.setWindowTitle("模型性能比较")
        self.resize(1050, 600)
        self.setMinimumSize(800, 400)

        # 设置窗口图标
        self.setWindowIcon(QPixmap(CONFIG["icon"]))

        # 居中显示
        self.center_window()

        self.init_ui()
        self.setup_worker()

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
        title_label = QLabel("模型性能比较")
        title_font = QFont("Microsoft YaHei", 16, QFont.Bold)
        title_label.setFont(title_font)
        layout.addWidget(title_label)

        # 创建选项卡
        self.tab_widget = QTabWidget()
        layout.addWidget(self.tab_widget)

        # 表格比较选项卡
        self.table_widget = self.create_table_tab()
        self.tab_widget.addTab(self.table_widget, "表格比较")

        # 图表比较选项卡
        self.plot_widget = self.create_plot_tab()
        self.tab_widget.addTab(self.plot_widget, "图表比较")

        # 雷达图比较选项卡
        self.radar_widget = self.create_radar_tab()
        self.tab_widget.addTab(self.radar_widget, "雷达图比较")

        # 综合评分选项卡
        self.score_widget = self.create_score_tab()
        self.tab_widget.addTab(self.score_widget, "综合评分")

        # 进度条
        self.progress_widget = self.create_progress_widget()
        layout.addWidget(self.progress_widget)

        # 按钮区域
        self.button_widget = self.create_button_widget()
        layout.addWidget(self.button_widget)

    def create_table_tab(self):
        """创建表格选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)

        # 创建表格
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE", "R²", "准确度(±0.001)(%)", "模型大小(MB)"
        ])

        # 设置列宽
        self.table.setColumnWidth(0, 150)  # 模型名称
        self.table.setColumnWidth(1, 100)  # 训练时长
        self.table.setColumnWidth(2, 100)  # MAE
        self.table.setColumnWidth(3, 100)  # RMSE
        self.table.setColumnWidth(4, 100)  # MedAE
        self.table.setColumnWidth(5, 100)  # SSE
        self.table.setColumnWidth(6, 100)  # R²
        self.table.setColumnWidth(7, 120)  # 准确度
        self.table.setColumnWidth(8, 100)  # 模型大小

        # 设置表格属性
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Interactive)

        layout.addWidget(self.table)
        return widget

    def create_plot_tab(self):
        """创建图表选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.plot_layout = layout
        return widget

    def create_radar_tab(self):
        """创建雷达图选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.radar_layout = layout
        return widget

    def create_score_tab(self):
        """创建综合评分选项卡"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        self.score_layout = layout
        return widget

    def create_progress_widget(self):
        """创建进度条组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        self.progress_label = QLabel("准备评估模型...")
        layout.addWidget(self.progress_label)

        self.progress_bar = AnimatedProgressBar()
        self.progress_bar.setRange(0, 100)
        layout.addWidget(self.progress_bar)

        self.stop_btn = QPushButton("停止评估")
        self.stop_btn.setStyleSheet("""
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
                padding: 10px 14px;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_evaluation)
        layout.addWidget(self.stop_btn)

        return widget

    def create_button_widget(self):
        """创建按钮组件"""
        widget = QWidget()
        layout = QHBoxLayout(widget)

        # 最佳模型标签
        self.best_model_label = QLabel("暂无最佳模型推荐")
        self.best_model_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.best_model_label.setStyleSheet("color: red;")
        layout.addWidget(self.best_model_label)

        # 按钮容器
        button_container = QWidget()
        button_layout = QHBoxLayout(button_container)

        self.load_best_btn = QPushButton("加载最佳模型")
        self.load_best_btn.setStyleSheet("""
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
                padding: 10px 14px;
            }
        """)
        self.load_best_btn.clicked.connect(self.load_best_model)
        button_layout.addWidget(self.load_best_btn)

        self.reevaluate_btn = QPushButton("重新评估")
        self.reevaluate_btn.setStyleSheet("""
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
                padding: 10px 14px;
            }
        """)
        self.reevaluate_btn.clicked.connect(self.reevaluate_models)
        button_layout.addWidget(self.reevaluate_btn)

        self.export_btn = QPushButton("导出比较结果")
        self.export_btn.setStyleSheet("""
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
                padding: 10px 14px;
            }
        """)
        self.export_btn.clicked.connect(self.export_comparison)
        button_layout.addWidget(self.export_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setStyleSheet("""
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
                background-color: #6c7a7b;
                padding: 10px 14px;
            }
        """)
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addWidget(button_container, alignment=Qt.AlignRight)

        return widget

    def setup_worker(self):
        """设置工作线程"""
        self.worker = None
        self.worker_thread = None

    def start_evaluation(self, force_recalculate=False):
        """开始评估"""
        if len(self.app.models_list) < 2:
            QMessageBox.information(self, "提示", "至少需要两个模型才能进行比较")
            return

        # 检查template文件夹中是否有理论数据图片
        template_dir = os.path.join(CONFIG["base_dir"], "template")
        if not os.path.exists(template_dir):
            QMessageBox.warning(self, "警告", "未找到template文件夹，请先生成理论数据")
            return

        # 查找template文件夹中的图片文件
        template_images = []
        for file in os.listdir(template_dir):
            if file.lower().endswith(('.png', '.jpg', '.jpeg')):
                template_images.append(os.path.join(template_dir, file))
        if not template_images:
            QMessageBox.warning(self, "警告", "template文件夹中没有找到图片文件，请先生成理论数据")
            return

        # 重置停止标志
        self.app.stop_evaluation_flag = False

        # 清空现有数据和表格
        self.model_data.clear()
        self.table.setRowCount(0)

        # 清空图表显示区域
        self.clear_layout(self.plot_layout)
        self.clear_layout(self.radar_layout)
        self.clear_layout(self.score_layout)

        # 创建并启动工作线程
        self.worker = ModelEvaluationWorker(self.app, self.app.models_list, template_images)
        self.worker_thread = Thread(target=lambda: self.worker.run_evaluation(force_recalculate))
        self.worker.progress_updated.connect(self.update_progress)
        self.worker.evaluation_finished.connect(self.on_evaluation_finished)
        self.worker.evaluation_stopped.connect(self.on_evaluation_stopped)
        self.worker.error_occurred.connect(self.on_error)
        # 连接单个模型评估完成信号
        self.worker.model_evaluated.connect(self.on_model_evaluated)

        self.worker_thread.start()

    def update_progress(self, value, text):
        """更新进度"""
        self.progress_bar.setValue(value)
        self.progress_label.setText(text)

    def on_model_evaluated(self, model_result):
        """单个模型评估完成"""
        # 添加到模型数据列表
        self.model_data.append(model_result)

        # 在表格中添加一行
        row_count = self.table.rowCount()
        self.table.insertRow(row_count)

        # 填充数据
        self.table.setItem(row_count, 0, QTableWidgetItem(model_result["name"]))
        self.table.setItem(row_count, 1, QTableWidgetItem(f"{model_result['training_time']:.2f}"))
        self.table.setItem(row_count, 2, QTableWidgetItem(f"{model_result['mae']:.4f}"))
        self.table.setItem(row_count, 3, QTableWidgetItem(f"{model_result['rmse']:.4f}"))
        self.table.setItem(row_count, 4, QTableWidgetItem(f"{model_result['median_ae']:.4f}"))
        self.table.setItem(row_count, 5, QTableWidgetItem(f"{model_result['sse']:.4f}"))
        self.table.setItem(row_count, 6, QTableWidgetItem(f"{model_result['r2']:.4f}"))
        self.table.setItem(row_count, 7, QTableWidgetItem(f"{model_result['accuracy']:.2f}"))
        self.table.setItem(row_count, 8, QTableWidgetItem(f"{model_result['model_size']:.2f}"))

        # 设置单元格对齐方式
        for j in range(self.table.columnCount()):
            item = self.table.item(row_count, j)
            if item:
                if j in [1, 2, 3, 4, 5, 6, 7, 8]:  # 数值列居中
                    item.setTextAlignment(Qt.AlignCenter)
                else:  # 其他列左对齐
                    item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        # 更新最佳模型显示
        self.update_best_model_label()

    def on_evaluation_finished(self, model_data):
        """评估完成"""
        # 生成图表
        self.generate_charts()
        self.generate_score_chart()

    def on_evaluation_stopped(self):
        """评估停止"""
        self.progress_label.setText("评估已停止")
        QMessageBox.information(self, "提示", "模型评估已停止")

    def on_error(self, error_msg):
        """处理错误"""
        self.progress_label.setText(f"评估出错: {error_msg}")
        QMessageBox.critical(self, "错误", f"模型评估过程中发生错误: {error_msg}")

    def stop_evaluation(self):
        """停止评估"""
        if self.worker:
            self.worker.stop_evaluation()
            self.progress_label.setText("正在停止评估...")
            self.stop_btn.setEnabled(False)

    def populate_table(self):
        """填充表格"""
        self.table.setRowCount(len(self.model_data))
        for i, data in enumerate(self.model_data):
            self.table.setItem(i, 0, QTableWidgetItem(data["name"]))
            self.table.setItem(i, 1, QTableWidgetItem(f"{data['training_time']:.2f}"))
            self.table.setItem(i, 2, QTableWidgetItem(f"{data['mae']:.4f}"))
            self.table.setItem(i, 3, QTableWidgetItem(f"{data['rmse']:.4f}"))
            self.table.setItem(i, 4, QTableWidgetItem(f"{data['median_ae']:.4f}"))
            self.table.setItem(i, 5, QTableWidgetItem(f"{data['sse']:.4f}"))
            self.table.setItem(i, 6, QTableWidgetItem(f"{data['r2']:.4f}"))
            self.table.setItem(i, 7, QTableWidgetItem(f"{data['accuracy']:.2f}"))
            self.table.setItem(i, 8, QTableWidgetItem(f"{data['model_size']:.2f}"))

        # 设置单元格对齐方式
        for i in range(self.table.rowCount()):
            for j in range(self.table.columnCount()):
                item = self.table.item(i, j)
                if item:
                    if j in [1, 2, 3, 4, 5, 6, 7, 8]:  # 数值列居中
                        item.setTextAlignment(Qt.AlignCenter)
                    else:  # 其他列左对齐
                        item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)

    def generate_charts(self):
        """生成图表"""
        if not self.model_data:
            return

        try:
            # 创建图表框架，使用较小的默认尺寸以适应窗口
            fig, axes = plt.subplots(2, 4, figsize=(15, 6))  # 调整为更小的尺寸

            # 训练时长比较图
            names = [d["name"] for d in self.model_data]
            training_time_values = [d["training_time"] for d in self.model_data]
            axes[0, 0].bar(names, training_time_values, color='cyan')
            axes[0, 0].set_title('训练时长', fontsize=10)
            axes[0, 0].set_ylabel('时间 (s)', fontsize=9)
            axes[0, 0].tick_params(axis='x', rotation=45, labelsize=8)

            # MAE 比较图
            mae_values = [d["mae"] for d in self.model_data]
            axes[0, 1].bar(names, mae_values, color='skyblue')
            axes[0, 1].set_title('平均绝对误差 (MAE)', fontsize=10)
            axes[0, 1].set_ylabel('MAE', fontsize=9)
            axes[0, 1].tick_params(axis='x', rotation=45, labelsize=8)

            # RMSE 比较图
            rmse_values = [d["rmse"] for d in self.model_data]
            axes[0, 2].bar(names, rmse_values, color='lightcoral')
            axes[0, 2].set_title('均方根误差 (RMSE)', fontsize=10)
            axes[0, 2].set_ylabel('RMSE', fontsize=9)
            axes[0, 2].tick_params(axis='x', rotation=45, labelsize=8)

            # SSE 比较图
            sse_values = [d["sse"] for d in self.model_data]
            axes[0, 3].bar(names, sse_values, color='lightgreen')
            axes[0, 3].set_title('残差平方和 (SSE)', fontsize=10)
            axes[0, 3].set_ylabel('SSE', fontsize=9)
            axes[0, 3].tick_params(axis='x', rotation=45, labelsize=8)

            # 中位数绝对误差比较图
            median_ae_values = [d["median_ae"] for d in self.model_data]
            axes[1, 0].bar(names, median_ae_values, color='gold')
            axes[1, 0].set_title('中位数绝对误差', fontsize=10)
            axes[1, 0].set_ylabel('MedAE', fontsize=9)
            axes[1, 0].tick_params(axis='x', rotation=45, labelsize=8)

            # R² 比较图
            r2_values = [d["r2"] for d in self.model_data]
            axes[1, 1].bar(names, r2_values, color='purple')
            axes[1, 1].set_title('决定系数 (R²)', fontsize=10)
            axes[1, 1].set_ylabel('R²', fontsize=9)
            axes[1, 1].set_ylim(0, 1)  # R²范围通常在0-1之间
            axes[1, 1].tick_params(axis='x', rotation=45, labelsize=8)

            # 模型大小比较图
            model_size_values = [d["model_size"] for d in self.model_data]
            axes[1, 2].bar(names, model_size_values, color='orange')
            axes[1, 2].set_title('模型大小', fontsize=10)
            axes[1, 2].set_ylabel('大小 (MB)', fontsize=9)
            axes[1, 2].tick_params(axis='x', rotation=45, labelsize=8)

            # 准确度比较图
            accuracy_values = [d["accuracy"] for d in self.model_data]
            axes[1, 3].bar(names, accuracy_values, color='violet')
            axes[1, 3].set_title('预测准确度 (%)', fontsize=10)
            axes[1, 3].set_ylabel('准确度(±0.001)(%)', fontsize=9)
            axes[1, 3].set_ylim(0, 100)
            axes[1, 3].tick_params(axis='x', rotation=45, labelsize=8)

            plt.tight_layout()

            # 显示图表
            self.clear_layout(self.plot_layout)

            # 创建工具栏
            toolbar = self.create_toolbar("plot")
            self.plot_layout.addWidget(toolbar)

            # 创建可滚动的图表区域
            scroll_area = DraggableScrollArea()

            # 创建自定义画布，将滚动区域作为父组件
            self.plot_canvas = ScrollableFigureCanvas(fig, scroll_area)
            scroll_area.setWidget(self.plot_canvas)
            scroll_area.setAlignment(Qt.AlignCenter)  # 居中显示
            scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.plot_layout.addWidget(scroll_area)

            # 保存图表
            plot_path = os.path.join(CONFIG["temp_dir"], "model_comparison.png")
            plt.savefig(plot_path, dpi=100, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"生成模型比较图表失败: {str(e)}")
            traceback.print_exc()
            self.clear_layout(self.plot_layout)
            error_label = QLabel(f"生成图表失败: {str(e)}")
            error_label.setFont(QFont("Microsoft YaHei", 12))
            self.plot_layout.addWidget(error_label)

        # 生成雷达图
        try:
            # 创建雷达图，使用合适的默认尺寸
            fig_radar = plt.figure(figsize=(12, 12))  # 调整为更小的尺寸
            ax_radar = fig_radar.add_subplot(111, projection='polar')

            # 准备数据
            model_names = [d["name"] for d in self.model_data]
            training_time_values = np.array([d["training_time"] for d in self.model_data])
            mae_values = np.array([d["mae"] for d in self.model_data])
            rmse_values = np.array([d["rmse"] for d in self.model_data])
            sse_values = np.array([d["sse"] for d in self.model_data])
            median_ae_values = np.array([d["median_ae"] for d in self.model_data])
            r2_values = np.array([d["r2"] for d in self.model_data])
            accuracy_values = np.array([d["accuracy"] for d in self.model_data])
            model_size_values = np.array([d["model_size"] for d in self.model_data])

            # 提取标准值
            min_training_time = np.min(training_time_values)
            max_mae = 1 - np.min(mae_values)
            max_rmse = 1 - np.min(rmse_values)
            max_sse = 1 - np.min(sse_values)
            max_median_ae = 1 - np.min(median_ae_values)
            min_model_size = np.min(model_size_values)
            max_accuracy = 100  # 最大准确度是100%

            # 归一化数据
            normalized_training_time = (min_training_time / training_time_values) if min_training_time > 0 else np.ones_like(training_time_values)
            normalized_mae = ((1 - mae_values) / max_mae)
            normalized_rmse = ((1 - rmse_values) / max_rmse)
            normalized_sse = ((1 - sse_values) / max_sse)
            normalized_median_ae = ((1 - median_ae_values) / max_median_ae)
            normalized_r2 = r2_values
            normalized_accuracy = (accuracy_values / max_accuracy)
            normalized_model_size = (min_model_size / model_size_values)

            # 确保值在0-1范围内
            normalized_training_time = np.clip(normalized_training_time, 0, 1)
            normalized_mae = np.clip(normalized_mae, 0, 1)
            normalized_rmse = np.clip(normalized_rmse, 0, 1)
            normalized_sse = np.clip(normalized_sse, 0, 1)
            normalized_median_ae = np.clip(normalized_median_ae, 0, 1)
            normalized_r2 = np.clip(normalized_r2, 0, 1)  # R²
            normalized_accuracy = np.clip(normalized_accuracy, 0, 1)
            normalized_model_size = np.clip(normalized_model_size, 0, 1)

            # 角度设置
            num_metrics = 8
            metric_angles = np.linspace(0, 2 * np.pi, num_metrics, endpoint=False).tolist()
            metric_labels = ['训练时长', 'MAE', 'RMSE', 'SSE', 'MedAE', 'R²', '准确度(±0.001)', '模型大小']

            # 为每个模型绘制雷达图
            colors = plt.cm.Set1(np.linspace(0, 1, len(model_names)))
            for i, (name, color) in enumerate(zip(model_names, colors)):
                # 获取当前模型的各项指标数据
                training_time = normalized_training_time[i]
                mae = normalized_mae[i]
                rmse = normalized_rmse[i]
                sse = normalized_sse[i]
                median_ae = normalized_median_ae[i]
                r2 = normalized_r2[i]
                accuracy = normalized_accuracy[i]
                model_size = normalized_model_size[i]

                # 创建数据点
                data = [training_time, mae, rmse, sse, median_ae, r2, accuracy, model_size]
                data += data[:1]  # 闭合图形，添加第一个点到最后

                # 为每个模型创建角度
                model_angles = metric_angles.copy()
                model_angles += model_angles[:1]  # 闭合角度

                # 绘制
                ax_radar.plot(model_angles, data, linewidth=1.5, label=name, color=color)
                ax_radar.fill(model_angles, data, alpha=0.25, color=color)

            # 添加标签
            ax_radar.set_xticks(metric_angles)
            ax_radar.set_xticklabels(metric_labels, fontsize=8)  # 减小字体
            ax_radar.set_ylim(0, 1)
            ax_radar.set_title('模型综合性能雷达图', pad=20, fontsize=10)  # 减小字体
            ax_radar.legend(loc='upper right', bbox_to_anchor=(1.3, 1.0), fontsize=7)  # 减小字体

            plt.tight_layout()

            # 显示雷达图
            self.clear_layout(self.radar_layout)

            # 创建工具栏
            toolbar = self.create_toolbar("radar")
            self.radar_layout.addWidget(toolbar)

            # 创建可滚动的雷达图区域
            radar_scroll_area = DraggableScrollArea()

            # 创建自定义画布，将滚动区域作为父组件
            self.radar_canvas = ScrollableFigureCanvas(fig_radar, radar_scroll_area)
            radar_scroll_area.setWidget(self.radar_canvas)
            radar_scroll_area.setAlignment(Qt.AlignCenter)  # 居中显示
            radar_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            radar_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.radar_layout.addWidget(radar_scroll_area)

            # 保存雷达图
            radar_path = os.path.join(CONFIG["temp_dir"], "model_radar.png")
            plt.savefig(radar_path, bbox_inches='tight', dpi=300)
            plt.close()

            # 自动保存比较结果到CSV文件
            try:
                comparison_csv_path = os.path.join(CONFIG["history_dir"], "model_comparison_results.csv")
                with open(comparison_csv_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.DictWriter(f, fieldnames=["模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE",
                                                           "R²", "准确度(±0.001)(%)", "模型大小(MB)"])
                    writer.writeheader()
                    for record in self.model_data:
                        writer.writerow({
                            "模型名称": record["name"],
                            "训练时长(s)": record["training_time"],
                            "MAE": record["mae"],
                            "RMSE": record["rmse"],
                            "MedAE": record["median_ae"],
                            "SSE": record["sse"],
                            "R²": record["r2"],
                            "准确度(±0.001)(%)": record["accuracy"],
                            "模型大小(MB)": record["model_size"]
                        })
                print(f"模型比较结果已自动保存至: {comparison_csv_path}")
            except Exception as e:
                print(f"自动保存比较结果失败: {str(e)}")
                traceback.print_exc()

        except Exception as e:
            print(f"生成雷达图失败: {str(e)}")
            traceback.print_exc()
            self.clear_layout(self.radar_layout)
            error_label = QLabel(f"生成雷达图失败: {str(e)}")
            error_label.setFont(QFont("Microsoft YaHei", 12))
            self.radar_layout.addWidget(error_label)

    def generate_score_chart(self):
        """生成综合评分图表"""
        if not self.model_data:
            return

        try:
            # 计算综合评分（加权平均）
            scores = []
            model_names = []
            # 获取各项指标的最大值（用于归一化）
            max_training_time = max([d["training_time"] for d in self.model_data]) if any(
                d["training_time"] > 0 for d in self.model_data) else 1
            max_mae = max([d["mae"] for d in self.model_data]) if any(d["mae"] > 0 for d in self.model_data) else 1
            max_rmse = max([d["rmse"] for d in self.model_data]) if any(d["rmse"] > 0 for d in self.model_data) else 1
            max_sse = max([d["sse"] for d in self.model_data]) if any(d["sse"] > 0 for d in self.model_data) else 1
            max_model_size = max([d["model_size"] for d in self.model_data]) if any(
                d["model_size"] > 0 for d in self.model_data) else 1

            for data in self.model_data:
                # 标准化各项指标到0-1范围（越大越好）, 对于误差类指标需要反转
                # 训练时长越小越好，需要反转
                norm_training_time = 1 - (data["training_time"] / max_training_time) if max_training_time > 0 else 1
                norm_mae = 1 - (data["mae"] / max_mae) if max_mae > 0 else 1
                norm_rmse = 1 - (data["rmse"] / max_rmse) if max_rmse > 0 else 1
                norm_sse = 1 - (data["sse"] / max_sse) if max_sse > 0 else 1
                norm_model_size = 1 - (data["model_size"] / max_model_size) if max_model_size > 0 else 1
                # R²已经是0-1范围，直接使用
                norm_r2 = data["r2"]  # R²越大越好
                # 准确度已经是百分比，需要除以100归一化
                norm_accuracy = data["accuracy"] / 100
                # 计算加权综合评分（调整权重，增加R²和准确度权重）
                score = (
                                norm_training_time * 0.10 +  # 训练时长权重10%
                                norm_mae * 0.10 +  # MAE权重10%
                                norm_rmse * 0.10 +  # RMSE权重10%
                                norm_sse * 0.10 +  # SSE权重10%
                                norm_r2 * 0.20 +  # R²权重20%
                                norm_model_size * 0.05 +  # 模型大小权重5%
                                norm_accuracy * 0.35  # 准确度权重35%
                        ) * 100  # 转换为百分制
                scores.append(score)
                model_names.append(data["name"])

            # 创建综合评分图表，使用合适的默认尺寸
            fig, ax = plt.subplots(figsize=(12, 12))
            bars = ax.bar(model_names, scores, color=plt.cm.viridis(scores))

            # 突出显示最佳模型
            if model_names and scores:
                best_idx = scores.index(max(scores))
                bars[best_idx].set_color('gold')
                bars[best_idx].set_edgecolor('red')
                bars[best_idx].set_linewidth(2)

                # 在最佳模型上添加特殊标记
                ax.text(bars[best_idx].get_x() + bars[best_idx].get_width() / 2,
                        bars[best_idx].get_height() + 3,
                        '推荐', ha='center', va='bottom',
                        fontweight='bold', color='red', fontsize=8)  # 减小字体

            # 添加数值标签
            for bar, score in zip(bars, scores):
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                        f'{score:.1f}', ha='center', va='bottom', fontsize=8)  # 减小字体

            ax.set_ylabel('综合评分', fontsize=9)  # 减小字体
            ax.set_title('模型综合评分比较', fontsize=10)  # 减小字体
            ax.set_ylim(0, 100)
            plt.xticks(rotation=45, ha='right', fontsize=8)  # 减小字体
            plt.yticks(fontsize=8)  # 减小字体
            plt.tight_layout()

            # 显示图表
            self.clear_layout(self.score_layout)

            # 创建工具栏
            toolbar = self.create_toolbar("score")
            self.score_layout.addWidget(toolbar)

            # 创建可滚动的评分图表区域
            score_scroll_area = DraggableScrollArea()

            # 创建自定义画布，将滚动区域作为父组件
            self.score_canvas = ScrollableFigureCanvas(fig, score_scroll_area)
            score_scroll_area.setWidget(self.score_canvas)
            score_scroll_area.setAlignment(Qt.AlignCenter)  # 居中显示
            score_scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            score_scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
            self.score_layout.addWidget(score_scroll_area)

            # 保存图表
            score_path = os.path.join(CONFIG["temp_dir"], "model_scores.png")
            plt.savefig(score_path, dpi=100, bbox_inches='tight')
            plt.close()

        except Exception as e:
            print(f"生成综合评分图表失败: {str(e)}")
            traceback.print_exc()
            self.clear_layout(self.score_layout)
            error_label = QLabel(f"生成综合评分图表失败: {str(e)}")
            error_label.setFont(QFont("Microsoft YaHei", 12))
            self.score_layout.addWidget(error_label)

    def create_toolbar(self, chart_type):
        """创建工具栏"""
        toolbar = QToolBar()
        toolbar.setStyleSheet("QToolBar { border: 1px solid gray; border-radius: 4px; background: #f0f0f0; }")

        # 放大按钮
        zoom_in_action = QAction("放大", self)
        zoom_in_action.triggered.connect(lambda: self.zoom_chart(chart_type, 1.2))
        toolbar.addAction(zoom_in_action)

        # 缩小按钮
        zoom_out_action = QAction("缩小", self)
        zoom_out_action.triggered.connect(lambda: self.zoom_chart(chart_type, 0.8))
        toolbar.addAction(zoom_out_action)

        # 重置按钮
        reset_action = QAction("重置", self)
        reset_action.triggered.connect(lambda: self.reset_chart(chart_type))
        toolbar.addAction(reset_action)

        return toolbar

    def zoom_chart(self, chart_type, factor):
        """缩放图表"""
        if chart_type == "plot" and hasattr(self, 'plot_canvas'):
            self.plot_canvas.figure.set_size_inches(
                self.plot_canvas.figure.get_size_inches()[0] * factor,
                self.plot_canvas.figure.get_size_inches()[1] * factor
            )
            self.plot_canvas.draw()
        elif chart_type == "radar" and hasattr(self, 'radar_canvas'):
            self.radar_canvas.figure.set_size_inches(
                self.radar_canvas.figure.get_size_inches()[0] * factor,
                self.radar_canvas.figure.get_size_inches()[1] * factor
            )
            self.radar_canvas.draw()
        elif chart_type == "score" and hasattr(self, 'score_canvas'):
            self.score_canvas.figure.set_size_inches(
                self.score_canvas.figure.get_size_inches()[0] * factor,
                self.score_canvas.figure.get_size_inches()[1] * factor
            )
            self.score_canvas.draw()

    def reset_chart(self, chart_type):
        """重置图表大小"""
        if chart_type == "plot" and hasattr(self, 'plot_canvas'):
            self.plot_canvas.figure.set_size_inches(15, 6)
            self.plot_canvas.draw()
        elif chart_type == "radar" and hasattr(self, 'radar_canvas'):
            self.radar_canvas.figure.set_size_inches(6, 6)
            self.radar_canvas.draw()
        elif chart_type == "score" and hasattr(self, 'score_canvas'):
            self.score_canvas.figure.set_size_inches(8, 5)
            self.score_canvas.draw()

    def find_best_model(self):
        """找到最佳模型"""
        if not self.model_data:
            return None, 0

        # 获取各项指标的最大值（用于归一化）
        max_training_time = max([d["training_time"] for d in self.model_data]) if any(
            d["training_time"] > 0 for d in self.model_data) else 1
        max_mae = max([d["mae"] for d in self.model_data]) if any(d["mae"] > 0 for d in self.model_data) else 1
        max_rmse = max([d["rmse"] for d in self.model_data]) if any(d["rmse"] > 0 for d in self.model_data) else 1
        max_sse = max([d["sse"] for d in self.model_data]) if any(d["sse"] > 0 for d in self.model_data) else 1
        max_model_size = max([d["model_size"] for d in self.model_data]) if any(
            d["model_size"] > 0 for d in self.model_data) else 1

        scores = []
        model_names = []
        for data in self.model_data:
            # 标准化各项指标到0-1范围（越大越好），对于误差类指标需要反转；训练时长越小越好，需要反转
            norm_training_time = 1 - (data["training_time"] / max_training_time) if max_training_time > 0 else 1
            norm_mae = 1 - (data["mae"] / max_mae) if max_mae > 0 else 1
            norm_rmse = 1 - (data["rmse"] / max_rmse) if max_rmse > 0 else 1
            norm_sse = 1 - (data["sse"] / max_sse) if max_sse > 0 else 1
            norm_model_size = 1 - (data["model_size"] / max_model_size) if max_model_size > 0 else 1

            # R²越大越好
            norm_r2 = data["r2"]

            # 准确度已经是百分比，需要除以100归一化
            norm_accuracy = data["accuracy"] / 100

            # 计算加权综合评分（调整权重，增加R²和准确度权重）
            score = (
                            norm_training_time * 0.05 +  # 训练时长权重5%
                            norm_mae * 0.10 +  # MAE权重10%
                            norm_rmse * 0.10 +  # RMSE权重10%
                            norm_sse * 0.10 +  # SSE权重10%
                            norm_r2 * 0.20 +  # R²权重20%
                            norm_model_size * 0.05 +  # 模型大小权重5%
                            norm_accuracy * 0.40  # 准确度权重40%
                    ) * 100  # 转换为百分制
            scores.append(score)
            model_names.append(data["name"])

        if scores:
            best_idx = scores.index(max(scores))
            return model_names[best_idx], scores[best_idx]
        return None, 0

    def update_best_model_label(self):
        """更新最佳模型标签"""
        best_model_name, best_score = self.find_best_model()
        if best_model_name:
            best_model_text = f"最佳模型: {best_model_name} (综合评分: {best_score:.1f})"
            self.best_model_label.setText(best_model_text)
            self.best_model_label.setStyleSheet("color: green; font-weight: bold;")
        else:
            self.best_model_label.setText("暂无最佳模型推荐")
            self.best_model_label.setStyleSheet("color: red; font-weight: bold;")

    def load_best_model(self):
        """加载推荐的最佳模型"""
        best_model_name, _ = self.find_best_model()
        if best_model_name:
            try:
                model_path = None

                # 在models_list中查找对应模型路径
                for model_info in self.app.models_list:
                    if model_info["name"] == best_model_name:
                        model_path = model_info["path"]
                        break

                # 检查模型路径是否存在
                if model_path and not os.path.exists(model_path):
                    reply = QMessageBox.question(
                        self,
                        "模型不存在",
                        f"推荐的最佳模型 '{best_model_name}' 已被删除，是否重新评估模型？",
                        QMessageBox.Yes | QMessageBox.No,
                        QMessageBox.Yes
                    )

                    if reply == QMessageBox.Yes:
                        # 重新扫描可用模型
                        self.app.scan_available_models()
                        # 重新开始评估
                        self.start_evaluation(force_recalculate=True)
                    return

                if model_path:
                    # 加载模型
                    progress_dialog = ModelLoadingProgress(self)
                    progress_dialog.show()

                    def progress_callback(value, text=""):
                        progress_dialog.update_progress(value, text)

                    self.app.predictor = RefractiveIndexPredictor(model_path, progress_callback)
                    self.app.current_model_dir = model_path
                    self.app.status_var.setText("已加载")
                    self.app.model_dir_var.setText(best_model_name)
                    print(f"已加载推荐模型: {best_model_name}")
                    QMessageBox.information(self, "成功", f"已加载推荐模型: {best_model_name}")

                    # 关闭进度条窗口、模型比较窗口
                    progress_dialog.close()
                    self.close()
                else:
                    QMessageBox.critical(self, "错误", "无法找到推荐模型的路径")
            except Exception as e:
                print(f"加载推荐模型失败: {str(e)}")
                QMessageBox.critical(self, "错误", f"加载推荐模型失败: {str(e)}")
        else:
            QMessageBox.information(self, "提示", "暂无推荐模型")

    def export_comparison(self):
        """导出比较结果"""
        if not self.model_data:
            QMessageBox.information(self, "提示", "没有数据可导出")
            return

        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "导出比较结果",
            "model_comparison.csv",
            "CSV files (*.csv);;Excel files (*.xlsx)"
        )

        if save_path:
            try:
                export_data = []
                for record in self.model_data:
                    export_data.append({
                        "模型名称": record["name"],
                        "训练时长(s)": record["training_time"],
                        "MAE": record["mae"],
                        "RMSE": record["rmse"],
                        "MedAE": record["median_ae"],
                        "SSE": record["sse"],
                        "R²": record["r2"],
                        "准确度(±0.001)(%)": record["accuracy"],
                        "模型大小(MB)": record["model_size"]
                    })

                if save_path.endswith('.xlsx'):
                    df = pd.DataFrame(export_data)
                    df.to_excel(save_path, index=False)
                else:
                    with open(save_path, 'w', newline='', encoding='utf-8') as f:
                        writer = csv.DictWriter(f, fieldnames=["模型名称", "训练时长(s)", "MAE", "RMSE", "MedAE", "SSE",
                                                               "R²", "准确度(±0.001)(%)", "模型大小(MB)"])
                        writer.writeheader()
                        writer.writerows(export_data)
                QMessageBox.information(self, "成功", f"比较结果已导出至:\n{save_path}")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"导出失败: {str(e)}")

    def reevaluate_models(self):
        """重新评估所有模型"""
        self.start_evaluation(force_recalculate=True)

    def clear_layout(self, layout):
        """清空布局中的所有部件"""
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()


class ModelComparator:
    """模型比较接口"""
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("ModelComparator")
        self.dialog = None

    def compare_models(self):
        """比较不同模型的性能"""
        self.dialog = ModelComparisonDialog(self.app)
        self.dialog.show()

        # 开始评估
        QTimer.singleShot(100, self.dialog.start_evaluation)
