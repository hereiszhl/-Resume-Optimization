"""Resume Optimize Agent：针对不同岗位类别进行多轮对话式简历优化"""

from typing import Optional, List, Dict
from agents.base_agent import BaseAgent
from models.schemas import (
    ResumeProfile, JobCategory, JobAnalysisResult,
    CategoryOptimizationResult, OptimizedSection, GapAnalysis,
)
from prompts.system_prompts import RESUME_OPTIMIZER_SYSTEM_PROMPT
from prompts.prompt_templates import (
    OPTIMIZE_INITIAL_PROMPT,
    OPTIMIZE_FOLLOWUP_PROMPT,
    OPTIMIZE_FINAL_PROMPT,
)
from utils.helpers import extract_json_from_response
from utils.logger import logger


class ResumeOptimizeAgent(BaseAgent):
    """
    简历优化 Agent（多轮对话核心）：
    
    针对每个岗位类别：
    1. 执行 Gap Analysis（差距分析）
    2. 分模块提供 STAR 法则优化
    3. 支持多轮对话追问用户补充细节
    4. 用户确认后输出结构化优化结果
    
    切换类别时自动 reset_memory() 避免串话。
    """

    def __init__(self, **kwargs):
        super().__init__(agent_name="ResumeOptimizeAgent", **kwargs)
        self.current_category: Optional[str] = None

    def run(
        self,
        resume_profile: ResumeProfile,
        job_analysis: JobAnalysisResult,
        resume_summary: str,
        skill_scores_text: str,
    ) -> List[CategoryOptimizationResult]:
        """
        对所有岗位类别执行多轮对话优化。
        
        Args:
            resume_profile: 简历分析结果
            job_analysis: 岗位分析结果
            resume_summary: 简历概要文本
            skill_scores_text: 能力评分文本
        
        Returns:
            各类别的优化结果列表
        """
        results = []
        total_categories = len(job_analysis.categories)

        print("\n" + "=" * 60)
        print("🎯 开始逐类别简历优化（多轮对话模式）")
        print(f"   共 {total_categories} 个岗位类别需要优化")
        print("=" * 60)

        for idx, category in enumerate(job_analysis.categories, 1):
            print(f"\n{'─' * 60}")
            print(f"📌 [{idx}/{total_categories}] 正在优化: {category.category_name}")
            print(f"   匹配度: {category.match_score:.0%} | "
                  f"岗位数: {category.job_count} | "
                  f"核心要求: {'、'.join(category.core_requirements[:3])}")
            print(f"{'─' * 60}")

            result = self.optimize_for_category(
                resume_profile=resume_profile,
                category=category,
                resume_summary=resume_summary,
                skill_scores_text=skill_scores_text,
            )
            results.append(result)

            print(f"\n✅ [{category.category_name}] 优化完成")

            # 如果还有更多类别，询问是否继续
            if idx < total_categories:
                print(f"\n还剩 {total_categories - idx} 个类别待优化。")
                user_input = input("输入 'next' 继续下一类别，'quit' 退出: ").strip().lower()
                if user_input in ("quit", "q", "退出"):
                    print("⏹  用户选择提前退出")
                    break

        return results

    def optimize_for_category(
        self,
        resume_profile: ResumeProfile,
        category: JobCategory,
        resume_summary: str,
        skill_scores_text: str,
    ) -> CategoryOptimizationResult:
        """
        针对单个岗位类别执行多轮对话优化。
        
        流程：
        1. 重置记忆 → 初始分析 → 展示结果
        2. 进入交互循环（用户补充信息 / Agent 追问）
        3. 用户输入 "完成" → 输出结构化结果
        """
        # ★ 切换类别时重置记忆，避免串话
        self.reset_memory()
        self.current_category = category.category_name

        # ===== 第 1 轮：初始分析 + 优化建议 =====
        initial_prompt = OPTIMIZE_INITIAL_PROMPT.format(
            category_name=category.category_name,
            core_requirements="\n".join(f"- {r}" for r in category.core_requirements),
            preferred_requirements="\n".join(f"- {r}" for r in category.preferred_requirements),
            key_keywords="、".join(category.key_keywords),
            optimization_focus="\n".join(f"- {f}" for f in category.optimization_focus),
            resume_summary=resume_summary,
            skill_scores=skill_scores_text,
        )

        logger.info(f"[ResumeOptimizeAgent] 开始优化 [{category.category_name}] - 第 1 轮")

        # 使用 BaseAgent 的 chat_with_history（自动管理对话历史）
        response = self.chat_with_history(
            user_message=initial_prompt,
            system_prompt=RESUME_OPTIMIZER_SYSTEM_PROMPT,
        )

        # 展示初始分析结果
        print(f"\n{'=' * 50}")
        print(f"📊 [{category.category_name}] 初始分析与优化建议")
        print(f"{'=' * 50}")
        print(response)

        # ===== 多轮交互循环 =====
        round_count = 1
        conversation_history = [
            {"role": "assistant", "content": response}
        ]

        while True:
            print(f"\n{'─' * 50}")
            print(f">> [对话轮次: {round_count + 1}]")
            print("请输入你的反馈/补充信息：")
            print("  - 直接输入文字：补充经历细节、回答 Agent 的提问")
            print("  - 输入 '完成'：结束当前类别优化并生成最终结果")
            print("  - 输入 '跳过'：跳过当前类别")
            print(f"{'─' * 50}")

            try:
                user_input = input("你: ").strip()
            except (EOFError, KeyboardInterrupt):
                user_input = "完成"

            if not user_input:
                print("(未输入内容，请重新输入)")
                continue

            # 检查退出指令
            if user_input in ("完成", "done", "finish", "结束"):
                break

            if user_input in ("跳过", "skip"):
                logger.info(f"[ResumeOptimizeAgent] 用户跳过 [{category.category_name}]")
                return CategoryOptimizationResult(
                    job_category=category,
                    overall_improvement="用户选择跳过此类别"
                )

            # 继续对话
            round_count += 1
            conversation_history.append({"role": "user", "content": user_input})

            followup_prompt = OPTIMIZE_FOLLOWUP_PROMPT.format(
                user_input=user_input,
                category_name=category.category_name,
            )

            logger.info(f"[ResumeOptimizeAgent] [{category.category_name}] 第 {round_count} 轮")

            # 使用 BaseAgent 的 chat_with_history 方法（自动管理上下文）
            response = self.chat_with_history(
                user_message=followup_prompt,
                system_prompt=RESUME_OPTIMIZER_SYSTEM_PROMPT,
            )
            conversation_history.append({"role": "assistant", "content": response})

            print(f"\n[Agent]:")
            print(response)

        # ===== 最终结构化输出 =====
        logger.info(f"[ResumeOptimizeAgent] [{category.category_name}] 生成最终结构化结果...")

        final_prompt = OPTIMIZE_FINAL_PROMPT.format(
            category_name=category.category_name,
        )

        # 使用 chat_with_history 带完整上下文调用
        final_response = self.chat_with_history(
            user_message=final_prompt,
            system_prompt=RESUME_OPTIMIZER_SYSTEM_PROMPT,
        )
        parsed = extract_json_from_response(final_response)

        # 构建结果
        if parsed:
            gap_data = parsed.get("gap_analysis", {})
            gap = GapAnalysis(**gap_data) if gap_data else GapAnalysis()

            sections = [
                OptimizedSection(**s) for s in parsed.get("optimized_sections", [])
            ]

            result = CategoryOptimizationResult(
                job_category=category,
                gap_analysis=gap,
                optimized_sections=sections,
                key_highlights=parsed.get("key_highlights", []),
                additional_suggestions=parsed.get("additional_suggestions", []),
                overall_improvement=parsed.get("overall_improvement", ""),
                conversation_history=conversation_history,
            )
        else:
            # 解析失败，保存原始对话
            logger.warning(f"[ResumeOptimizeAgent] [{category.category_name}] JSON 解析失败，保存原始对话")
            result = CategoryOptimizationResult(
                job_category=category,
                overall_improvement=final_response,
                conversation_history=conversation_history,
            )

        logger.info(
            f"[ResumeOptimizeAgent] [{category.category_name}] 优化完成:\n"
            f"  匹配技能: {len(result.gap_analysis.matched_skills)}\n"
            f"  缺失技能: {len(result.gap_analysis.missing_skills)}\n"
            f"  优化模块: {len(result.optimized_sections)}\n"
            f"  对话轮数: {round_count}"
        )

        return result
