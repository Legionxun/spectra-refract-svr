# core/data_pipeline.py
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

from .som import SOM


class DataPipeline:
    """数据处理流水线"""
    def __init__(self, n_clusters, som_params=None, clustering_method="kmeans"):
        self.scaler = StandardScaler()
        self.clustering_method = clustering_method

        if self.clustering_method == "kmeans":
            self.cluster_model = KMeans(
                n_clusters=n_clusters,
                n_init=10,
                random_state=3407
            )
        elif self.clustering_method == "som":  # SOM聚类
            grid_size = n_clusters
            if som_params is None:
                som_params = {}

            self.cluster_model = SOM(
                grid_size=grid_size,
                learning_rate=som_params.get('learning_rate', 0.5),
                sigma=som_params.get('sigma', 1.0),
                sigma_decay=som_params.get('sigma_decay', 'exponential'),
                learning_rate_decay=som_params.get('learning_rate_decay', 'exponential'),
                neighborhood_function=som_params.get('neighborhood_function', 'gaussian'),
                max_iter=som_params.get('max_iter', 1000),
                random_state=3407,
                verbose=som_params.get('verbose', False),
                plot_training=som_params.get('plot_training', False)
            )

    def process_data(self, features, labels=None, training=False, progress_callback=None, phase="", model_dir=None):
        """处理数据流程"""
        if progress_callback:
            progress_callback(0, len(features), phase)

        # 确保clustering_method属性存在（向后兼容旧模型）
        if not hasattr(self, 'clustering_method'):
            if hasattr(self, 'cluster_model'):
                if isinstance(self.cluster_model, KMeans):
                    self.clustering_method = "kmeans"
                elif isinstance(self.cluster_model, SOM):
                    self.clustering_method = "som"
                else:
                    self.clustering_method = "kmeans"  # 默认使用kmeans
            else:
                self.clustering_method = "kmeans"  # 默认使用kmeans

        # 确保cluster_model属性存在（向后兼容非常旧的模型）
        if not hasattr(self, 'cluster_model'):
            if hasattr(self, 'kmeans'):
                # 旧模型使用kmeans属性
                self.cluster_model = self.kmeans
                self.clustering_method = "kmeans"
            else:
                self.cluster_model = KMeans(n_clusters=3, n_init=10, random_state=3407)
                self.clustering_method = "kmeans"

        if training:
            scaled = self.scaler.fit_transform(features)
            scaled = np.nan_to_num(scaled, nan=0.0)

            # 分批处理以支持进度更新
            if progress_callback:
                progress_callback(1, 3, f"{phase} - 数据标准化完成")

            # 根据聚类方法进行训练
            if self.clustering_method == "kmeans":
                self.cluster_model.fit(scaled)
            else:
                self.cluster_model.fit(scaled, progress_callback=progress_callback, model_dir=model_dir)

            if progress_callback:
                progress_callback(3, 3, f"{phase} - 聚类完成")

            return scaled, self.cluster_model.labels_
        else:
            scaled = self.scaler.transform(features)
            scaled = np.nan_to_num(scaled, nan=0.0)

            # 分批处理以支持进度更新
            if progress_callback:
                progress_callback(1, 2, f"{phase} - 数据标准化完成")

            if self.clustering_method == "kmeans":
                labels = self.cluster_model.predict(scaled)
            else:
                labels = self.cluster_model.predict(scaled)

            if progress_callback:
                progress_callback(2, 2, f"{phase} - 聚类预测完成")

            return scaled, labels
