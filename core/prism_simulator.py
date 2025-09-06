# core.prism_simulator.py
import os, math, logging
import numpy as np
import matplotlib.pyplot as plt
from .utils import get_output_path

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False


class PrismSimulator:
    def __init__(self, base_dir=".", output_callback=None):
        self.base_dir = base_dir
        self.output_folder = get_output_path(os.path.join(base_dir, "template"))
        self.actual_folder = get_output_path(os.path.join(base_dir, "actual_data"))
        self.i1_deg = 44  # 初始入射角
        self.prism_angle = 60  # 棱镜角度
        self._create_folders()
        self.logger = logging.getLogger("PrismSimulator")
        self.output_callback = output_callback  # 新增：输出回调函数
        self.stop_flag = False  # 添加停止标志
        self.logger.info(f"棱镜模拟器初始化，输出目录: {base_dir}")

    def _create_folders(self):
        """创建必要的输出文件夹"""
        os.makedirs(self.output_folder, exist_ok=True)
        os.makedirs(self.actual_folder, exist_ok=True)

    def _update_progress(self, current, total, message=""):
        """更新进度信息"""
        if self.output_callback:
            self.output_callback(current, total, message)

    def set_stop_flag(self, flag=True):
        """设置停止标志"""
        self.stop_flag = flag

    def _calculate_deviation(self, Rn, start_angle, steps=73, step_size=0.5):
        """计算给定折射率的偏向角数据"""
        results = []
        i1_current = start_angle

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

    def generate_theoretical_data(self, rn_range=np.arange(1.5, 1.701, 0.001)):
        """生成理论数据并保存图像"""
        self.logger.info(f"开始生成理论数据，折射率范围: {rn_range[0]:.3f} 到 {rn_range[-1]:.3f}")
        total = len(rn_range)
        all_results = []

        # 初始化进度
        self._update_progress(0, total, "开始生成理论数据...")

        for i, Rn in enumerate(rn_range):
            # 检查是否需要停止
            if self.stop_flag:
                self.logger.info("理论数据生成被用户中断")
                self._update_progress(i, total, "理论数据生成被用户中断")
                break

            data = self._calculate_deviation(Rn, self.i1_deg)
            all_results.append(data)
            filename = os.path.join(self.output_folder, f"Rn_{Rn:.3f}.png")

            # 绘制并保存单个折射率的图像
            plt.figure(figsize=(4, 4))
            plt.plot(data[:, 0], data[:, 1], label=f"Rn={Rn:.3f}")
            plt.ylim(45, 80)
            plt.xlim(45, 80)
            plt.xlabel("入射角 i1 (度)")
            plt.ylabel("偏向角 delta (度)")
            plt.title(f"Rn = {Rn:.3f}")
            plt.grid(True)
            plt.legend()
            plt.savefig(filename)
            plt.close()

            # 更新进度
            progress = i + 1
            percent = (progress / total) * 100
            self._update_progress(progress, total,
                                  f"进度: {percent:.1f}% | 当前折射率: {Rn:.3f}")

            # 显式清理内存
            plt.close('all')
            import gc
            gc.collect()

        # 合并所有结果
        if not self.stop_flag:
            full_array = np.vstack(all_results)
            self.logger.info(f"成功生成 {len(rn_range)} 组理论数据")
            self._update_progress(total, total, "所有理论数据生成完成！")
            return full_array
        else:
            self.logger.info(f"理论数据生成中断，已生成 {len(all_results)} 组数据")
            self._update_progress(len(all_results), total, "理论数据生成被用户中断")
            return np.vstack(all_results) if all_results else np.array([])
