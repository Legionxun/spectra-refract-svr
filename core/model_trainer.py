# core/model_trainer.py
import os, joblib, logging, optuna, datetime, math, time, shutil
import numpy as np
from sklearn.model_selection import train_test_split, KFold
from sklearn.metrics import mean_absolute_error, mean_squared_error
from optuna.samplers import TPESampler
from optuna.visualization import plot_optimization_history
from PySide6.QtCore import QTimer, Signal, QObject, QMutex
from bayes_opt import BayesianOptimization
import plotly.graph_objects as go
import plotly.offline as pyo

from .config import CONFIG, TUNING_CONFIG
from .feature_extractor import FeatureExtractor
from .data_pipeline import DataPipeline
from .cluster_regressor import ClusterRegressor
from .visualizer import Visualizer
from .utils import get_unique_timestamp_dir

os.environ['PYTHONIOENCODING'] = 'utf-8-sig'


class ProgressSignal(QObject):
    """进度信号接口"""
    progress_updated = Signal(int, int, str)  # 当前进度, 总进度, 描述


class ModelTrainer:
    """模型训练器接口"""
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
        self.grid_size = None
        self.app = app
        self.training_worker = training_worker  # 添加训练工作线程引用
        self.progress_signal = ProgressSignal()  # 进度信号
        self.last_progress_update = 0  # 用于控制进度更新频率
        self.optimization_method = self.tuning_config.get("optimization_method", "hybrid")  # 获取优化方法配置，默认使用混合方法
        self.clustering_method = self.tuning_config.get("clustering_method", "kmeans")  # 获取聚类方法配置，默认使用KMeans
        self._progress_mutex = QMutex()  # 添加互斥锁保护进度更新

    def _load_dataset(self):
        """加载数据集"""
        self.logger.info("开始加载数据集")
        print("正在加载数据集...")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        features, labels = [], []
        try:
            file_list = [f for f in os.listdir(self.config["data_path"]) if f.startswith("Rn_") and f.endswith(".png")]
            total_files = len(file_list)

            for idx, fname in enumerate(file_list):
                # 检查是否需要停止训练
                if self.app and self.app.stop_training_flag:
                    raise optuna.exceptions.OptunaError("训练被用户中断")

                # 更新进度 - 使用互斥锁保护，并控制更新频率
                if idx % max(1, total_files // 100) == 0 or idx + 1 == total_files:
                    self._progress_mutex.lock()
                    try:
                        if hasattr(self.app, 'trainer_progress_signal') and self.app.trainer_progress_signal:
                            progress_desc = f"加载数据文件 {idx + 1}/{total_files}"
                            total_progress = int(20 * (idx + 1) / total_files)
                            self.app.trainer_total_progress_signal(total_progress)
                            self.app.trainer_progress_signal(idx + 1, total_files, progress_desc)
                    finally:
                        self._progress_mutex.unlock()

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

        # 根据聚类方法选择不同的参数空间
        if self.clustering_method == "kmeans":
            params = {
                "n_clusters": trial.suggest_int("n_clusters", 2, max_clusters),
                "svr_kernel": trial.suggest_categorical("svr_kernel", ["rbf", "linear"]),
                "svr_C": trial.suggest_float("svr_C", 1e-6, 1e6, log=True),
                "svr_epsilon": trial.suggest_float("svr_epsilon", 1e-6, 1e-3, log=True)
            }
        else:  # SOM聚类
            # 动态调整SOM网格大小
            max_grid_size = max(2, min(5, int(np.sqrt(len(X)) // 2)))
            params = {
                "grid_size": trial.suggest_int("grid_size", 2, max_grid_size),
                "svr_kernel": trial.suggest_categorical("svr_kernel", ["rbf", "linear"]),
                "svr_C": trial.suggest_float("svr_C", 1e-6, 1e6, log=True),
                "svr_epsilon": trial.suggest_float("svr_epsilon", 1e-6, 1e-3, log=True)
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

                if self.clustering_method == "kmeans":
                    # KMeans聚类
                    pipeline = DataPipeline(params["n_clusters"], clustering_method="kmeans")
                else:
                    # SOM聚类
                    pipeline = DataPipeline(params["grid_size"], clustering_method="som")

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

        # 根据选择的方法执行超参数优化
        if self.optimization_method == "bayesian":
            return self._tune_with_bayesian(X_train, y_train)
        elif self.optimization_method == "optuna":
            return self._tune_with_optuna(X_train, y_train)
        else:  # 默认使用混合方法
            # 先使用贝叶斯优化快速探索参数空间
            bayesian_history = {}  # 用于存储贝叶斯优化历史
            bayesian_params = self._tune_with_bayesian(X_train, y_train, bayesian_history)
            # 再使用Optuna进行精细调优，并传递贝叶斯优化历史
            return self._tune_with_optuna(X_train, y_train, initial_params=bayesian_params,
                                          bayesian_history=bayesian_history)

    def _tune_with_bayesian(self, X_train, y_train, history=None):
        """使用贝叶斯优化执行超参数优化"""
        self.logger.info("开始贝叶斯超参数优化")
        print("\n=== 开始贝叶斯超参数优化 ===")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            print("\n=== 训练已被用户中断 ===")
            self.logger.info("贝叶斯超参数优化被用户中断")
            return None

        # 存储优化历史
        optimization_history = {
            'trial_number': [],
            'target': [],
            'best_target': [],  # 添加最优目标值历史
            'params': []
        }

        # 定义参数边界,动态调整最大聚类数
        max_clusters = max(2, min(5, len(X_train) // 5))

        # 贝叶斯优化迭代计数器
        bayesian_trial_count = 0
        total_bayesian_trials = self.tuning_config.get("bayesian_trials", 20) + 5  # 5是初始探索点
        best_target_value = -np.inf  # 跟踪最优目标值
        last_update_time = 0  # 上次更新时间

        def bayesian_objective(n_clusters, svr_C, svr_epsilon, svr_kernel_choice):
            nonlocal bayesian_trial_count, best_target_value, last_update_time

            # 检查是否需要停止训练
            if self.app and self.app.stop_training_flag:
                raise KeyboardInterrupt("训练被用户中断")

            # 更新进度 - 使用互斥锁保护
            bayesian_trial_count += 1
            progress_desc = f"贝叶斯优化迭代 {bayesian_trial_count}/{total_bayesian_trials}"

            # 控制更新频率，避免过于频繁的GUI更新
            current_time = time.time()
            should_update = (current_time - last_update_time > 0.5) or (bayesian_trial_count == total_bayesian_trials)
            if should_update:
                self._progress_mutex.lock()
                try:
                    self.progress_signal.progress_updated.emit(bayesian_trial_count, total_bayesian_trials,
                                                               progress_desc)

                    # 同时更新总进度
                    if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
                        if self.optimization_method == "bayesian":
                            # 贝叶斯模式
                            total_progress = int(20 + 60 * bayesian_trial_count / total_bayesian_trials)
                        else:
                            # 混合模式
                            total_progress = int(20 + 30 * bayesian_trial_count / total_bayesian_trials)
                        self.app.trainer_total_progress_signal(total_progress)
                        self.app.trainer_progress_signal(bayesian_trial_count, total_bayesian_trials, progress_desc)
                    last_update_time = current_time
                finally:
                    self._progress_mutex.unlock()

            # 将连续的svr_kernel_choice转换为离散值
            svr_kernel = "rbf" if svr_kernel_choice >= 0.5 else "linear"

            # 转换参数类型
            if self.clustering_method == "kmeans":
                n_clusters = int(round(n_clusters))
            else:
                self.grid_size = int(round(n_clusters))
            svr_C = float(svr_C)
            svr_epsilon = float(svr_epsilon)

            # 使用KFold交叉验证
            kf = KFold(n_splits=self.tuning_config["cv_folds"], shuffle=True)
            mae_scores = []

            for train_idx, val_idx in kf.split(X_train):
                try:
                    X_train_fold, X_val_fold = X_train[train_idx], X_train[val_idx]
                    y_train_fold, y_val_fold = y_train[train_idx], y_train[val_idx]

                    if self.clustering_method == "kmeans":
                        pipeline = DataPipeline(n_clusters, clustering_method="kmeans")
                    else:
                        pipeline = DataPipeline(self.grid_size, clustering_method="som")

                    X_train_proc, train_clusters = pipeline.process_data(X_train_fold, training=True)

                    # 检查有效聚类数
                    valid_clusters = len(np.unique(train_clusters))
                    if valid_clusters < 2:
                        return -9999  # 返回大的错误值作为惩罚

                    model = ClusterRegressor({
                        "kernel": svr_kernel,
                        "C": svr_C,
                        "epsilon": svr_epsilon
                    })
                    model.train(X_train_proc, y_train_fold, train_clusters)

                    X_val_proc, val_clusters = pipeline.process_data(X_val_fold)
                    y_pred = model.predict(X_val_proc, val_clusters)

                    # 最终保护
                    y_pred = np.nan_to_num(y_pred, nan=model.global_mean)
                    mae = mean_absolute_error(y_val_fold, y_pred)
                    mae_scores.append(mae)

                except Exception as e:
                    print(f"交叉验证失败: {str(e)}")
                    mae_scores.append(9999)  # 惩罚无效参数组合

            target_value = -np.nanmean(mae_scores)  # 贝叶斯优化默认是最大化目标函数

            # 更新最优目标值
            if target_value > best_target_value:
                best_target_value = target_value

            # 记录优化历史
            optimization_history['trial_number'].append(bayesian_trial_count)
            optimization_history['target'].append(target_value)
            optimization_history['best_target'].append(best_target_value)  # 记录当前最优值
            optimization_history['params'].append({
                'n_clusters': n_clusters if self.clustering_method == "kmeans" else self.grid_size,
                'svr_C': svr_C,
                'svr_epsilon': svr_epsilon,
                'svr_kernel': svr_kernel
            })

            return target_value  # 贝叶斯优化默认是最大化目标函数

        # 定义参数搜索空间
        if self.clustering_method == "kmeans":
            pbounds = {
                'n_clusters': (2, max_clusters),
                'svr_C': self.tuning_config["svr_c_range"],
                'svr_epsilon': self.tuning_config["epsilon_range"],  # 修正为正确的范围
                'svr_kernel_choice': (0, 1)  # 0表示linear，1表示rbf
            }
        else:
            max_grid_size = max(2, min(5, int(np.sqrt(len(X_train)) // 2)))
            pbounds = {
                'n_clusters': (2, max_grid_size),
                'svr_C': self.tuning_config["svr_c_range"],
                'svr_epsilon': self.tuning_config["epsilon_range"],
                'svr_kernel_choice': (0, 1)
            }

        # 创建贝叶斯优化对象
        optimizer = BayesianOptimization(
            f=bayesian_objective,
            pbounds=pbounds,
            random_state=3407,
        )

        # 添加探索点，确保在有效范围内
        if self.clustering_method == "kmeans":
            optimizer.probe(
                params={'n_clusters': 3, 'svr_C': 1.0, 'svr_epsilon': 0.0001, 'svr_kernel_choice': 0.7},
                lazy=True,
            )
        else:
            optimizer.probe(
                params={'n_clusters': 2, 'svr_C': 1.0, 'svr_epsilon': 0.0001, 'svr_kernel_choice': 0.7},
                lazy=True,
            )

        # 执行优化
        try:
            optimizer.maximize(
                init_points=4,  # 初始随机探索点
                n_iter=self.tuning_config.get("bayesian_trials", 20),  # 贝叶斯优化迭代次数
            )
        except KeyboardInterrupt:
            if self.app and self.app.stop_training_flag:
                print("\n=== 训练已被用户中断 ===")
                self.logger.info("贝叶斯超参数优化被用户中断")
                return None
            else:
                raise

        # 确保贝叶斯优化完成后进度条显示100%
        if hasattr(self.app, 'trainer_progress_signal') and self.app.trainer_progress_signal:
            self._progress_mutex.lock()
            try:
                self.app.trainer_progress_signal(
                    total_bayesian_trials,
                    total_bayesian_trials,
                    f"贝叶斯优化完成 {total_bayesian_trials}/{total_bayesian_trials}"
                )

                # 同时更新总进度
                if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
                    if self.optimization_method == "bayesian":
                        # 贝叶斯模式
                        total_progress = int(20 + 60)  # 80%
                    else:
                        # 混合模式
                        total_progress = int(20 + 30)  # 50%
                    self.app.trainer_total_progress_signal(total_progress)
            finally:
                self._progress_mutex.unlock()

        # 获取最佳参数
        best_params = optimizer.max['params']
        if self.clustering_method == "kmeans":
            self.best_params = {
                "n_clusters": int(round(best_params['n_clusters'])),
                "svr_C": float(best_params['svr_C']),
                "svr_epsilon": float(best_params['svr_epsilon']),
                "svr_kernel": "rbf" if best_params['svr_kernel_choice'] >= 0.5 else "linear"
            }
        else:
            self.best_params = {
                "grid_size": int(round(best_params['n_clusters'])),
                "svr_C": float(best_params['svr_C']),
                "svr_epsilon": float(best_params['svr_epsilon']),
                "svr_kernel": "rbf" if best_params['svr_kernel_choice'] >= 0.5 else "linear"
            }

        print("\n=== 贝叶斯优化最佳参数 ===")
        print(self.best_params)
        self.logger.info(f"贝叶斯超参数优化完成，最佳目标值: {-optimizer.max['target']:.4f}")
        self.logger.info(f"最佳参数: {self.best_params}")

        # 保存优化历史
        if history is not None:
            history.update(optimization_history)
        else:
            self._save_bayesian_history(optimization_history)

        return self.best_params

    def _save_bayesian_history(self, optimization_history):
        """保存贝叶斯优化历史记录为HTML文件"""
        if not self.model_dir:
            raise ValueError("模型目录未设置")

        # 准备数据
        trial_numbers = optimization_history['trial_number']
        targets = optimization_history['target']
        best_targets = optimization_history['best_target']

        # 使用plotly创建图表
        fig = go.Figure()

        # 添加每次试验的目标值
        fig.add_trace(go.Scatter(
            x=trial_numbers,
            y=targets,
            mode='markers',
            name='试验目标值',
            marker=dict(color='blue', size=6),
            hovertemplate='试验 #%{x}<br>目标值: %{y:.4f}<extra></extra>'
        ))

        # 添加最优解的变化曲线
        fig.add_trace(go.Scatter(
            x=trial_numbers,
            y=best_targets,
            mode='lines+markers',
            name='最优目标值',
            line=dict(color='red', width=2),
            marker=dict(color='red', size=6),
            hovertemplate='试验 #%{x}<br>最优值: %{y:.4f}<extra></extra>'
        ))

        # 更新布局
        fig.update_layout(
            title='贝叶斯优化历史记录',
            xaxis_title='试验次数',
            yaxis_title='目标值 (负MAE)',
            font=dict(size=18),
            plot_bgcolor='white',
            showlegend=True,
            hovermode='x unified'
        )

        # 保存到当前模型目录
        html_path = os.path.join(self.model_dir, "optimization_history.html")
        pyo.plot(fig, filename=html_path, auto_open=False)
        print(f"贝叶斯优化历史已保存至 {html_path}")
        self.logger.info(f"贝叶斯优化历史已保存至 {html_path}")

    def _tune_with_optuna(self, X_train, y_train, initial_params=None, bayesian_history=None):
        """使用Optuna执行超参数优化"""
        self.logger.info("开始Optuna超参数优化")
        print("\n=== 开始Optuna超参数优化 ===")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            print("\n=== 训练已被用户中断 ===")
            self.logger.info("Optuna超参数优化被用户中断")
            return None

        self.study = optuna.create_study(
            direction="minimize",
            sampler=TPESampler(seed=3407)
        )

        # 如果提供了初始参数，可以将其添加到study中
        if initial_params:
            print("使用贝叶斯优化结果作为初始参数")
            self.study.enqueue_trial(initial_params)

        # 创建自定义回调函数来更新进度
        def progress_callback(study, trial):
            current_trial = len(study.trials)
            total_trials = self.tuning_config["n_trials"]

            # 控制更新频率，避免过于频繁的GUI更新
            current_time = time.time()
            if not hasattr(progress_callback, 'last_update_time'):
                progress_callback.last_update_time = 0

            # 确保最后一次试验一定会更新进度
            should_update = (current_time - progress_callback.last_update_time > (0.1 if self.clustering_method == "kmeans" else 0.5)) or (current_trial == total_trials)
            if should_update:
                # 每次迭代都更新进度
                best_value = study.best_value if study.best_value is not None else 0.0
                progress_desc = f"Optuna优化迭代 {current_trial}/{total_trials} (最佳值: {best_value:.6f})"

                # 使用互斥锁保护进度更新
                self._progress_mutex.lock()
                try:
                    self.progress_signal.progress_updated.emit(current_trial, total_trials, progress_desc)

                    # 同时更新总进度
                    if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
                        if initial_params:
                            # 混合模式
                            total_progress = int(50 + 30 * current_trial / total_trials)
                        else:
                            # 纯Optuna模式
                            total_progress = int(20 + 60 * current_trial / total_trials)
                        self.app.trainer_total_progress_signal(total_progress)
                        self.app.trainer_progress_signal(current_trial, total_trials, progress_desc)
                    progress_callback.last_update_time = current_time
                finally:
                    self._progress_mutex.unlock()

            print(
                f"{datetime.datetime.now()} 试验{trial.number}完成，得到值为{trial.value:.8f}，参数为{trial.params}，当前最佳值: {study.best_value}")

        try:
            self.study.optimize(
                lambda trial: self._objective(trial, X_train, y_train),
                n_trials=self.tuning_config["n_trials"],
                timeout=self.tuning_config["timeout"],
                callbacks=[progress_callback]
            )
        except optuna.exceptions.OptunaError as e:
            if "训练被用户中断" in str(e):
                print("\n=== 训练已被用户中断 ===")
                self.logger.info("Optuna超参数优化被用户中断")
                return None
            else:
                raise e

        # 确保Optuna优化完成后进度条显示100%
        if hasattr(self.app, 'trainer_progress_signal') and self.app.trainer_progress_signal:
            self._progress_mutex.lock()
            try:
                self.app.trainer_progress_signal(
                    self.tuning_config["n_trials"],
                    self.tuning_config["n_trials"],
                    f"Optuna优化完成 {self.tuning_config['n_trials']}/{self.tuning_config['n_trials']} (最佳值: {self.study.best_value:.6f})"
                )

                # 同时更新总进度
                if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
                    if initial_params:
                        # 混合模式
                        total_progress = int(50 + 30)  # 80%
                    else:
                        # 纯Optuna模式
                        total_progress = int(20 + 60)  # 80%
                    self.app.trainer_total_progress_signal(total_progress)
            finally:
                self._progress_mutex.unlock()

        # 保存优化历史
        fig = plot_optimization_history(self.study)
        fig.update_layout(
            title="优化历史记录",
            xaxis_title="试验次数",
            yaxis_title="目标值",
            font=dict(size=18),
            plot_bgcolor="white"
        )

        # 如果在混合模式下且有贝叶斯优化历史，则添加到图表中
        if bayesian_history and len(bayesian_history.get('trial_number', [])) > 0:
            # 添加贝叶斯优化历史作为散点图
            fig.add_trace(go.Scatter(
                x=bayesian_history['trial_number'],
                y=bayesian_history['target'],
                mode='markers',
                name='贝叶斯优化历史',
                marker=dict(color='orange', size=8),
                yaxis='y'
            ))

            # 添加贝叶斯优化最佳值变化曲线
            if 'best_target' in bayesian_history and len(bayesian_history['best_target']) > 0:
                fig.add_trace(go.Scatter(
                    x=bayesian_history['trial_number'],
                    y=bayesian_history['best_target'],
                    mode='lines+markers',
                    name='贝叶斯最优值',
                    line=dict(color='red', width=2),
                    marker=dict(color='red', size=6),
                    yaxis='y'
                ))

            # 更新布局以包含图例
            fig.update_layout(
                showlegend=True,
                legend=dict(
                    yanchor="top",
                    y=0.99,
                    xanchor="left",
                    x=0.01
                )
            )
        fig.write_html(os.path.join(self.model_dir, "optimization_history.html"))
        print(f"优化历史已保存至 {self.model_dir} 目录")
        self.best_params = self.study.best_params
        print("\n=== 最佳参数 ===")
        print(self.best_params)
        self.logger.info(f"Optuna超参数优化完成，最佳MAE: {self.study.best_value:.4f}")
        self.logger.info(f"最佳参数: {self.best_params}")

        return self.best_params

    def train_final_model(self, X_train, y_train, best_params):
        """使用最佳参数训练最终模型"""
        self.logger.info("开始训练最终模型")

        # 检查是否需要停止训练
        if self.app and self.app.stop_training_flag:
            raise optuna.exceptions.OptunaError("训练被用户中断")

        # 根据聚类方法创建不同的pipeline
        if self.clustering_method == "kmeans":
            self.pipeline = DataPipeline(best_params["n_clusters"], clustering_method="kmeans")
        else:
            som_params = {
                'learning_rate': 0.5,
                'sigma': 1.0,
                'max_iter': 1000,
                'verbose': True,
                'plot_training': True  # 启用训练过程可视化
            }
            self.pipeline = DataPipeline(
                best_params["grid_size"],
                clustering_method="som",
                som_params=som_params
            )

        # 定义SOM训练的进度回调函数
        def som_progress_callback(current, total, phase):
            if self.app and self.app.stop_training_flag:
                raise optuna.exceptions.OptunaError("训练被用户中断")

            # SOM训练时总进度更新 - 使用互斥锁保护
            self._progress_mutex.lock()
            try:
                if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
                    som_total_progress = 80 + int((current / total) * 10)
                    self.app.trainer_total_progress_signal(som_total_progress)
                    self.app.trainer_progress_signal(current, total, phase)

                # 更新阶段描述
                if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
                    self.app.trainer_phase_signal(phase)
            finally:
                self._progress_mutex.unlock()

        # 根据聚类方法选择是否使用进度回调
        if self.clustering_method == "som":
            X_train_proc, train_clusters = self.pipeline.process_data(
                X_train, training=True, progress_callback=som_progress_callback, phase="SOM训练中",
                model_dir=self.model_dir)
        else:
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
                "pipeline": self.pipeline,  # 保存数据处理流水线
                "regressor": self.model,  # 保存回归模型
                "best_params": self.best_params,  # 保存最佳参数
                "training_time": self.app.training_time,  # 保存训练时间
                "clustering_method": self.clustering_method,  # 保存聚类方法信息
                "optimization_method": self.optimization_method  # 保存优化方法信息
            },
            os.path.join(self.model_dir, "models", self.config["save_model"])
        )
        print(f"模型已保存至 {self.model_dir} 目录")

    def _safe_visualization_call(self, func, *args, **kwargs):
        """安全调用可视化函数，避免GUI阻塞"""
        try:
            # 在调用前处理事件队列
            if self.app and hasattr(self.app, 'processEvents'):
                self.app.processEvents()

            result = func(*args, **kwargs)

            # 在调用后处理事件队列
            if self.app and hasattr(self.app, 'processEvents'):
                self.app.processEvents()

            return result
        except Exception as e:
            self.logger.error(f"可视化函数 {func.__name__} 执行出错: {str(e)}")
            print(f"可视化函数 {func.__name__} 执行出错: {str(e)}")
            return None

    @property
    def run_training(self):
        """执行完整训练流程"""
        self.logger.info("开始完整训练流程")

        # 创建唯一模型目录
        self.model_name, self.model_dir = get_unique_timestamp_dir(base_dir=CONFIG["base_model_dir"],
                                                                   cluster=self.clustering_method,
                                                                   mode=self.optimization_method)
        print(f"本次运行结果将保存至: {self.model_dir}")

        # 记录训练开始时间
        self.app.training_time = time.perf_counter()

        # 在主界面显示训练开始信息
        if self.training_worker:
            self.training_worker.training_message.emit("分簇开始", "正在数据分簇...")
        if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
            self.app.trainer_phase_signal("数据加载中...")
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
            X, y, test_size=0.2, random_state=3407)

        print(f"\n数据集划分：")
        print(f"- 训练样本: {len(X_train_all)}")
        print(f"- 测试样本: {len(X_test)}")

        if self.training_worker:
            self.training_worker.training_message.emit("训练开始", "训练中，请稍等...")
        if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
            self.app.trainer_phase_signal("超参数优化中...")
        self.logger.info("训练中，请稍等...")

        # 设置主线程聚类方法
        self.app.clustering_methods = self.clustering_method

        # 当训练样本过少时自动调整聚类数
        if len(X_train_all) < 50:
            if self.clustering_method == "kmeans":
                self.config["n_clusters"] = max(2, min(3, len(X_train_all) // 10))
                print(f"调整聚类数为: {self.config['n_clusters']}")
            else:
                self.config["grid_size"] = max(2, min(3, int(np.sqrt(len(X_train_all)) // 2)))
                print(f"调整SOM网格大小为: {self.config['grid_size']}")

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
        if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
            self.app.trainer_phase_signal("训练最终模型...")

        self.train_final_model(X_train_all, y_train_all, best_params)

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在最终模型训练阶段被用户中断")
            return self.model_dir

        # 更新总进度到85%
        if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
            self.app.trainer_total_progress_signal(90)

        # 评估模型
        if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
            self.app.trainer_phase_signal("评估模型...")

        y_pred = self.evaluate_model(X_test, y_test)

        # 检查是否需要停止训练
        if self.app.stop_training_flag:
            print("训练已被用户中断")
            self.logger.info("训练在模型评估阶段被用户中断")
            return self.model_dir

        # 更新总进度到93%
        if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
            self.app.trainer_total_progress_signal(93)

        # 停止计时
        self.app.training_time = time.perf_counter() - self.app.training_time
        print(f"训练总耗时: {self.app.training_time:.8f} 秒")
        self.logger.info(f"训练总耗时: {self.app.training_time:.8f} 秒")

        # 保存模型
        if hasattr(self.app, 'trainer_phase_signal') and self.app.trainer_phase_signal:
            self.app.trainer_phase_signal("保存模型...")
        self.save_model()
        self.app.trainer_total_progress_signal(95)

        # 可视化 - 使用异步方式避免阻塞GUI线程
        print("生成可视化图表...")
        self.app.trainer_phase_signal("生成可视化图表...")

        # 在可视化之前确保进度更新完成
        if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
            self.app.trainer_total_progress_signal(96)

        try:
            self._safe_visualization_call(Visualizer.create_dir, self.model_dir)
            self._safe_visualization_call(Visualizer.plot_features, X_train_all, y_train_all, self.model_dir)
            self.app.trainer_total_progress_signal(97)

            self._safe_visualization_call(Visualizer.plot_clusters, self.pipeline.cluster_model.labels_, self.model_dir)
            self.app.trainer_total_progress_signal(98)

            self._safe_visualization_call(Visualizer.plot_results, y_test, y_pred, self.model_dir)
            self.app.trainer_total_progress_signal(99)
        except Exception as e:
            self.logger.error(f"可视化过程中发生错误: {str(e)}")
            print(f"可视化过程中发生错误: {str(e)}")

        if self.training_worker:
            QTimer.singleShot(0, lambda: self.training_worker.training_message.emit("训练完成",
                                                                                    f"模型已保存至 {self.model_dir} 目录"))

        # 复制模型到用户目录
        self.person_model_dir = os.path.join(CONFIG["user_info"], self.app.current_username, "models", self.model_name)
        try:
            shutil.copytree(self.model_dir, str(self.person_model_dir))
        except Exception as e:
            self.logger.error(f"复制模型到用户目录失败: {str(e)}")
            print(f"复制模型到用户目录失败: {str(e)}")

        self.logger.info(f"训练完成! 模型保存至: {self.model_dir}")
        if hasattr(self.app, 'trainer_total_progress_signal') and self.app.trainer_total_progress_signal:
            self.app.trainer_total_progress_signal(100)

        return self.model_dir
