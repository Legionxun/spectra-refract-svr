# core/config.py
import os
from .utils import get_output_path

# 环境变量
os.environ["OMP_NUM_THREADS"] = "1"  # 解决KMeans内存泄漏
os.environ["LOKY_MAX_CPU_COUNT"] = "16"  # 根据物理核心数设置


# ======================
# 配置参数
# ======================
CONFIG = {
    "base_dir": get_output_path(r"."),  # 基础目录
    "img": get_output_path(r".\img"), # 系统图片路径
    "download": get_output_path(r".\download"), # 下载保存路径
    "temp_dir": get_output_path(r".\temp"),  # 临时目录
    "prediction_results": get_output_path(r".\prediction_results"), # 预测结果保存路径
    "history_dir": get_output_path(r".\history"),  # 历史记录路径
    "settings_dir": get_output_path(r".\settings"),  # 配置文件保存路径
    "data_path": get_output_path(r".\template"),  # 数据集路径
    "actual_data_dir": get_output_path(r".\actual_data"),  # 预测图像路径
    "LibreHardwareMonitor": get_output_path(r".\LibreHardwareMonitor"), # 获取硬件信息dll文件路径
    "monitoring_logs": get_output_path(r".\monitoring_logs"), # 硬件监控日志保存路径
    "resnet50": get_output_path(r".\resnet50"), # 预训练模型保存路径
    "input_size": (128, 128),  # 输入图像尺寸
    "n_clusters": 3,  # 聚类数量
    "pretrained_layer": "conv4_block6_out",  # 使用的预训练层
    "save_picture": "results",  # 模型数据保存路径
    "save_part": "feature_extractor", # 数据特征保存路径
    "save_model": "pretrained_model.pkl",  # 模型保存路径
    "physical_cores": 16,  # 实际物理核心数
    "base_model_dir": "saved_models"  # 基础模型目录
}


# ======================
# 优化参数
# ======================
TUNING_CONFIG = {
    "n_trials": 100,  # 优化试验次数
    "timeout": 7200,  # 最大优化时间(秒)
    "cv_folds": 3,  # 交叉验证折数
    "svr_c_range": (1e-6, 1e6),  # SVR正则化参数范围
    "epsilon_range": (1e-6, 1e-3),  # SVR容忍度范围
    "n_clusters_range": (2, 5),  # 聚类数量范围
    "bayesian_trials": 100,  # 贝叶斯优化试验次数
    "optimization_method": "hybrid"  # 默认优化方法: "optuna", "bayesian", "hybrid"
}


# ======================
# 默认快捷键配置
# ======================
DEFAULT_SHORTCUTS = {
    # 数据处理
    "generate_theoretical_data": "Ctrl+G",
    "custom_generate_theoretical_data": "Ctrl+Shift+G",
    "stop_generation": "Ctrl+Z",
    "data_augmentation": "Ctrl+Shift+U",

    # 文件操作
    "save_results": "Ctrl+S",
    "import_original": "Ctrl+O",
    "import_processed": "Ctrl+Shift+O",
    "exit_app": "Ctrl+Q",

    # 模型操作
    "start_training": "Ctrl+T",
    "stop_training": "Ctrl+X",
    "load_model": "Ctrl+L",
    "export_model": "Ctrl+E",

    # 预测分析
    "predict_refractive_index": "Ctrl+P",
    "batch_prediction": "Ctrl+B",

    # 查看分析
    "show_optimization_history": "Ctrl+O",
    "show_visualizations": "Ctrl+V",
    "compare_models": "Ctrl+M",

    # 历史记录
    "show_prediction_history": "Ctrl+H",
    "show_monitoring_logs": "Ctrl+N",

    # 系统工具
    "system_monitor": "Ctrl+Y",
    "refresh_page": "F5",
    "clear_chart": "Ctrl+D",
    "clear_output": "Ctrl+Shift+D",

    # 帮助
    "toggle_theme": "Alt+D",
    "show_usage_guide": "F1",
    "show_shortcuts_dialog": "Ctrl+K",
    "customize_shortcuts": "Ctrl+Shift+K",
    "check_for_updates": "Ctrl+U",
    "show_about": "Ctrl+A"
}
