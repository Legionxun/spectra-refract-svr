# core/cloud_sync.py
import os, json, logging, requests, zipfile, tempfile, shutil, base64, urllib3, py7zr, hashlib
from typing import Optional, Dict, List
from datetime import datetime
from PySide6.QtCore import QObject, Signal, QTimer, QRunnable, QThreadPool
from cryptography.fernet import Fernet

from .config import CONFIG
from .user_manager import UserManager

# 禁用SSL警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger("CloudSync")


class GitHubSyncManager:
    """GitHub云同步管理器"""
    def __init__(self, token: str = None, repo_owner: str = None, repo_name: str = None):
        """
        初始化GitHub同步管理器

        Args:
            token: GitHub个人访问令牌
            repo_owner: 仓库所有者用户名
            repo_name: 仓库名称
        """
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.base_url = "https://api.github.com"
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "OptiSVR-Cloud-Sync"
        }
        if self.token:
            self.headers["Authorization"] = f"token {token}"

    def set_credentials(self, token: str, repo_owner: str, repo_name: str):
        """设置认证信息"""
        self.token = token
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.headers["Authorization"] = f"token {token}"

    def check_repo_exists(self) -> bool:
        """检查仓库是否存在"""
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}"
            response = requests.get(url, headers=self.headers, verify=False)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"检查仓库失败: {str(e)}")
            return False

    def create_repo(self, private: bool = True) -> bool:
        """创建仓库"""
        try:
            url = f"{self.base_url}/user/repos"
            data = {
                "name": self.repo_name,
                "private": private,
                "description": "OptiSVR分光计折射率预测系统云同步仓库",
                "auto_init": True,
            }
            response = requests.post(url, headers=self.headers, json=data, verify=False)
            logger.info(f"创建仓库结果: {response.status_code}")
            return response.status_code in [201, 422]  # 422表示仓库已存在
        except Exception as e:
            logger.error(f"创建仓库失败: {str(e)}")
            return False

    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """上传文件到GitHub"""
        try:
            # 读取文件内容
            with open(local_path, 'rb') as f:
                content = f.read()

            # 检查文件是否已存在
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{remote_path}"
            response = requests.get(url, headers=self.headers, verify=False)

            encoded_content = base64.b64encode(content).decode('utf-8')

            data = {
                "message": f"Upload {remote_path}",
                "content": encoded_content
            }

            # 如果文件已存在，需要提供sha值
            if response.status_code == 200:
                file_info = response.json()
                data["sha"] = file_info["sha"]

            response = requests.put(url, headers=self.headers, json=data, verify=False)
            return response.status_code in [200, 201]
        except Exception as e:
            logger.error(f"上传文件失败 {local_path}: {str(e)}")
            return False

    def download_file(self, remote_path: str, local_path: str) -> bool:
        """从GitHub下载文件"""
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{remote_path}"
            response = requests.get(url, headers=self.headers, verify=False)

            if response.status_code != 200:
                logger.warning(f"文件不存在: {remote_path}")
                return False

            file_info = response.json()

            # 获取下载内容
            download_response = requests.get(file_info["download_url"], verify=False)
            content = download_response.content

            # 确保本地目录存在
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # 写入文件
            with open(local_path, 'wb') as f:
                f.write(content)

            logger.info(f"下载文件成功 {remote_path}")

            return True
        except Exception as e:
            logger.error(f"下载文件失败 {remote_path}: {str(e)}")
            return False

    def list_files(self, path: str = "") -> List[Dict]:
        """列出仓库中的文件"""
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{path}"
            response = requests.get(url, headers=self.headers, verify=False)

            if response.status_code == 200:
                return response.json()
            return []
        except Exception as e:
            logger.error(f"列出文件失败: {str(e)}")
            return []

    def delete_file(self, remote_path: str, sha: str) -> bool:
        """从GitHub删除文件"""
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{remote_path}"
            data = {
                "message": f"Delete {remote_path}",
                "sha": sha
            }
            response = requests.delete(url, headers=self.headers, json=data, verify=False)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"删除文件失败 {remote_path}: {str(e)}")
            return False

    def get_file_info(self, remote_path: str) -> Optional[Dict]:
        """获取远程文件信息"""
        try:
            url = f"{self.base_url}/repos/{self.repo_owner}/{self.repo_name}/contents/{remote_path}"
            response = requests.get(url, headers=self.headers, verify=False)
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.error(f"获取文件信息失败 {remote_path}: {str(e)}")
            return None


class SyncRunnable(QRunnable):
    """同步任务"""
    def __init__(self, cloud_sync_manager, callback_object=None):
        super().__init__()
        self.cloud_sync_manager = cloud_sync_manager
        self.callback_object = callback_object

    def run(self):
        """执行同步操作"""
        try:
            success = self.cloud_sync_manager.sync_all_internal()
            if self.callback_object:
                self.callback_object.sync_finished.emit(success, "数据同步完成" if success else "数据同步失败")
        except Exception as e:
            if self.callback_object:
                self.callback_object.sync_finished.emit(False, f"同步过程中发生错误: {str(e)}")


