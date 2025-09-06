# core/gui_components/system_monitor.py
import time, os, psutil, logging, datetime, sys, threading
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QTextEdit, QPushButton,
    QFileDialog, QMessageBox, QApplication)
from PySide6.QtCore import QTimer, Signal, QObject
from PySide6.QtGui import QFont, QTextCursor

from ..config import CONFIG


class RedirectOutput:
    """重定向输出到文本框"""

    def __init__(self, text_widget):
        self.text_widget = text_widget
        self.original_stdout = sys.stdout

    def write(self, text):
        # 在主线程中更新UI
        if hasattr(self.text_widget, 'append'):
            QApplication.instance().processEvents()  # 处理挂起的事件
            self.text_widget.append(text.rstrip())
            self.text_widget.moveCursor(QTextCursor.End)
        else:
            self.original_stdout.write(text)

    def flush(self):
        if hasattr(self.original_stdout, 'flush'):
            self.original_stdout.flush()


class SystemMonitorWorker(QObject):
    """系统监控工作线程"""
    update_monitor_display = Signal(str)
    update_status = Signal(str)
    error_occurred = Signal(str)
    finished = Signal()  # 添加完成信号

    def __init__(self, app, monitor_logger):
        super().__init__()
        self.app = app
        self.monitor_logger = monitor_logger
        self.computer = None
        self.gpu_hardware = []
        self.LIBRE_HARDWARE_MONITOR_AVAILABLE = False
        self.running = False
        self._init_hardware_monitor()

    def _init_hardware_monitor(self):
        """初始化硬件监控器"""
        try:
            import clr
            print(f"CLR模块导入成功")
            dll_path = os.path.join(CONFIG["base_dir"], "LibreHardwareMonitor", "LibreHardwareMonitorLib.dll")

            # 检查DLL文件是否存在
            if not os.path.exists(dll_path):
                print(f"LibreHardwareMonitor DLL文件不存在: {dll_path}")
                self.LIBRE_HARDWARE_MONITOR_AVAILABLE = False
                return

            clr.AddReference(dll_path)
            from LibreHardwareMonitor.Hardware import Computer
            self.computer = Computer()
            self.computer.IsGpuEnabled = True
            self.computer.IsCpuEnabled = False
            self.computer.IsMemoryEnabled = False
            self.computer.IsMotherboardEnabled = False
            self.computer.IsControllerEnabled = False
            self.computer.IsNetworkEnabled = False
            self.computer.IsStorageEnabled = False
            self.computer.Open()
            self.gpu_hardware = []

            # 获取GPU硬件列表
            gpu_count = 0
            for hardware in self.computer.Hardware:
                print(f"检测到硬件: {hardware.Name}, 类型: {hardware.HardwareType}")
                if str(hardware.HardwareType) in ["GpuAmd", "GpuNvidia", "GpuIntel"]:
                    hardware.Update()
                    self.gpu_hardware.append(hardware)
                    gpu_count += 1

            self.LIBRE_HARDWARE_MONITOR_AVAILABLE = True
            print(f"LibreHardwareMonitor初始化成功，检测到 {gpu_count} 个GPU")

            if gpu_count == 0:
                print("未检测到GPU硬件，列出所有检测到的硬件:")
                for i, hardware in enumerate(self.computer.Hardware):
                    print(f"  [{i}] {hardware.Name} (类型: {hardware.HardwareType})")

        except Exception as e:
            error_msg = f"LibreHardwareMonitor初始化失败: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            self.LIBRE_HARDWARE_MONITOR_AVAILABLE = False
            self.computer = None
            self.gpu_hardware = []

    def _close_hardware_monitor(self):
        """关闭硬件监控器，释放.dll资源"""
        try:
            if self.computer:
                print("正在关闭硬件监控器...")
                self.computer.Close()
                self.gpu_hardware = []
                self.computer = None
                self.LIBRE_HARDWARE_MONITOR_AVAILABLE = False
                print("硬件监控器已关闭")
        except Exception as e:
            print(f"关闭硬件监控器时出错: {str(e)}")
            import traceback
            traceback.print_exc()

    def start_monitoring(self):
        """开始监控"""
        self.running = True
        self.run_system_monitor()

    def stop_monitoring(self):
        """停止监控"""
        print("收到停止监控信号...")
        self.running = False

    def run_system_monitor(self):
        """运行系统监控"""
        try:
            while self.running:
                try:
                    # 获取系统信息
                    cpu_percent = psutil.cpu_percent(interval=1)  # 减少间隔以提高响应性
                    memory = psutil.virtual_memory()
                    disk = psutil.disk_usage('/')

                    # 获取GPU信息（如果可用）
                    gpu_info = self.get_gpu_info()

                    # 格式化输出
                    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    monitor_text = (
                        f"[{timestamp}]\n"
                        f"CPU使用率: {cpu_percent}%\n"
                        f"内存使用: {memory.used / (1024 ** 3):.2f} GB / {memory.total / (1024 ** 3):.2f} GB "
                        f"({memory.percent}%)\n"
                        f"磁盘使用: {disk.used / (1024 ** 3):.2f} GB / {disk.total / (1024 ** 3):.2f} GB "
                        f"({disk.percent}%)\n"
                    )

                    # 添加GPU信息（如果可用）
                    if gpu_info:
                        for i, gpu in enumerate(gpu_info):
                            monitor_text += (
                                f"GPU {i} ({gpu['name']}): 使用率 {gpu['utilization']}%, "
                                f"显存 {gpu['memory_used']:.0f} MB / {gpu['memory_total']:.0f} MB "
                                f"({gpu['memory_percent']:.1f}%)\n"
                            )
                    else:
                        monitor_text += "GPU信息: 未检测到GPU或缺少依赖库\n"

                    monitor_text += f"{'-' * 50}\n"

                    # 发送信号更新监控显示区域
                    self.update_monitor_display.emit(monitor_text)

                    # 更新状态栏
                    self.update_status.emit("正在监控")

                    # 检查是否仍需要运行，提高响应性
                    if not self.running:
                        break

                    # 每1秒更新一次
                    for _ in range(2):
                        if not self.running:
                            break
                        time.sleep(0.5)

                except Exception as e:
                    error_text = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n监控出错: {str(e)}\n"
                    self.update_monitor_display.emit(error_text)
                    self.error_occurred.emit(f"监控出错: {str(e)}")
                    for _ in range(2):
                        if not self.running:
                            break
                        time.sleep(0.5)
        finally:
            print("正在退出监控循环...")
            self._close_hardware_monitor()
            print("监控循环已退出")
            self.finished.emit()

    def get_gpu_info(self):
        """获取GPU信息 - 使用LibreHardwareMonitor"""
        gpu_info = []

        if self.LIBRE_HARDWARE_MONITOR_AVAILABLE and self.computer and self.running:
            try:
                # 如果GPU硬件列表为空，重新扫描
                if not self.gpu_hardware:
                    print("GPU硬件列表为空，重新扫描...")
                    self.gpu_hardware = []  # 确保列表为空
                    for hardware in self.computer.Hardware:
                        if not self.running:  # 检查是否已停止
                            return []
                        print(f"重新扫描硬件: {hardware.Name}, 类型: {hardware.HardwareType}")
                        if str(hardware.HardwareType) in ["GpuAmd", "GpuNvidia", "GpuIntel"]:
                            hardware.Update()
                            self.gpu_hardware.append(hardware)
                            print(f"重新添加GPU硬件: {hardware.Name}")

                # 更新硬件信息
                for hardware in self.gpu_hardware:
                    if not self.running:  # 检查是否已停止
                        return []
                    hardware.Update()

                    name = hardware.Name
                    utilization = 0
                    memory_used = 0
                    memory_total = 0

                    # 遍历传感器获取GPU信息
                    for sensor in hardware.Sensors:
                        if not self.running:  # 检查是否已停止
                            return []
                        if str(sensor.SensorType) == "Load" and "GPU" in sensor.Name:
                            utilization = sensor.Value if sensor.Value is not None else 0
                        elif str(sensor.SensorType) == "SmallData" and "GPU Memory" in sensor.Name:
                            if "Used" in sensor.Name or "已用" in sensor.Name:
                                memory_used = sensor.Value if sensor.Value is not None else 0
                            elif "Total" in sensor.Name or "总量" in sensor.Name:
                                memory_total = sensor.Value if sensor.Value is not None else 0

                    memory_percent = (memory_used / memory_total * 100) if memory_total > 0 else 0

                    gpu_info.append({
                        "name": name,
                        "utilization": int(utilization),
                        "memory_used": memory_used,
                        "memory_total": memory_total,
                        "memory_percent": memory_percent
                    })
            except Exception as e:
                print(f"通过LibreHardwareMonitor获取GPU信息失败: {str(e)}")
                import traceback
                traceback.print_exc()

        return gpu_info  # 返回GPU信息列表


