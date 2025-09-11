import requests, os, sys, logging, subprocess, urllib3
from PySide6.QtWidgets import QMessageBox, QProgressDialog, QApplication
from PySide6.QtCore import Qt, QThread, Signal
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from ..config import CONFIG

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UpdateChecker(QThread):
    """检查更新线程"""
    # 定义信号，用于通知主线程检查结果
    update_available = Signal(dict)  # 有可用更新时发出信号
    no_update = Signal()  # 无更新时发出信号
    error_occurred = Signal(str)  # 出现错误时发出信号
    def __init__(self, current_version, silent=False):
        super().__init__()
        self.current_version = current_version
        self.repo_url = "https://api.github.com/repos/Legionxun/spectra-refract-svr/releases/latest"
        self.logger = logging.getLogger("AutoUpdater")
        self.silent = silent  # 是否静默更新

    def create_session(self):
        """创建一个带有重试策略和SSL处理的requests会话"""
        session = requests.Session()

        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def run(self):
        try:
            if not self.silent:
                self.logger.info("开始检查更新")
            else:
                self.logger.debug("开始静默检查更新")

            # 创建会话
            session = self.create_session()

            # 尝试多种方式获取数据
            response = None
            errors = []

            # 方法1: 正常请求
            try:
                response = session.get(self.repo_url, timeout=20, verify=True)
            except Exception as e:
                errors.append(f"正常请求失败: {str(e)}")

                # 方法2: 不验证SSL证书
                try:
                    response = session.get(self.repo_url, timeout=20, verify=False)
                    self.logger.warning("使用不验证SSL证书的方式获取更新信息")
                except Exception as e:
                    errors.append(f"跳过SSL验证也失败: {str(e)}")

                    # 方法3: 使用系统证书
                    try:
                        response = session.get(self.repo_url, timeout=20, verify=True,
                                               certifi_cert=True if 'certifi' in sys.modules else False)
                    except Exception as e:
                        errors.append(f"使用系统证书也失败: {str(e)}")

            if response is None or response.status_code != 200:
                error_msg = "无法连接到更新服务器。错误详情:\n" + "\n".join(errors)
                if response:
                    error_msg += f"\nHTTP状态码: {response.status_code}"
                self.error_occurred.emit(error_msg)
                return

            release_info = response.json()
            latest_version = release_info.get("tag_name", "").lstrip("vV")

            self.logger.debug(f"当前版本: {self.current_version}, 最新版本: {latest_version}")

            # 简单的版本比较（实际项目中可能需要更复杂的版本比较逻辑）
            if latest_version > self.current_version:
                self.update_available.emit(release_info)
            else:
                self.no_update.emit()

        except Exception as e:
            self.logger.error(f"检查更新时发生错误: {str(e)}")
            self.error_occurred.emit(f"检查更新时发生错误: {str(e)}")


