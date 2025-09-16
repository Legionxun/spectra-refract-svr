# core/gui_components/data_import.py
import logging
import numpy as np
import matplotlib.pyplot as plt
from PySide6.QtWidgets import QFileDialog, QMessageBox
from scipy.interpolate import Akima1DInterpolator, PchipInterpolator, UnivariateSpline

from ..utils import get_unique_filename
from ..config import CONFIG


class DataImporter:
    """数据导入接口"""
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("DataImporter")
        self.output_folder = CONFIG["actual_data_dir"]

    def _smooth_convex_interpolation(self, i1_data, delta_data, i1_dense):
        """
        生成光滑、下凸且经过所有原始点的插值曲线
        """
        sorted_indices = np.argsort(i1_data)
        i1_sorted = i1_data[sorted_indices]
        delta_sorted = delta_data[sorted_indices]

        # 使用Akima插值
        try:
            akima = Akima1DInterpolator(i1_sorted, delta_sorted)
            delta_interp = akima(i1_dense)

            # 检查凸性
            if self._check_convexity(i1_dense, delta_interp):
                return delta_interp
        except Exception as e:
            self.logger.warning(f"Akima插值失败: {str(e)}")

        # 如果Akima插值不能满足凸性要求，使用PCHIP插值
        try:
            pchip = PchipInterpolator(i1_sorted, delta_sorted)
            delta_interp = pchip(i1_dense)

            # 检查凸性
            if self._check_convexity(i1_dense, delta_interp):
                return delta_interp
        except Exception as e:
            self.logger.warning(f"PCHIP插值失败: {str(e)}")

        # 如果以上方法都不行，使用强制通过点的插值方法
        try:
            delta_interp = self._forced_interpolation(i1_sorted, delta_sorted, i1_dense)
            return delta_interp
        except Exception as e:
            self.logger.warning(f"强制插值失败: {str(e)}")

        # 最终回退方案：样条插值
        spline = UnivariateSpline(i1_sorted, delta_sorted, s=0, k=min(3, len(i1_sorted) - 1))
        delta_interp = spline(i1_dense)
        return delta_interp

    def _forced_interpolation(self, x, y, x_new):
        """
        强制通过所有点的插值方法，同时尽量保持光滑和凸性
        """
        # 使用Akima插值
        akima = Akima1DInterpolator(x, y)
        y_new = akima(x_new)

        # 验证是否通过所有点
        for i in range(len(x)):
            y_interp = akima(x[i])
            if abs(y_interp - y[i]) > 1e-10:  # 数值误差容限
                return np.interp(x_new, x, y)

        return y_new

    def _check_convexity(self, x, y, tolerance=1e-6):
        """
        检查曲线是否为下凸（凹向上）
        """
        if len(x) < 3:
            return True

        # 计算数值二阶导数
        dx = np.diff(x)
        dy = np.diff(y)
        if np.any(dx <= 0):
            return False

        dy_dx = dy / dx  # 一阶导数的近似
        d2y_dx2 = np.diff(dy_dx) / dx[1:]  # 二阶导数的近似

        # 检查是否下凸
        return np.all(d2y_dx2 >= -tolerance)

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

            # 使用光滑下凸插值方法
            i1_dense = np.linspace(min(i1_values), max(i1_values), 500)
            delta_dense = self._smooth_convex_interpolation(i1_values, delta_values, i1_dense)

            # 绘制图像
            plt.figure(figsize=(6, 6))
            plt.plot(i1_dense, delta_dense)
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.grid(True)

            base_name = "interpolated_plot"
            filename = get_unique_filename(self.output_folder, base_name, "png")
            plt.savefig(filename, dpi=400)
            plt.close()

            self.app.predict_data_path = filename
            print(f"插值后的图像已保存至 '{CONFIG['actual_data_dir']}' 文件夹")
            self.logger.info(f"插值后的图像已保存至 '{CONFIG['actual_data_dir']}' 文件夹")
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
            max_i1 = max(i1_values)

            if max_i1 >= 80:
                i1_dense = np.linspace(min(i1_values), max_i1, 500)
                delta_dense = self._smooth_convex_interpolation(i1_values, delta_values, i1_dense)
            else:
                i1_dense = np.linspace(min(i1_values), 80, 500)

                # 使用Akima插值进行外推
                try:
                    # 创建插值器
                    interpolator = Akima1DInterpolator(i1_values, delta_values)

                    # 获取最后一个点的导数信息用于外推
                    last_x = i1_values[-1]

                    # 计算最后一个区间的斜率作为外推的基础
                    if len(i1_values) >= 2:
                        dx = i1_values[-1] - i1_values[-2]
                        dy = delta_values[-1] - delta_values[-2]
                        slope = dy / dx if dx != 0 else 0
                    else:
                        slope = 0

                    # 生成扩展点，基于趋势外推
                    i1_extend = np.linspace(last_x, 80, 50)
                    delta_extend = interpolator(i1_extend, extrapolate=True)

                    # 确保外推部分保持凸性
                    delta_extend = self._ensure_convex_extrapolation(
                        i1_values, delta_values, i1_extend, delta_extend, slope)

                    # 合并原始数据和扩展数据点
                    i1_combined = np.concatenate([i1_values[:-1], i1_extend])
                    delta_combined = np.concatenate([delta_values[:-1], delta_extend])

                    # 使用组合数据进行插值
                    delta_dense = self._smooth_convex_interpolation(i1_combined, delta_combined, i1_dense)
                except Exception as e:
                    self.logger.warning(f"外推方法失败: {str(e)}")
                    delta_dense = self._smooth_convex_interpolation(i1_values, delta_values, i1_dense)

            # 绘制图像：显示原始数据点和插值曲线
            plt.figure(figsize=(6, 6))
            plt.plot(i1_dense, delta_dense)
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.grid(True)

            base_name = "yuce"
            filename = get_unique_filename(self.output_folder, base_name, "png")
            plt.savefig(filename, dpi=400)
            plt.close()

            self.app.predict_data_path = filename
            print(f"插值后的图像已保存至 '{self.output_folder}' 文件夹")
            self.app.display_image(self.app.predict_data_path)
            self.logger.info(f"插值后的图像已保存至 '{self.output_folder}' 文件夹")

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

    def _ensure_convex_extrapolation(self, i1_orig, delta_orig, i1_extend, delta_extend, initial_slope):
        """确保外推部分保持凸性和平滑性"""
        if len(i1_extend) < 2:
            return delta_extend
        i1_combined = np.concatenate([i1_orig, i1_extend])
        delta_combined = np.concatenate([delta_orig, delta_extend])

        # 使用PCHIP插值器
        try:
            pchip = PchipInterpolator(i1_combined, delta_combined)
            delta_new = pchip(i1_extend)
            return delta_new
        except Exception as e:
            self.logger.warning(f"PCHIP外推失败: {str(e)}")

        # 如果PCHIP失败，尝试Akima插值
        try:
            akima = Akima1DInterpolator(i1_combined, delta_combined)
            delta_new = akima(i1_extend)
            return delta_new
        except Exception as e:
            self.logger.warning(f"Akima外推失败: {str(e)}")

        # 回退到原来的调整方法
        if len(i1_orig) >= 3:
            x_vals = i1_orig[-3:]
            y_vals = delta_orig[-3:]
            dy_dx = (y_vals[-1] - y_vals[-2]) / (x_vals[-1] - x_vals[-2])
        else:
            dy_dx = initial_slope

        # 调整外推部分以保持平滑连接
        delta_adjusted = np.copy(delta_extend)

        # 确保外推曲线的初始斜率与原始曲线一致
        if len(delta_extend) >= 2:
            current_slope = (delta_extend[1] - delta_extend[0]) / (i1_extend[1] - i1_extend[0])
            slope_diff = dy_dx - current_slope
            for i in range(1, len(delta_extend)):
                # 按距离加权调整
                weight = i / len(delta_extend)
                adjustment = slope_diff * weight * (i1_extend[i] - i1_extend[0])
                delta_adjusted[i] += adjustment

        # 确保凸性
        for i in range(2, len(delta_adjusted)):
            prev_slope = (delta_adjusted[i - 1] - delta_adjusted[i - 2]) / (i1_extend[i - 1] - i1_extend[i - 2])
            curr_slope = (delta_adjusted[i] - delta_adjusted[i - 1]) / (i1_extend[i] - i1_extend[i - 1])
            if curr_slope < prev_slope:
                delta_adjusted[i] = delta_adjusted[i - 1] + prev_slope * (i1_extend[i] - i1_extend[i - 1])

        return delta_adjusted

