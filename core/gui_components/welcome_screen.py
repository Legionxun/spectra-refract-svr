# core/gui_components/welcome_screen.py
import random, logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsTextItem
from PySide6.QtCore import Qt, QTimer, QRectF
from PySide6.QtGui import QPainter, QColor, QFont, QBrush, QPen, QLinearGradient


class BubbleItem(QGraphicsEllipseItem):
    """气泡图形项"""

    def __init__(self, x, y, size, color, alpha):
        super().__init__(0, 0, size, size)
        self.size = size
        self.speed = random.uniform(0.8, 2.5)
        self.drift = random.uniform(-0.5, 0.5)
        self.alpha = alpha

        # 设置气泡主体
        color_with_alpha = QColor(color)
        color_with_alpha.setAlphaF(alpha)
        self.setBrush(QBrush(color_with_alpha))
        self.setPen(QPen(Qt.NoPen))
        self.setPos(x, y)

        # 创建高光
        highlight_size = size // 3
        self.highlight = QGraphicsEllipseItem(
            0, 0, highlight_size, highlight_size)
        self.highlight.setBrush(QBrush(QColor(255, 255, 255, 180)))
        self.highlight.setPen(QPen(Qt.NoPen))
        self.highlight.setParentItem(self)
        self.highlight.setPos(size * 0.2, size * 0.2)

        # 创建反光
        reflection_size = size // 5
        self.reflection = QGraphicsEllipseItem(
            0, 0, reflection_size, reflection_size)
        self.reflection.setBrush(QBrush(QColor(255, 255, 255, 128)))
        self.reflection.setPen(QPen(Qt.NoPen))
        self.reflection.setParentItem(self)
        self.reflection.setPos(size * 0.6, size * 0.4)

    def update_position(self, width, height):
        """更新气泡位置"""
        # 移动气泡
        y = self.y() - self.speed
        x = self.x() + self.drift

        # 如果气泡移出顶部，重置到底部
        if y + self.size < 0:
            y = height
            x = random.randint(0, int(width))

        # 更新气泡位置
        self.setPos(x, y)
        return x, y


