# core/som.py
import logging, os
import numpy as np
from sklearn.base import BaseEstimator, ClusterMixin
from sklearn.utils.validation import check_array, check_is_fitted
from sklearn.decomposition import PCA
import plotly.graph_objects as go


class SOM(BaseEstimator, ClusterMixin):
    """自组织映射神经网络聚类算法"""
    def __init__(self, grid_size=3, learning_rate=0.5, sigma=1.0,
                 sigma_decay='exponential', learning_rate_decay='exponential',
                 neighborhood_function='gaussian', max_iter=1000,
                 random_state=None, verbose=False, plot_training=False):
        """
        初始化SOM参数

        参数:
        grid_size: SOM网格大小 (将创建 grid_size x grid_size 的神经元网格)
        learning_rate: 初始学习率
        sigma: 初始邻域半径
        sigma_decay: 邻域半径衰减方式 ('linear', 'exponential', 'inverse')
        learning_rate_decay: 学习率衰减方式 ('linear', 'exponential', 'inverse')
        neighborhood_function: 邻域函数 ('gaussian', 'bubble', 'mexican_hat')
        max_iter: 最大迭代次数
        random_state: 随机种子
        verbose: 是否输出详细信息
        plot_training: 是否绘制训练过程动画
        """
        self.grid_size = grid_size
        self.learning_rate = learning_rate
        self.sigma = sigma
        self.sigma_decay = sigma_decay
        self.learning_rate_decay = learning_rate_decay
        self.neighborhood_function = neighborhood_function
        self.max_iter = max_iter
        self.random_state = random_state
        self.verbose = verbose
        self.plot_training = plot_training
        self.logger = logging.getLogger("SOM")

        # 训练历史记录
        self.history = {
            'iteration': [],
            'learning_rate': [],
            'sigma': [],
            'quantization_error': [],
            'topographic_error': []
        }

        # 浏览器进程管理
        self.browser_process = None
        self.browser_pids = set()

        # 用于存储训练过程中的动画帧
        self.animation_frames = []

    def _initialize_weights(self, X):
        """初始化权重矩阵 - 多种初始化方法"""
        n_samples, n_features = X.shape

        rng = np.random.RandomState(self.random_state)

        # 随机选择样本初始化
        indices = rng.choice(n_samples, self.grid_size * self.grid_size, replace=False)
        self.weights_ = X[indices].copy()

        # 线性初始化
        try:
            # 尝试PCA初始化
            from sklearn.decomposition import PCA
            pca = PCA(n_components=2)
            pca.fit(X)

            # 获取主成分
            pc1, pc2 = pca.components_

            # 沿主成分方向创建网格
            for i in range(self.grid_size):
                for j in range(self.grid_size):
                    idx = i * self.grid_size + j
                    # 沿两个主成分方向线性分布
                    self.weights_[idx] = pca.mean_ + \
                                         (i - self.grid_size / 2) * 0.1 * pc1 + \
                                         (j - self.grid_size / 2) * 0.1 * pc2
        except:
            # 如果PCA失败，使用随机初始化
            self.weights_ = rng.rand(self.grid_size * self.grid_size, n_features) * \
                            (np.max(X, axis=0) - np.min(X, axis=0)) + np.min(X, axis=0)

        # 重塑为网格形状
        self.weights_ = self.weights_.reshape(self.grid_size, self.grid_size, n_features)

        # 创建网格坐标
        self.grid_ = np.array([[i, j] for i in range(self.grid_size) for j in range(self.grid_size)])
        self.grid_ = self.grid_.reshape(self.grid_size, self.grid_size, 2)

    def _find_bmu(self, x):
        """找到最佳匹配单元(BMU)"""
        # 计算所有节点与输入向量的距离
        distances = np.linalg.norm(self.weights_ - x, axis=2)

        # 找到最小距离的索引
        bmu_index = np.unravel_index(np.argmin(distances, axis=None), distances.shape)
        return bmu_index

    def _calculate_decay(self, initial_value, iteration, decay_type):
        """计算衰减值"""
        # 线性衰减
        if decay_type == 'linear':
            return initial_value * (1 - iteration / self.max_iter)
        # 指数衰减
        elif decay_type == 'exponential':
            return initial_value * np.exp(-iteration / self.max_iter)
        # 反向指数衰减
        elif decay_type == 'inverse':
            return initial_value / (1 + iteration / (self.max_iter / 2))
        else:
            return initial_value

    def _get_neighborhood(self, bmu_index, iteration):
        """计算邻域函数"""
        # 计算网格中每个节点与BMU的距离
        distances = np.linalg.norm(self.grid_ - np.array(bmu_index), axis=2)

        # 计算随时间衰减的邻域半径
        current_sigma = self._calculate_decay(self.sigma, iteration, self.sigma_decay)

        # 计算邻域函数值
        if self.neighborhood_function == 'gaussian':
            neighborhood = np.exp(-distances ** 2 / (2 * current_sigma ** 2))
        elif self.neighborhood_function == 'bubble':
            neighborhood = (distances <= current_sigma).astype(float)
        elif self.neighborhood_function == 'mexican_hat':
            neighborhood = (1 - distances ** 2 / current_sigma ** 2) * \
                           np.exp(-distances ** 2 / (2 * current_sigma ** 2))
        else:  # 默认高斯
            neighborhood = np.exp(-distances ** 2 / (2 * current_sigma ** 2))

        return neighborhood, current_sigma

    def _calculate_quantization_error(self, X):
        """计算量化误差"""
        errors = []
        for x in X:
            bmu_index = self._find_bmu(x)
            error = np.linalg.norm(x - self.weights_[bmu_index])
            errors.append(error)
        return np.mean(errors)

    def _calculate_topographic_error(self, X):
        """计算拓扑误差"""
        errors = 0
        for x in X:
            # 找到前两个最佳匹配单元
            distances = np.linalg.norm(self.weights_ - x, axis=2)
            flat_distances = distances.flatten()
            sorted_indices = np.argsort(flat_distances)

            # 获取前两个BMU的坐标
            bmu1_idx = np.unravel_index(sorted_indices[0], distances.shape)
            bmu2_idx = np.unravel_index(sorted_indices[1], distances.shape)

            # 检查它们是否相邻
            distance_between_bmus = np.linalg.norm(np.array(bmu1_idx) - np.array(bmu2_idx))
            if distance_between_bmus > 1.5:  # 如果不相邻
                errors += 1

        return errors / len(X)

    def _setup_animation(self, X):
        """设置训练过程动画"""
        if not self.plot_training:
            return None

        # 初始化动画帧列表
        self.animation_frames = []
        return True

    def _update_animation(self, iteration, quant_error, topo_error):
        """更新训练过程动画"""
        if not self.plot_training:
            return

        # 记录当前训练状态用于动画
        self.animation_frames.append({
            'iteration': iteration,
            'weights': self.weights_.copy(),
            'quant_error': quant_error,
            'topo_error': topo_error
        })

    def _save_animation(self, model_dir):
        """保存训练过程动画到results目录"""
        # 动画现在集成在HTML报告中，不需要单独保存
        pass

    def fit(self, X, y=None, progress_callback=None, model_dir=None):
        """训练SOM模型"""
        X = check_array(X)
        n_samples, n_features = X.shape

        # 初始化权重
        self._initialize_weights(X)

        # 设置动画
        if self.plot_training:
            self._setup_animation(X)

        # 训练循环
        for iteration in range(self.max_iter):
            # 更新进度回调
            if progress_callback and iteration % 10 == 0:
                progress_callback(iteration, self.max_iter, f"SOM训练迭代 {iteration}/{self.max_iter}")

            # 选择随机样本
            index = np.random.randint(0, n_samples)
            x = X[index]

            # 找到BMU
            bmu_index = self._find_bmu(x)

            # 计算邻域函数
            neighborhood, current_sigma = self._get_neighborhood(bmu_index, iteration)

            # 计算随时间衰减的学习率
            current_learning_rate = self._calculate_decay(self.learning_rate, iteration, self.learning_rate_decay)

            # 更新权重
            for i in range(self.grid_size):
                for j in range(self.grid_size):
                    # 更新公式: Δw_ij = η(t) * h_ij(t) * (x - w_ij)
                    update = current_learning_rate * neighborhood[i, j] * (x - self.weights_[i, j])
                    self.weights_[i, j] += update

            # 记录训练历史
            if iteration % 10 == 0:
                quant_error = self._calculate_quantization_error(X)
                topo_error = self._calculate_topographic_error(X)

                self.history['iteration'].append(iteration)
                self.history['learning_rate'].append(current_learning_rate)
                self.history['sigma'].append(current_sigma)
                self.history['quantization_error'].append(quant_error)
                self.history['topographic_error'].append(topo_error)

                # 更新动画
                if self.plot_training and iteration % 50 == 0:
                    self._update_animation(iteration, quant_error, topo_error)

                if self.verbose:
                    self.logger.info(f"Iteration {iteration}: "
                                     f"LR={current_learning_rate:.4f}, "
                                     f"Sigma={current_sigma:.4f}, "
                                     f"QuantError={quant_error:.4f}, "
                                     f"TopoError={topo_error:.4f}")

        # 最后一次进度更新
        if progress_callback:
            progress_callback(self.max_iter, self.max_iter, "SOM训练完成")

        # 为预测阶段准备
        self.labels_ = self.predict(X)

        # 生成交互式HTML报告
        if model_dir:
            self._generate_interactive_html(model_dir, X)

        return self

    def predict(self, X):
        """预测样本的聚类标签"""
        check_is_fitted(self, 'weights_')
        X = check_array(X)

        labels = []
        for x in X:
            # 找到BMU
            bmu_index = self._find_bmu(x)
            # 将二维索引转换为一维标签
            label = bmu_index[0] * self.grid_size + bmu_index[1]
            labels.append(label)

        return np.array(labels)

    def fit_predict(self, X, y=None, progress_callback=None, model_dir=None):
        """训练并预测"""
        self.fit(X, progress_callback=progress_callback, model_dir=model_dir)
        return self.labels_

    def get_u_matrix(self):
        """获取U矩阵 (统一距离矩阵)"""
        check_is_fitted(self, 'weights_')

        u_matrix = np.zeros((self.grid_size, self.grid_size))

        for i in range(self.grid_size):
            for j in range(self.grid_size):
                # 计算当前神经元与所有邻居的距离
                distances = []

                # 上邻居
                if i > 0:
                    distances.append(np.linalg.norm(self.weights_[i, j] - self.weights_[i - 1, j]))

                # 下邻居
                if i < self.grid_size - 1:
                    distances.append(np.linalg.norm(self.weights_[i, j] - self.weights_[i + 1, j]))

                # 左邻居
                if j > 0:
                    distances.append(np.linalg.norm(self.weights_[i, j] - self.weights_[i, j - 1]))

                # 右邻居
                if j < self.grid_size - 1:
                    distances.append(np.linalg.norm(self.weights_[i, j] - self.weights_[i, j + 1]))

                # 计算平均距离
                u_matrix[i, j] = np.mean(distances) if distances else 0

        # 确保矩阵不为空且为有限值
        u_matrix = np.nan_to_num(u_matrix, nan=0.0, posinf=0.0, neginf=0.0)

        # 添加一个小的偏移量确保不会所有值都相同
        if np.all(u_matrix == u_matrix[0, 0]):
            u_matrix += 1e-10 * np.random.random(u_matrix.shape)

        return u_matrix

    def _generate_interactive_html(self, model_dir, X):
        """生成交互式HTML报告"""
        check_is_fitted(self, 'weights_')

        # 创建results目录
        results_dir = os.path.join(model_dir, "results")
        os.makedirs(results_dir, exist_ok=True)

        # 创建独立的图表并放入标签页中
        figures = {}

        # 1. U矩阵图表
        u_matrix = self.get_u_matrix()
        fig_u_matrix = go.Figure(data=go.Heatmap(z=u_matrix, colorscale='Hot'))
        fig_u_matrix.update_layout(
            title="U-Matrix (统一距离矩阵)",
            xaxis_title="X坐标",
            yaxis_title="Y坐标"
        )
        figures['U-Matrix'] = fig_u_matrix

        # 2. 权重分布图
        fig_weights = go.Figure()
        weights_flat = self.weights_.reshape(-1, self.weights_.shape[2])

        if X.shape[1] == 2:
            # 2D数据可以直接可视化
            fig_weights.add_trace(go.Scatter(
                x=X[:, 0], y=X[:, 1],
                mode='markers',
                marker=dict(color='blue', size=6),
                name='数据点'
            ))

            fig_weights.add_trace(go.Scatter(
                x=weights_flat[:, 0], y=weights_flat[:, 1],
                mode='markers',
                marker=dict(color='red', size=8, symbol='x'),
                name='神经元'
            ))

            # 连接相邻神经元
            for i in range(self.grid_size):
                for j in range(self.grid_size):
                    # 绘制下方连接线
                    if i < self.grid_size - 1:
                        fig_weights.add_trace(go.Scatter(
                            x=[self.weights_[i, j, 0], self.weights_[i + 1, j, 0]],
                            y=[self.weights_[i, j, 1], self.weights_[i + 1, j, 1]],
                            mode='lines',
                            line=dict(color='black', width=1),
                            showlegend=False,
                            name=f'连接线 {i},{j}-{i + 1},{j}' if i == 0 and j == 0 else None
                        ))
                    # 绘制右侧连接线
                    if j < self.grid_size - 1:
                        fig_weights.add_trace(go.Scatter(
                            x=[self.weights_[i, j, 0], self.weights_[i, j + 1, 0]],
                            y=[self.weights_[i, j, 1], self.weights_[i, j + 1, 1]],
                            mode='lines',
                            line=dict(color='black', width=1),
                            showlegend=False,
                            name=f'连接线 {i},{j}-{i},{j + 1}' if i == 0 and j == 0 else None
                        ))
        else:
            # 高维数据使用PCA降维可视化
            try:
                pca = PCA(n_components=2)
                X_pca = pca.fit_transform(X)
                weights_pca = pca.transform(weights_flat)

                fig_weights.add_trace(go.Scatter(
                    x=X_pca[:, 0], y=X_pca[:, 1],
                    mode='markers',
                    marker=dict(color='blue', size=6),
                    name='数据点'
                ))

                fig_weights.add_trace(go.Scatter(
                    x=weights_pca[:, 0], y=weights_pca[:, 1],
                    mode='markers',
                    marker=dict(color='red', size=8, symbol='x'),
                    name='神经元'
                ))

                # 连接相邻神经元
                for i in range(self.grid_size):
                    for j in range(self.grid_size):
                        if i < self.grid_size - 1:
                            idx1 = i * self.grid_size + j
                            idx2 = (i + 1) * self.grid_size + j
                            fig_weights.add_trace(go.Scatter(
                                x=[weights_pca[idx1, 0], weights_pca[idx2, 0]],
                                y=[weights_pca[idx1, 1], weights_pca[idx2, 1]],
                                mode='lines',
                                line=dict(color='black', width=1),
                                showlegend=False,
                                name=f'连接线 {idx1}-{idx2}' if i == 0 and j == 0 else None
                            ))
                        if j < self.grid_size - 1:
                            idx1 = i * self.grid_size + j
                            idx2 = i * self.grid_size + j + 1
                            fig_weights.add_trace(go.Scatter(
                                x=[weights_pca[idx1, 0], weights_pca[idx2, 0]],
                                y=[weights_pca[idx1, 1], weights_pca[idx2, 1]],
                                mode='lines',
                                line=dict(color='black', width=1),
                                showlegend=False,
                                name=f'连接线 {idx1}-{idx2}' if i == 0 and j == 0 and i < self.grid_size - 1 else None
                            ))
            except Exception as e:
                self.logger.error(f"PCA降维时出错: {str(e)}")

        fig_weights.update_layout(
            title="权重分布",
            xaxis_title="PCA维度1" if X.shape[1] != 2 else "维度1",
            yaxis_title="PCA维度2" if X.shape[1] != 2 else "维度2"
        )
        figures['Weights'] = fig_weights

        # 3. 训练历史图表
        fig_history = go.Figure()
        if self.history['iteration']:
            fig_history.add_trace(go.Scatter(
                x=self.history['iteration'],
                y=self.history['quantization_error'],
                mode='lines',
                line=dict(color='blue'),
                name='量化误差'
            ))
            fig_history.add_trace(go.Scatter(
                x=self.history['iteration'],
                y=self.history['topographic_error'],
                mode='lines',
                line=dict(color='red'),
                name='拓扑误差'
            ))

        fig_history.update_layout(
            title="训练历史",
            xaxis_title="迭代次数",
            yaxis_title="误差"
        )
        figures['History'] = fig_history

        # 4. 3D权重分布
        fig_3d = go.Figure()
        if weights_flat.shape[1] >= 3:
            fig_3d.add_trace(go.Scatter3d(
                x=weights_flat[:, 0],
                y=weights_flat[:, 1],
                z=weights_flat[:, 2],
                mode='markers',
                marker=dict(
                    size=5,
                    color=np.arange(len(weights_flat)),
                    colorscale='Viridis',
                    showscale=False
                ),
                name='神经元3D'
            ))

        fig_3d.update_layout(
            title="3D权重分布",
            scene=dict(
                xaxis_title="维度1",
                yaxis_title="维度2",
                zaxis_title="维度3"
            )
        )
        figures['3D Weights'] = fig_3d

        # 5. 组件平面
        n_features = min(self.weights_.shape[2], 12)
        for i in range(n_features):
            component_data = self.weights_[:, :, i]
            fig_component = go.Figure(data=go.Heatmap(
                z=component_data,
                colorscale='Viridis',
                colorbar=dict(title=f"特征 {i}")
            ))
            fig_component.update_layout(
                title=f"组件平面 - 特征 {i}",
                xaxis_title="X坐标",
                yaxis_title="Y坐标"
            )
            figures[f'Component {i}'] = fig_component

        # 创建一个包含所有图表的HTML页面
        html_string = '''
        <html>
            <head>
                <style>
                    body { 
                        font-family: Arial, sans-serif;
                        margin: 0;
                        padding: 20px;
                        background-color: #f5f5f5;
                    }
                    .header {
                        text-align: center;
                        color: #333;
                        margin-bottom: 20px;
                    }
                    .tabs {
                        display: flex;
                        flex-wrap: wrap;
                        background: #fff;
                        border-radius: 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                        overflow: hidden;
                        margin-bottom: 20px;
                    }
                    .tab-button {
                        flex: 1;
                        min-width: 120px;
                        padding: 15px 20px;
                        background: #f1f1f1;
                        border: none;
                        cursor: pointer;
                        transition: background 0.3s;
                        font-weight: bold;
                        text-align: center;
                    }
                    .tab-button:hover {
                        background: #e0e0e0;
                    }
                    .tab-button.active {
                        background: #007bff;
                        color: white;
                    }
                    .tab-content {
                        display: none;
                        padding: 20px;
                        background: white;
                        border-radius: 0 0 8px 8px;
                        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                    }
                    .tab-content.active {
                        display: block;
                    }
                    .chart-container {
                        width: 100%;
                        height: 80vh;
                    }
                </style>
            </head>
            <body>
                <h1 class="header">SOM训练结果可视化报告</h1>
                <div class="tabs">
        '''

        # 添加标签按钮
        tab_names = list(figures.keys())
        for i, tab_name in enumerate(tab_names):
            button_class = "tab-button active" if i == 0 else "tab-button"
            html_string += f'<button class="{button_class}" onclick="openTab(\'tab{i}\')">{tab_name}</button>\n'

        html_string += '''
                </div>
        '''

        # 添加标签内容
        for i, (tab_name, fig) in enumerate(figures.items()):
            content_class = "tab-content active" if i == 0 else "tab-content"
            html_string += f'<div id="tab{i}" class="{content_class}">\n'
            html_string += '<div class="chart-container">\n'
            html_string += fig.to_html(include_plotlyjs=True, div_id=f"plotly-graph{i}")  # 内联Plotly.js
            html_string += '</div>\n</div>\n'

        # 添加JavaScript
        html_string += '''
                <script>
                    function openTab(tabId) {
                        // 隐藏所有标签内容
                        var tabContents = document.getElementsByClassName("tab-content");
                        for (var i = 0; i < tabContents.length; i++) {
                            tabContents[i].classList.remove("active");
                        }

                        // 移除所有活动按钮的活动类
                        var tabButtons = document.getElementsByClassName("tab-button");
                        for (var i = 0; i < tabButtons.length; i++) {
                            tabButtons[i].classList.remove("active");
                        }

                        // 显示当前标签并添加活动类到按钮
                        document.getElementById(tabId).classList.add("active");
                        event.currentTarget.classList.add("active");

                        // 重新调整图表大小
                        var chartId = "plotly-graph" + tabId.replace("tab", "");
                        if (typeof Plotly !== 'undefined') {
                            Plotly.Plots.resize(chartId);
                        }
                    }

                    // 页面加载完成后调整所有图表大小
                    window.addEventListener('load', function() {
        '''

        # 添加调整所有图表大小的代码
        for i in range(len(figures)):
            html_string += f"                        if (typeof Plotly !== 'undefined') Plotly.Plots.resize('plotly-graph{i}');\n"

        html_string += '''
                    });

                    // 窗口大小改变时调整所有图表大小
                    window.addEventListener('resize', function() {
        '''

        # 添加调整所有图表大小的代码
        for i in range(len(figures)):
            html_string += f"                        if (typeof Plotly !== 'undefined') Plotly.Plots.resize('plotly-graph{i}');\n"

        html_string += '''
                    });
                </script>
            </body>
        </html>
        '''

        # 保存HTML文件
        html_path = os.path.join(model_dir, "som_visualization.html")
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_string)

        self.som_html_path = html_path
        self.logger.info(f"SOM交互式可视化报告已保存至: {html_path}")
