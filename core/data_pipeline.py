# core.data_pipeline.py
import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

class DataPipeline:
    def __init__(self, n_clusters):
        self.scaler = StandardScaler()
        self.kmeans = KMeans(
            n_clusters=n_clusters,
            n_init=10,  # 显式设置n_init避免警告
            random_state=42
        )

    def process_data(self, features, labels=None, training=False):
        """处理数据流程"""
        if training:
            scaled = self.scaler.fit_transform(features)
            scaled = np.nan_to_num(scaled, nan=0.0)  # 新增处理
            self.kmeans.fit(scaled)
            return scaled, self.kmeans.labels_
        else:
            scaled = self.scaler.transform(features)
            scaled = np.nan_to_num(scaled, nan=0.0)  # 新增处理
            return scaled, self.kmeans.predict(scaled)