# core/model_trainer.py
import os, joblib, logging, optuna, datetime, math
import numpy as np
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error
from optuna.samplers import TPESampler
from optuna.visualization import plot_optimization_history
from PySide6.QtCore import QTimer
from .config import CONFIG, TUNING_CONFIG
from .feature_extractor import FeatureExtractor
from .data_pipeline import DataPipeline
from .cluster_regressor import ClusterRegressor
from .visualizer import Visualizer
from .utils import get_unique_timestamp_dir


class ModelTrainer:
    def __init__(self, config=CONFIG, tuning_config=TUNING_CONFIG, app=None, training_worker=None):
        self.logger = logging.getLogger("ModelTrainer")
        self.logger.info("模型训练器初始化")
        self.config = config
        self.tuning_config = tuning_config
        self.fe = FeatureExtractor()
        self.study = None
        self.best_params = None
        self.model = None
        self.pipeline = None
        self.model_dir = None
        self.X = None
        self.app = app
        self.training_worker = training_worker  # 添加训练工作线程引用

    def _load_dataset(self):
        """加载数据集"""
        self.logger.info("开始加载数据集")
        print("正在加载数据集...")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        features = []
        labels = []
        try:
            for fname in os.listdir(self.config["data_path"]):
                # 检查是否需要停止训练
                if self.app and self.app.stop_training_flag:
                    raise optuna.exceptions.OptunaError("训练被用户中断")

                if not fname.startswith("Rn_") or not fname.endswith(".png"):
                    continue

                try:
                    # 提取特征
                    img_path = os.path.join(self.config["data_path"], fname)
                    features.append(self.fe.extract(img_path))

                    # 解析标签
                    parts = fname.split('_')[1].rsplit('.', 2)
                    label = int(parts[0]) + int(parts[1]) * round(math.pow(0.1, len(parts[1])), len(parts[1]))
                    labels.append(label)
                except Exception as e:
                    print(f"处理文件 {fname} 时出错: {str(e)}")

            self.X = np.array(features)
            y = np.array(labels)
            print(f"成功加载 {len(self.X)} 个样本")
            if len(self.X) < 10:
                raise ValueError(f"有效样本不足（{len(self.X)}），至少需要10个样本")
            self.logger.info(f"成功加载 {len(self.X)} 个样本，{len(np.unique(y))} 种折射率")
            return self.X, y

        except ValueError:
            self.logger.error(f"有效样本不足（{len(self.X)}），至少需要10个样本")

    def _objective(self, trial, X, y):
        """超参数优化目标函数"""
        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        # 动态调整最大聚类数
        max_clusters = max(2, min(5, len(X) // 5))
        params = {
            "n_clusters": trial.suggest_int("n_clusters", 2, max_clusters),
            "svr_kernel": trial.suggest_categorical("svr_kernel", ["rbf", "linear"]),
            "svr_C": trial.suggest_float("svr_C", 1e-3, 1e3, log=True),
            "svr_epsilon": trial.suggest_float("svr_epsilon", 1e-6, 0.1, log=True)
        }

        kf = KFold(n_splits=self.tuning_config["cv_folds"], shuffle=True)
        mae_scores = []

        for train_idx, val_idx in kf.split(X):
            # 检查是否需要停止训练
            if self.app and self.app.stop_training_flag:
                raise optuna.exceptions.OptunaError("训练被用户中断")

            try:
                X_train, X_val = X[train_idx], X[val_idx]
                y_train, y_val = y[train_idx], y[val_idx]

                pipeline = DataPipeline(params["n_clusters"])
                X_train_proc, train_clusters = pipeline.process_data(X_train, training=True)

                # 检查是否需要停止训练
                if self.app and self.app.stop_training_flag:
                    raise optuna.exceptions.OptunaError("训练被用户中断")

                # 检查有效聚类数
                valid_clusters = len(np.unique(train_clusters))
                if valid_clusters < 2:
                    raise ValueError("有效聚类数不足")

                model = ClusterRegressor({
                    "kernel": params["svr_kernel"],
                    "C": params["svr_C"],
                    "epsilon": params["svr_epsilon"]
                })
                model.train(X_train_proc, y_train, train_clusters)

                # 检查是否需要停止训练
                if self.app and self.app.stop_training_flag:
                    raise optuna.exceptions.OptunaError("训练被用户中断")

                X_val_proc, val_clusters = pipeline.process_data(X_val)
                y_pred = model.predict(X_val_proc, val_clusters)

                # 最终保护
                y_pred = np.nan_to_num(y_pred, nan=model.global_mean)
                mae = mean_absolute_error(y_val, y_pred)
                mae_scores.append(mae)

            except Exception as e:
                print(f"交叉验证失败: {str(e)}")
                mae_scores.append(np.inf)  # 惩罚无效参数组合

        return np.nanmean(mae_scores)

    def tune_hyperparameters(self, X_train, y_train):
        """执行超参数优化"""
        self.logger.info("开始超参数优化")
        print("\n=== 开始超参数优化 ===")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            print("\n=== 训练已被用户中断 ===")
            self.logger.info("超参数优化被用户中断")
            return None

        self.study = optuna.create_study(
            direction="minimize",
            sampler=TPESampler(seed=42)
        )

        try:
            self.study.optimize(
                lambda trial: self._objective(trial, X_train, y_train),
                n_trials=self.tuning_config["n_trials"],
                timeout=self.tuning_config["timeout"],
                callbacks=[lambda study, trial: print(
                    f"{datetime.datetime.now()} 试验{trial.number}完成，得到值为{trial.value:.8f}，参数为{trial.params}，当前最佳值: {study.best_value:.8f}")]
            )
        except optuna.exceptions.OptunaError as e:
            if "训练被用户中断" in str(e):
                print("\n=== 训练已被用户中断 ===")
                self.logger.info("超参数优化被用户中断")
                return None
            else:
                raise e

        # 保存优化历史
        fig = plot_optimization_history(self.study)
        fig.update_layout(
            title="优化历史记录",
            xaxis_title="试验次数",
            yaxis_title="目标值",
            font=dict(size=18),
            plot_bgcolor="white"
        )
        # 保存到当前模型目录
        fig.write_html(os.path.join(self.model_dir, "optimization_history.html"))
        print(f"优化历史已保存至 {self.model_dir} 目录")
        self.best_params = self.study.best_params
        print("\n=== 最佳参数 ===")
        print(self.best_params)
        self.logger.info(f"超参数优化完成，最佳MAE: {self.study.best_value:.4f}")
        self.logger.info(f"最佳参数: {self.best_params}")

        return self.best_params

    def train_final_model(self, X_train, y_train, best_params):
        """使用最佳参数训练最终模型"""
        self.logger.info("开始训练最终模型")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        self.pipeline = DataPipeline(best_params["n_clusters"])
        X_train_proc, train_clusters = self.pipeline.process_data(X_train, training=True)

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        svr_params = {
            "kernel": best_params["svr_kernel"],
            "C": best_params["svr_C"],
            "epsilon": best_params["svr_epsilon"]
        }
        self.model = ClusterRegressor(svr_params)
        self.model.train(X_train_proc, y_train, train_clusters)

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        self.logger.info("最终模型训练完成")
        return self.model, self.pipeline

    def evaluate_model(self, X_test, y_test):
        """评估模型性能"""
        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        X_test_proc, test_clusters = self.pipeline.process_data(X_test)
        y_pred = self.model.predict(X_test_proc, test_clusters)

        print("\n=== 最终评估 ===")
        print(f"测试集 MAE: {mean_absolute_error(y_test, y_pred):.4f}")
        print(f"测试集 MSE: {mean_squared_error(y_test, y_pred):.4f}")
        return y_pred

    def save_model(self):
        """保存整个模型到当前模型目录"""
        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        if not self.model_dir:
            raise ValueError("模型目录未设置")

        # 创建子目录
        os.makedirs(os.path.join(self.model_dir, "models"), exist_ok=True)
        os.makedirs(os.path.join(self.model_dir, "results"), exist_ok=True)

        # 保存模型
        self.fe.save(os.path.join(self.model_dir, "models", self.config["save_part"]))

        # 设置类的模块路径
        self.pipeline.__class__.__module__ = 'core.data_pipeline'
        self.model.__class__.__module__ = 'core.cluster_regressor'

        joblib.dump(
            {
                "pipeline": self.pipeline,
                "regressor": self.model,
                "best_params": self.best_params
            },
            os.path.join(self.model_dir, "models", self.config["save_model"])
        )
        print(f"模型已保存至 {self.model_dir} 目录")

    def run_training(self):
        """执行完整训练流程"""
        self.logger.info("开始完整训练流程")
        # 创建唯一模型目录
        self.model_dir = get_unique_timestamp_dir(CONFIG["base_model_dir"])
        print(f"本次运行结果将保存至: {self.model_dir}")

        # 在主界面显示训练开始信息
        if self.training_worker:
            self.training_worker.training_message.emit("分簇开始", "正在数据分簇...")
        self.logger.info("正在数据分簇过程...")

        # 加载数据集
        X, y = self._load_dataset()

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在数据加载阶段被用户中断")
            return self.model_dir

        # 划分数据集
        X_train_all, X_test, y_train_all, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42)

        print(f"\n数据集划分：")
        print(f"- 训练样本: {len(X_train_all)}")
        print(f"- 测试样本: {len(X_test)}")

        if self.training_worker:
            self.training_worker.training_message.emit("训练开始", "训练中，请稍等...")
        self.logger.info("训练中，请稍等...")

        # 当训练样本过少时自动调整聚类数
        if len(X_train_all) < 50:
            self.config["n_clusters"] = max(2, min(3, len(X_train_all) // 10))
            print(f"调整聚类数为: {self.config['n_clusters']}")

        # 超参数优化
        best_params = self.tune_hyperparameters(X_train_all, y_train_all)

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在超参数优化阶段被用户中断")
            return self.model_dir

        # 如果超参数优化被中断，则直接返回
        if best_params is None:
            return self.model_dir

        # 训练最终模型
        self.train_final_model(X_train_all, y_train_all, best_params)

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在最终模型训练阶段被用户中断")
            return self.model_dir

        # 评估模型
        y_pred = self.evaluate_model(X_test, y_test)

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在模型评估阶段被用户中断")
            return self.model_dir

        # 保存模型
        self.save_model()

        # 可视化
        print("生成可视化图表...")
        Visualizer.create_dir(self.model_dir)
        feature_plot_path = Visualizer.plot_features(X_train_all, y_train_all, self.model_dir)
        cluster_plot_path = Visualizer.plot_clusters(self.pipeline.kmeans.labels_, self.model_dir)
        result_plot_path = Visualizer.plot_results(y_test, y_pred, self.model_dir)

        # 在主界面显示训练完成信息和图片
        if self.training_worker:
            QTimer.singleShot(0, lambda: self.training_worker.training_message.emit("训练完成", f"模型已保存至 {self.model_dir} 目录"))

        self.logger.info(f"训练完成! 模型保存至: {self.model_dir}")
        return self.model_dir
