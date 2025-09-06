# core/gui_components/system_support.py
import sys
from PySide6.QtWidgets import QTextEdit
from PySide6.QtGui import QTextCursor
from PySide6.QtCore import QObject

# ======================
# 输出重定向类
# ======================
class RedirectOutput:
    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.original_stdout = sys.stdout

    def write(self, string):
        if hasattr(self.text_widget, 'append'):
            # PySide6 QTextEdit 使用 append 方法添加文本
            self.text_widget.append(string.rstrip('\n'))  # 移除末尾换行符，因为append会自动添加
            # 滚动到末尾
            self.text_widget.moveCursor(QTextCursor.End)
        else:
            # 如果不是QTextEdit，尝试使用原始方法
            if hasattr(self.text_widget, 'insert'):
                self.text_widget.insert(string)
                if hasattr(self.text_widget, 'see'):
                    self.text_widget.see('end')
                if hasattr(self.text_widget, 'update_idletasks'):
                    self.text_widget.update_idletasks()
            else:
                # 回退到标准输出
                self.original_stdout.write(string)

    def flush(self):
        if hasattr(self.original_stdout, 'flush'):
            self.original_stdout.flush()