class SystemMonitor:
    def __init__(self, app):
        self.app = app
        self.logger = logging.getLogger("SystemMonitor")
        self.monitor_logger = None
        self.worker = None
        self.worker_thread = None
        self.monitor_text = None  # 保存监控文本框的引用

    def toggle_system_monitor(self):
        """切换系统监控状态"""
        try:
            self.app.monitoring_active = not self.app.monitoring_active
            if self.app.monitoring_active:
                self.app.sys_status_var.setText("监控中...")
                print("系统监控已启动")
                # 显示监控面板
                self.show_system_monitor_panel()
            else:
                self.app.sys_status_var.setText("正常")
                print("系统监控已停止")

                # 安全停止监控
                self.safe_stop_monitoring()

                # 延迟刷新页面，避免冲突
                QTimer.singleShot(100, self.app.refresh_page)
        except Exception as e:
            self.logger.error(f"切换系统监控时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"切换系统监控失败: {str(e)}")

    def safe_stop_monitoring(self):
        """安全停止监控线程"""
        try:
            if self.worker and self.worker_thread and self.worker_thread.is_alive():
                # 请求停止
                self.worker.stop_monitoring()

                # 等待线程退出
                self.worker_thread.join(timeout=3.0)
                if self.worker_thread.is_alive():
                    print("线程未在3秒内退出")

                print("监控线程已停止")
                self.worker = None
                self.worker_thread = None
        except Exception as e:
            self.logger.error(f"安全停止监控时出错: {str(e)}")

    def show_system_monitor_panel(self):
        """在系统输出框中添加系统监控标签"""
        try:
            # 检查是否已经添加了监控标签
            if not self.app.monitor_tab_added:
                # 创建监控文本框
                self.monitor_text = QTextEdit()
                self.monitor_text.setReadOnly(True)
                self.monitor_text.setFont(QFont('Consolas', 11))
                self.monitor_text.setStyleSheet("""
                    QTextEdit {
                        background-color: #ffffff;
                        color: #2c3e50;
                        border: 1px solid #bdc3c7;
                        border-radius: 3px;
                    }
                """)

                # 将监控文本框添加为系统输出框的新标签
                self.app.monitor_tab_index = self.app.output_tab_widget.addTab(self.monitor_text, "系统监控")
                self.app.monitor_tab_added = True

                # 启动监控
                QTimer.singleShot(100, self.start_monitoring)

                print("系统监控面板已添加到系统输出标签栏")
            else:
                # 如果已经添加了标签，则切换到监控标签页并获取文本框引用
                monitor_tab_index = -1
                for i in range(self.app.output_tab_widget.count()):
                    if self.app.output_tab_widget.tabText(i) == "系统监控":
                        self.app.output_tab_widget.setCurrentIndex(i)
                        monitor_tab_index = i
                        break

                # 获取已存在的监控文本框引用
                if monitor_tab_index != -1:
                    self.monitor_text = self.app.output_tab_widget.widget(monitor_tab_index)

                # 即使标签已存在，也要重新启动监控
                QTimer.singleShot(100, self.start_monitoring)

        except Exception as e:
            self.logger.error(f"显示系统监控面板时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"显示系统监控面板失败: {str(e)}")

    def setup_monitoring_logger(self):
        """设置系统监控日志记录器"""
        try:
            # 创建监控日志目录
            monitor_log_dir = os.path.join(CONFIG["base_dir"], "monitoring_logs")
            os.makedirs(monitor_log_dir, exist_ok=True)

            # 创建日志文件名（按日期）
            log_filename = f"system_monitor_{datetime.datetime.now().strftime('%Y%m%d')}.log"
            log_filepath = os.path.join(monitor_log_dir, log_filename)

            # 配置日志记录器
            self.monitor_logger = logging.getLogger("SystemMonitor")
            self.monitor_logger.setLevel(logging.INFO)

            # 清除现有的处理器以避免重复
            for handler in self.monitor_logger.handlers[:]:
                self.monitor_logger.removeHandler(handler)
                handler.close()

            # 创建文件处理器，使用UTF-8编码
            from logging.handlers import RotatingFileHandler
            file_handler = RotatingFileHandler(
                log_filepath,
                maxBytes=10 * 1024 * 1024,
                backupCount=5,
                encoding='utf-8'
            )
            file_handler.setLevel(logging.INFO)

            # 创建格式化器
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)

            self.monitor_logger.addHandler(file_handler)
        except Exception as e:
            self.app.logger.error(f"设置监控日志记录器时出错: {str(e)}")

    def start_monitoring(self):
        """启动监控"""
        try:
            # 设置监控日志记录器
            self.setup_monitoring_logger()

            # 创建工作对象
            self.worker = SystemMonitorWorker(self.app, self.monitor_logger)

            # 连接信号
            self.worker.update_monitor_display.connect(self._update_monitor_display)
            self.worker.update_status.connect(self._update_status)
            self.worker.error_occurred.connect(self._handle_error)
            self.worker.finished.connect(self._on_monitoring_finished)  # 连接完成信号

            self.worker_thread = threading.Thread(target=self.worker.start_monitoring, daemon=True)
            self.worker_thread.start()

        except Exception as e:
            error_msg = f"启动监控时出错: {str(e)}"
            self.app.logger.error(error_msg)
            QMessageBox.critical(self.app, "错误", error_msg)

    def _on_monitoring_finished(self):
        """监控线程完成时的处理"""
        self.worker = None
        self.worker_thread = None

    def _update_monitor_display(self, text):
        """更新监控显示区域并记录日志"""
        try:
            # 更新UI
            if hasattr(self, 'monitor_text') and self.monitor_text:
                self.monitor_text.append(text)
                self.monitor_text.moveCursor(QTextCursor.End)

            # 记录到日志文件
            if self.monitor_logger:
                lines = text.strip().split('\n')
                for line in lines:
                    if line and not line.startswith("=") and not line.startswith("-"):
                        if "[" in line and "]" in line:
                            continue
                        if isinstance(line, str):
                            self.monitor_logger.info(line.strip())
                        else:
                            self.monitor_logger.info(str(line).strip())
        except Exception as e:
            self.app.logger.error(f"更新监控显示时出错: {str(e)}")

    def _update_status(self, text):
        """更新状态"""
        try:
            if hasattr(self.app, 'sys_status_var') and self.app.sys_status_var:
                self.app.sys_status_var.setText(text)
        except Exception as e:
            self.app.logger.error(f"更新状态时出错: {str(e)}")

    def _handle_error(self, error_msg):
        """处理错误"""
        try:
            error_text = f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}]\n监控出错: {error_msg}\n"
            self._update_monitor_display(error_text)
            self.app.logger.error(f"监控出错: {error_msg}")
            QMessageBox.warning(self.app, "监控警告", f"监控过程中出现错误: {error_msg}")
        except Exception as e:
            self.app.logger.error(f"处理错误时出错: {str(e)}")

    def show_monitoring_logs(self):
        """显示监控日志"""
        try:
            logs_dialog = MonitoringLogsDialog(self.app)
            logs_dialog.show()
        except Exception as e:
            self.logger.error(f"显示监控日志时出错: {str(e)}")
            QMessageBox.critical(self.app, "错误", f"显示监控日志失败: {str(e)}")


