# core/user_manager.py
import sqlite3, hashlib, os, logging, json
from enum import Enum
from typing import Optional, List, Tuple

from .config import CONFIG

logger = logging.getLogger("UserManager")


class UserRole(Enum):
    """用户角色枚举"""
    ADMIN = "admin"  # 管理员 - 拥有所有权限
    ADVANCED = "advanced"  # 高级用户 - 不能使用系统监控功能
    BASIC = "basic"  # 基础用户 - 只能使用kmeans+optuna进行模型训练
    GUEST = "guest"  # 访客 - 只能导入模型、导入数据、预测和查看


class UserManager:
    """用户管理类"""
    def __init__(self, db_path: str = None):
        """初始化用户管理器"""
        if db_path is None:
            db_path = os.path.join(CONFIG["user_info"], "users_info.db")

        self.db_path = db_path
        self.init_database()

        # 尝试加载记住的用户
        self.remembered_users = self._load_remembered_users()

    def init_database(self):
        """初始化用户数据库"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 创建用户表
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS users
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               username
                               TEXT
                               UNIQUE
                               NOT
                               NULL,
                               password_hash
                               TEXT
                               NOT
                               NULL,
                               role
                               TEXT
                               NOT
                               NULL
                               DEFAULT
                               'basic',
                               nickname
                               TEXT,
                               gender
                               TEXT,
                               email
                               TEXT,
                               avatar_path
                               TEXT,
                               created_at
                               TIMESTAMP
                               DEFAULT
                               CURRENT_TIMESTAMP,
                               last_login
                               TIMESTAMP,
                               is_active
                               BOOLEAN
                               DEFAULT
                               1
                           )
                           ''')

            # 创建默认管理员账户
            cursor.execute('''
                           INSERT
                           OR IGNORE INTO users (username, password_hash, role) 
                VALUES (?, ?, ?)
                           ''', ('admin', self._hash_password('admin123'), UserRole.ADMIN.value))

            # 创建记住用户表
            cursor.execute('''
                           CREATE TABLE IF NOT EXISTS remembered_users
                           (
                               id
                               INTEGER
                               PRIMARY
                               KEY
                               AUTOINCREMENT,
                               username
                               TEXT
                               UNIQUE,
                               password
                               TEXT,
                               token
                               TEXT
                           )
                           ''')

            conn.commit()
            conn.close()

            # 为默认管理员创建个人文件夹
            self._create_user_directory('admin')
            logger.info("用户数据库初始化完成")
        except Exception as e:
            logger.error(f"初始化用户数据库失败: {str(e)}")
            raise

    def _hash_password(self, password: str) -> str:
        """对密码进行哈希处理"""
        return hashlib.sha256(password.encode('utf-8')).hexdigest()

    def authenticate_user(self, username: str, password: str) -> Optional[Tuple[int, str, UserRole]]:
        """验证用户身份"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            password_hash = self._hash_password(password)
            cursor.execute('''
                           SELECT id, username, role
                           FROM users
                           WHERE username = ?
                             AND password_hash = ?
                             AND is_active = 1
                           ''', (username, password_hash))

            result = cursor.fetchone()
            conn.close()

            if result:
                # 更新最后登录时间
                self._update_last_login(username)
                user_id, username, role = result
                return (user_id, username, UserRole(role))
            return None
        except Exception as e:
            logger.error(f"用户认证失败: {str(e)}")
            return None

    def _update_last_login(self, username: str):
        """更新用户最后登录时间"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE users
                           SET last_login = CURRENT_TIMESTAMP
                           WHERE username = ?
                           ''', (username,))
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"更新最后登录时间失败: {str(e)}")

    def create_user(self, username: str, password: str, role: UserRole = UserRole.BASIC) -> bool:
        """创建新用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            password_hash = self._hash_password(password)
            cursor.execute('''
                           INSERT INTO users (username, password_hash, role)
                           VALUES (?, ?, ?)
                           ''', (username, password_hash, role.value))

            conn.commit()
            conn.close()

            # 为用户创建个人文件夹
            self._create_user_directory(username)

            logger.info(f"用户 {username} 创建成功")
            return True
        except sqlite3.IntegrityError:
            logger.warning(f"用户 {username} 已存在")
            return False
        except Exception as e:
            logger.error(f"创建用户失败: {str(e)}")
            return False

    def _create_user_directory(self, username: str):
        """为用户创建个人文件夹和初始文件"""
        try:
            # 创建用户目录
            user_dir = os.path.join(CONFIG["user_info"], username)
            if not os.path.exists(user_dir):
                os.makedirs(user_dir)

            # 创建用户配置文件
            user_config_file = os.path.join(user_dir, "user_config.json")
            if not os.path.exists(user_config_file):
                config_data = {
                    "theme": "default",
                    "language": "zh"
                }
                with open(user_config_file, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)

            # 创建用户数据目录
            user_data_dir = os.path.join(user_dir, "data")
            if not os.path.exists(user_data_dir):
                os.makedirs(user_data_dir)

            # 创建用户模型目录
            user_model_dir = os.path.join(user_dir, "models")
            if not os.path.exists(user_model_dir):
                os.makedirs(user_model_dir)

            # 创建用户历史记录目录
            user_history_dir = os.path.join(user_dir, "history")
            if not os.path.exists(user_history_dir):
                os.makedirs(user_history_dir)
            logger.info(f"用户 {username} 的个人目录创建成功")
        except Exception as e:
            logger.error(f"创建用户 {username} 个人目录失败: {str(e)}")

    def update_user_role(self, username: str, new_role: UserRole) -> bool:
        """更新用户角色"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE users
                           SET role = ?
                           WHERE username = ?
                           ''', (new_role.value, username))

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"用户 {username} 角色更新为 {new_role.value}")
                return True
            else:
                conn.close()
                return False
        except Exception as e:
            logger.error(f"更新用户角色失败: {str(e)}")
            return False

    def deactivate_user(self, username: str) -> bool:
        """停用用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           UPDATE users
                           SET is_active = 0
                           WHERE username = ?
                           ''', (username,))

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()
                logger.info(f"用户 {username} 已停用")
                return True
            else:
                conn.close()
                return False
        except Exception as e:
            logger.error(f"停用用户失败: {str(e)}")
            return False

    def get_all_users(self) -> List[Tuple[int, str, str, str, str, bool]]:
        """获取所有用户信息"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT id, username, role, created_at, last_login, is_active
                           FROM users
                           ORDER BY created_at DESC
                           ''')
            results = cursor.fetchall()
            conn.close()
            return results
        except Exception as e:
            logger.error(f"获取用户列表失败: {str(e)}")
            return []

    def change_password(self, username: str, old_password: str, new_password: str) -> bool:
        """修改用户密码"""
        if not self.authenticate_user(username, old_password):
            return False

        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            new_password_hash = self._hash_password(new_password)
            cursor.execute('''
                           UPDATE users
                           SET password_hash = ?
                           WHERE username = ?
                           ''', (new_password_hash, username))

            conn.commit()
            conn.close()
            logger.info(f"用户 {username} 密码修改成功")
            return True
        except Exception as e:
            logger.error(f"修改密码失败: {str(e)}")
            return False

    def reset_password(self, username: str, new_password: str) -> bool:
        """重置用户密码（用于忘记密码功能）"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            new_password_hash = self._hash_password(new_password)
            cursor.execute('''
                           UPDATE users
                           SET password_hash = ?
                           WHERE username = ?
                           ''', (new_password_hash, username))

            conn.commit()
            conn.close()
            logger.info(f"用户 {username} 密码重置成功")
            return True
        except Exception as e:
            logger.error(f"重置密码失败: {str(e)}")
            return False

    def user_exists(self, username: str) -> bool:
        """检查用户是否存在"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT COUNT(*)
                           FROM users
                           WHERE username = ?
                           ''', (username,))

            result = cursor.fetchone()
            conn.close()

            return result[0] > 0
        except Exception as e:
            logger.error(f"检查用户是否存在失败: {str(e)}")
            return False

    def save_remembered_user(self, username: str, password: str, remember: bool):
        """保存记住的用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            if remember:
                # 对密码进行加密存储
                encrypted_password = self._hash_password(password)
                cursor.execute('''
                    INSERT OR REPLACE INTO remembered_users (username, password, token)
                    VALUES (?, ?, ?)
                ''', (username, password, encrypted_password))
            else:
                cursor.execute('''
                               DELETE
                               FROM remembered_users
                               WHERE username = ?
                               ''', (username,))

            conn.commit()
            conn.close()

            # 更新内存中的记住用户列表
            self.remembered_users = self._load_remembered_users()
        except Exception as e:
            logger.error(f"保存记住用户失败: {str(e)}")

    def _load_remembered_users(self) -> List[Tuple[str, str]]:
        """加载记住的用户列表"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           SELECT username, password
                           FROM remembered_users
                           ''')
            results = cursor.fetchall()
            conn.close()

            return results
        except Exception as e:
            logger.error(f"加载记住用户失败: {str(e)}")
            return []

    def get_remembered_users(self) -> List[Tuple[str, str]]:
        """获取记住的用户列表"""
        return self.remembered_users

    def update_user_profile(self, username: str, nickname: str = None, gender: str = None,
                            email: str = None, avatar_path: str = None) -> bool:
        """更新用户个人资料"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 构建更新语句
            updates = []
            params = []

            if nickname is not None:
                updates.append("nickname = ?")
                params.append(nickname)

            if gender is not None:
                updates.append("gender = ?")
                params.append(gender)

            if email is not None:
                updates.append("email = ?")
                params.append(email)

            if avatar_path is not None:
                updates.append("avatar_path = ?")
                params.append(avatar_path)

            if not updates:
                return True

            # 添加用户名作为WHERE条件
            params.append(username)

            query = f"UPDATE users SET {', '.join(updates)} WHERE username = ?"
            cursor.execute(query, params)

            conn.commit()
            conn.close()
            logger.info(f"用户 {username} 个人资料更新成功")
            return True
        except Exception as e:
            logger.error(f"更新用户个人资料失败: {str(e)}")
            return False

    def get_user_profile(self, username: str) -> Optional[dict]:
        """获取用户个人资料"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute('''
                           SELECT username, nickname, gender, email, avatar_path
                           FROM users
                           WHERE username = ?
                           ''', (username,))

            result = cursor.fetchone()
            conn.close()

            if result:
                return {
                    'username': result[0],
                    'nickname': result[1],
                    'gender': result[2],
                    'email': result[3],
                    'avatar_path': result[4]
                }
            return None
        except Exception as e:
            logger.error(f"获取用户个人资料失败: {str(e)}")
            return None

    def delete_user(self, username: str) -> bool:
        """删除用户"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                           DELETE
                           FROM users
                           WHERE username = ?
                           ''', (username,))

            if cursor.rowcount > 0:
                conn.commit()
                conn.close()

                # 删除用户的个人文件夹
                self._delete_user_directory(username)
                logger.info(f"用户 {username} 已删除")
                return True
            else:
                conn.close()
                return False
        except Exception as e:
            logger.error(f"删除用户失败: {str(e)}")
            return False

    def _delete_user_directory(self, username: str):
        """删除用户的个人文件夹"""
        try:
            user_dir = os.path.join(CONFIG["user_info"], username)
            if os.path.exists(user_dir):
                import shutil
                shutil.rmtree(user_dir)
                logger.info(f"用户 {username} 的个人目录已删除")
        except Exception as e:
            logger.error(f"删除用户 {username} 个人目录失败: {str(e)}")


