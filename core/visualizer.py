# core.visualizer.py
import os
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.manifold import TSNE
from sklearn.metrics import mean_absolute_error
from .config import CONFIG
from .utils import get_unique_filename

plt.rc("font", family='Microsoft YaHei')
plt.rcParams['axes.unicode_minus'] = False

class Visualizer:
    @staticmethod
    def create_dir(model_dir):
        """创建可视化目录"""
        os.makedirs(os.path.join(model_dir, CONFIG["save_picture"]), exist_ok=True)

    @staticmethod
    def plot_features(features, labels, model_dir):
        """特征空间可视化（自动参数调整）"""
        n_samples = len(features)

        # 样本数不足时跳过
        if n_samples < 5:
            print(f"样本数不足（{n_samples}），跳过特征可视化")
            return

        # 动态参数设置
        perplexity = min(30, max(5, n_samples // 2))
        n_iter = 500 if n_samples > 100 else 250

        try:
            tsne = TSNE(
                n_components=2,
                perplexity=perplexity,
                max_iter=n_iter,
                random_state=42,
                init="pca"  # 更稳定的初始化方式
            )
            reduced = tsne.fit_transform(features)

            plt.figure(figsize=(12, 6))
            plt.subplot(121)
            scatter = sns.scatterplot(
                x=reduced[:, 0], y=reduced[:, 1],
                hue=labels, palette="viridis",
                size=labels, sizes=(20, 200),
                alpha=0.7
            )
            plt.title(f"t-SNE可视化 (perplexity={perplexity}, n_iter={n_iter})")

            plt.subplot(122)
            sns.kdeplot(
                x=reduced[:, 0], y=reduced[:, 1],
                fill=True, cmap="rocket",
                thresh=0.1, levels=30
            )
            plt.title("特征密度分布")
            plt.tight_layout()
            output_path = get_unique_filename(os.path.join(model_dir, CONFIG["save_picture"]), "特征密度分布", "png")
            plt.savefig(output_path)
            plt.close()
            return output_path

        except Exception as e:
            print(f"特征可视化失败: {str(e)}")

    @staticmethod
    def plot_clusters(clusters, model_dir):
        """聚类分布可视化"""
        plt.figure(figsize=(8, 4))
        sns.histplot(clusters, bins=CONFIG["n_clusters"],
                     kde=True, discrete=True)
        plt.xlabel("Cluster ID")
        plt.ylabel("样本数量")
        plt.title("聚类分布直方图")
        output_path = get_unique_filename(os.path.join(model_dir, CONFIG["save_picture"]), "聚类分布直方图", "png")
        plt.savefig(output_path)
        plt.close()
        return output_path

    @staticmethod
    def plot_results(y_true, y_pred, model_dir):
        """预测结果可视化"""
        plt.figure(figsize=(12, 5))

        plt.subplot(121)
        sns.regplot(x=y_true, y=y_pred,
                    scatter_kws={"alpha": 0.4, "color": "blue"},
                    line_kws={"color": "red"})
        plt.plot([min(y_true), max(y_true)],
                 [min(y_true), max(y_true)],
                 'g--', lw=2)
        plt.xlabel("真实值")
        plt.ylabel("预测值")
        plt.title("预测结果回归图")

        plt.subplot(122)
        residuals = y_pred - y_true
        sns.histplot(residuals, kde=True,
                     bins=30, color="orange")
        plt.axvline(0, color='red', linestyle='--')
        plt.xlabel("残差")
        plt.title(f"残差分布 (MAE: {mean_absolute_error(y_true, y_pred):.4f})")
        plt.tight_layout()
        output_path = get_unique_filename(os.path.join(model_dir, CONFIG["save_picture"]), "残差分布", "png")
        plt.savefig(output_path)
        plt.close()
        return output_path
