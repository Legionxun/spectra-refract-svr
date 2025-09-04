# core.utils.py
import os, datetime, logging, logging.handlers, sys

def get_unique_filename(directory, base_name, extension):
    """生成唯一的文件名（在原名称基础上添加数字）"""
    counter = 1
    filename = f"{base_name}.{extension}"
    while os.path.exists(os.path.join(directory, filename)):
        filename = f"{base_name}_{counter}.{extension}"
        counter += 1
    return os.path.join(directory, filename)

def get_unique_timestamp_dir(base_dir, prefix="run"):
    """生成基于时间戳的唯一目录"""
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{prefix}_{timestamp}"
    full_path = os.path.join(base_dir, dir_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path

def resource_path(relative_path):
    if getattr(sys, 'frozen', False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.abspath(".")

    # 处理Windows路径分隔符问题
    if sys.platform == "win32":
        relative_path = relative_path.replace("/", "\\")
    else:
        relative_path = relative_path.replace("\\", "/")

    return os.path.join(base_path, relative_path)

def setup_logging():
    """配置日志记录系统"""
    # 创建日志目录
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # 生成唯一的日志文件名（基于时间戳）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"refractive_index_system_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 创建文件处理器 - 记录所有级别的日志
    file_handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=10 * 1024 * 1024, backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)

    # 创建控制台处理器 - 只记录INFO及以上级别的日志
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)

    # 创建格式化器
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)
    console_handler.setFormatter(formatter)

    # 添加处理器到记录器
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return log_path