class MonitoringLogsDialog(QDialog):
    def __init__(self, app):
        super().__init__(app)
        self.app = app
        self.log_path = None
        self.setWindowTitle("监控日志")
        self.resize(900, 600)
        self.center_window()
        self.init_ui()

    def center_window(self):
        """居中显示窗口"""
        screen = QApplication.primaryScreen().geometry()
        window_geometry = self.frameGeometry()
        center_point = screen.center()
        window_geometry.moveCenter(center_point)
        self.move(window_geometry.topLeft())

    def init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)

        # 标题
        self.title_label = QLabel("监控日志")
        title_font = QFont("Microsoft YaHei", 14, QFont.Bold)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)

        # 创建文本框显示日志内容
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setFont(QFont('Consolas', 10))
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #2c3e50;
                border: 1px solid #bdc3c7;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.log_text)

        # 添加按钮
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.refresh_btn = QPushButton("刷新")
        self.refresh_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        self.refresh_btn.clicked.connect(self.refresh_log)
        button_layout.addWidget(self.refresh_btn)

        self.select_btn = QPushButton("选择文件")
        self.select_btn.setStyleSheet("background-color: #3498db; color: white; font-weight: bold;")
        self.select_btn.clicked.connect(self.select_log_file)
        button_layout.addWidget(self.select_btn)

        self.close_btn = QPushButton("关闭")
        self.close_btn.setStyleSheet("background-color: #95a5a6; color: white; font-weight: bold;")
        self.close_btn.clicked.connect(self.close)
        button_layout.addWidget(self.close_btn)

        layout.addLayout(button_layout)

        # 加载最新的日志文件
        self.load_latest_log()

    def load_latest_log(self):
        """加载最新的日志文件"""
        monitor_log_dir = os.path.join(CONFIG["base_dir"], "monitoring_logs")
        if not os.path.exists(monitor_log_dir):
            QMessageBox.information(self, "提示", "暂无监控日志")
            return

        log_files = [f for f in os.listdir(monitor_log_dir) if f.endswith('.log')]
        if not log_files:
            QMessageBox.information(self, "提示", "暂无监控日志")
            return

        # 按修改时间排序，获取最新的日志文件
        log_files.sort(key=lambda x: os.path.getmtime(os.path.join(monitor_log_dir, x)), reverse=True)
        latest_log = log_files[0]
        self.log_path = os.path.join(monitor_log_dir, latest_log)
        self.title_label.setText(f"监控日志 - {latest_log}")

        # 读取并显示日志内容
        content = self.read_log_file(self.log_path)
        if content is not None:
            self.log_text.setPlainText(content)
            self.log_text.moveCursor(QTextCursor.End)
        else:
            self.log_text.setPlainText("读取日志文件失败")

    def read_log_file(self, file_path):
        """尝试多种编码方式读取日志文件"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']

        # 首先尝试检测文件编码
        try:
            import chardet
            with open(file_path, 'rb') as f:
                raw_data = f.read()
                result = chardet.detect(raw_data)
                detected_encoding = result['encoding']
                if detected_encoding and detected_encoding not in encodings:
                    encodings.insert(0, detected_encoding)
        except ImportError:
            # chardet未安装，跳过自动检测
            pass
        except Exception:
            # 检测失败，使用默认编码列表
            pass

        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                return content
            except UnicodeDecodeError:
                continue
            except Exception:
                continue

        # 如果所有编码都失败，使用二进制模式读取并解码
        try:
            with open(file_path, 'rb') as f:
                content = f.read()
                return content.decode('utf-8', errors='ignore')
        except Exception:
            return None

    def refresh_log(self):
        """刷新日志内容"""
        if self.log_path and os.path.exists(self.log_path):
            content = self.read_log_file(self.log_path)
            if content is not None:
                self.log_text.setPlainText(content)
                self.log_text.moveCursor(QTextCursor.End)
            else:
                self.log_text.setPlainText("读取日志文件失败")

    def select_log_file(self):
        """选择其他日志文件"""
        monitor_log_dir = os.path.join(CONFIG["base_dir"], "monitoring_logs")
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "选择日志文件",
            monitor_log_dir,
            "Log files (*.log)"
        )
        if file_path:
            self.log_path = file_path
            self.title_label.setText(f"监控日志 - {os.path.basename(file_path)}")
            content = self.read_log_file(file_path)
            if content is not None:
                self.log_text.setPlainText(content)
                self.log_text.moveCursor(QTextCursor.End)
            else:
                self.log_text.setPlainText("读取日志文件失败")
