import requests, os, sys, logging, subprocess, tempfile, urllib3, threading
from tkinter import messagebox, ttk
import tkinter as tk
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class UpdateChecker:
    """检查更新类"""
    def __init__(self, current_version, silent=False):
        self.current_version = current_version
        self.repo_url = "https://api.github.com/repos/Legionxun/spectra-refract-svr/releases/latest"
        self.logger = logging.getLogger("AutoUpdater")
        self.silent = silent  # 是否静默更新
        self.callbacks = {
            'update_available': [],
            'no_update': [],
            'error_occurred': []
        }

    def add_callback(self, event_type, callback):
        """添加回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def remove_callback(self, event_type, callback):
        """移除回调函数"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def trigger_callback(self, event_type, *args):
        """触发回调函数"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                callback(*args)

    def create_session(self):
        """
        创建一个带有重试策略和SSL处理的requests会话
        """
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

    def check_update(self):
        """执行更新检查"""
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
                response = session.get(self.repo_url, timeout=10, verify=True)
            except Exception as e:
                errors.append(f"正常请求失败: {str(e)}")

                # 方法2: 不验证SSL证书
                try:
                    response = session.get(self.repo_url, timeout=10, verify=False)
                    self.logger.warning("使用不验证SSL证书的方式获取更新信息")
                except Exception as e:
                    errors.append(f"跳过SSL验证也失败: {str(e)}")

                    # 方法3: 使用系统证书
                    try:
                        response = session.get(self.repo_url, timeout=10, verify=True,
                                               certifi_cert=True if 'certifi' in sys.modules else False)
                    except Exception as e:
                        errors.append(f"使用系统证书也失败: {str(e)}")

            if response is None or response.status_code != 200:
                error_msg = "无法连接到更新服务器。错误详情:\n" + "\n".join(errors)
                if response:
                    error_msg += f"\nHTTP状态码: {response.status_code}"
                self.trigger_callback('error_occurred', error_msg)
                return

            release_info = response.json()
            latest_version = release_info.get("tag_name", "").lstrip("vV")

            self.logger.debug(f"当前版本: {self.current_version}, 最新版本: {latest_version}")

            # 简单的版本比较
            if self._compare_versions(latest_version, self.current_version) > 0:
                self.trigger_callback('update_available', release_info)
            else:
                self.trigger_callback('no_update')

        except Exception as e:
            self.logger.error(f"检查更新时发生错误: {str(e)}")
            self.trigger_callback('error_occurred', f"检查更新时发生错误: {str(e)}")

    def _compare_versions(self, version1, version2):
        """
        比较两个版本号
        返回: 1 如果 version1 > version2
             0 如果 version1 == version2
            -1 如果 version1 < version2
        """
        v1_parts = [int(x) for x in version1.split('.')]
        v2_parts = [int(x) for x in version2.split('.')]

        # 补齐版本号长度
        while len(v1_parts) < len(v2_parts):
            v1_parts.append(0)
        while len(v2_parts) < len(v1_parts):
            v2_parts.append(0)

        # 逐个比较版本号部分
        for i in range(len(v1_parts)):
            if v1_parts[i] > v2_parts[i]:
                return 1
            elif v1_parts[i] < v2_parts[i]:
                return -1
        return 0

    def start_check(self):
        """在新线程中启动检查更新"""
        thread = threading.Thread(target=self.check_update)
        thread.daemon = True
        thread.start()


class UpdateDownloader:
    """更新下载器"""
    def __init__(self, download_url, save_path):
        self.download_url = download_url
        self.save_path = save_path
        self.logger = logging.getLogger("AutoUpdater")
        self.callbacks = {
            'download_progress': [],
            'download_complete': [],
            'download_error': []
        }

    def add_callback(self, event_type, callback):
        """添加回调函数"""
        if event_type in self.callbacks:
            self.callbacks[event_type].append(callback)

    def remove_callback(self, event_type, callback):
        """移除回调函数"""
        if event_type in self.callbacks and callback in self.callbacks[event_type]:
            self.callbacks[event_type].remove(callback)

    def trigger_callback(self, event_type, *args):
        """触发回调函数"""
        if event_type in self.callbacks:
            for callback in self.callbacks[event_type]:
                callback(*args)

    def download(self):
        """执行下载任务"""
        try:
            self.logger.info(f"开始下载更新: {self.download_url}")

            # 创建目录
            os.makedirs(os.path.dirname(self.save_path), exist_ok=True)

            # 下载文件
            response = requests.get(self.download_url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get('content-length', 0))
            downloaded_size = 0

            with open(self.save_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded_size += len(chunk)

                        # 触发进度更新
                        if total_size > 0:
                            progress = (downloaded_size / total_size) * 100
                            self.trigger_callback('download_progress', progress)

            self.trigger_callback('download_complete', self.save_path)

        except Exception as e:
            self.logger.error(f"下载更新时出错: {str(e)}")
            self.trigger_callback('download_error', str(e))

    def start_download(self):
        """在新线程中启动下载"""
        thread = threading.Thread(target=self.download)
        thread.daemon = True
        thread.start()


class AutoUpdater:
    def __init__(self, root_window, current_version="1.0"):
        self.root_window = root_window
        self.current_version = current_version
        self.logger = logging.getLogger("AutoUpdater")
        self.update_checker = None
        self.update_downloader = None
        self.download_window = None
        self.progress_var = None

    def check_for_updates(self, silent=False):
        """
        检查是否有可用更新
        :param silent: 是否静默检查更新（不显示进度条）
        """
        if not silent:
            self.logger.info("正在检查更新...")
        else:
            self.logger.debug("正在静默检查更新...")

        # 创建并启动检查更新
        self.update_checker = UpdateChecker(self.current_version, silent)
        self.update_checker.add_callback('update_available',
                                         lambda info: self.on_update_available(info, silent))
        self.update_checker.add_callback('no_update',
                                         lambda: self.on_no_update(silent))
        self.update_checker.add_callback('error_occurred',
                                         lambda msg: self.on_check_error(msg, silent))
        self.update_checker.start_check()

    def on_update_available(self, release_info, silent=False):
        """当有可用更新时调用"""
        latest_version = release_info.get("tag_name", "")
        release_notes = release_info.get("body", "无更新说明")

        self.logger.info(f"发现新版本 {latest_version}")
        print(f"发现新版本 {latest_version}")

        # 弹出对话框询问用户是否下载更新（仅在非静默模式下）
        if not silent:
            message = f"发现新版本 {latest_version}，是否下载更新？\n\n更新说明：\n{release_notes}"
            result = messagebox.askyesno("发现新版本", message)

            if result:
                self.download_update(release_info)

    def on_no_update(self, silent=False):
        """当无更新时调用"""
        if not silent:  # 只在非静默模式下显示提示
            messagebox.showinfo(
                "检查更新",
                f"当前已是最新版本 ({self.current_version})"
            )
        else:
            self.logger.debug(f"静默检查更新：当前已是最新版本 ({self.current_version})")
            print(f"当前已是最新版本 ({self.current_version})")

    def on_check_error(self, error_msg, silent=False):
        """当检查更新出错时调用"""
        if not silent:  # 只在非静默模式下显示错误
            messagebox.showwarning(
                "检查更新",
                f"检查更新时发生错误：\n{error_msg}"
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

            # 创建临时目录用于存放下载的文件
            temp_dir = tempfile.gettempdir()
            file_path = os.path.join(temp_dir, file_name)

            # 创建下载进度窗口
            self.create_download_window()

            # 创建并启动下载线程
            self.update_downloader = UpdateDownloader(download_url, file_path)
            self.update_downloader.add_callback('download_progress', self.on_download_progress)
            self.update_downloader.add_callback('download_complete', self.on_download_finished)
            self.update_downloader.add_callback('download_error', self.on_download_error)
            self.update_downloader.start_download()
        else:
            messagebox.showwarning(
                "下载更新",
                "未找到更新文件下载链接",
                parent=self.root_window
            )

    def create_download_window(self):
        """创建下载进度窗口"""
        self.download_window = tk.Toplevel(self.root_window)
        self.download_window.title("下载更新")
        self.download_window.geometry("300x100")
        self.download_window.resizable(False, False)
        self.download_window.transient(self.root_window)
        self.download_window.grab_set()

        # 居中显示
        self.download_window.update_idletasks()
        x = (self.download_window.winfo_screenwidth() // 2) - (300 // 2)
        y = (self.download_window.winfo_screenheight() // 2) - (100 // 2)
        self.download_window.geometry(f"300x100+{x}+{y}")

        # 添加标签和进度条
        label = tk.Label(self.download_window, text="正在下载更新...")
        label.pack(pady=10)

        self.progress_var = tk.DoubleVar()
        progress_bar = ttk.Progressbar(self.download_window, variable=self.progress_var, maximum=100)
        progress_bar.pack(fill=tk.X, padx=20, pady=10)

    def on_download_progress(self, progress):
        """更新下载进度"""
        if self.download_window and self.progress_var:
            self.progress_var.set(progress)
            self.download_window.update_idletasks()

    def on_download_finished(self, file_path):
        """下载完成时调用"""
        if self.download_window:
            self.download_window.destroy()
            self.download_window = None

        # 询问用户是否立即安装更新
        result = messagebox.askyesno(
            "下载完成",
            f"更新已下载到：\n{file_path}\n\n是否立即安装？",
            parent=self.root_window
        )

        if result:
            self.install_update(file_path)

    def on_download_error(self, error_msg):
        """下载出错时调用"""
        if self.download_window:
            self.download_window.destroy()
            self.download_window = None

        messagebox.showwarning(
            "下载更新",
            f"下载更新时发生错误：\n{error_msg}",
            parent=self.root_window
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
                result = messagebox.askyesno(
                    "安装更新",
                    "安装程序已启动，是否关闭当前程序？",
                    parent=self.root_window
                )

                if result:
                    self.root_window.quit()
            else:
                # 对于压缩包，打开文件所在目录
                directory = os.path.dirname(file_path)
                if sys.platform == "win32":
                    os.startfile(directory)
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", directory])
                else:
                    subprocess.Popen(["xdg-open", directory])

                messagebox.showinfo(
                    "安装更新",
                    f"更新文件已下载到：\n{directory}\n\n请手动解压并安装。",
                    parent=self.root_window
                )

        except Exception as e:
            self.logger.error(f"安装更新时发生错误: {str(e)}")
            messagebox.showwarning(
                "安装更新",
                f"启动安装程序时发生错误：\n{str(e)}",
                parent=self.root_window
            )
