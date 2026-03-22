"""
Resume Optimize Agent 测试脚本：
使用缓存的简历分析 + 岗位分析结果，自动化测试单类别优化流程。
模拟用户交互：初始分析 → 自动输入"完成" → 生成结构化 JSON。
"""
import sys, os, json, threading, time
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from models.schemas import ResumeProfile, JobAnalysisResult, JobCategory
from agents.resume_optimizer import ResumeOptimizeAgent
from agents.resume_reader import ResumeReadingAgent
from utils.helpers import save_json
from utils.logger import logger


def main():
    print("=" * 60)
    print("Resume Optimize Agent 测试（单类别自动化）")
    print("=" * 60)

    # Step 1: 加载缓存数据
    resume_path = os.path.join(SCRIPT_DIR, "outputs", "resume_analysis.json")
    jobs_path = os.path.join(SCRIPT_DIR, "outputs", "job_analysis.json")

    for p, name in [(resume_path, "简历分析"), (jobs_path, "岗位分析")]:
        if not os.path.exists(p):
            print(f"[!] {name}结果不存在: {p}")
            return

    with open(resume_path, "r", encoding="utf-8") as f:
        resume_profile = ResumeProfile(**json.load(f))
    with open(jobs_path, "r", encoding="utf-8") as f:
        job_analysis = JobAnalysisResult(**json.load(f))

    print(f"[OK] 简历: {resume_profile.name} (评分 {resume_profile.overall_score}/10)")
    print(f"[OK] 岗位类别: {len(job_analysis.categories)} 个")
    for cat in job_analysis.categories:
        print(f"     - {cat.category_name} ({cat.job_count} 岗位, 匹配{cat.match_score:.0%})")

    # Step 2: 准备 resume_summary 和 skill_scores_text
    reader = ResumeReadingAgent()
    resume_summary = reader.get_resume_summary(resume_profile)
    skill_scores_text = reader.get_skill_scores_text(resume_profile)

    print(f"\n简历概要:\n{resume_summary}")
    print(f"\n能力评分:\n{skill_scores_text}")

    # Step 3: 选择匹配度最高的类别测试
    best_cat = max(job_analysis.categories, key=lambda c: c.match_score)
    print(f"\n{'=' * 60}")
    print(f"测试类别: {best_cat.category_name} (匹配度 {best_cat.match_score:.0%})")
    print(f"核心要求: {', '.join(best_cat.core_requirements[:5])}")
    print(f"关键词: {', '.join(best_cat.key_keywords[:5])}")
    print("=" * 60)

    # Step 4: 运行 optimize_for_category（单类别）
    # 因为 optimize_for_category 内部有 input() 交互，我们用 monkey-patch 模拟
    # 模拟策略：
    #   第1次 input(): 用户输入 "完成" -> 结束后生成结构化结果
    input_responses = iter(["完成"])
    original_input = __builtins__.__dict__.get("input", input)

    def mock_input(prompt=""):
        try:
            val = next(input_responses)
            print(f"{prompt}{val}  [自动输入]")
            return val
        except StopIteration:
            print(f"{prompt}完成  [自动输入-兜底]")
            return "完成"

    # Patch input
    import builtins
    builtins.input = mock_input

    try:
        print(f"\n开始优化（LLM 调用中，预计 2-5 分钟）...\n")
        start_time = time.time()

        optimizer = ResumeOptimizeAgent()
        result = optimizer.optimize_for_category(
            resume_profile=resume_profile,
            category=best_cat,
            resume_summary=resume_summary,
            skill_scores_text=skill_scores_text,
        )

        elapsed = time.time() - start_time
        print(f"\n{'=' * 60}")
        print(f"优化完成！耗时 {elapsed:.0f} 秒")
        print("=" * 60)

        # Step 5: 展示结果
        print(f"\n  类别: {result.job_category.category_name}")
        print(f"  匹配度: {result.gap_analysis.match_percentage:.0%}")
        print(f"  匹配技能: {', '.join(result.gap_analysis.matched_skills[:5])}")
        print(f"  缺失技能: {', '.join(result.gap_analysis.missing_skills[:5])}")
        print(f"  优化模块数: {len(result.optimized_sections)}")

        for sec in result.optimized_sections:
            print(f"\n  [{sec.section_name}]")
            print(f"    策略: {', '.join(sec.strategy_used[:3])}")
            print(f"    原始: {sec.original_content[:100]}...")
            print(f"    优化: {sec.optimized_content[:100]}...")

        if result.key_highlights:
            print(f"\n  关键亮点:")
            for h in result.key_highlights[:5]:
                print(f"    - {h}")

        if result.additional_suggestions:
            print(f"\n  补充建议:")
            for s in result.additional_suggestions[:5]:
                print(f"    - {s}")

        print(f"\n  整体提升: {result.overall_improvement[:200]}")

        # Step 6: 保存结果
        output_path = os.path.join(SCRIPT_DIR, "outputs", "test_optimize_result.json")
        save_json(result, output_path)
        print(f"\n结果已保存: {output_path}")

    finally:
        builtins.input = original_input


if __name__ == "__main__":
    main()