class UpdateDownloader(QThread):
    """更新下载线程"""
    # 定义信号
    download_progress = Signal(int)  # 下载进度信号
    download_finished = Signal(str)  # 下载完成信号，传递文件路径
    download_error = Signal(str)  # 下载错误信号
    def __init__(self, download_url, file_name):
        super().__init__()
        self.download_url = download_url
        self.file_name = file_name
        self.logger = logging.getLogger("AutoUpdater")

    def run(self):
        try:
            self.logger.info(f"开始下载更新: {self.download_url}")

            # 创建临时目录用于存放下载的文件
            os.makedirs(CONFIG["download"], exist_ok=True)
            file_path = os.path.join(CONFIG["download"], self.file_name)

            # 发起下载请求，处理SSL证书问题
            session = requests.Session()
            retry_strategy = Retry(
                total=3,
                backoff_factor=1,
                status_forcelist=[429, 500, 502, 503, 504],
            )
            adapter = HTTPAdapter(max_retries=retry_strategy)
            session.mount("http://", adapter)
            session.mount("https://", adapter)

            # 尝试多种方式下载
            response = None
            errors = []

            # 方法1: 正常请求
            try:
                response = session.get(self.download_url, stream=True, timeout=60, verify=True)
            except Exception as e:
                errors.append(f"正常下载失败: {str(e)}")

                # 方法2: 不验证SSL证书
                try:
                    response = session.get(self.download_url, stream=True, timeout=60, verify=False)
                    self.logger.warning("使用不验证SSL证书的方式下载更新文件")
                except Exception as e:
                    errors.append(f"跳过SSL验证也失败: {str(e)}")

            if response is None:
                error_msg = "无法下载更新文件。错误详情:\n" + "\n".join(errors)
                print("无法下载更新文件，请访问以下网页手动下载安装包。")
                print(self.download_url)
                raise Exception(error_msg)

            response.raise_for_status()

            # 获取文件总大小
            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            # 写入文件并更新进度
            with open(file_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 计算并发送进度
                        if total_size > 0:
                            progress = int((downloaded_size / total_size) * 100)
                            self.download_progress.emit(progress)

            self.logger.info(f"更新下载完成: {file_path}")
            self.download_finished.emit(file_path)

        except Exception as e:
            self.logger.error(f"下载更新时发生错误: {str(e)}")
            self.download_error.emit(f"下载更新时发生错误: {str(e)}")


class AutoUpdater:
    """自动更新管理器"""
    def __init__(self, main_window, current_version="3.1.0"):
        self.main_window = main_window
        self.current_version = current_version
        self.logger = logging.getLogger("AutoUpdater")
        self.update_checker = None
        self.update_downloader = None
        self.progress_dialog = None

    def check_for_updates(self, silent=False):
        """
        检查是否有可用更新
        :param silent: 是否静默检查更新（不显示进度条）
        """
        if not silent:
            self.logger.info("正在检查更新...")
        else:
            self.logger.debug("正在静默检查更新...")

        # 创建进度对话框（仅在非静默模式下显示）
        if not silent:
            self.progress_dialog = QProgressDialog("正在检查更新...", "取消", 0, 0, self.main_window)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setWindowTitle("检查更新")
            self.progress_dialog.show()

        # 创建并启动检查更新线程
        self.update_checker = UpdateChecker(self.current_version, silent)
        self.update_checker.update_available.connect(lambda info: self.on_update_available(info, silent))
        self.update_checker.no_update.connect(lambda: self.on_no_update(silent))
        self.update_checker.error_occurred.connect(lambda msg: self.on_check_error(msg, silent))

        # 静默模式下不显示进度条，但仍需在完成后清理
        if silent:
            self.update_checker.finished.connect(lambda: None)
        else:
            self.update_checker.finished.connect(self.progress_dialog.close)

        self.update_checker.start()

    def on_update_available(self, release_info, silent=False):
        """当有可用更新时调用"""
        latest_version = release_info.get("tag_name", "")
        release_notes = release_info.get("body", "无更新说明")

        self.logger.info(f"发现新版本 {latest_version}")
        print(f"发现新版本 {latest_version}")

        # 弹出对话框询问用户是否下载更新（仅在非静默模式下）
        reply = QMessageBox.question(
            self.main_window,
            "发现新版本",
            f"发现新版本 {latest_version}，是否下载更新？\n\n更新说明：\n{release_notes}",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.download_update(release_info)

    def on_no_update(self, silent=False):
        """当无更新时调用"""
        if not silent:  # 只在非静默模式下显示提示
            QMessageBox.information(
                self.main_window,
                "检查更新",
                f"当前已是最新版本 ({self.current_version})",
                QMessageBox.Ok
            )
        else:
            self.logger.debug(f"静默检查更新：当前已是最新版本 ({self.current_version})")
            print(f"当前已是最新版本 ({self.current_version})")

    def on_check_error(self, error_msg, silent=False):
        """当检查更新出错时调用"""
        if not silent:  # 只在非静默模式下显示错误
            QMessageBox.warning(
                self.main_window,
                "检查更新",
                f"检查更新时发生错误：\n{error_msg}",
                QMessageBox.Ok
            )
        else:
            self.logger.warning(f"静默检查更新时发生错误：{error_msg}")

    def download_update(self, release_info):
        """下载更新文件"""
        # 查找exe安装包的下载链接
        assets = release_info.get("assets", [])
        download_url = None
        file_name = "optisvr_setup.exe"

        # 查找optisvr_setup.exe文件
        for asset in assets:
            if "optisvr_setup.exe" in asset.get("name", ""):
                download_url = asset.get("browser_download_url")
                file_name = asset.get("name")
                break

        # 如果没有找到exe文件，则使用源码包
        if not download_url:
            download_url = release_info.get("zipball_url")
            file_name = f"spectra-refract-svr-{release_info.get('tag_name')}.zip"

        if download_url:
            self.logger.info(f"找到更新文件: {file_name}")

            # 创建下载进度对话框
            self.progress_dialog = QProgressDialog("正在下载更新...", "取消", 0, 100, self.main_window)
            self.progress_dialog.setWindowModality(Qt.WindowModal)
            self.progress_dialog.setWindowTitle("下载更新")
            self.progress_dialog.show()

            # 创建并启动下载线程
            self.update_downloader = UpdateDownloader(download_url, file_name)
            self.update_downloader.download_progress.connect(self.on_download_progress)
            self.update_downloader.download_finished.connect(self.on_download_finished)
            self.update_downloader.download_error.connect(self.on_download_error)
            self.update_downloader.start()
        else:
            QMessageBox.warning(
                self.main_window,
                "下载更新",
                "未找到更新文件下载链接",
                QMessageBox.Ok
            )

    def on_download_progress(self, progress):
        """更新下载进度"""
        if self.progress_dialog:
            self.progress_dialog.setValue(progress)

    def on_download_finished(self, file_path):
        """下载完成时调用"""
        if self.progress_dialog:
            self.progress_dialog.close()

        # 询问用户是否立即安装更新
        reply = QMessageBox.question(
            self.main_window,
            "下载完成",
            f"更新已下载到：\n{file_path}\n\n是否立即安装？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )

        if reply == QMessageBox.Yes:
            self.install_update(file_path)

    def on_download_error(self, error_msg):
        """下载出错时调用"""
        if self.progress_dialog:
            self.progress_dialog.close()

        QMessageBox.warning(
            self.main_window,
            "下载更新",
            f"下载更新时发生错误：\n{error_msg}",
            QMessageBox.Ok
        )

    def install_update(self, file_path):
        """安装更新"""
        try:
            self.logger.info(f"启动安装程序: {file_path}")

            # 根据文件类型执行不同的操作
            if file_path.endswith('.exe'):
                # 启动exe安装程序
                subprocess.Popen([file_path])

                # 询问是否关闭当前程序
                reply = QMessageBox.question(
                    self.main_window,
                    "安装更新",
                    "安装程序已启动，是否关闭当前程序？",
                    QMessageBox.Yes | QMessageBox.No,
                    QMessageBox.Yes
                )

                if reply == QMessageBox.Yes:
                    QApplication.quit()
            else:
                directory = os.path.dirname(file_path)
                if sys.platform == "win32":
                    os.startfile(directory)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", directory])
                else:
                    subprocess.Popen(["xdg-open", directory])

                QMessageBox.information(
                    self.main_window,
                    "安装更新",
                    f"更新文件已下载到：\n{directory}\n\n请手动解压并安装。",
                    QMessageBox.Ok
                )

        except Exception as e:
            self.logger.error(f"安装更新时发生错误: {str(e)}")
            QMessageBox.warning(
                self.main_window,
                "安装更新",
                f"启动安装程序时发生错误：\n{str(e)}",
                QMessageBox.Ok
            )
