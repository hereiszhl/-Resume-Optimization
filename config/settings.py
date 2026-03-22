"""配置管理模块：从 .env 文件加载 API 配置和系统参数"""

import os
from pathlib import Path
from dotenv import load_dotenv

# 加载项目根目录下的 .env 文件
_project_root = Path(__file__).resolve().parent.parent
_env_path = _project_root / ".env"
load_dotenv(_env_path)


class Settings:
    """全局配置单例，统一管理 API Key、模型参数和运行时配置"""

    # ---- 智谱 GLM API ----
    ZHIPU_API_KEY: str = os.getenv("ZHIPU_API_KEY", "")
    ZHIPU_API_BASE: str = os.getenv("ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4")
    ZHIPU_MODEL_NAME: str = os.getenv("ZHIPU_MODEL_NAME", "glm-4.7")

    # ---- 模型参数 ----
    LLM_TEMPERATURE: float = float(os.getenv("LLM_TEMPERATURE", "0.3"))
    LLM_TOP_P: float = float(os.getenv("LLM_TOP_P", "0.8"))
    LLM_MAX_TOKENS: int = int(os.getenv("LLM_MAX_TOKENS", "4096"))

    # ---- Agent 配置 ----
    MAX_ITERATIONS: int = int(os.getenv("MAX_ITERATIONS", "10"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    REQUEST_DELAY: float = float(os.getenv("REQUEST_DELAY", "1.0"))

    # ---- 日志配置 ----
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_DIR: str = os.getenv("LOG_DIR", str(_project_root / "outputs" / "logs"))

    # ---- 项目路径 ----
    PROJECT_ROOT: Path = _project_root
    DATA_DIR: Path = _project_root / "data"
    RESUMES_DIR: Path = _project_root / "data" / "resumes"
    JD_DIR: Path = _project_root / "data" / "job_descriptions"
    OUTPUT_DIR: Path = _project_root / "outputs"

    @classmethod
    def validate(cls) -> bool:
        """验证关键配置是否已设置"""
        if not cls.ZHIPU_API_KEY or cls.ZHIPU_API_KEY == "your_api_key_here":
            raise ValueError(
                "请在 .env 文件中设置 ZHIPU_API_KEY\n"
                f"配置文件路径: {_env_path}"
            )
        return True

    @classmethod
    def ensure_dirs(cls):
        """确保所有必要目录存在"""
        for dir_path in [cls.DATA_DIR, cls.RESUMES_DIR, cls.JD_DIR, cls.OUTPUT_DIR, Path(cls.LOG_DIR)]:
            dir_path.mkdir(parents=True, exist_ok=True)

    @classmethod
    def info(cls) -> str:
        """打印当前配置信息（隐藏 API Key）"""
        masked_key = cls.ZHIPU_API_KEY[:8] + "****" if len(cls.ZHIPU_API_KEY) > 8 else "未设置"
        return (
            f"=== 配置信息 ===\n"
            f"API Base: {cls.ZHIPU_API_BASE}\n"
            f"API Key:  {masked_key}\n"
            f"模型:     {cls.ZHIPU_MODEL_NAME}\n"
            f"温度:     {cls.LLM_TEMPERATURE}\n"
            f"Max Tokens: {cls.LLM_MAX_TOKENS}\n"
            f"项目根目录: {cls.PROJECT_ROOT}\n"
        )