class WelcomeGraphicsView(QGraphicsView):
    """欢迎界面图形视图"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: transparent; border: none;")
        self.setRenderHint(QPainter.Antialiasing)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setFrameShape(QGraphicsView.NoFrame)


class WelcomeScreen:
    # 欢迎界面
    def __init__(self, parent_frame, app):
        self.parent_frame = parent_frame
        self.app = app
        self.logger = logging.getLogger("WelcomeScreen")
        self.bubbles = []
        self.animation_running = False
        self.animation_timer = None
        self.current_title = "OptiSVR分光计折射率预测系统"
        self.current_subtitle = "使用AI技术支持向量回归算法（SVR）和分簇回归模型预测棱镜折射率"
        self.current_prompt = "请使用左侧按钮开始操作：生成理论数据 → 训练模型 → 加载模型 → 导入数据 → 预测"
        self.graphics_view = None
        self.background_scene = None
        self.content_scene = None
        self.title_item = None
        self.subtitle_item = None
        self.prompt_item = None
        self.background_item = None


    def show_welcome_image(self):
        """显示带渐变色和气泡动画的欢迎界面"""
        self.logger.info("运行启动界面")

        # 清空父框架中的所有部件
        for i in reversed(range(self.parent_frame.layout().count())):
            widget = self.parent_frame.layout().itemAt(i).widget()
            if widget:
                widget.deleteLater()

        # 创建欢迎界面容器
        welcome_container = QWidget()
        layout = QVBoxLayout(welcome_container)
        layout.setContentsMargins(0, 0, 0, 0)

        # 创建图形视图
        self.graphics_view = WelcomeGraphicsView()

        self.background_scene = QGraphicsScene()
        self.content_scene = QGraphicsScene()

        # 设置视图使用内容场景
        self.graphics_view.setScene(self.content_scene)

        layout.addWidget(self.graphics_view)
        self.parent_frame.layout().addWidget(welcome_container)

        # 绘制背景和内容
        self.draw_content()

        # 开始气泡动画
        self.start_bubble_animation()

    def draw_content(self):
        """绘制内容"""
        if not self.graphics_view:
            return

        # 获取视图尺寸
        rect = self.graphics_view.rect()
        width = rect.width()
        height = rect.height()

        if width < 10 or height < 10:
            return

        # 清空场景
        self.content_scene.clear()
        self.background_scene.clear()
        self.bubbles = []
        self.background_item = None

        # 绘制渐变背景
        self.draw_gradient_background(width, height)

        # 设置背景场景
        background_rect = QRectF(0, 0, width, height)
        self.background_scene.setSceneRect(background_rect)
        self.graphics_view.setBackgroundBrush(self.background_scene.backgroundBrush())

        # 创建固定坐标系中的气泡
        self.create_bubbles(25, 800, 600)

        # 添加标题
        self.title_item = QGraphicsTextItem(self.current_title)
        title_font = QFont('Microsoft YaHei', 38, QFont.Bold)
        self.title_item.setFont(title_font)
        self.title_item.setDefaultTextColor(QColor("#ffffff"))
        self.title_item.setGraphicsEffect(None)  # 移除可能的特效

        # 添加副标题
        self.subtitle_item = QGraphicsTextItem(self.current_subtitle)
        subtitle_font = QFont('Microsoft YaHei', 22)
        self.subtitle_item.setFont(subtitle_font)
        self.subtitle_item.setDefaultTextColor(QColor("#bbdefb"))

        # 添加功能提示
        self.prompt_item = QGraphicsTextItem(self.current_prompt)
        prompt_font = QFont('Microsoft YaHei', 18)
        self.prompt_item.setFont(prompt_font)
        self.prompt_item.setDefaultTextColor(QColor("#4fc3f7"))

        # 设置内容场景
        content_width, content_height = 800, 600
        content_rect = QRectF(0, 0, content_width, content_height)
        self.content_scene.setSceneRect(content_rect)

        # 将文本项添加到场景中并居中定位
        self.content_scene.addItem(self.title_item)
        self.content_scene.addItem(self.subtitle_item)
        self.content_scene.addItem(self.prompt_item)

        # 居中放置文本
        self.title_item.setPos(content_width // 2 - self.title_item.boundingRect().width() // 2,
                               content_height // 2 - 80)
        self.subtitle_item.setPos(content_width // 2 - self.subtitle_item.boundingRect().width() // 2,
                                  content_height // 2)
        self.prompt_item.setPos(content_width // 2 - self.prompt_item.boundingRect().width() // 2,
                                content_height // 2 + 80)

        # 调整视图以适应内容
        self.graphics_view.fitInView(content_rect, Qt.KeepAspectRatio)

    def update_message(self, title, message):
        """更新欢迎界面上的文本信息"""
        self.current_title = title
        self.current_subtitle = message
        self.current_prompt = "训练进行中，请稍候..."

        # 更新文本项
        if self.title_item:
            self.title_item.setPlainText(self.current_title)
            # 重新居中
            content_width = 800
            self.title_item.setPos(content_width // 2 - self.title_item.boundingRect().width() // 2,
                                   self.title_item.pos().y())

        if self.subtitle_item:
            self.subtitle_item.setPlainText(self.current_subtitle)
            # 重新居中
            content_width = 800
            self.subtitle_item.setPos(content_width // 2 - self.subtitle_item.boundingRect().width() // 2,
                                      self.subtitle_item.pos().y())

        if self.prompt_item:
            self.prompt_item.setPlainText(self.current_prompt)
            # 重新居中
            content_width = 800
            self.prompt_item.setPos(content_width // 2 - self.prompt_item.boundingRect().width() // 2,
                                    self.prompt_item.pos().y())

    def draw_gradient_background(self, width, height):
        """绘制深空蓝色渐变背景"""
        if width < 10 or height < 10:
            return

        # 使用线性渐变替代逐行绘制，消除条纹
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(30, 40, 100))  # 深空蓝
        gradient.setColorAt(0.5, QColor(20, 30, 80))  # 中间色调
        gradient.setColorAt(1, QColor(10, 20, 60))  # 更深的蓝紫色

        # 设置背景画刷
        self.background_scene.setBackgroundBrush(QBrush(gradient))

    def create_bubbles(self, count, width, height):
        """创建气泡"""
        if width < 100 or height < 100:
            return

        colors = ["#64b5f6", "#4fc3f7", "#4dd0e1", "#80deea", "#bbdefb"]
        for _ in range(count):
            # 随机气泡大小
            size = random.randint(15, 60)
            # 随机起始位置
            x = random.randint(0, int(max(0, width - size)))
            y = random.randint(0, int(height))
            # 随机透明度
            alpha = random.uniform(0.2, 0.6)
            # 随机选择气泡颜色
            color = random.choice(colors)

            # 创建气泡
            bubble = BubbleItem(x, y, size, color, alpha)
            self.content_scene.addItem(bubble)

            # 保存气泡引用
            self.bubbles.append(bubble)

    def start_bubble_animation(self):
        """启动气泡动画"""
        # 如果动画已经在运行，则先停止
        if self.animation_running:
            self.stop_bubble_animation()

        # 启动新的动画定时器
        if not self.animation_running:
            self.animation_running = True
            self.animation_timer = QTimer()
            self.animation_timer.timeout.connect(self._update_bubble_positions)
            self.animation_timer.start(30)  # 30ms延迟，约33FPS

    def stop_bubble_animation(self):
        """停止气泡动画"""
        self.animation_running = False
        if self.animation_timer:
            self.animation_timer.stop()
            self.animation_timer = None

    def _update_bubble_positions(self):
        """更新气泡位置"""
        if not self.animation_running or not self.content_scene:
            return

        try:
            # 使用固定坐标系统更新气泡位置
            width, height = 800, 600

            if width < 10 or height < 10:
                return
            # 更新每个气泡的位置
            for bubble in self.bubbles:
                bubble.update_position(width, height)

        except Exception as e:
            self.logger.error(f"更新气泡位置出错: {str(e)}")

    def on_resize(self, event):
        """处理尺寸变化事件"""
        self.draw_content()
