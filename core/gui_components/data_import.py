# core/gui_components/data_import.py
from PySide6.QtWidgets import QFileDialog, QMessageBox
import numpy as np
import os, logging
from scipy.interpolate import interp1d
import matplotlib.pyplot as plt

from ..utils import get_unique_filename


class DataImporter:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("DataImporter")

    def import_data_original(self):
        """导入原始数据"""
        file_path = QFileDialog.getOpenFileName()[0]
        if not file_path:
            return
        self.logger.info("用户请求导入数据")
        try:
            data = np.loadtxt(file_path)
            i1_values = data[:, 0]  # 入射角
            delta_values = data[:, 1]  # 偏向角

            # 进行三次样条插值
            interp_func = interp1d(i1_values, delta_values, kind='cubic', fill_value="extrapolate")

            # 生成更平滑的曲线，使用更密集的入射角点
            i1_dense = np.linspace(min(i1_values), max(i1_values), 500)
            delta_dense = interp_func(i1_dense)

            output_folder = os.path.abspath(r"./actual_data")
            os.makedirs(output_folder, exist_ok=True)

            base_name = "interpolated_plot"
            filename = get_unique_filename(output_folder, base_name, "png")

            # 绘制图像
            plt.figure(figsize=(4, 4))
            plt.plot(i1_dense, delta_dense, label="插值曲线")
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.xlabel("入射角 i1 (度)")
            plt.ylabel("偏向角 delta (度)")
            plt.title("入射角与偏向角的关系")
            plt.grid(True)
            plt.legend()
            plt.savefig(filename)
            plt.close()

            self.app.predict_data_path = filename
            print(f"插值后的图像已保存至 '{output_folder}' 文件夹")
            self.logger.info(f"插值后的图像已保存至 '{output_folder}' 文件夹")
            self.app.display_image(self.app.predict_data_path)
            self.app.data_loaded = True
            self.app.data_status_var.setText("已加载")
            self.app.data_status_indicator.setStyleSheet("color: green;")
            print("数据已成功导入")
            self.logger.info("数据已成功导入")

        except Exception as e:
            print(f"导入原始数据失败: {str(e)}")
            self.logger.error(f"导入原始数据失败: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"导入原始数据失败: {str(e)}")

    def import_data_processed(self):
        """导入数据并预测至入射角为 80°"""
        file_path, _ = QFileDialog.getOpenFileName(filter="Text Files (*.txt)")
        if not file_path:
            QMessageBox.warning(self.app, "警告", "未选择文件")
            return
        self.logger.info("用户请求导入数据并预测至入射角为 80°")
        try:
            data = np.loadtxt(file_path)
            i1_values = data[:, 0]  # 入射角
            delta_values = data[:, 1]  # 偏向角
            interp_func = interp1d(i1_values, delta_values, kind='cubic', fill_value="extrapolate")
            i1_dense = np.linspace(min(i1_values), 80, 500)
            delta_dense = interp_func(i1_dense)

            output_folder = os.path.abspath(r"./actual_data")
            os.makedirs(output_folder, exist_ok=True)

            base_name = "yuce"
            filename = get_unique_filename(output_folder, base_name, "png")

            plt.figure(figsize=(4, 4))
            plt.plot(i1_dense, delta_dense, label="插值曲线")
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.xlabel("入射角 i1 (度)")
            plt.ylabel("偏向角 delta (度)")
            plt.title("入射角与偏向角的关系")
            plt.grid(True)
            plt.legend()
            plt.savefig(filename)
            plt.close()

            self.app.predict_data_path = filename
            print(f"插值后的图像已保存至 '{output_folder}' 文件夹")
            self.app.display_image(self.app.predict_data_path)
            self.logger.info(f"插值后的图像已保存至 '{output_folder}' 文件夹")

            # 更新数据状态
            self.app.data_loaded = True
            self.app.data_status_var.setText("已加载")
            self.app.data_status_indicator.setStyleSheet("color: green;")  # 设置状态为绿色
            print("数据已成功导入")
            self.logger.info("数据已成功导入")
        except Exception as e:
            print(f"导入处理数据失败: {str(e)}")
            self.logger.error(f"导入处理数据失败: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"导入处理数据失败: {str(e)}")
