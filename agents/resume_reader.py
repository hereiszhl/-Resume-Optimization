"""Resume Reading Agent：解析 PDF 简历并进行结构化分析与能力量化评估"""

from typing import Optional
from pathlib import Path
from agents.base_agent import BaseAgent
from models.schemas import ResumeProfile
from prompts.system_prompts import RESUME_READER_SYSTEM_PROMPT
from prompts.prompt_templates import RESUME_PARSE_PROMPT
from utils.pdf_parser import extract_text_from_pdf
from utils.helpers import extract_json_from_response, save_json
from utils.logger import logger
from config.settings import Settings


class ResumeReadingAgent(BaseAgent):
    """
    简历阅读 Agent：
    1. 使用 pdfplumber 从 PDF 中提取文本
    2. 调用 LLM 进行结构化解析
    3. 多维度能力量化评估（8 个维度，各 1-10 分）
    4. 输出 ResumeProfile 结构化数据
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="ResumeReadingAgent", **kwargs)

    def run(
        self,
        resume_path: str,
        save_result: bool = True,
        output_path: Optional[str] = None,
    ) -> ResumeProfile:
        """
        执行简历分析流程。
        
        Args:
            resume_path: PDF 简历文件路径
            save_result: 是否将结果保存为 JSON
            output_path: 分析结果保存路径，默认 outputs/resume_analysis.json
        
        Returns:
            ResumeProfile 结构化数据
        """
        resume_path = Path(resume_path)
        logger.info(f"[ResumeReadingAgent] 开始分析简历: {resume_path.name}")

        # Step 1: 提取 PDF 文本
        resume_text = extract_text_from_pdf(resume_path)
        if not resume_text.strip():
            raise ValueError(f"无法从 PDF 中提取文本: {resume_path}")

        logger.info(f"[ResumeReadingAgent] 提取到 {len(resume_text)} 字符，开始 LLM 分析...")

        # Step 2: 构建 Prompt 并调用 LLM
        user_prompt = RESUME_PARSE_PROMPT.format(resume_text=resume_text)
        response = self.llm_client.simple_query(
            prompt=user_prompt,
            system_prompt=RESUME_READER_SYSTEM_PROMPT,
        )

        # Step 3: 解析 JSON 响应
        parsed = extract_json_from_response(response)
        if parsed is None:
            logger.error("[ResumeReadingAgent] LLM 响应解析失败，尝试重试...")
            # 重试一次
            response = self.llm_client.simple_query(
                prompt=user_prompt + "\n\n请务必返回有效的 JSON 格式。",
                system_prompt=RESUME_READER_SYSTEM_PROMPT,
            )
            parsed = extract_json_from_response(response)
            if parsed is None:
                raise ValueError("LLM 响应无法解析为 JSON，请检查模型输出")

        # Step 4: 构建 ResumeProfile
        profile = ResumeProfile(**parsed)
        logger.info(
            f"[ResumeReadingAgent] 分析完成:\n"
            f"  姓名: {profile.name}\n"
            f"  教育: {len(profile.education)} 段\n"
            f"  实习: {len(profile.internships)} 段\n"
            f"  项目: {len(profile.projects)} 段\n"
            f"  综合评分: {profile.overall_score}/10"
        )

        # Step 5: 保存结果
        if save_result:
            save_path = Path(output_path) if output_path else (Settings.OUTPUT_DIR / "resume_analysis.json")
            save_json(profile, save_path)
            logger.info(f"[ResumeReadingAgent] 分析结果已保存: {save_path}")

        # 保存到记忆中以供后续使用
        self.add_to_memory(
            f"分析简历: {resume_path.name}",
            f"分析完成，综合评分 {profile.overall_score}/10，"
            f"优势: {', '.join(profile.strengths[:3])}，"
            f"不足: {', '.join(profile.weaknesses[:3])}"
        )

        return profile

    def get_resume_summary(self, profile: ResumeProfile) -> str:
        """生成简历概要文本（供其他 Agent 使用）"""
        lines = []
        lines.append(f"## 候选人概要")
        lines.append(f"- 姓名: {profile.name}")

        if profile.education:
            edu = profile.education[0]
            lines.append(f"- 学历: {edu.school} · {edu.major} · {edu.degree}")

        if profile.skills:
            all_skills = []
            for skill_group in profile.skills:
                all_skills.extend(skill_group.skills)
            lines.append(f"- 技能: {', '.join(all_skills[:10])}")

        lines.append(f"- 实习经历: {len(profile.internships)} 段")
        lines.append(f"- 项目经历: {len(profile.projects)} 段")
        lines.append(f"- 综合评分: {profile.overall_score}/10")

        if profile.strengths:
            lines.append(f"- 优势: {', '.join(profile.strengths[:3])}")
        if profile.weaknesses:
            lines.append(f"- 不足: {', '.join(profile.weaknesses[:3])}")

        return "\n".join(lines)

    def get_skill_scores_text(self, profile: ResumeProfile) -> str:
        """生成能力评分文本（供 Optimize Agent 使用）"""
        lines = []
        for score in profile.skill_scores:
            lines.append(f"- {score.dimension}: {score.score}/10（{score.evidence[:50]}）")
        lines.append(f"- 综合: {profile.overall_score}/10")
        return "\n".join(lines)
