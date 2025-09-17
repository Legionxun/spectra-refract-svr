# core/cluster_regressor.py
import os
import numpy as np
from sklearn.svm import SVR
from sklearn.pipeline import make_pipeline

# 设置环境变量以支持UTF-8编码
os.environ['PYTHONIOENCODING'] = 'utf-8'

class ClusterRegressor:
    def __init__(self, svr_params):
        self.models = {}
        self.svr_params = svr_params
        self.global_mean = None

    def train(self, features, labels, clusters):
        """分簇训练回归器（增加全局均值）"""
        self.global_mean = np.nanmean(labels)
        for c in np.unique(clusters):
            mask = (clusters == c)
            if sum(mask) < 5:
                continue
            try:
                model = make_pipeline(SVR(**self.svr_params))
                model.fit(features[mask], labels[mask])
                self.models[c] = model
            except Exception as e:
                print(f"聚类{c}训练失败: {str(e)}")
                continue

    def predict(self, features, clusters):
        """分簇预测（多重保护机制）"""
        preds = np.full(len(features), self.global_mean)
        if not self.models:
            return preds

        for c in np.unique(clusters):
            mask = (clusters == c)
            if c in self.models:
                try:
                    pred = self.models[c].predict(features[mask])
                    pred = np.nan_to_num(pred, nan=self.global_mean)
                    preds[mask] = pred
                except Exception as e:
                    print(f"聚类{c}预测失败: {str(e)}")
                    preds[mask] = self.global_mean
        return preds