class PermissionManager:
    """权限管理类"""
    # 定义权限列表
    PERMISSIONS = {
        # 基础功能权限
        'view_prediction': '查看预测结果',
        'run_prediction': '运行预测',
        'import_data': '导入数据',
        'export_data': '当前系统输出内容',
        'generate_data': '生成数据',
        'import_model': '导入模型',
        'export_model': '导出模型',
        'compare_model': '模型比较',

        # 高级功能权限
        'train_model': '训练模型',
        'customize_shortcuts': '自定义快捷键',
        'data_augmentation': '数据增强',
        'manage_models': '模型管理',

        # 管理员权限
        'user_management': '用户管理',
        'system_monitor': '系统监控',
        'show_monitoring_logs': '查看日志',
    }

    # 各角色权限映射
    ROLE_PERMISSIONS = {
        UserRole.ADMIN: list(PERMISSIONS.keys()),
        UserRole.ADVANCED: [
            'view_prediction', 'run_prediction', 'import_data', 'generate_data',
            'data_augmentation', 'export_data', 'import_model', 'export_model',
            'train_model', 'customize_shortcuts', 'compare_model', 'manage_models',
        ],
        UserRole.BASIC: [
            'view_prediction', 'run_prediction', 'import_data', 'generate_data',
            'export_data', 'import_model', 'export_model', 'train_model',
            'compare_model',
        ],
        UserRole.GUEST: [
            'view_prediction', 'run_prediction', 'import_data', 'export_data',
            'import_model', 'compare_model',
        ]
    }

    @staticmethod
    def check_permission(role: UserRole, permission: str) -> bool:
        """检查角色是否具有特定权限"""
        return permission in PermissionManager.ROLE_PERMISSIONS.get(role, [])

    @staticmethod
    def get_role_permissions(role: UserRole) -> List[str]:
        """获取角色的所有权限"""
        return PermissionManager.ROLE_PERMISSIONS.get(role, [])
