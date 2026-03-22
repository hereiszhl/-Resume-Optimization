"""LLM 客户端：对接智谱 GLM-4.7 API（通过 LangChain ChatOpenAI 兼容层）"""

import time
from typing import List, Dict, Optional
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from config.settings import Settings


class LLMClient:
    """
    统一的 LLM 客户端，使用 LangChain 的 ChatOpenAI 对接智谱 GLM-4.7。
    智谱 API 兼容 OpenAI Chat Completions 格式。
    """

    def __init__(
        self,
        model_name: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        api_key: Optional[str] = None,
        api_base: Optional[str] = None,
        request_timeout: int = 300,
        max_retries: int = 2,
    ):
        self.model_name = model_name or Settings.ZHIPU_MODEL_NAME
        self.temperature = temperature if temperature is not None else Settings.LLM_TEMPERATURE
        self.max_tokens = max_tokens or Settings.LLM_MAX_TOKENS
        self.api_key = api_key or Settings.ZHIPU_API_KEY
        self.api_base = api_base or Settings.ZHIPU_API_BASE
        self.request_timeout = request_timeout
        self.max_retries = max_retries

        # 初始化 LangChain ChatOpenAI（智谱兼容 OpenAI 格式）
        self.llm = ChatOpenAI(
            model=self.model_name,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            openai_api_key=self.api_key,
            openai_api_base=self.api_base,
            request_timeout=self.request_timeout,
        )

    def chat(self, messages: List[Dict[str, str]]) -> str:
        """
        多消息对话，带重试和错误处理。
        messages 格式: [{"role": "system"|"user"|"assistant", "content": "..."}]
        """
        lc_messages = []
        for msg in messages:
            role = msg["role"]
            content = msg["content"]
            if role == "system":
                lc_messages.append(SystemMessage(content=content))
            elif role == "user":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant":
                lc_messages.append(AIMessage(content=content))

        last_error = None
        for attempt in range(1, self.max_retries + 1):
            try:
                response = self.llm.invoke(lc_messages)
                return response.content
            except Exception as e:
                last_error = e
                error_msg = str(e)
                if attempt < self.max_retries:
                    wait = 2 ** attempt
                    print(f"[LLM] 第 {attempt} 次调用失败: {error_msg[:100]}，{wait}s 后重试...")
                    time.sleep(wait)
                else:
                    print(f"[LLM] 第 {attempt} 次调用仍失败: {error_msg[:200]}")
        
        raise RuntimeError(
            f"LLM API 调用失败（已重试 {self.max_retries} 次）: {last_error}"
        )

    def simple_query(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """简单单轮问答"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        return self.chat(messages)

    def get_langchain_llm(self) -> ChatOpenAI:
        """返回底层 LangChain LLM 实例，供 Agent 框架直接使用"""
        return self.llm
