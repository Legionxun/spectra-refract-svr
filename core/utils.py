# core/utils.py
import os, datetime, logging, logging.handlers, sys

def get_app_root():
    """获取应用程序根目录（可执行文件所在目录）"""
    if getattr(sys, 'frozen', False):
        # 打包环境：可执行文件所在目录
        return os.path.dirname(sys.executable)
    else:
        # 开发环境：当前工作目录
        return os.getcwd()

def get_output_path(*subpaths):
    """获取输出路径（在可执行文件目录下）并确保目录存在"""
    base_path = get_app_root()
    full_path = os.path.join(base_path, *subpaths)

    # 确保目录存在
    if not os.path.isdir(os.path.dirname(full_path)):
        os.makedirs(os.path.dirname(full_path), exist_ok=True)

    return full_path


def get_unique_filename(directory, base_name, extension):
    """生成唯一的文件名（在原名称基础上添加数字）"""
    # 使用get_output_path确保目录存在
    output_dir = get_output_path(directory)

    counter = 1
    filename = f"{base_name}.{extension}"
    while os.path.exists(os.path.join(output_dir, filename)):
        filename = f"{base_name}_{counter}.{extension}"
        counter += 1
    return os.path.join(output_dir, filename)


def get_unique_timestamp_dir(base_dir, cluster="", mode="", prefix="run"):
    """生成基于时间戳的唯一目录"""
    # 使用get_output_path确保基础目录存在
    base_output_dir = get_output_path(base_dir)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    dir_name = f"{prefix}_{timestamp}_{cluster}_{mode}"
    full_path = os.path.join(base_output_dir, dir_name)
    os.makedirs(full_path, exist_ok=True)
    return full_path


def setup_logging():
    """配置日志记录系统，确保日志文件在可执行文件目录下"""
    # 创建日志目录（在可执行文件目录下的logs子目录）
    log_dir = get_output_path("logs")
    os.makedirs(log_dir, exist_ok=True)

    # 生成唯一的日志文件名（基于时间戳）
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f"refractive_index_system_{timestamp}.log"
    log_path = os.path.join(log_dir, log_filename)

    # 创建日志记录器
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    # 清除现有处理器（避免重复添加）
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)

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

    # 记录日志系统初始化信息
    logger.info(f"日志系统初始化完成，日志文件位置: {log_path}")
    logger.info(f"应用程序根目录: {get_app_root()}")

    return log_path
