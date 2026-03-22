"""
Job Requirement Agent 测试脚本：
使用爬虫抓取的数据 + 缓存的简历分析结果，测试岗位分类流程。
"""
import sys, os, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from models.schemas import ResumeProfile
from agents.job_reader import JobRequirementAgent
from utils.logger import logger


def main():
    print("=" * 60)
    print("Job Requirement Agent 测试")
    print("=" * 60)

    # Step 1: 加载爬虫抓取结果
    scraped_path = os.path.join(SCRIPT_DIR, "outputs", "scraped_jobs_raw.json")
    if not os.path.exists(scraped_path):
        print(f"[!] 爬虫数据不存在: {scraped_path}")
        print("    请先运行 test_scraper.py")
        return

    with open(scraped_path, "r", encoding="utf-8") as f:
        scraped_jobs = json.load(f)
    print(f"[OK] 已加载 {len(scraped_jobs)} 个爬虫岗位数据")

    # Step 2: 加载缓存的简历分析结果
    resume_path = os.path.join(SCRIPT_DIR, "outputs", "resume_analysis.json")
    if not os.path.exists(resume_path):
        print(f"[!] 简历分析结果不存在: {resume_path}")
        print("    请先运行简历分析")
        return

    with open(resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)
    resume_profile = ResumeProfile(**resume_data)
    print(f"[OK] 已加载简历: {resume_profile.name}")

    # Step 3: 初始化并运行 Agent
    print(f"\n{'=' * 60}")
    print("开始岗位分析（调用 LLM 分类）...")
    print("=" * 60)

    agent = JobRequirementAgent()
    result = agent.run(
        resume_profile=resume_profile,
        scraped_jobs=scraped_jobs,
        save_result=True,
    )

    # Step 4: 打印结果
    print(f"\n{'=' * 60}")
    print(f"分析完成！共 {result.total_jobs} 个岗位，{len(result.categories)} 个分类")
    print("=" * 60)

    for cat in result.categories:
        print(f"\n  【{cat.category_name}】({cat.job_count} 个岗位, 匹配度 {cat.match_score:.0%})")
        print(f"    代表岗位: {', '.join(cat.representative_titles[:3])}")
        print(f"    核心要求: {', '.join(cat.core_requirements[:5])}")
        print(f"    加分项: {', '.join(cat.preferred_requirements[:3])}")
        print(f"    关键词: {', '.join(cat.key_keywords[:5])}")
        print(f"    优化方向: {', '.join(cat.optimization_focus[:3])}")

    if result.common_trends:
        print(f"\n  跨类别趋势:")
        for trend in result.common_trends:
            print(f"    - {trend}")

    print(f"\n结果已保存至 outputs/job_analysis.json")


if __name__ == "__main__":
    main()
