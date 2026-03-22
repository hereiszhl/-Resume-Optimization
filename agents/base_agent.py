"""Agent 抽象基类：封装 LLM 初始化、对话记忆管理"""

from abc import ABC, abstractmethod
from typing import Optional, List, Dict, Any
from models.llm_client import LLMClient
from config.settings import Settings
from utils.logger import logger


class BaseAgent(ABC):
    """
    所有 Agent 的抽象基类。
    
    提供:
    - LLM 客户端初始化
    - 手动对话历史管理（替代已废弃的 ConversationBufferMemory）
    - 通用的记忆操作接口（重置、导出、带上下文调用）
    """

    def __init__(
        self,
        agent_name: str = "BaseAgent",
        llm_client: Optional[LLMClient] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        max_iterations: int = None,
    ):
        self.agent_name = agent_name
        self.max_iterations = max_iterations or Settings.MAX_ITERATIONS

        # 初始化 LLM 客户端
        if llm_client:
            self.llm_client = llm_client
        else:
            self.llm_client = LLMClient(
                temperature=temperature,
                max_tokens=max_tokens,
            )
        self.llm = self.llm_client.get_langchain_llm()

        # 对话历史（手动管理）
        self.chat_history: List[Dict[str, str]] = []

        logger.info(f"[{self.agent_name}] 初始化完成")

    def reset_memory(self):
        """重置对话记忆（在切换类别时使用）"""
        self.chat_history.clear()
        logger.debug(f"[{self.agent_name}] 对话记忆已重置")

    def get_conversation_history(self) -> List[Dict[str, str]]:
        """导出对话历史"""
        return list(self.chat_history)

    def add_to_memory(self, user_input: str, ai_output: str):
        """手动添加一轮对话到记忆"""
        self.chat_history.append({"role": "user", "content": user_input})
        self.chat_history.append({"role": "assistant", "content": ai_output})

    def chat_with_history(self, user_message: str, system_prompt: str = "") -> str:
        """
        带完整对话历史的 LLM 调用。
        自动将 system_prompt + 历史对话 + 当前输入拼接为消息列表。
        """
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.extend(self.chat_history)
        messages.append({"role": "user", "content": user_message})

        response = self.llm_client.chat(messages)

        # 自动添加到历史
        self.add_to_memory(user_message, response)

        return response

    @abstractmethod
    def run(self, *args, **kwargs) -> Any:
        """执行 Agent 的核心任务（子类必须实现）"""
        pass
