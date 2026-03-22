"""Job Requirement Agent：读取/接收岗位 JD，进行智能分类与需求总结"""

from typing import List, Optional, Dict
from pathlib import Path
from agents.base_agent import BaseAgent
from models.schemas import (
    JobDescription, JobCategory, JobAnalysisResult, ResumeProfile
)
from prompts.system_prompts import JOB_READER_SYSTEM_PROMPT
from prompts.prompt_templates import (
    JOB_CLASSIFICATION_PROMPT,
    JOB_MANUAL_INPUT_PROMPT,
)
from utils.helpers import (
    extract_json_from_response, save_json,
    read_text_files_from_dir, read_text_file,
)
from utils.logger import logger
from config.settings import Settings


class JobRequirementAgent(BaseAgent):
    """
    岗位需求分析 Agent：
    1. 支持三种输入模式（自动爬取 / 文件读取 / 手动输入）
    2. 调用 LLM 对岗位进行智能聚类分类
    3. 按类别总结核心需求、加分项、关键词
    4. 输出 JobAnalysisResult 结构化数据
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="JobRequirementAgent", **kwargs)
        self.collected_jobs: List[JobDescription] = []

    def run(
        self,
        resume_profile: ResumeProfile,
        jobs_dir: Optional[str] = None,
        manual_jobs: Optional[List[str]] = None,
        scraped_jobs: Optional[List[Dict[str, str]]] = None,
        save_result: bool = True,
    ) -> JobAnalysisResult:
        """
        执行岗位分析流程。
        
        Args:
            resume_profile: 简历分析结果（用于匹配度评估）
            jobs_dir: JD 文件目录路径（文件模式）
            manual_jobs: 手动输入的 JD 文本列表（手动模式）
            scraped_jobs: 爬虫抓取的岗位数据列表（自动模式）
            save_result: 是否将结果保存为 JSON
        
        Returns:
            JobAnalysisResult 结构化数据
        """
        logger.info(f"[JobRequirementAgent] 开始岗位分析")

        # Step 1: 收集岗位数据（三种来源）
        if scraped_jobs:
            self._load_scraped_jobs(scraped_jobs)
        if jobs_dir:
            self._load_jobs_from_dir(jobs_dir)
        if manual_jobs:
            for jd_text in manual_jobs:
                self._parse_single_job(jd_text, len(self.collected_jobs) + 1)

        if not self.collected_jobs:
            logger.warning("[JobRequirementAgent] 未收集到任何岗位数据")
            return JobAnalysisResult()

        logger.info(f"[JobRequirementAgent] 共收集 {len(self.collected_jobs)} 个岗位，开始分类分析...")

        # Step 2: 生成简历概要
        resume_summary = self._generate_resume_summary(resume_profile)

        # Step 3: 构建岗位描述文本
        job_descriptions_text = self._format_jobs_for_prompt()

        # Step 4: 调用 LLM 进行分类
        user_prompt = JOB_CLASSIFICATION_PROMPT.format(
            job_descriptions=job_descriptions_text,
            resume_summary=resume_summary,
            total_jobs=len(self.collected_jobs),
        )

        response = self.llm_client.simple_query(
            prompt=user_prompt,
            system_prompt=JOB_READER_SYSTEM_PROMPT,
        )

        # Step 5: 解析响应
        parsed = extract_json_from_response(response)
        if parsed is None:
            logger.error("[JobRequirementAgent] LLM 响应解析失败，尝试重试...")
            response = self.llm_client.simple_query(
                prompt=user_prompt + "\n\n请务必返回有效的 JSON 格式。",
                system_prompt=JOB_READER_SYSTEM_PROMPT,
            )
            parsed = extract_json_from_response(response)
            if parsed is None:
                raise ValueError("LLM 响应无法解析为 JSON，请检查模型输出")

        # Step 6: 构建结果
        result = JobAnalysisResult(
            total_jobs=len(self.collected_jobs),
            categories=[JobCategory(**cat) for cat in parsed.get("categories", [])],
            common_trends=parsed.get("common_trends", []),
            raw_jobs=self.collected_jobs,
        )

        logger.info(
            f"[JobRequirementAgent] 分析完成:\n"
            f"  总岗位数: {result.total_jobs}\n"
            f"  分类数: {len(result.categories)}"
        )
        for cat in result.categories:
            logger.info(
                f"  - {cat.category_name}: {cat.job_count} 个岗位, "
                f"匹配度 {cat.match_score:.0%}"
            )

        # Step 7: 保存结果
        if save_result:
            output_path = Settings.OUTPUT_DIR / "job_analysis.json"
            save_json(result, output_path)
            logger.info(f"[JobRequirementAgent] 分析结果已保存: {output_path}")

        return result

    def collect_jobs_interactive(self) -> List[str]:
        """
        交互式手动输入岗位 JD。
        
        Returns:
            收集到的 JD 文本列表
        """
        print("\n" + "=" * 60)
        print("📋 手动输入岗位描述")
        print("=" * 60)
        print("请逐个粘贴岗位描述（JD），每个岗位输入完成后：")
        print("  - 输入空行后再输入 'END' 表示当前岗位输入完成")
        print("  - 输入 'DONE' 表示所有岗位输入完成")
        print("=" * 60)

        job_texts = []
        job_index = 1

        while True:
            print(f"\n--- 第 {job_index} 个岗位 (输入 'DONE' 结束) ---")
            lines = []

            while True:
                try:
                    line = input()
                except EOFError:
                    break

                if line.strip().upper() == "DONE":
                    if lines:
                        job_texts.append("\n".join(lines))
                    return job_texts

                if line.strip().upper() == "END":
                    break

                lines.append(line)

            if lines:
                job_text = "\n".join(lines)
                job_texts.append(job_text)
                print(f"  ✅ 第 {job_index} 个岗位已记录 ({len(job_text)} 字符)")
                job_index += 1

        return job_texts

    def _load_jobs_from_dir(self, jobs_dir: str):
        """从目录中加载 JD 文件"""
        dir_path = Path(jobs_dir)
        if not dir_path.exists():
            logger.warning(f"[JobRequirementAgent] JD 目录不存在: {jobs_dir}")
            return

        files = read_text_files_from_dir(dir_path, extensions=[".txt", ".md", ".json"])
        logger.info(f"[JobRequirementAgent] 从目录加载了 {len(files)} 个 JD 文件")

        for file_info in files:
            content = file_info["content"]
            if content and not content.startswith("[读取失败"):
                job = JobDescription(
                    raw_text=content,
                    title=file_info["filename"].rsplit(".", 1)[0],
                )
                self.collected_jobs.append(job)

    def _load_scraped_jobs(self, scraped_jobs: List[Dict[str, str]]):
        """从爬虫抓取结果加载岗位数据"""
        logger.info(f"[JobRequirementAgent] 从爬虫结果加载 {len(scraped_jobs)} 个岗位")
        for item in scraped_jobs:
            description = item.get("description", "")
            meta = item.get("meta", "")
            raw_text = ""
            if meta:
                raw_text += f"{meta}\n\n"
            raw_text += description

            job = JobDescription(
                title=item.get("title", ""),
                company=item.get("company", ""),
                raw_text=raw_text,
            )
            self.collected_jobs.append(job)
            logger.info(f"  - 已加载: {job.title} ({job.company})")

    def _parse_single_job(self, jd_text: str, index: int):
        """解析单个 JD 文本"""
        user_prompt = JOB_MANUAL_INPUT_PROMPT.format(
            job_index=index,
            job_text=jd_text,
        )
        response = self.llm_client.simple_query(
            prompt=user_prompt,
            system_prompt=JOB_READER_SYSTEM_PROMPT,
        )
        parsed = extract_json_from_response(response)
        if parsed:
            job = JobDescription(
                raw_text=jd_text,
                **{k: v for k, v in parsed.items() if k in JobDescription.model_fields}
            )
        else:
            job = JobDescription(raw_text=jd_text, title=f"岗位_{index}")

        self.collected_jobs.append(job)
        logger.info(f"[JobRequirementAgent] 已解析岗位 {index}: {job.title}")

    def _generate_resume_summary(self, profile: ResumeProfile) -> str:
        """生成简历概要供分类时参考"""
        lines = []
        if profile.name:
            lines.append(f"姓名: {profile.name}")
        if profile.education:
            edu = profile.education[0]
            lines.append(f"学历: {edu.school} {edu.major} {edu.degree}")
        if profile.skills:
            all_skills = []
            for sg in profile.skills:
                all_skills.extend(sg.skills)
            lines.append(f"技能: {', '.join(all_skills[:15])}")
        lines.append(f"实习经历: {len(profile.internships)} 段")
        lines.append(f"项目经历: {len(profile.projects)} 段")
        if profile.strengths:
            lines.append(f"优势: {', '.join(profile.strengths[:3])}")
        return "\n".join(lines)

    def _format_jobs_for_prompt(self) -> str:
        """格式化所有岗位数据为 Prompt 文本"""
        parts = []
        for i, job in enumerate(self.collected_jobs, 1):
            header = f"### 岗位 {i}"
            if job.title:
                header += f": {job.title}"
            if job.company:
                header += f" ({job.company})"

            content_lines = [header]
            if job.raw_text:
                content_lines.append(job.raw_text)
            else:
                if job.requirements:
                    content_lines.append("**要求**: " + "、".join(job.requirements))
                if job.responsibilities:
                    content_lines.append("**职责**: " + "、".join(job.responsibilities))

            parts.append("\n".join(content_lines))

        return "\n\n---\n\n".join(parts)