class CloudSyncManager(QObject):
    """云同步管理器"""
    sync_progress = Signal(int, int)  # current, total
    sync_file_progress = Signal(str, int, int)  # filename, current, total
    sync_finished = Signal(bool, str)  # success, message
    def __init__(self, seven_zip_available: bool = True):
        super().__init__()
        self.config_file = os.path.join(CONFIG["settings_dir"], "cloud_sync_config.json")
        self.sync_state_file = os.path.join(CONFIG["settings_dir"], "sync_state.json")
        self.SEVEN_ZIP_AVAILABLE = seven_zip_available
        self.sync_config = self._load_config()
        self.sync_state = self._load_sync_state()
        self.github_manager = GitHubSyncManager()
        self.user_manager = UserManager(showinfo=False)
        self.sync_in_progress = False  # 添加同步进行状态标志
        self.thread_pool = QThreadPool.globalInstance()  # 使用全局线程池
        self._connected_parent_apps = set()  # 跟踪已连接的父应用

        # 如果配置存在，设置认证信息
        if self.sync_config.get("enabled", False):
            self.github_manager.set_credentials(
                Fernet(CONFIG["key"]).decrypt(self.sync_config.get("github_token", "").encode("utf-8")).decode(
                    "utf-8") if self.sync_config.get("github_token", "") else "",
                self.sync_config.get("github_username", ""),
                self.sync_config.get("github_repo", "")
            )
        # 如果没有配置文件，使用config.py中的默认配置
        elif CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                "cloud_sync_name"):
            self.github_manager.set_credentials(
                Fernet(CONFIG["key"]).decrypt(CONFIG["repo_token_bytes"]).decode("utf-8"),
                CONFIG["repo_username"],
                CONFIG["cloud_sync_name"]
            )

    def _load_config(self) -> Dict:
        """加载云同步配置"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载云同步配置失败: {str(e)}")
        return {}

    def _load_sync_state(self) -> Dict:
        """加载同步状态"""
        if os.path.exists(self.sync_state_file):
            try:
                with open(self.sync_state_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"加载同步状态失败: {str(e)}")
        return {}

    def _save_sync_state(self):
        """保存同步状态"""
        try:
            os.makedirs(CONFIG["settings_dir"], exist_ok=True)
            with open(self.sync_state_file, 'w', encoding='utf-8') as f:
                json.dump(self.sync_state, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存同步状态失败: {str(e)}")

    def _get_file_hash(self, file_path: str) -> str:
        """计算文件的哈希值"""
        if not os.path.exists(file_path):
            return ""

        try:
            hash_md5 = hashlib.md5()
            with open(file_path, "rb") as f:
                for chunk in iter(lambda: f.read(4096), b""):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            logger.error(f"计算文件哈希失败 {file_path}: {str(e)}")
            return ""

    def save_config(self):
        """保存云同步配置"""
        try:
            os.makedirs(CONFIG["settings_dir"], exist_ok=True)
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.sync_config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存云同步配置失败: {str(e)}")

    def configure_sync(self, github_token: str, github_username: str, github_repo: str) -> bool:
        """配置云同步"""
        self.sync_config = {
            "enabled": True,
            "github_token": Fernet(CONFIG["key"]).encrypt(github_token.encode('utf-8')).decode("utf-8"),
            "github_username": github_username,
            "github_repo": github_repo,
            "last_sync": None
        }

        self.github_manager.set_credentials(github_token, github_username, github_repo)

        # 检查或创建仓库
        if not self.github_manager.check_repo_exists():
            if not self.github_manager.create_repo():
                logger.error("无法创建或访问GitHub仓库")
                return False

        self.save_config()
        return True

    def disable_sync(self):
        """禁用云同步"""
        self.sync_config["enabled"] = False
        self.save_config()

    def _is_file_changed(self, local_path: str, remote_path: str) -> bool:
        """检查文件是否已更改"""
        # 检查本地文件是否存在
        if not os.path.exists(local_path):
            return True  # 本地文件不存在，需要从云端下载

        # 获取本地文件哈希
        local_hash = self._get_file_hash(local_path)
        if not local_hash:
            return False

        # 检查同步状态中是否记录了该文件
        if remote_path in self.sync_state and self.sync_state[remote_path].get("hash") == local_hash:
            return False

        # 检查远程文件是否存在
        remote_info = self.github_manager.get_file_info(remote_path)
        if not remote_info:
            return True

        # 检查远程文件哈希
        if remote_path in self.sync_state and "remote_hash" in self.sync_state[remote_path]:
            return self.sync_state[remote_path]["remote_hash"] != local_hash

        # 如果没有记录远程哈希，则假定需要上传
        return True

    def _update_file_state(self, local_path: str, remote_path: str):
        """更新文件同步状态"""
        local_hash = self._get_file_hash(local_path)
        if local_hash:
            self.sync_state[remote_path] = {
                "hash": local_hash,
                "last_sync": datetime.now().isoformat()
            }
            self._save_sync_state()

    def sync_user_data(self, username: str) -> bool:
        """同步指定用户的数据（双向）"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            user_dir = os.path.join(CONFIG["user_info"], username)
            os.makedirs(user_dir, exist_ok=True)

            # 处理用户目录下的models文件夹
            user_models_dir = os.path.join(user_dir, "models")
            processed_models = set()  # 记录已处理的模型文件夹
            if os.path.exists(user_models_dir) and os.path.isdir(user_models_dir):
                model_folders = [f for f in os.listdir(user_models_dir)
                                 if os.path.isdir(os.path.join(user_models_dir, f))]
                for i, model_folder in enumerate(model_folders):
                    model_path = os.path.join(user_models_dir, model_folder)
                    if os.path.isdir(model_path):
                        # 创建压缩文件名
                        archive_name = f"{model_folder}{'.7z' if self.SEVEN_ZIP_AVAILABLE else '.zip'}"
                        archive_path = os.path.join(user_models_dir, archive_name)

                        # 检查模型文件夹是否存在
                        if not os.path.exists(model_path):
                            logger.warning(f"模型文件夹不存在: {model_path}")
                            continue

                        # 检查云端是否已存在对应的压缩包
                        remote_path = f"user_data/{username}/models/{archive_name}"
                        remote_info = self.github_manager.get_file_info(remote_path)

                        # 如果云端不存在该文件，则需要上传
                        if not remote_info:
                            # 创建压缩文件（优先使用7z，否则使用zip）
                            if self.SEVEN_ZIP_AVAILABLE:
                                with py7zr.SevenZipFile(archive_path, 'w') as archive:
                                    archive.writeall(model_path, model_folder)
                            else:
                                with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                    for root, dirs, files in os.walk(model_path):
                                        for file in files:
                                            file_path = os.path.join(root, file)
                                            arc_path = os.path.relpath(file_path, model_path)
                                            zipf.write(file_path, arc_path)

                            self.sync_file_progress.emit(archive_name, i + 1, len(model_folders))

                            # 上传压缩文件到用户的models目录
                            if self.github_manager.upload_file(archive_path, remote_path):
                                self._update_file_state(archive_path, remote_path)
                                logger.info(f"上传模型压缩包成功: {archive_path}")
                            else:
                                logger.warning(f"上传模型压缩包失败: {archive_path}")
                        else:
                            self.sync_file_progress.emit(f"跳过 {archive_name} (未更改)", i + 1, len(model_folders))
                            logger.info(f"模型压缩包未更改，跳过上传: {archive_name}")

                        # 检查压缩文件是否存在再删除
                        if os.path.exists(archive_path):
                            os.remove(archive_path)

                        # 记录已处理的模型文件夹
                        processed_models.add(model_folder)

            # 计算用户目录下需要同步的文件总数
            file_list = []
            for root, dirs, files in os.walk(user_dir):
                relative_path = os.path.relpath(root, user_dir)
                if relative_path == ".":
                    relative_path = ""

                # 跳过已处理的models文件夹中的内容
                if relative_path.startswith("models" + os.sep):
                    model_folder_name = relative_path.split(os.sep)[1]
                    if model_folder_name in processed_models:
                        continue

                for file in files:
                    file_list.append((root, file, relative_path))

            # 同步用户目录下的所有文件和子目录（上传）
            for i, (root, file, relative_path) in enumerate(file_list):
                local_file_path = os.path.join(root, file)
                if relative_path:
                    remote_file_path = f"user_data/{username}/{relative_path}/{file}"
                else:
                    remote_file_path = f"user_data/{username}/{file}"

                # 检查云端是否已存在该文件
                remote_info = self.github_manager.get_file_info(remote_file_path)

                # 如果云端不存在该文件，则需要上传
                if not remote_info or self._is_file_changed(local_file_path, remote_file_path):
                    self.sync_file_progress.emit(file, i + 1, len(file_list))

                    # 上传文件
                    if self.github_manager.upload_file(local_file_path, remote_file_path):
                        self._update_file_state(local_file_path, remote_file_path)
                        logger.info(f"上传文件成功: {local_file_path}")
                    else:
                        logger.warning(f"上传文件失败: {local_file_path}")
                else:
                    self.sync_file_progress.emit(f"跳过 {file} (未更改)", i + 1, len(file_list))
                    logger.info(f"文件未更改，跳过上传: {file}")

            # 从云端下载用户目录中本地不存在的文件
            remote_user_files = self._list_remote_user_files(username)
            local_user_files = self._get_local_user_files(username)

            # 下载云端存在但本地不存在的文件
            for i, remote_file in enumerate(remote_user_files):
                relative_path = remote_file["path"].replace(f"user_data/{username}/", "")
                local_file_path = os.path.join(user_dir, relative_path)

                # 检查本地是否存在该文件
                if not os.path.exists(local_file_path):
                    self.sync_file_progress.emit(f"下载 {remote_file['name']}", i + 1, len(remote_user_files))

                    # 特殊处理models文件夹下的压缩包
                    if relative_path.startswith("models/") and remote_file["name"].endswith((".zip", ".7z")):
                        # 对于models文件夹下的压缩包，先检查是否有同名文件夹
                        model_name = remote_file["name"].replace(".zip", "").replace(".7z", "")
                        model_folder_path = os.path.join(user_models_dir, model_name)

                        # 如果没有同名文件夹，则下载并解压
                        if not os.path.exists(model_folder_path):
                            temp_dir = tempfile.mkdtemp()
                            temp_archive_path = os.path.join(temp_dir, remote_file["name"])

                            if self.github_manager.download_file(remote_file["path"], temp_archive_path):
                                # 移动到目标位置
                                if os.path.exists(local_file_path):
                                    os.remove(local_file_path)
                                shutil.move(temp_archive_path, local_file_path)

                                # 更新文件状态
                                self._update_file_state(local_file_path, remote_file["path"])

                                # 解压文件
                                os.makedirs(model_folder_path, exist_ok=True)

                                # 根据文件扩展名选择解压方式
                                if remote_file["name"].endswith(".7z") and self.SEVEN_ZIP_AVAILABLE:
                                    with py7zr.SevenZipFile(local_file_path, mode='r') as archive:
                                        archive.extractall(path=user_models_dir)
                                else:
                                    with zipfile.ZipFile(local_file_path, 'r') as zipf:
                                        zipf.extractall(user_models_dir)

                                # 删除下载的压缩包
                                if os.path.exists(local_file_path):
                                    os.remove(local_file_path)

                                logger.info(f"下载并解压模型 {model_name} 完成")
                            else:
                                logger.warning(f"下载模型失败: {remote_file['name']}")

                            # 清理临时文件
                            shutil.rmtree(temp_dir)
                        else:
                            self.sync_file_progress.emit(f"跳过 {remote_file['name']} (文件夹已存在)", i + 1,
                                                         len(remote_user_files))
                            logger.info(f"模型文件夹 {model_name} 已存在，跳过下载")
                    else:
                        # 下载其他文件
                        if self.github_manager.download_file(remote_file["path"], local_file_path):
                            self._update_file_state(local_file_path, remote_file["path"])
                            logger.info(f"下载文件成功: {local_file_path}")
                        else:
                            logger.warning(f"下载文件失败: {local_file_path}")
                else:
                    self.sync_file_progress.emit(f"跳过 {remote_file['name']} (已存在)", i + 1, len(remote_user_files))
                    logger.info(f"文件已存在，跳过下载: {remote_file['name']}")

            return True
        except Exception as e:
            logger.error(f"同步用户数据失败 {username}: {str(e)}")
            return False

    def _list_remote_user_files(self, username: str) -> List[Dict]:
        """列出云端指定用户的文件"""
        try:
            files = []
            folders_to_check = [f"user_data/{username}"]

            while folders_to_check:
                current_folder = folders_to_check.pop()
                folder_files = self.github_manager.list_files(current_folder)
                for file_info in folder_files:
                    if file_info.get("type") == "dir":
                        folders_to_check.append(file_info["path"])
                    else:
                        files.append(file_info)
            return files
        except Exception as e:
            logger.error(f"列出云端用户文件失败 {username}: {str(e)}")
            return []

    def _get_local_user_files(self, username: str) -> List[str]:
        """获取本地用户文件列表"""
        user_dir = os.path.join(CONFIG["user_info"], username)
        local_files = []

        if os.path.exists(user_dir):
            for root, dirs, files in os.walk(user_dir):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), user_dir)
                    local_files.append(relative_path)
        return local_files

    def sync_user_db(self) -> bool:
        """同步用户数据库文件（双向）"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            user_db_path = os.path.join(CONFIG["user_info"], "users_info.db")
            os.makedirs(CONFIG["user_info"], exist_ok=True)

            # 检查文件是否已更改
            remote_path = "user_data/users_info.db"

            # 如果本地文件不存在或者已更改，则上传或下载
            if self._is_file_changed(user_db_path, remote_path):
                # 检查远程文件是否存在
                remote_info = self.github_manager.get_file_info(remote_path)

                # 如果远程文件不存在或者本地文件存在，则上传
                if not remote_info or os.path.exists(user_db_path):
                    self.sync_file_progress.emit("users_info.db", 1, 2)
                    # 上传用户数据库文件
                    if self.github_manager.upload_file(user_db_path, remote_path):
                        self._update_file_state(user_db_path, remote_path)
                        logger.info("上传用户数据库文件成功")
                    else:
                        logger.warning(f"上传用户数据库文件失败: {user_db_path}")
                        return False
                else:
                    # 远程文件存在但本地不存在，下载
                    self.sync_file_progress.emit("users_info.db", 1, 2)
                    if self.github_manager.download_file(remote_path, user_db_path):
                        self._update_file_state(user_db_path, remote_path)
                        logger.info("下载用户数据库文件成功")
                    else:
                        logger.warning(f"下载用户数据库文件失败: {user_db_path}")
                        return False
            else:
                self.sync_file_progress.emit("跳过 users_info.db (未更改)", 1, 2)
                logger.info("用户数据库文件未更改，跳过同步")

            return True
        except Exception as e:
            logger.error(f"同步用户数据库失败: {str(e)}")
            return False

    def download_user_db(self) -> bool:
        """从云端下载用户数据库"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            user_db_path = os.path.join(CONFIG["user_info"], "users_info.db")

            # 确保目录存在
            os.makedirs(CONFIG["user_info"], exist_ok=True)

            # 从云端下载数据库文件
            remote_path = "user_data/users_info.db"

            # 检查本地文件是否存在且是否需要更新
            if os.path.exists(user_db_path):
                if not self._is_file_changed(user_db_path, remote_path):
                    logger.info("用户数据库文件已是最新，无需下载")
                    return True

            if self.github_manager.download_file(remote_path, user_db_path):
                self._update_file_state(user_db_path, remote_path)
                return True
            return False
        except Exception as e:
            logger.error(f"下载用户数据库失败: {str(e)}")
            return False

    def sync_models(self) -> bool:
        """同步模型文件（双向）"""
        update_total_progress = hasattr(self, '_total_progress_callback') and callable(self._total_progress_callback)

        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            models_dir = CONFIG["base_model_dir"]
            os.makedirs(models_dir, exist_ok=True)

            # 获取所有模型文件夹
            model_folders = [f for f in os.listdir(models_dir)
                             if os.path.isdir(os.path.join(models_dir, f))]

            # 遍历所有模型目录（上传）
            total_model_folders = len(model_folders)
            for i, model_folder in enumerate(model_folders):
                if update_total_progress and total_model_folders > 0:
                    progress = (i / total_model_folders) * 100
                    self._total_progress_callback(f"正在同步模型 ({i + 1}/{total_model_folders})", progress)

                model_path = os.path.join(models_dir, model_folder)
                if os.path.isdir(model_path):
                    archive_name = f"{model_folder}{'.7z' if self.SEVEN_ZIP_AVAILABLE else '.zip'}"
                    archive_path = os.path.join(models_dir, archive_name)

                    # 检查模型文件夹是否存在
                    if not os.path.exists(model_path):
                        logger.warning(f"模型文件夹不存在: {model_path}")
                        continue

                    # 检查云端是否已存在对应的压缩包
                    remote_path = f"models/{archive_name}"
                    remote_info = self.github_manager.get_file_info(remote_path)

                    # 如果云端不存在该压缩包，则需要压缩并上传
                    if not remote_info:
                        # 创建压缩文件（优先使用7z，否则使用zip）
                        if self.SEVEN_ZIP_AVAILABLE:
                            with py7zr.SevenZipFile(archive_path, 'w') as archive:
                                archive.writeall(model_path, model_folder)
                        else:
                            with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                                for root, dirs, files in os.walk(model_path):
                                    for file in files:
                                        file_path = os.path.join(root, file)
                                        arc_path = os.path.relpath(file_path, model_path)
                                        zipf.write(file_path, arc_path)

                        self.sync_file_progress.emit(archive_name, i + 1, len(model_folders))

                        # 上传压缩文件
                        if self.github_manager.upload_file(archive_path, remote_path):
                            self._update_file_state(archive_path, remote_path)
                            logger.info(f"上传模型压缩包成功: {archive_path}")
                        else:
                            logger.warning(f"上传模型压缩包失败: {archive_path}")
                    else:
                        self.sync_file_progress.emit(f"跳过 {archive_name} (未更改)", i + 1, len(model_folders))
                        logger.info(f"模型压缩包未更改，跳过上传: {archive_name}")

                    # 检查压缩文件是否存在再删除
                    if os.path.exists(archive_path):
                        os.remove(archive_path)

            # 从云端下载本地不存在的模型
            remote_models = self.github_manager.list_files("models")
            for i, remote_model in enumerate(remote_models):
                if remote_model["name"].endswith((".zip", ".7z")):
                    local_archive_path = os.path.join(models_dir, remote_model["name"])
                    model_name = remote_model["name"].replace(".zip", "").replace(".7z", "")
                    local_extract_path = os.path.join(models_dir, model_name)

                    # 检查是否存在同名文件夹，如果不存在则下载并解压
                    if not os.path.exists(local_extract_path):
                        self.sync_file_progress.emit(f"下载 {remote_model['name']}", i + 1, len(remote_models))

                        # 下载压缩文件
                        temp_dir = tempfile.mkdtemp()
                        temp_archive_path = os.path.join(temp_dir, remote_model["name"])

                        if self.github_manager.download_file(remote_model["path"], temp_archive_path):
                            if os.path.exists(local_archive_path):
                                os.remove(local_archive_path)
                            shutil.move(temp_archive_path, local_archive_path)

                            # 更新文件状态
                            self._update_file_state(local_archive_path, remote_model["path"])

                            # 解压文件
                            os.makedirs(local_extract_path, exist_ok=True)

                            # 根据文件扩展名选择解压方式
                            if remote_model["name"].endswith(".7z") and self.SEVEN_ZIP_AVAILABLE:
                                with py7zr.SevenZipFile(local_archive_path, mode='r') as archive:
                                    archive.extractall(path=models_dir)
                            else:
                                with zipfile.ZipFile(local_archive_path, 'r') as zipf:
                                    zipf.extractall(models_dir)

                            # 删除下载的压缩包
                            if os.path.exists(local_archive_path):
                                os.remove(local_archive_path)

                            logger.info(f"下载并解压模型 {model_name} 完成")
                        else:
                            logger.warning(f"下载模型失败: {remote_model['name']}")

                        # 清理临时文件
                        shutil.rmtree(temp_dir)
                    else:
                        self.sync_file_progress.emit(f"跳过 {remote_model['name']} (文件夹已存在)", i + 1,
                                                     len(remote_models))
                        logger.info(f"模型文件夹 {model_name} 已存在，跳过下载")

            return True
        except Exception as e:
            logger.error(f"同步模型失败: {str(e)}")
            return False

    def sync_history(self) -> bool:
        """同步根目录下的history文件夹（双向）"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            history_dir = CONFIG["history_dir"]
            os.makedirs(history_dir, exist_ok=True)

            # 计算需要同步的文件列表
            file_list = []
            for root, dirs, files in os.walk(history_dir):
                for file in files:
                    file_list.append((root, file))

            # 同步history目录下的所有文件（上传）
            for i, (root, file) in enumerate(file_list):
                local_file_path = os.path.join(root, file)
                relative_path = os.path.relpath(local_file_path, history_dir)
                remote_file_path = f"history/{relative_path}"

                # 检查文件是否已更改
                if self._is_file_changed(local_file_path, remote_file_path):
                    self.sync_file_progress.emit(file, i + 1, len(file_list))

                    # 上传文件
                    if self.github_manager.upload_file(local_file_path, remote_file_path):
                        self._update_file_state(local_file_path, remote_file_path)
                        logger.info(f"上传history文件成功: {local_file_path}")
                    else:
                        logger.warning(f"上传history文件失败: {local_file_path}")
                else:
                    self.sync_file_progress.emit(f"跳过 {file} (未更改)", i + 1, len(file_list))
                    logger.info(f"history文件未更改，跳过上传: {file}")

            # 从云端下载本地不存在的history文件
            remote_history_files = self._list_remote_history_files()
            local_history_files = self._get_local_history_files()

            # 下载云端存在但本地不存在的文件
            for i, remote_file in enumerate(remote_history_files):
                relative_path = remote_file["path"].replace("history/", "")
                local_file_path = os.path.join(history_dir, relative_path)

                # 检查本地是否存在该文件
                if not os.path.exists(local_file_path):
                    self.sync_file_progress.emit(f"下载 {remote_file['name']}", i + 1, len(remote_history_files))

                    # 下载文件
                    if self.github_manager.download_file(remote_file["path"], local_file_path):
                        self._update_file_state(local_file_path, remote_file["path"])
                        logger.info(f"下载history文件成功: {local_file_path}")
                    else:
                        logger.warning(f"下载history文件失败: {local_file_path}")
                else:
                    self.sync_file_progress.emit(f"跳过 {remote_file['name']} (已存在)", i + 1,
                                                 len(remote_history_files))
                    logger.info(f"history文件已存在，跳过下载: {remote_file['name']}")

            return True
        except Exception as e:
            logger.error(f"同步history目录失败: {str(e)}")
            return False

    def _list_remote_history_files(self) -> List[Dict]:
        """列出云端history目录中的文件"""
        try:
            files = []
            folders_to_check = ["history"]

            while folders_to_check:
                current_folder = folders_to_check.pop()
                folder_files = self.github_manager.list_files(current_folder)
                for file_info in folder_files:
                    if file_info.get("type") == "dir":
                        folders_to_check.append(file_info["path"])
                    else:
                        files.append(file_info)
            return files
        except Exception as e:
            logger.error(f"列出云端history文件失败: {str(e)}")
            return []

    def _get_local_history_files(self) -> List[str]:
        """获取本地history文件列表"""
        history_dir = CONFIG["history_dir"]
        local_files = []

        if os.path.exists(history_dir):
            for root, dirs, files in os.walk(history_dir):
                for file in files:
                    relative_path = os.path.relpath(os.path.join(root, file), history_dir)
                    local_files.append(relative_path)
        return local_files

    def download_history(self) -> bool:
        """从云端下载history目录"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            history_dir = CONFIG["history_dir"]
            os.makedirs(history_dir, exist_ok=True)

            # 列出云端history目录中的文件
            files = self.github_manager.list_files("history")
            all_files = []
            folders_to_check = ["history"]

            while folders_to_check:
                current_folder = folders_to_check.pop()
                folder_files = self.github_manager.list_files(current_folder)
                for file_info in folder_files:
                    if file_info.get("type") == "dir":
                        folders_to_check.append(file_info["path"])
                    else:
                        all_files.append(file_info)

            # 下载所有文件
            for i, file_info in enumerate(all_files):
                remote_path = file_info["path"]
                local_relative_path = os.path.relpath(remote_path, "history")
                local_file_path = os.path.join(history_dir, local_relative_path)

                # 确保本地目录存在
                os.makedirs(os.path.dirname(local_file_path), exist_ok=True)

                # 检查是否需要更新
                if self._is_file_changed(local_file_path, remote_path):
                    self.sync_file_progress.emit(file_info["name"], i + 1, len(all_files))

                    if self.github_manager.download_file(remote_path, local_file_path):
                        self._update_file_state(local_file_path, remote_path)
                        logger.info(f"下载history文件成功: {local_file_path}")
                    else:
                        logger.warning(f"下载history文件失败: {local_file_path}")
                else:
                    self.sync_file_progress.emit(f"跳过 {file_info['name']} (未更改)", i + 1, len(all_files))
                    logger.info(f"history文件未更改，跳过下载: {file_info['name']}")

            return True
        except Exception as e:
            logger.error(f"下载history目录失败: {str(e)}")
            return False

    def download_models(self) -> bool:
        """从云端下载模型"""
        if not self.sync_config.get("enabled", False):
            if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                    "cloud_sync_name"):
                pass
            else:
                return False

        try:
            models_dir = CONFIG["base_model_dir"]
            os.makedirs(models_dir, exist_ok=True)

            # 列出云端模型
            files = self.github_manager.list_files("models")
            for file_info in files:
                logger.info(f"正在处理模型: {file_info['name']}")
                if file_info["name"].endswith((".zip", ".7z")):
                    local_archive_path = os.path.join(models_dir, file_info["name"])
                    model_name = file_info["name"].replace(".zip", "").replace(".7z", "")
                    local_extract_path = os.path.join(models_dir, model_name)

                    # 检查是否存在同名文件夹，如果不存在则下载并解压
                    if not os.path.exists(local_extract_path):
                        # 下载压缩文件
                        temp_dir = tempfile.mkdtemp()
                        temp_archive_path = os.path.join(temp_dir, file_info["name"])

                        if self.github_manager.download_file(file_info["path"], temp_archive_path):
                            if os.path.exists(local_archive_path):
                                os.remove(local_archive_path)
                            shutil.move(temp_archive_path, local_archive_path)

                            # 更新文件状态
                            self._update_file_state(local_archive_path, file_info["path"])

                            # 解压文件
                            os.makedirs(local_extract_path, exist_ok=True)

                            # 根据文件扩展名选择解压方式
                            if file_info["name"].endswith(".7z") and self.SEVEN_ZIP_AVAILABLE:
                                with py7zr.SevenZipFile(local_archive_path, mode='r') as archive:
                                    archive.extractall(path=models_dir)
                            else:
                                with zipfile.ZipFile(local_archive_path, 'r') as zipf:
                                    zipf.extractall(models_dir)

                            # 删除下载的压缩包
                            if os.path.exists(local_archive_path):
                                os.remove(local_archive_path)

                            logger.info(f"模型 {model_name} 下载并解压完成")
                        else:
                            logger.warning(f"下载模型失败: {file_info['name']}")

                        # 清理临时文件
                        shutil.rmtree(temp_dir)
                    else:
                        logger.info(f"模型文件夹 {model_name} 已存在，跳过下载")

            return True
        except Exception as e:
            logger.error(f"下载模型失败: {str(e)}")
            return False

    def sync_all_internal(self) -> bool:
        """同步所有数据（双向）- 内部方法，仅在同步线程中调用"""
        self.sync_in_progress = True
        success = False

        try:
            if not self.sync_config.get("enabled", False):
                if CONFIG.get("repo_token_bytes").decode("utf-8") and CONFIG.get("repo_username") and CONFIG.get(
                        "cloud_sync_name"):
                    self.github_manager.set_credentials(
                        Fernet(CONFIG["key"]).decrypt(CONFIG["repo_token_bytes"]).decode("utf-8"),
                        CONFIG["repo_username"],
                        CONFIG["cloud_sync_name"]
                    )
                else:
                    self.sync_in_progress = False
                    self.sync_finished.emit(False, "云同步未启用")
                    return False

            # 发出开始同步信号
            self.sync_progress.emit(0, 6)
            # 保存用户列表供模型同步时使用
            users = [u for u in os.listdir(CONFIG["user_info"])
                     if os.path.isdir(os.path.join(CONFIG["user_info"], u))]

            # 同步用户数据库
            if not self.sync_user_db():
                self.sync_finished.emit(False, "同步用户数据库失败")
                self.sync_in_progress = False
                return False
            self.sync_progress.emit(1, 6)

            # 同步所有用户数据
            success = True
            for i, username in enumerate(users):
                user_path = os.path.join(CONFIG["user_info"], username)
                if os.path.isdir(user_path):
                    if not self.sync_user_data(username):
                        success = False
                        logger.warning(f"同步用户 {username} 数据时出现问题")
                    self.sync_progress.emit(2 + i, 5 + len(users))

            # 同步模型
            def total_progress_callback(message, progress):
                total_steps = 5 + len(users) + 1
                current_step = 2 + len(users)
                mapped_progress = current_step + (progress / 100.0)
                self.sync_progress.emit(int(mapped_progress), total_steps)
                self.sync_file_progress.emit(message, int(progress), 100)

            self._total_progress_callback = total_progress_callback
            if not self.sync_models():
                success = False
                logger.warning("同步模型时出现问题")
            self.sync_progress.emit(2 + len(users), 5 + len(users) + 1)

            # 清理回调函数
            if hasattr(self, '_total_progress_callback'):
                del self._total_progress_callback

            # 同步history目录
            if not self.sync_history():
                success = False
                logger.warning("同步历史记录时出现问题")
            self.sync_progress.emit(3 + len(users), 5 + len(users) + 2)

            # 更新最后同步时间
            if success and self.sync_config.get("enabled", False):
                self.sync_config["last_sync"] = datetime.now().isoformat()
                self.save_config()

            # 确保在任何情况下都发送完成信号
            try:
                self.sync_progress.emit(5 + len(users), 5 + len(users))
            except:
                pass

            self.sync_in_progress = False

            # 确保发送完成信号
            finish_message = "数据同步完成" if success else "数据同步完成但有错误"
            self.sync_finished.emit(success, finish_message)
            logger.info(f"同步完成: {finish_message}")
            return success
        except Exception as e:
            logger.error(f"同步所有数据失败: {str(e)}")
            self.sync_in_progress = False
            self.sync_finished.emit(False, f"同步过程中发生错误: {str(e)}")
            return False

    def sync_all(self) -> bool:
        """同步所有数据（双向）- 公共方法，可在任何线程中调用"""
        # 同步包装器
        return self.sync_all_internal()

    def is_sync_enabled(self) -> bool:
        """检查是否启用了云同步"""
        return self.sync_config.get("enabled", False)

    def is_sync_in_progress(self) -> bool:
        """检查是否有同步正在进行"""
        return self.sync_in_progress

    def get_last_sync_time(self) -> Optional[str]:
        """获取最后同步时间"""
        return self.sync_config.get("last_sync", None)

    def trigger_sync(self, parent_app=None):
        """触发同步（事件驱动）"""
        if self.is_sync_in_progress():
            logger.info("同步已在进行中，跳过本次触发")
            if parent_app and hasattr(parent_app, 'show_message'):
                parent_app.show_message("同步已在进行中", "警告")
            return

        try:
            # 检查是否启用了云同步
            if self.is_sync_enabled():
                if parent_app and hasattr(parent_app, 'show_sync_progress'):
                    parent_app.show_sync_progress(True)

                # 在后台线程中执行同步
                sync_runnable = SyncRunnable(self, self)
                if parent_app and parent_app not in self._connected_parent_apps:
                    self.sync_progress.connect(parent_app.update_sync_progress)
                    self.sync_finished.connect(
                        lambda success, message: self.on_sync_finished(success, message, parent_app))
                    self._connected_parent_apps.add(parent_app)
                elif not parent_app:
                    pass

                self.thread_pool.start(sync_runnable)
            else:
                if parent_app and hasattr(parent_app, 'show_message'):
                    parent_app.show_message("云同步未启用，请先配置云同步", "警告")
                logger.warning("尝试触发同步但云同步未启用")
        except Exception as e:
            logger.warning(f"触发同步失败: {str(e)}")
            if parent_app and hasattr(parent_app, 'show_sync_progress'):
                parent_app.show_sync_progress(False)
            if parent_app and hasattr(parent_app, 'show_message'):
                parent_app.show_message(f"触发同步失败: {str(e)}", "错误")

    def on_sync_finished(self, success, message, parent_app=None):
        """同步完成回调"""
        self.sync_in_progress = False
        if parent_app:
            if parent_app in self._connected_parent_apps:
                self._connected_parent_apps.remove(parent_app)

        if parent_app and hasattr(parent_app, 'show_sync_progress'):
            parent_app.show_sync_progress(False)
        logger.info(f"同步完成: {message}")

    def stop_sync(self):
        """停止同步"""
        self.sync_in_progress = False

    def is_auto_sync_needed(self, start=False) -> bool:
        """检查是否需要自动同步"""
        # 如果云同步未启用，则不需要同步
        if not self.is_sync_enabled():
            return False

        # 检查是否从未同步过
        last_sync = self.get_last_sync_time()
        if not last_sync:
            return True

        # 每次启动都需要同步
        if start:
            return True

        return False

    def setup_auto_sync(self, parent_app, start=False):
        """设置自动同步"""
        self.parent_app = parent_app

        if self.is_auto_sync_needed(start):
            logger.info("检测到软件启动或从未同步过，触发自动同步")
            QTimer.singleShot(5000, lambda: self.trigger_sync(parent_app))
