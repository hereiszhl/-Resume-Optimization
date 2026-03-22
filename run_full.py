"""
完整运行简历优化系统：
使用缓存的简历分析 + 岗位分析结果，对所有类别执行优化，生成 Markdown 报告。

自动模拟用户交互：
- 每个类别：初始分析后直接输入"完成"生成结构化结果
- 类别之间：自动输入"next"继续下一类别
"""
import sys, os, json, time, builtins
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from pathlib import Path
from config.settings import Settings
from models.schemas import (
    ResumeProfile, JobAnalysisResult, ResumeOptimizationPlan
)
from agents.resume_reader import ResumeReadingAgent
from agents.resume_optimizer import ResumeOptimizeAgent
from utils.helpers import save_json, load_json, generate_timestamp
from utils.report_generator import generate_markdown_report
from utils.logger import logger


def main():
    Settings.validate()
    Settings.ensure_dirs()

    print("=" * 60)
    print("  简历多类别优化系统 - 完整运行")
    print("=" * 60)

    # ===== 阶段 1: 加载缓存的简历分析结果 =====
    analysis_cache = os.path.join(SCRIPT_DIR, "outputs", "resume_analysis.json")
    jobs_cache = os.path.join(SCRIPT_DIR, "outputs", "job_analysis.json")

    for p, name in [(analysis_cache, "简历分析"), (jobs_cache, "岗位分析")]:
        if not os.path.exists(p):
            print(f"[!] {name}缓存不存在: {p}")
            print("    请先运行简历分析和岗位分析。")
            return

    resume_profile = ResumeProfile(**load_json(analysis_cache))
    job_analysis = JobAnalysisResult(**load_json(jobs_cache))

    print(f"\n[阶段 1] 已加载简历分析: {resume_profile.name} (评分 {resume_profile.overall_score}/10)")
    print(f"[阶段 2] 已加载岗位分析: {job_analysis.total_jobs} 个岗位, {len(job_analysis.categories)} 个类别")
    for cat in job_analysis.categories:
        print(f"         - {cat.category_name} ({cat.job_count} 岗位, 匹配{cat.match_score:.0%})")

    # ===== 阶段 3: 逐类别优化 =====
    print(f"\n{'=' * 60}")
    print(f"[阶段 3] 开始逐类别简历优化（共 {len(job_analysis.categories)} 个类别）")
    print(f"{'=' * 60}")

    # 准备数据
    reader = ResumeReadingAgent()
    resume_summary = reader.get_resume_summary(resume_profile)
    skill_scores_text = reader.get_skill_scores_text(resume_profile)

    # Monkey-patch input() 实现自动化
    # 策略: 每个类别对话中输入"完成"，类别切换时输入"next"
    original_input = builtins.input

    def auto_input(prompt=""):
        prompt_lower = prompt.lower() if prompt else ""
        # 判断是类别间切换提示还是对话轮次提示
        if "next" in prompt_lower or "quit" in prompt_lower or "继续" in prompt_lower:
            val = "next"
        else:
            val = "完成"
        print(f"{prompt}{val}  [自动]")
        return val

    builtins.input = auto_input

    try:
        start_time = time.time()

        optimizer = ResumeOptimizeAgent()
        optimizations = optimizer.run(
            resume_profile=resume_profile,
            job_analysis=job_analysis,
            resume_summary=resume_summary,
            skill_scores_text=skill_scores_text,
        )

        elapsed = time.time() - start_time
        print(f"\n[阶段 3] 所有类别优化完成！耗时 {elapsed:.0f} 秒")

    finally:
        builtins.input = original_input

    # ===== 阶段 4: 生成报告 =====
    print(f"\n{'=' * 60}")
    print(f"[阶段 4] 生成优化报告")
    print(f"{'=' * 60}")

    # 汇总通用建议
    general_suggestions = []
    if resume_profile.weaknesses:
        general_suggestions.extend(f"【通用】{w}" for w in resume_profile.weaknesses[:3])
    if job_analysis.common_trends:
        general_suggestions.extend(f"【趋势】{t}" for t in job_analysis.common_trends[:3])

    # 构建完整结果
    plan = ResumeOptimizationPlan(
        original_resume_path="data/resumes/resume.pdf",
        resume_profile=resume_profile,
        job_analysis=job_analysis,
        optimizations=optimizations,
        general_suggestions=general_suggestions,
    )

    # 保存 JSON
    timestamp = generate_timestamp()
    json_path = Settings.OUTPUT_DIR / f"optimization_{timestamp}.json"
    save_json(plan, json_path)
    print(f"  JSON 结果: {json_path}")

    # 生成 Markdown 报告
    md_path = Settings.OUTPUT_DIR / f"optimization_report_{timestamp}.md"
    generate_markdown_report(plan, md_path)

    print(f"\n{'=' * 60}")
    print(f"  全部完成！")
    print(f"{'=' * 60}")
    print(f"  JSON 结果:     {json_path}")
    print(f"  Markdown 报告: {md_path}")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
