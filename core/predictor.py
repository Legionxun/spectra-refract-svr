# core.predictor.py
import os, joblib, logging, sys, types, subprocess, psutil, time

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
        self.browser_process = None
        self.browser_pids = set()  # 用于跟踪所有可能的浏览器进程

    def get_app_path(self):
        """获取应用程序路径的公共函数"""
        if hasattr(sys, '_APP_PATH'):
            return sys._APP_PATH
        elif getattr(sys, 'frozen', False):
            return os.path.dirname(sys.executable)
        else:
            return os.path.dirname(os.path.abspath(__file__))

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
        """获取优化历史 - 使用系统默认浏览器"""
        if not os.path.exists(self.html):
            raise FileNotFoundError(f"文件不存在: {self.html}")

        # 获取绝对路径
        absolute_path = os.path.abspath(self.html)
        self.logger.info(f"准备打开优化历史文件: {absolute_path}")

        try:
            # 记录打开前的浏览器进程
            before_pids = set(p.info['pid'] for p in psutil.process_iter(['pid', 'name'])
                              if any(browser in p.info['name'].lower()
                                     for browser in ['chrome', 'firefox', 'edge', 'safari', 'browser']))

            if os.name == 'nt':  # Windows系统
                cmd = f'start "" "{absolute_path}"'
                self.browser_process = subprocess.Popen(cmd, shell=True)
            else:  # Linux/Mac系统
                self.browser_process = subprocess.Popen(['xdg-open', absolute_path])

            # 等待一小段时间让浏览器进程启动
            time.sleep(0.5)

            # 记录可能的新浏览器进程
            after_pids = set(p.info['pid'] for p in psutil.process_iter(['pid', 'name'])
                             if any(browser in p.info['name'].lower()
                                    for browser in ['chrome', 'firefox', 'edge', 'safari', 'browser']))

            # 保存新启动的浏览器进程PID
            self.browser_pids = after_pids - before_pids
            self.browser_pids.add(self.browser_process.pid)

            self.logger.info(f"使用subprocess打开优化历史, PID={self.browser_process.pid}")
            self.logger.info(f"跟踪的浏览器进程: {self.browser_pids}")
            return True
        except Exception as e:
            self.logger.error(f"所有打开方法均失败: {str(e)}")
            raise RuntimeError(
                f"无法打开优化历史文件:\n"
                f"请尝试手动打开: {absolute_path}\n"
                f"错误详情: {str(e)}"
            )

    def close_browser(self):
        """关闭浏览器进程"""
        if not self.browser_process and not self.browser_pids:
            self.logger.info("没有浏览器进程需要关闭")
            return True

        # 收集所有需要关闭的进程
        processes_to_close = set()

        # 1. 添加通过subprocess启动的进程及其子进程
        if self.browser_process:
            try:
                parent = psutil.Process(self.browser_process.pid)
                processes_to_close.add(parent)
                # 添加所有子进程
                processes_to_close.update(parent.children(recursive=True))
            except psutil.NoSuchProcess:
                self.logger.info(f"浏览器进程已不存在: PID={self.browser_process.pid}")

        # 2. 添加跟踪到的浏览器进程
        for pid in self.browser_pids:
            try:
                process = psutil.Process(pid)
                processes_to_close.add(process)
            except psutil.NoSuchProcess:
                self.logger.info(f"浏览器进程已不存在: PID={pid}")

        # 3. 查找命令行中包含HTML文件名的进程
        try:
            html_filename = os.path.basename(self.html)
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if proc.info['cmdline'] and any(html_filename in cmd for cmd in proc.info['cmdline']):
                        processes_to_close.add(proc)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            self.logger.error(f"查找相关浏览器进程时出错: {str(e)}")

        # 关闭所有收集到的进程
        closed_count = 0
        for process in processes_to_close:
            try:
                if process.is_running():
                    process.terminate()
                    closed_count += 1
            except psutil.NoSuchProcess:
                pass
            except Exception as e:
                self.logger.error(f"终止进程 {process.pid} 时出错: {str(e)}")

        # 等待进程结束
        if processes_to_close:
            gone, alive = psutil.wait_procs(list(processes_to_close), timeout=3)
            # 强制杀死未响应的进程
            for process in alive:
                try:
                    process.kill()
                    closed_count += 1
                except psutil.NoSuchProcess:
                    pass
                except Exception as e:
                    self.logger.error(f"强制终止进程 {process.pid} 时出错: {str(e)}")

        self.logger.info(f"已关闭 {closed_count} 个浏览器相关进程")

        # 清理状态
        self.browser_process = None
        self.browser_pids.clear()
        return True

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
