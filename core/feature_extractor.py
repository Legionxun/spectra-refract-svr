# core.feature_extractor.py
import logging, os
import tensorflow as tf
import numpy as np
from tensorflow.keras.applications import ResNet50
from tensorflow.keras.applications.resnet50 import preprocess_input
from tensorflow.keras.models import Model

from .config import CONFIG
from .utils import get_app_root


class FeatureExtractor:
    def __init__(self, input_size=CONFIG["input_size"]):
        # 加载预训练ResNet50（不包含顶层）
        self.logger = logging.getLogger("FeatureExtractor")
        self.logger.info("初始化特征提取器")
        base_model = ResNet50(
            weights = os.path.join(get_app_root(),"resnet50","resnet50_weights_tf_dim_ordering_tf_kernels_notop.h5"),
            include_top=False,
            input_shape=input_size + (3,)
        )
        # 获取指定层的输出
        self.feature_model = Model(
            inputs=base_model.input,
            outputs=base_model.get_layer(CONFIG["pretrained_layer"]).output
        )
        # 添加全局平均池化
        self.model = tf.keras.Sequential([
            self.feature_model,
            tf.keras.layers.GlobalAveragePooling2D()
        ])

    def extract(self, img_path):
        """从单张图像提取特征向量"""
        self.logger.debug(f"从图像提取特征: {img_path}")
        try:
            img = tf.keras.preprocessing.image.load_img(
                img_path,
                target_size=CONFIG["input_size"])
            img_array = tf.keras.preprocessing.image.img_to_array(img)
            img_array = preprocess_input(img_array)
            features = self.model.predict(np.expand_dims(img_array, axis=0))[0]
            self.logger.debug(f"成功提取特征，向量长度: {len(features)}")
            return features
        except Exception as e:
            self.logger.error(f"特征提取失败: {str(e)}")
            raise

    def save(self, path):
        """单独保存Keras模型"""
        self.model.save(path)
        self.logger.debug(f"成功保存Keras模型")

    @classmethod
    def load(cls, path, input_size):
        """加载Keras模型"""
        instance = cls(input_size)
        instance.model = tf.keras.models.load_model(path)
        return instance
