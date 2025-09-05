# core.config.py
import os
from .utils import get_output_path

# ======================
# 环境变量
# ======================
os.environ["OMP_NUM_THREADS"] = "1"  # 解决KMeans内存泄漏
os.environ["LOKY_MAX_CPU_COUNT"] = "16"  # 根据物理核心数设置

# ======================
# 配置参数
# ======================
CONFIG = {
    "data_path": get_output_path(r".\template"),  # 数据集路径
    "download": get_output_path(r".\download"), # 下载保存路径
    "current_version": "1.2.0",
    "input_size": (128, 128),  # 输入图像尺寸
    "n_clusters": 3,  # 聚类数量
    "pretrained_layer": "conv4_block6_out",  # 使用的预训练层
    "save_picture": "results",
    "save_part": "feature_extractor",
    "save_model": "pretrained_model.pkl",  # 模型保存路径
    "physical_cores": 16,  # 实际物理核心数
    "base_model_dir": "saved_models"  # 基础模型目录
}

TUNING_CONFIG = {
    "n_trials": 100,  # 优化试验次数
    "timeout": 7200,  # 最大优化时间(秒)
    "cv_folds": 3,  # 交叉验证折数
    "svr_c_range": (1e-3, 1e3),  # SVR正则化参数范围
    "epsilon_range": (1e-6, 1e-3),  # SVR容忍度范围
    "n_clusters_range": (2, 5)  # 聚类数量范围
}