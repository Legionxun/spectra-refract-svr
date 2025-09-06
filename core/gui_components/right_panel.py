# core/gui_components/right_panel.py
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter, QGroupBox, QTextEdit
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class RightPanelBuilder:
    def __init__(self, parent, app):
        self.parent = parent
        self.app = app

    def create(self):
        # 创建右侧面板主部件
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)

        # 创建可调整大小的分割器
        self.splitter = QSplitter(Qt.Vertical)
        self.splitter.setHandleWidth(5)  # 设置分割条宽度
        self.splitter.setStyleSheet("""
            QSplitter::handle {
                background-color: #bdc3c7;
                border: 1px solid #95a5a6;
            }
            QSplitter::handle:hover {
                background-color: #95a5a6;
            }
        """)

        # 输出文本框框架
        output_group = QGroupBox("系统输出")
        output_layout = QVBoxLayout(output_group)
        output_layout.setContentsMargins(5, 5, 5, 5)

        # 创建输出文本框
        self.output_text = QTextEdit()
        self.output_text.setReadOnly(True)
        self.output_text.setFont(QFont('Consolas', 10))
        self.output_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
        """)
        self.output_text.setLineWrapMode(QTextEdit.WidgetWidth)
        output_layout.addWidget(self.output_text)

        # 结果展示区域框架
        self.result_frame = QGroupBox("结果展示")
        self.result_layout = QVBoxLayout(self.result_frame)
        self.result_layout.setContentsMargins(5, 5, 5, 5)

        # 添加两个窗格到分割器中
        self.splitter.addWidget(output_group)
        self.splitter.addWidget(self.result_frame)

        # 设置初始大小比例
        self.splitter.setSizes([300, 300])

        right_layout.addWidget(self.splitter)

        # 绑定输出文本框和结果展示区域
        self.app.output_text = self.output_text
        self.app.result_frame = self.result_frame
        self.app.result_layout = self.result_layout

        return right_widget
