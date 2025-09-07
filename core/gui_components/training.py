# core/gui_components/training.py
import threading, os, shutil, logging
from PySide6.QtWidgets import (QMessageBox, QDialog, QVBoxLayout, QHBoxLayout, QComboBox,
                               QPushButton, QLabel, QApplication, QGroupBox, QRadioButton)
from PySide6.QtCore import QObject, Signal, QTimer, Qt

from .progress_dialogs import ModelLoadingProgress, AnimatedProgressBar
from ..model_trainer import ModelTrainer
from ..config import CONFIG, TUNING_CONFIG
from ..predictor import RefractiveIndexPredictor


class OptimizationMethodDialog(QDialog):
    """优化方法选择对话框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择训练参数")
        self.setModal(True)
        self.resize(400, 250)
        self.optimization_method = "hybrid"  # 默认方法
        self.clustering_method = "kmeans"  # 默认聚类方法

        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 优化方法选择组
        optimization_group = QGroupBox("超参数优化方法:")
        optimization_layout = QVBoxLayout()

        self.optimization_combo = QComboBox()
        self.optimization_combo.addItems([
            "混合优化 (贝叶斯优化 + Optuna) - 推荐",
            "贝叶斯优化",
            "Optuna优化"
        ])
        optimization_method = TUNING_CONFIG.get("optimization_method", "hybrid")
        if optimization_method == "bayesian":
            self.optimization_combo.setCurrentIndex(1)
        elif optimization_method == "optuna":
            self.optimization_combo.setCurrentIndex(2)
        else:
            self.optimization_combo.setCurrentIndex(0)
        optimization_layout.addWidget(self.optimization_combo)

        # 说明文本
        optimization_info = QLabel(
            "混合优化结合了贝叶斯优化的全局搜索能力和Optuna的局部优化能力，\n"
            "通常能获得更好的优化效果。"
        )
        optimization_info.setWordWrap(True)
        optimization_layout.addWidget(optimization_info)

        optimization_group.setLayout(optimization_layout)
        layout.addWidget(optimization_group)

        # 聚类方法选择组
        clustering_group = QGroupBox("聚类方法:")
        clustering_layout = QVBoxLayout()

        self.kmeans_radio = QRadioButton("K-Means聚类 (默认)")
        self.som_radio = QRadioButton("SOM神经网络聚类")

        # 根据配置设置默认选项
        clustering_method = TUNING_CONFIG.get("clustering_method", "kmeans")
        if clustering_method == "som":
            self.som_radio.setChecked(True)
        else:
            self.kmeans_radio.setChecked(True)

        clustering_layout.addWidget(self.kmeans_radio)

        # SOM说明文本
        som_info = QLabel(
            "SOM(自组织映射)是一种无监督神经网络聚类方法，\n"
            "能够更好地发现数据中的非线性结构，但训练时间较长。"
        )
        som_info.setWordWrap(True)
        clustering_layout.addWidget(self.som_radio)
        clustering_layout.addWidget(som_info)

        clustering_group.setLayout(clustering_layout)
        layout.addWidget(clustering_group)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.ok_button = QPushButton("确定")
        self.cancel_button = QPushButton("取消")
        self.ok_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def get_selected_methods(self):
        """获取选择的优化方法和聚类方法"""
        opt_index = self.optimization_combo.currentIndex()
        if opt_index == 0:
            optimization_method = "hybrid"
        elif opt_index == 1:
            optimization_method = "bayesian"
        elif opt_index == 2:
            optimization_method = "optuna"
        else:
            optimization_method = "hybrid"

        clustering_method = "som" if self.som_radio.isChecked() else "kmeans"

        return optimization_method, clustering_method


class TrainingProgressDialog(QDialog):
    """训练进度对话框"""
    def __init__(self, manager, parent=None):
        super().__init__(parent)
        self.setWindowTitle("模型训练进度")
        self.setModal(False)
        self.resize(400, 200)
        self.setWindowFlags(Qt.Dialog | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
        self.stop_requested = False
        self.manager = manager
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # 阶段标签
        self.phase_label = QLabel("准备训练...")
        self.phase_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.phase_label)

        # 总体进度条
        self.total_progress_label = QLabel("总体进度:")
        layout.addWidget(self.total_progress_label)

        self.total_progress_bar = AnimatedProgressBar()
        self.total_progress_bar.setRange(0, 100)
        self.total_progress_bar.setValue(0)
        self.total_progress_bar.setTextVisible(True)
        layout.addWidget(self.total_progress_bar)

        # 当前阶段进度标签
        self.current_phase_label = QLabel("当前阶段进度:")
        layout.addWidget(self.current_phase_label)

        self.current_phase_progress_bar = AnimatedProgressBar()
        self.current_phase_progress_bar.setRange(0, 100)
        self.current_phase_progress_bar.setValue(0)
        self.current_phase_progress_bar.setTextVisible(True)
        layout.addWidget(self.current_phase_progress_bar)

        # 详细信息标签
        self.detail_label = QLabel("")
        self.detail_label.setAlignment(Qt.AlignCenter)
        self.detail_label.setWordWrap(True)
        layout.addWidget(self.detail_label)

        # 按钮布局
        button_layout = QHBoxLayout()
        self.minimize_button = QPushButton("最小化")
        self.cancel_button = QPushButton("停止训练")
        self.minimize_button.clicked.connect(self.showMinimized)
        self.cancel_button.clicked.connect(self.request_stop_training)

        button_layout.addWidget(self.minimize_button)
        button_layout.addWidget(self.cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def request_stop_training(self):
        """请求停止训练"""
        reply = QMessageBox.question(self, "确认", "确定要停止训练吗？",QMessageBox.Yes | QMessageBox.No)
        if reply == QMessageBox.Yes:
            self.stop_requested = True
            self.cancel_button.setEnabled(False)
            self.detail_label.setText("正在停止训练...")
            self.manager.stop_training()

    def update_progress(self, current, total, description):
        """更新进度"""
        if total > 0:
            percentage = (current / total) * 100
            self.current_phase_progress_bar.setValue(percentage)
            self.detail_label.setText(description)
            QApplication.processEvents()

    def update_phase(self, phase_text):
        """更新阶段文本"""
        self.phase_label.setText(phase_text)
        QApplication.processEvents()

    def update_total_progress(self, percentage):
        """更新总体进度"""
        self.total_progress_bar.setValue(percentage)
        QApplication.processEvents()


class TrainingWorker(QObject):
    """训练工作线程"""
    training_finished = Signal(bool, str, str)
    training_progress = Signal(str)
    training_error = Signal(str)
    training_message = Signal(str, str)  # 更新欢迎界面消息
    training_results = Signal(str, str, str, str)  # 显示训练结果

    def __init__(self, app):
        super().__init__()
        self.app = app
        self.logger = logging.getLogger("TrainingWorker")
        self.model_dir = None
        self.progress_dialog = None

    def run_training(self):
        """执行训练过程"""
        try:
            # 在主线程中创建进度对话框
            QApplication.instance().processEvents()

            if not os.path.exists(CONFIG["data_path"]):
                os.makedirs(CONFIG["data_path"])
                self.logger.info(f"创建数据目录: {CONFIG['data_path']}")
                self.training_progress.emit(f"创建数据目录: {CONFIG['data_path']}")

            # 调用训练主函数
            self.app.trainer = ModelTrainer(
                app=self.app,
                training_worker=self,
                tuning_config=self.app.tuning_config  # 传递更新后的配置
            )

            self.model_dir = self.app.trainer.run_training()

            if self.app.stop_training_flag:
                message = "训练已被用户中断"
                self.logger.info(message)
                self.training_progress.emit(message)

                # 删除中断训练生成的模型目录
                self._delete_model_dir()

                # 释放GPU资源
                self.release_gpu_resources()
                self.training_finished.emit(False, "", "训练已被用户中断")
            else:
                message = f"训练完成！模型已保存至 {self.model_dir} 目录"
                self.logger.info("训练完成！模型已保存至 %s 目录", self.model_dir)
                self.training_progress.emit(message)

                # 获取可视化图表路径
                feature_plot = os.path.join(self.model_dir, "results", "特征密度分布.png")
                cluster_plot = os.path.join(self.model_dir, "results", "聚类分布直方图.png")
                result_plot = os.path.join(self.model_dir, "results", "残差分布.png")

                # 发送训练结果信号
                if feature_plot and cluster_plot and result_plot:
                    self.training_results.emit(self.model_dir, feature_plot, cluster_plot, result_plot)
                else:
                    self.logger.warning("未能找到所有可视化图表文件")

                self.training_finished.emit(True, self.model_dir, message)

        except Exception as e:
            if not self.app.stop_training_flag:
                error_msg = f"训练过程中发生错误: {str(e)}"
                self.logger.error(error_msg, exc_info=True)
                self.training_error.emit(error_msg)

                # 删除训练失败生成的模型目录
                self._delete_model_dir()

                self.training_finished.emit(False, "", error_msg)
            else:
                # 即使是异常情况，如果训练被中断，也要删除模型目录
                message = "训练已被用户中断"
                self.logger.info(message)
                self.training_progress.emit(message)

                # 删除中断训练生成的模型目录
                self._delete_model_dir()

                self.training_finished.emit(False, "", "训练已被用户中断")

    def _delete_model_dir(self):
        """删除模型目录的辅助方法"""
        # 首先尝试使用self.model_dir
        model_dir_to_delete = self.model_dir

        # 尝试从trainer中获取
        if not model_dir_to_delete and hasattr(self.app, 'trainer') and self.app.trainer:
            model_dir_to_delete = self.app.trainer.model_dir

        print(f"尝试删除模型目录: {model_dir_to_delete}")

        if model_dir_to_delete and os.path.exists(model_dir_to_delete):
            try:
                shutil.rmtree(model_dir_to_delete)
                msg = f"已删除中断训练生成的模型目录: {model_dir_to_delete}"
                self.logger.info(msg)
                self.training_progress.emit(msg)
            except Exception as e:
                msg = f"删除中断训练生成的模型目录失败: {str(e)}"
                self.logger.error(msg, exc_info=True)
                self.training_progress.emit(msg)
        elif model_dir_to_delete:
            msg = f"模型目录不存在: {model_dir_to_delete}"
            self.logger.warning(msg)
            self.training_progress.emit(msg)
        else:
            msg = "未找到需要删除的模型目录"
            self.logger.warning(msg)
            self.training_progress.emit(msg)

    def release_gpu_resources(self):
        """释放GPU资源"""
        try:
            # 清理TensorFlow GPU资源
            try:
                import tensorflow as tf
                # 清空Keras会话
                try:
                    tf.keras.backend.clear_session()
                except:
                    pass

                # 重置默认图
                try:
                    tf.compat.v1.reset_default_graph()
                except:
                    pass

                self.training_progress.emit("TensorFlow GPU资源已释放")
            except ImportError:
                pass
            except Exception as e:
                msg = f"释放TensorFlow GPU资源时出错: {str(e)}"
                self.training_progress.emit(msg)

        except Exception as e:
            msg = f"释放GPU资源时发生错误: {str(e)}"
            self.logger.error(msg)
            self.training_progress.emit(msg)


class TrainingManager:
    """模型训练管理接口"""
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("TrainingManager")
        self.worker = None
        self.worker_thread = None
        self.progress_dialog = None

    def start_training(self):
        """开始训练模型"""
        self.logger.info("用户启动模型训练")

        # 显示优化方法选择对话框
        dialog = OptimizationMethodDialog(self.app)
        if dialog.exec() == QDialog.Accepted:
            # 获取用户选择的优化方法和聚类方法
            optimization_method, clustering_method = dialog.get_selected_methods()
            # 更新配置
            TUNING_CONFIG["optimization_method"] = optimization_method
            TUNING_CONFIG["clustering_method"] = clustering_method
            self.app.tuning_config = TUNING_CONFIG  # 更新应用的配置
            self.logger.info(f"用户选择了优化方法: {optimization_method}, 聚类方法: {clustering_method}")
        else:
            # 用户取消了训练
            return

        result = QMessageBox.question(
            self.app,
            "确认",
            "尚未生成理论数据，是否继续训练？",
            QMessageBox.Yes | QMessageBox.No
        ) if (not self.app.theoretical_data_generated and not os.listdir(CONFIG["data_path"])) else QMessageBox.Yes

        if result == QMessageBox.No:
            return

        if self.app.training_in_progress:
            QMessageBox.warning(self.app, "警告", "训练已在运行中")
            return

        # 禁用除"停止训练"外的所有功能按钮
        self.app.disable_all_buttons_except_stop()

        # 在新线程中运行训练
        self.app.training_in_progress = True
        self.app.stop_training_flag = False
        print("\n=== 开始训练模型 ===")
        print("正在初始化训练过程...")

        # 创建并显示进度对话框在主线程中
        self.progress_dialog = TrainingProgressDialog(self, self.app)
        self.progress_dialog.show()

        # 将进度对话框传递给worker
        # 创建并启动工作线程
        self.worker = TrainingWorker(self.app)

        # 连接进度对话框的更新方法到trainer的信号
        self.app.trainer_progress_signal = self.progress_dialog.update_progress
        self.app.trainer_phase_signal = self.progress_dialog.update_phase
        self.app.trainer_total_progress_signal = self.progress_dialog.update_total_progress

        self.worker_thread = threading.Thread(target=self.worker.run_training)
        self.worker_thread.daemon = True

        # 连接信号
        try:
            self.worker.training_finished.connect(self.on_training_finished)
            self.worker.training_progress.connect(self.on_training_progress)
            self.worker.training_error.connect(self.on_training_error)
            self.worker.training_message.connect(self.on_training_message)  # 连接新信号
            self.worker.training_results.connect(self.on_training_results)  # 连接训练结果信号
        except Exception as e:
            self.logger.error(f"连接信号时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"初始化训练线程失败: {str(e)}")
            self.app.training_in_progress = False
            self.app.enable_all_buttons_except_stop()
            return

        try:
            self.worker_thread.start()
        except Exception as e:
            self.logger.error(f"启动训练线程时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"启动训练线程失败: {str(e)}")
            self.app.training_in_progress = False
            self.app.enable_all_buttons_except_stop()

    def stop_training(self):
        """停止训练"""
        self.logger.info("用户请求停止训练")
        if self.app.training_in_progress:
            self.app.stop_training_flag = True
            print("\n=== 正在停止训练 ===")

            # 初始化结果区域
            self.app.init_result_frame()

            # 清理线程资源
            if self.worker_thread and self.worker_thread.is_alive():
                self.worker_thread.join()

            QMessageBox.information(self.app, "提示", "已停止训练")
        else:
            QMessageBox.warning(self.app, "警告", "当前没有正在进行的训练")

        # 恢复所有按钮状态
        self.app.training_in_progress = False
        self.app.stop_training_flag = True
        self.app.enable_all_buttons_except_stop()

        # 关闭进度对话框
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

    def on_training_finished(self, success, model_dir, message):
        """训练完成回调"""
        QTimer.singleShot(0, lambda: self._handle_training_finished(success, model_dir, message))

    def _handle_training_finished(self, success, model_dir, message):
        """在主线程中处理训练完成"""
        # 关闭进度对话框
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        if success:
            self.app.status_var.setText("已训练")
            self.app.model_dir_var.setText(os.path.basename(model_dir))
            print(message)

            # 加载刚训练的模型
            try:
                # 创建并显示进度条窗口
                progress_dialog = ModelLoadingProgress(self.app)
                progress_dialog.show()

                # 创建进度回调函数
                def progress_callback(value, text=""):
                    progress_dialog.update_progress(value, text)

                self.app.predictor = RefractiveIndexPredictor(model_dir, progress_callback)
                self.app.current_model_dir = model_dir
                print("模型已成功加载")
                self.logger.info("模型已成功加载")

                # 关闭进度条窗口
                progress_dialog.close()
                QMessageBox.information(self.app, "成功", f"模型加载成功！\n目录: {self.app.current_model_dir}")
            except Exception as e:
                self.logger.error(f"加载模型失败: {str(e)}")
                print(f"加载模型失败: {str(e)}")
        else:
            if message != "训练已被用户中断":
                print(message)

        # 释放GPU资源
        if self.worker:
            try:
                self.worker.release_gpu_resources()
            except Exception as e:
                self.logger.error(f"释放GPU资源时出错: {str(e)}")
        self.app.training_in_progress = False
        self.app.stop_training_flag = False
        self.app.enable_all_buttons_except_stop()

        # 清理线程资源
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)

    def on_training_progress(self, message):
        """训练进度回调"""
        QTimer.singleShot(0, lambda: print(message))

    def on_training_error(self, error_msg):
        """训练错误回调"""
        QTimer.singleShot(0, lambda: self._handle_training_error(error_msg))

    def _handle_training_error(self, error_msg):
        """在主线程中处理训练错误"""
        # 关闭进度对话框
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None

        print(error_msg)
        QMessageBox.critical(self.app, "训练错误", error_msg)

        # 释放GPU资源
        if self.worker:
            try:
                self.worker.release_gpu_resources()
            except Exception as e:
                self.logger.error(f"释放GPU资源时出错: {str(e)}")
        self.app.training_in_progress = False
        self.app.stop_training_flag = False
        self.app.enable_all_buttons_except_stop()

    def on_training_message(self, title, message):
        """训练消息回调，用于更新欢迎界面"""
        QTimer.singleShot(0, lambda: self.app.show_message(title, message))

    def on_training_results(self, model_dir, feature_plot_path, cluster_plot_path, result_plot_path):
        """训练结果回调，用于显示训练结果"""
        QTimer.singleShot(0, lambda: self.app.show_training_results(model_dir, feature_plot_path, cluster_plot_path,
                                                                    result_plot_path))
