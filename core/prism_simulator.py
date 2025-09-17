# core/prism_simulator.py
import os, math, logging, gc
import numpy as np
import matplotlib.pyplot as plt

from .config import CONFIG

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False


class PrismSimulator:
    """理论数据生成接口"""
    def __init__(self, base_dir=CONFIG["base_dir"], output_callback=None, progress_callback=None):
        self.base_dir = base_dir
        self.output_folder = CONFIG["data_path"]
        self.actual_folder = CONFIG["actual_data_dir"]
        self.i1_deg = 45  # 初始入射角
        self.i2_deg = 80  # 终止入射角
        self.prism_angle = 60  # 棱镜角度
        self._create_folders()
        self.logger = logging.getLogger("PrismSimulator")
        self.output_callback = output_callback  # 输出回调函数
        self.progress_callback = progress_callback
        self.stop_flag = False  # 停止标志
        self.logger.info(f"分光计模拟器初始化，输出目录: {base_dir}")

    def _create_folders(self):
        """创建必要的输出文件夹"""
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.actual_folder, exist_ok=True)

    def _update_progress(self, current, total, message=""):
        """更新进度信息"""
        if self.output_callback:
            self.output_callback(current, total, message)
        if self.progress_callback:
            self.progress_callback(current, total, message)

    def set_stop_flag(self, flag=True):
        """设置停止标志"""
        self.stop_flag = flag

    def _calculate_deviation(self, Rn, start_angle, step_size=0.1):
        """计算给定折射率的偏向角数据"""
        results = []
        i1_current = start_angle
        steps = int((self.i2_deg - self.i1_deg) / step_size + 1)

        for _ in range(steps):
            i1_rad = math.radians(i1_current)
            sin_i1 = math.sin(i1_rad)

            # 计算折射角 r1
            r1_deg = math.degrees(math.asin(sin_i1 / Rn))

            # 计算第二个面的入射角
            r2_deg = self.prism_angle - r1_deg

            # 计算出射角 i2
            sin_r2 = math.sin(math.radians(r2_deg))
            i2_deg = math.degrees(math.asin(Rn * sin_r2))

            # 计算偏向角
            delta_deg = i1_current + i2_deg - self.prism_angle

            results.append((i1_current, delta_deg, Rn))
            i1_current += step_size

        return np.array(results)

    def generate_theoretical_data(self, rn_range=np.linspace(1.5, 1.700, 201)):
        """生成理论数据并保存图像"""
        self.logger.info(f"开始生成理论数据，折射率范围: {rn_range[0]:.3f} 到 {rn_range[-1]:.3f}")
        total, all_results = len(rn_range), []

        # 初始化进度
        self._update_progress(0, total, "开始生成理论数据...")
        for i, Rn in enumerate(rn_range):
            # 检查是否需要停止
            if self.stop_flag:
                self.logger.info("理论数据生成被用户中断")
                self._update_progress(i, total, "理论数据生成被用户中断")
                break

            try:
                data = self._calculate_deviation(Rn, self.i1_deg)
                all_results.append(data)

                if not self.stop_flag:
                    os.makedirs(self.output_folder, exist_ok=True)

                    filename = os.path.join(self.output_folder, f"Rn_{Rn:.3f}.png")
                    plt.figure(figsize=(6, 6))
                    plt.plot(data[:, 0], data[:, 1])
                    plt.ylim(45, 80)
                    plt.xlim(45, 80)
                    plt.grid(True)
                    plt.savefig(filename, dpi=400)
                    plt.close()

                # 更新进度
                progress = i + 1
                percent = (progress / total) * 100
                self._update_progress(progress, total,f"进度: {percent:.1f}% | 当前折射率: {Rn:.3f}")

                # 显式清理内存
                plt.close('all')
                gc.collect()
            except Exception as e:
                self.logger.error(f"生成折射率 {Rn:.3f} 的数据时出错: {str(e)}")
                if self.stop_flag:
                    break
                continue

        # 合并所有结果
        if not self.stop_flag and all_results:
            full_array = np.vstack(all_results)
            self.logger.info(f"成功生成 {len(rn_range)} 组理论数据")
            self._update_progress(total, total, "所有理论数据生成完成！")
            return full_array
        else:
            self.logger.info(f"理论数据生成中断，已生成 {len(all_results)} 组数据")
            self._update_progress(len(all_results), total, "理论数据生成被用户中断")
            return np.vstack(all_results) if all_results else np.array([])
