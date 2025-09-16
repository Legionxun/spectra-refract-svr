# OptiSVR_Spectral_Refractive_Index_Prediction_System.py
import threading, datetime, logging, os, sys, certifi
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer

from core.start_screen import StartScreen
from core.gui import RefractiveIndexApp
from core.utils import setup_logging

def get_base_path():
    """获取基础路径"""
    if getattr(sys, 'frozen', False):
        return os.path.dirname(sys.executable)
    else:
        return os.path.dirname(os.path.abspath(__file__))

def where():
    """替代certifi的where函数"""
    base_path = get_base_path()
    cert_path = os.path.join(base_path, 'certifi', 'cacert.pem')

    # 检查是否存在cacert.pem文件
    if not os.path.exists(cert_path):
        cert_path = os.path.join(os.path.dirname(sys.executable), 'certifi', 'cacert.pem')
    if os.path.exists(cert_path):
        return cert_path
    try:
        import certifi as orig_certifi
        return orig_certifi.where()
    except ImportError:
        return os.path.join(os.path.dirname(__file__), 'cacert.pem')

def contents():
    """替代certifi的contents函数"""
    cert_path = where()
    try:
        with open(cert_path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        logging.error(f"读取证书文件失败: {str(e)}")
        return ""

def on_closing():
    """处理应用程序关闭事件"""
    global closing_flag
    if closing_flag:
        return
    closing_flag = True

    for timer in timers[:]:
        if timer is not None:
            timer.stop()
            timers.remove(timer)
    start_screen.stop_animation()
    logger.info("应用程序安全退出")

def setup_timers():
    """安全设置定时器"""
    global timers
    timer1 = QTimer()
    timer1.timeout.connect(lambda: start_screen.close_welcome())
    timer1.setSingleShot(True)
    timer1.start(1500)
    timers.append(timer1)

    timer2 = QTimer()
    timer2.timeout.connect(lambda: None)
    timer2.setSingleShot(True)
    timer2.start(1800)
    timers.append(timer2)

# 主程序入口
if __name__ == "__main__":
    # 添加一个标志来防止递归调用
    closing_flag = False

    # 配置日志系统
    log_file_path = setup_logging()
    logger = logging.getLogger("Main")

    # 记录启动信息
    logger.info("=" * 50)
    logger.info("OptiSVR分光计折射率预测系统启动")
    logger.info(f"日志文件路径: {log_file_path}")
    logger.info(f"系统时间: {datetime.datetime.now()}")
    logger.info("=" * 50)

    # 设置证书路径
    certifi.where = where
    certifi.contents = contents

    # 创建 PySide6 应用程序
    app = QApplication(sys.argv)
    app.setApplicationName("OptiSVR分光计折射率预测系统")

    # 创建主窗口
    main_window = RefractiveIndexApp()

    # 创建启动画面
    start_screen = StartScreen()

    # 将主窗口传递给启动画面
    start_screen.set_main_window(main_window)

    # 定时器列表
    timers = []

    # 启动启动画面线程
    tmain = threading.Thread(target=start_screen.show_welcome)
    tmain.daemon = True
    tmain.start()

    # 设置定时器
    QTimer.singleShot(100, lambda: setup_timers())

    # 处理应用程序退出事件
    app.aboutToQuit.connect(on_closing)

    # 启动主程序循环
    sys.exit(app.exec())
