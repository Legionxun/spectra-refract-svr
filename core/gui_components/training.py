# core/gui_components/training.py
import threading, os, shutil, logging
from PySide6.QtWidgets import QMessageBox
from PySide6.QtCore import QObject, Signal, QTimer

from ..model_trainer import ModelTrainer
from ..config import CONFIG
from ..predictor import RefractiveIndexPredictor


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

    def run_training(self):
        """执行训练过程"""
        try:
            if not os.path.exists(CONFIG["data_path"]):
                os.makedirs(CONFIG["data_path"])
                self.logger.info(f"创建数据目录: {CONFIG['data_path']}")
                self.training_progress.emit(f"创建数据目录: {CONFIG['data_path']}")

            # 调用训练主函数
            self.app.trainer = ModelTrainer(app=self.app, training_worker=self)
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
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("TrainingManager")
        self.worker = None
        self.worker_thread = None

    def start_training(self):
        """开始训练模型"""
        self.logger.info("用户启动模型训练")
        result = QMessageBox.question(
            self.app,
            "确认",
            "尚未生成理论数据，是否继续训练？",
            QMessageBox.Yes | QMessageBox.No
        ) if not self.app.theoretical_data_generated else QMessageBox.Yes

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

        # 创建并启动工作线程
        self.worker = TrainingWorker(self.app)
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
            self.app.enable_all_buttons()
            return

        try:
            self.worker_thread.start()
        except Exception as e:
            self.logger.error(f"启动训练线程时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"启动训练线程失败: {str(e)}")
            self.app.training_in_progress = False
            self.app.enable_all_buttons()

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
        self.app.enable_all_buttons()

    def on_training_finished(self, success, model_dir, message):
        """训练完成回调"""
        QTimer.singleShot(0, lambda: self._handle_training_finished(success, model_dir, message))

    def _handle_training_finished(self, success, model_dir, message):
        """在主线程中处理训练完成"""
        if success:
            self.app.status_var.setText("已训练")
            self.app.model_dir_var.setText(os.path.basename(model_dir))
            print(message)

            # 加载刚训练的模型
            try:
                self.app.predictor = RefractiveIndexPredictor(model_dir)
                self.app.current_model_dir = model_dir
                print("模型已成功加载")
                self.logger.info("模型已成功加载")
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
        self.app.enable_all_buttons()

        # 清理线程资源
        if self.worker_thread and self.worker_thread.is_alive():
            self.worker_thread.join(timeout=1)

    def on_training_progress(self, message):
        """训练进度回调"""
        # 确保在主线程中更新UI
        QTimer.singleShot(0, lambda: print(message))

    def on_training_error(self, error_msg):
        """训练错误回调"""
        QTimer.singleShot(0, lambda: self._handle_training_error(error_msg))

    def _handle_training_error(self, error_msg):
        """在主线程中处理训练错误"""
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
        self.app.enable_all_buttons()

    def on_training_message(self, title, message):
        """训练消息回调，用于更新欢迎界面"""
        QTimer.singleShot(0, lambda: self.app.show_message(title, message))

    def on_training_results(self, model_dir, feature_plot_path, cluster_plot_path, result_plot_path):
        """训练结果回调，用于显示训练结果"""
        QTimer.singleShot(0, lambda: self.app.show_training_results(model_dir, feature_plot_path, cluster_plot_path,
                                                                    result_plot_path))
