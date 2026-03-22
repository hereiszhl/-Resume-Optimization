"""日志模块：控制台彩色输出 + 文件双输出"""

import logging
import sys
from pathlib import Path
from datetime import datetime
from config.settings import Settings


def setup_logger(name: str = "resume_optimizer", log_file: str = None) -> logging.Logger:
    """
    创建带控制台和文件双输出的 Logger。
    
    Args:
        name: Logger 名称
        log_file: 日志文件路径，None 则自动生成
    
    Returns:
        配置好的 Logger 实例
    """
    logger = logging.getLogger(name)

    # 避免重复添加 handler
    if logger.handlers:
        return logger

    logger.setLevel(getattr(logging, Settings.LOG_LEVEL, logging.INFO))

    # 格式
    console_fmt = logging.Formatter(
        "%(asctime)s │ %(levelname)-7s │ %(message)s",
        datefmt="%H:%M:%S"
    )
    file_fmt = logging.Formatter(
        "%(asctime)s │ %(name)s │ %(levelname)-7s │ %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # 控制台 Handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(console_fmt)
    logger.addHandler(console_handler)

    # 文件 Handler
    if log_file is None:
        log_dir = Path(Settings.LOG_DIR)
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_file = log_dir / f"{name}_{timestamp}.log"

    file_handler = logging.FileHandler(str(log_file), encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_fmt)
    logger.addHandler(file_handler)

    return logger


# 全局 Logger 实例
logger = setup_logger()
