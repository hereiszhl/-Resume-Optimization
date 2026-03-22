"""Markdown 报告生成器：将优化结果渲染为结构化 Markdown 文档"""

from pathlib import Path
from datetime import datetime
from models.schemas import ResumeOptimizationPlan, CategoryOptimizationResult
from utils.logger import logger


def generate_markdown_report(plan: ResumeOptimizationPlan, output_path: str | Path) -> Path:
    """
    生成完整的 Markdown 优化报告。
    
    Args:
        plan: 顶层优化结果
        output_path: 输出文件路径
    
    Returns:
        保存的文件路径
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    lines = []

    # ===== 标题 =====
    lines.append("# 📋 简历多类别优化报告\n")
    lines.append(f"> **生成时间**: {plan.generated_at.strftime('%Y-%m-%d %H:%M')}")
    if plan.original_resume_path:
        lines.append(f"> **原始简历**: `{plan.original_resume_path}`")
    lines.append("")

    # ===== 简历分析概览 =====
    if plan.resume_profile:
        profile = plan.resume_profile
        lines.append("---\n## 📄 简历分析概览\n")

        if profile.name:
            lines.append(f"**姓名**: {profile.name}")
        if profile.education:
            edu = profile.education[0]
            lines.append(f"**学历**: {edu.school} · {edu.major} · {edu.degree}")
        lines.append("")

        # 能力评分表
        if profile.skill_scores:
            lines.append("### 🎯 多维能力评分\n")
            lines.append("| 评估维度 | 评分 | 评分依据 | 提升建议 |")
            lines.append("|---------|:----:|---------|---------|")
            for score in profile.skill_scores:
                bar = "█" * score.score + "░" * (10 - score.score)
                lines.append(
                    f"| {score.dimension} | {bar} {score.score}/10 | "
                    f"{score.evidence[:30]}{'...' if len(score.evidence) > 30 else ''} | "
                    f"{score.suggestion[:30]}{'...' if len(score.suggestion) > 30 else ''} |"
                )
            lines.append(f"\n**综合评分**: {profile.overall_score:.1f}/10\n")

        # 优势与不足
        if profile.strengths:
            lines.append("### ✅ 核心优势\n")
            for s in profile.strengths:
                lines.append(f"- {s}")
            lines.append("")

        if profile.weaknesses:
            lines.append("### ⚠️ 待提升领域\n")
            for w in profile.weaknesses:
                lines.append(f"- {w}")
            lines.append("")

        if profile.summary:
            lines.append(f"### 📝 整体评价\n\n{profile.summary}\n")

    # ===== 岗位分析概览 =====
    if plan.job_analysis:
        analysis = plan.job_analysis
        lines.append("---\n## 🏢 岗位需求分析\n")
        lines.append(f"共分析 **{analysis.total_jobs}** 个岗位，聚类为 "
                      f"**{len(analysis.categories)}** 个类别：\n")

        # 类别概览表
        lines.append("| 岗位类别 | 岗位数 | 匹配度 | 核心要求 |")
        lines.append("|---------|:------:|:------:|---------|")
        for cat in analysis.categories:
            reqs = "、".join(cat.core_requirements[:4])
            match_bar = "●" * int(cat.match_score * 5) + "○" * (5 - int(cat.match_score * 5))
            lines.append(
                f"| **{cat.category_name}** | {cat.job_count} | "
                f"{match_bar} {cat.match_score:.0%} | {reqs} |"
            )
        lines.append("")

        # 共同趋势
        if analysis.common_trends:
            lines.append("### 📈 跨类别共同趋势\n")
            for t in analysis.common_trends:
                lines.append(f"- {t}")
            lines.append("")

    # ===== 逐类别优化详情（核心部分）=====
    if plan.optimizations:
        lines.append("---\n## 🎯 分类别简历优化方案\n")

        for idx, opt in enumerate(plan.optimizations, 1):
            _render_category_optimization(lines, idx, opt)

    # ===== 通用建议 =====
    if plan.general_suggestions:
        lines.append("---\n## 💡 通用提升建议\n")
        for i, sug in enumerate(plan.general_suggestions, 1):
            lines.append(f"{i}. {sug}")
        lines.append("")

    # ===== 写入文件 =====
    content = "\n".join(lines)
    output_path.write_text(content, encoding="utf-8")
    logger.info(f"✅ Markdown 报告已保存: {output_path}")
    return output_path


def _render_category_optimization(
    lines: list,
    idx: int,
    opt: CategoryOptimizationResult
):
    """渲染单个类别的优化详情"""
    cat = opt.job_category
    lines.append(f"### {idx}. {cat.category_name}")
    lines.append(f"**匹配度**: {cat.match_score:.0%} | "
                  f"**包含岗位**: {'、'.join(cat.representative_titles[:3])}\n")

    # 核心要求
    if cat.core_requirements:
        lines.append("**核心要求**: " + "、".join(cat.core_requirements))
    if cat.optimization_focus:
        lines.append("**优化重点**: " + "、".join(cat.optimization_focus))
    lines.append("")

    # Gap 分析
    gap = opt.gap_analysis
    if gap.matched_skills or gap.missing_skills:
        lines.append("#### 🔍 差距分析\n")
        if gap.matched_skills:
            lines.append("**已匹配技能**: " + "、".join(gap.matched_skills))
        if gap.missing_skills:
            lines.append("**缺失技能**: " + "、".join(gap.missing_skills))
        if gap.experience_gaps:
            lines.append("\n**经历缺口（建议补充）**:")
            for eg in gap.experience_gaps:
                lines.append(f"- ⚡ {eg}")
        if gap.match_percentage:
            lines.append(f"\n> 当前匹配度: **{gap.match_percentage:.0%}**")
        lines.append("")

    # 各模块优化
    if opt.optimized_sections:
        lines.append("#### 📝 模块优化详情\n")
        for section in opt.optimized_sections:
            lines.append(f"##### {section.section_name}\n")
            if section.change_rationale:
                lines.append(f"> 💡 **修改理由**: {section.change_rationale}\n")
            if section.strategy_used:
                lines.append(f"**使用策略**: {', '.join(section.strategy_used)}\n")
            if section.original_content:
                lines.append("<details><summary>📋 查看原始内容</summary>\n")
                lines.append(f"```\n{section.original_content}\n```\n")
                lines.append("</details>\n")
            lines.append(f"**✨ 优化后内容**:\n\n{section.optimized_content}\n")

    # 关键亮点
    if opt.key_highlights:
        lines.append("#### 🌟 关键亮点\n")
        for h in opt.key_highlights:
            lines.append(f"- {h}")
        lines.append("")

    # 补充建议
    if opt.additional_suggestions:
        lines.append("#### 📌 补充建议\n")
        for s in opt.additional_suggestions:
            lines.append(f"- {s}")
        lines.append("")

    # 整体提升
    if opt.overall_improvement:
        lines.append(f"#### 📊 整体提升总结\n\n{opt.overall_improvement}\n")

    lines.append("")
