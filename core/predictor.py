# core.predictor.py
import os, joblib, logging, sys, types
from selenium import webdriver
from selenium.webdriver.edge.service import Service
from selenium.webdriver.edge.options import Options

from .config import CONFIG
from .feature_extractor import FeatureExtractor
from .data_pipeline import DataPipeline
from .cluster_regressor import ClusterRegressor

class RefractiveIndexPredictor:
    def __init__(self, model_dir):
        # 加载特征提取器
        self.logger = logging.getLogger("Predictor")
        self.logger.info(f"加载预测器，模型目录: {model_dir}")
        self.fe = FeatureExtractor.load(
            os.path.join(model_dir, "models", CONFIG["save_part"]),
            CONFIG["input_size"]
        )
        # 加载其他组件
        model_path = os.path.join(model_dir, "models", CONFIG["save_model"])
        self._create_main_module()
        data = joblib.load(model_path)

        # 存储优化历史路径
        self.html = os.path.join(model_dir, "optimization_history.html")
        self.model_dir = model_dir
        self.driver = None
        self.pipeline = data["pipeline"]
        self.regressor = data["regressor"]
        self.best_params = data.get("best_params", {})  # 获取优化参数

    def _create_main_module(self):
        """创建伪 __main__ 模块以兼容旧模型"""
        # 检查是否已经存在伪模块
        if not hasattr(sys, 'frozen_main'):
            sys.frozen_main = types.ModuleType('__main__')
            sys.modules['__main__'] = sys.frozen_main

            # 将当前类添加到伪模块中
            sys.frozen_main.DataPipeline = DataPipeline
            sys.frozen_main.ClusterRegressor = ClusterRegressor

    def get_optimization_history(self):
        """获取优化历史"""
        if not os.path.exists(self.html):
            raise FileNotFoundError(f"文件不存在: {self.html}")
        absolute_path = os.path.abspath(self.html)
        if os.name == 'nt':
            absolute_path = absolute_path.replace('\\', '/')
            file_url = f"file:///{absolute_path}"
        else:
            file_url = f"file://{absolute_path}"

        edge_options = Options()
        edge_options.add_argument("--start-maximized")  # 最大化窗口
        edge_options.add_argument("--disable-extensions")  # 禁用扩展
        edge_options.add_argument("--disable-infobars")  # 禁用信息栏

        edge_service = Service(executable_path=os.path.abspath('.\WebDriver\msedgedriver.exe'))
        self.driver = webdriver.Edge(
            service=edge_service,  
            options=edge_options
        )

        self.driver.get(file_url)

    def close_browser(self):
        """关闭浏览器"""
        if self.driver:
            self.driver.quit()

    def predict(self, img_path):
        """预测折射率"""
        self.logger.info(f"开始预测折射率，图像: {img_path}")
        try:
            # 特征提取
            features = self.fe.extract(img_path)
            # 预处理
            processed, cluster = self.pipeline.process_data(
                features.reshape(1, -1))

            # 预测
            prediction = self.regressor.predict(processed, cluster)[0]
            self.logger.info(f"预测完成! 折射率: {prediction:.4f}")
            return round(prediction, 4)

        except Exception as e:
            print(f"预测失败: {str(e)}")
            self.logger.error(f"预测失败: {str(e)}")
            return None