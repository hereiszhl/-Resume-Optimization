"""
简历多类别优化系统 - 主入口
================================

基于 LLM Agent 的简历优化程序，使用智谱 GLM-4.7 模型。

三个 Agent 协作流水线：
1. Resume Reading Agent   - 解析 PDF 简历，量化能力评估
2. Job Requirement Agent  - 岗位分类与需求总结
3. Resume Optimize Agent  - 逐类别多轮对话式简历优化

使用方式:
    # 完整流程（启动后从 data/resumes 中选择简历）
    python main.py

    # 完整流程（手动指定简历）
    python main.py --resume data/resumes/my_resume.pdf

    # 完整流程（手动输入 JD）
    python main.py --resume data/resumes/my_resume.pdf --input-mode manual

    # 完整流程（从文件读取 JD）
    python main.py --resume data/resumes/my_resume.pdf --input-mode file --jobs-dir data/job_descriptions/

    # 仅分析简历
    python main.py --mode analyze

    # 从已有分析结果继续优化
    python main.py --mode optimize --analysis-cache outputs/my_resume_resume_analysis.json --jobs-cache outputs/job_analysis.json
"""

import sys
import os
import argparse
from pathlib import Path

# Windows 终端 GBK 编码兼容：强制 stdout/stderr 使用 UTF-8
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# 确保项目根目录在 Python 路径中
PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import Settings
from agents.resume_reader import ResumeReadingAgent
from agents.job_reader import JobRequirementAgent
from agents.resume_optimizer import ResumeOptimizeAgent
from models.schemas import (
    ResumeProfile, JobAnalysisResult, ResumeOptimizationPlan
)
from utils.helpers import save_json, load_json, generate_timestamp
from utils.report_generator import generate_markdown_report
from utils.logger import logger


def run_full_pipeline(args):
    """完整流水线：简历分析 → 岗位分析 → 逐类别优化 → Markdown 报告"""

    Settings.validate()
    Settings.ensure_dirs()
    logger.info("=" * 60)
    logger.info("🚀 简历多类别优化系统启动")
    logger.info("=" * 60)
    logger.info(Settings.info())

    # ===== 阶段 1: 简历分析 =====
    resume_profile = _run_resume_analysis(args)

    # ===== 阶段 2: 岗位分析 =====
    job_analysis = _run_job_analysis(args, resume_profile)

    # ===== 阶段 3: 逐类别优化 =====
    optimizations = _run_optimization(args, resume_profile, job_analysis)

    # ===== 阶段 4: 生成报告 =====
    _generate_report(args, resume_profile, job_analysis, optimizations)


def run_analyze_only(args):
    """仅执行简历分析"""
    Settings.validate()
    Settings.ensure_dirs()

    profile = _run_resume_analysis(args)
    print(f"\n📊 简历分析完成！综合评分: {profile.overall_score}/10")
    print(f"  优势: {', '.join(profile.strengths[:3])}")
    print(f"  不足: {', '.join(profile.weaknesses[:3])}")


def run_optimize_only(args):
    """从缓存的分析结果继续优化"""
    Settings.validate()
    Settings.ensure_dirs()

    # 加载缓存
    if not args.analysis_cache or not args.jobs_cache:
        print("❌ --mode optimize 需要指定 --analysis-cache 和 --jobs-cache")
        sys.exit(1)

    logger.info("从缓存加载分析结果...")
    resume_data = load_json(args.analysis_cache)
    resume_profile = ResumeProfile(**resume_data)

    jobs_data = load_json(args.jobs_cache)
    job_analysis = JobAnalysisResult(**jobs_data)

    optimizations = _run_optimization(args, resume_profile, job_analysis)
    _generate_report(args, resume_profile, job_analysis, optimizations)


# ===== 各阶段实现 =====

def _list_resume_pdfs() -> list[Path]:
    """列出 data/resumes 目录中的 PDF 简历"""
    resume_dir = Settings.RESUMES_DIR
    if not resume_dir.exists():
        return []

    return sorted(
        [f for f in resume_dir.iterdir() if f.is_file() and f.suffix.lower() == ".pdf"],
        key=lambda p: p.name.lower()
    )


def _choose_resume_interactive(pdf_files: list[Path]) -> Path:
    """交互式选择简历 PDF"""
    print("\n📂 在 data/resumes 中发现以下简历：")
    for idx, file_path in enumerate(pdf_files, 1):
        print(f"  {idx}. {file_path.name}")

    while True:
        choice = input("\n请输入要解析的简历编号: ").strip()
        if not choice.isdigit():
            print("[!] 输入无效，请输入数字编号")
            continue

        selected_idx = int(choice)
        if 1 <= selected_idx <= len(pdf_files):
            selected = pdf_files[selected_idx - 1]
            print(f"[OK] 已选择简历: {selected.name}")
            return selected

        print(f"[!] 编号超出范围，请输入 1~{len(pdf_files)}")


def _resolve_resume_path(args) -> Path:
    """解析本次运行要使用的简历路径"""
    if args.resume:
        resume_path = Path(args.resume)
        if not resume_path.exists():
            print(f"❌ 简历文件不存在: {resume_path}")
            sys.exit(1)
        return resume_path

    pdf_files = _list_resume_pdfs()
    if not pdf_files:
        print(f"❌ 未在 {Settings.RESUMES_DIR} 找到任何 PDF 简历")
        print("   请放入 PDF 后重试，或通过 --resume 指定路径")
        sys.exit(1)

    return _choose_resume_interactive(pdf_files)


def _get_resume_analysis_cache_path(resume_path: Path) -> Path:
    """按简历文件名生成对应分析缓存路径"""
    return Settings.OUTPUT_DIR / f"{resume_path.stem}_resume_analysis.json"


def _run_resume_analysis(args) -> ResumeProfile:
    """阶段 1: 简历分析"""
    # 检查是否有缓存
    if args.analysis_cache:
        logger.info(f"从缓存加载简历分析: {args.analysis_cache}")
        data = load_json(args.analysis_cache)
        return ResumeProfile(**data)

    resume_path = _resolve_resume_path(args)
    args.resume = str(resume_path)
    resume_cache_path = _get_resume_analysis_cache_path(resume_path)

    if resume_cache_path.exists():
        logger.info(f"命中简历缓存，跳过 LLM 解析: {resume_cache_path}")
        data = load_json(resume_cache_path)
        profile = ResumeProfile(**data)
        save_json(profile, Settings.OUTPUT_DIR / "resume_analysis.json")
        print(f"\n♻️ 复用已解析简历缓存: {resume_cache_path.name}")
        return profile

    logger.info("=" * 50)
    logger.info("📄 阶段 1: 简历分析")
    logger.info("=" * 50)

    reader = ResumeReadingAgent()
    profile = reader.run(str(resume_path), output_path=str(resume_cache_path))
    save_json(profile, Settings.OUTPUT_DIR / "resume_analysis.json")
    logger.info(f"已同步更新通用简历缓存: {Settings.OUTPUT_DIR / 'resume_analysis.json'}")

    print(f"\n📊 简历分析完成！")
    print(f"  姓名: {profile.name}")
    print(f"  综合评分: {profile.overall_score}/10")
    print(f"  优势: {', '.join(profile.strengths[:3])}")
    print(f"  不足: {', '.join(profile.weaknesses[:3])}")

    return profile


def _run_job_analysis(args, resume_profile: ResumeProfile) -> JobAnalysisResult:
    """阶段 2: 岗位分析（支持自动爬取/文件读取/手动输入三种模式）"""
    # 检查是否有缓存
    if args.jobs_cache:
        logger.info(f"从缓存加载岗位分析: {args.jobs_cache}")
        data = load_json(args.jobs_cache)
        return JobAnalysisResult(**data)

    logger.info("\n" + "=" * 50)
    logger.info("[阶段 2] 岗位需求分析")
    logger.info("=" * 50)

    job_agent = JobRequirementAgent()
    manual_jobs = None
    scraped_jobs = None
    jobs_dir = args.jobs_dir

    input_mode = getattr(args, "input_mode", "auto")

    if input_mode == "auto":
        # 自动爬取模式（默认）：从实习僧收藏页抓取岗位
        print("\n[auto] 自动爬取实习僧收藏岗位...")
        try:
            from utils.web_scraper import scrape_collected_jobs
            scraped_jobs = scrape_collected_jobs(max_jobs=getattr(args, 'max_jobs', 30))
            if not scraped_jobs:
                print("[!] 自动爬取未获取到岗位，切换到手动输入模式...")
                manual_jobs = job_agent.collect_jobs_interactive()
                if not manual_jobs:
                    print("[!] 未输入任何岗位，请至少提供一个岗位描述")
                    sys.exit(1)
            else:
                print(f"[OK] 成功爬取 {len(scraped_jobs)} 个岗位")
        except ImportError:
            print("[!] Playwright 未安装，切换到手动输入模式...")
            print("    安装方式: pip install playwright && playwright install chromium")
            manual_jobs = job_agent.collect_jobs_interactive()
        except Exception as e:
            print(f"[!] 爬取出错: {e}")
            print("切换到手动输入模式...")
            manual_jobs = job_agent.collect_jobs_interactive()

    elif input_mode == "manual":
        # 手动输入模式
        manual_jobs = job_agent.collect_jobs_interactive()
        if not manual_jobs:
            print("[!] 未输入任何岗位，请至少提供一个岗位描述")
            sys.exit(1)

    elif input_mode == "file":
        # 文件读取模式
        if not jobs_dir:
            jobs_dir = str(Settings.JD_DIR)
        dir_path = Path(jobs_dir)
        if not dir_path.exists() or not any(f.suffix in ('.txt', '.md', '.json') for f in dir_path.iterdir() if f.is_file()):
            print(f"[!] JD 目录为空或不存在: {jobs_dir}")
            print("切换到手动输入模式...")
            manual_jobs = job_agent.collect_jobs_interactive()
            jobs_dir = None

    result = job_agent.run(
        resume_profile=resume_profile,
        jobs_dir=jobs_dir if input_mode == "file" and jobs_dir else None,
        manual_jobs=manual_jobs,
        scraped_jobs=scraped_jobs,
    )

    print(f"\n[OK] 岗位分析完成！")
    print(f"  总岗位数: {result.total_jobs}")
    print(f"  分类数: {len(result.categories)}")
    for cat in result.categories:
        print(f"  - {cat.category_name}: {cat.job_count} 个岗位, "
              f"匹配度 {cat.match_score:.0%}")

    return result


def _run_optimization(args, resume_profile, job_analysis):
    """阶段 3: 逐类别多轮对话优化"""
    if not job_analysis.categories:
        logger.warning("没有岗位类别可优化")
        return []

    logger.info("\n" + "=" * 50)
    logger.info("🎯 阶段 3: 逐类别简历优化（多轮对话）")
    logger.info("=" * 50)

    # 准备简历概要文本
    reader = ResumeReadingAgent()
    resume_summary = reader.get_resume_summary(resume_profile)
    skill_scores_text = reader.get_skill_scores_text(resume_profile)

    # 创建优化 Agent 并执行
    optimizer = ResumeOptimizeAgent()
    optimizations = optimizer.run(
        resume_profile=resume_profile,
        job_analysis=job_analysis,
        resume_summary=resume_summary,
        skill_scores_text=skill_scores_text,
    )

    return optimizations


def _generate_report(args, resume_profile, job_analysis, optimizations):
    """阶段 4: 生成 Markdown 报告"""
    logger.info("\n" + "=" * 50)
    logger.info("📝 阶段 4: 生成优化报告")
    logger.info("=" * 50)

    # 汇总通用建议
    general_suggestions = []
    if resume_profile.weaknesses:
        general_suggestions.extend(
            f"【通用】{w}" for w in resume_profile.weaknesses[:3]
        )
    if job_analysis.common_trends:
        general_suggestions.extend(
            f"【趋势】{t}" for t in job_analysis.common_trends[:3]
        )

    # 构建顶层结果
    plan = ResumeOptimizationPlan(
        original_resume_path=args.resume or "",
        resume_profile=resume_profile,
        job_analysis=job_analysis,
        optimizations=optimizations,
        general_suggestions=general_suggestions,
    )

    # 保存 JSON
    timestamp = generate_timestamp()
    json_path = Settings.OUTPUT_DIR / f"optimization_{timestamp}.json"
    save_json(plan, json_path)
    logger.info(f"JSON 结果已保存: {json_path}")

    # 生成 Markdown 报告
    md_path = Settings.OUTPUT_DIR / f"optimization_report_{timestamp}.md"
    generate_markdown_report(plan, md_path)

    print(f"\n{'=' * 60}")
    print("✅ 全部完成！")
    print(f"{'=' * 60}")
    print(f"  📊 JSON 结果:  {json_path}")
    print(f"  📋 Markdown 报告: {md_path}")
    print(f"{'=' * 60}")


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(
        description="简历多类别优化系统 - 基于 LLM Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 完整流程（启动后从 data/resumes 里选择简历）
  python main.py

  # 完整流程（手动指定简历）
  python main.py --resume data/resumes/my_resume.pdf

  # 完整流程（手动输入 JD）
  python main.py --resume data/resumes/my_resume.pdf --input-mode manual

  # 完整流程（从文件读取 JD）
  python main.py --resume data/resumes/my_resume.pdf --input-mode file --jobs-dir data/job_descriptions/

  # 仅分析简历
  python main.py --mode analyze

  # 从缓存继续优化
  python main.py --mode optimize --analysis-cache outputs/my_resume_resume_analysis.json --jobs-cache outputs/job_analysis.json
        """
    )

    parser.add_argument(
        "--resume", type=str, default=None,
        help="简历 PDF 文件路径；不传则启动时从 data/resumes 目录交互选择"
    )
    parser.add_argument(
        "--jobs-dir", type=str, default=None,
        help="岗位 JD 文件目录路径"
    )
    parser.add_argument(
        "--input-mode", type=str, choices=["auto", "file", "manual"],
        default="auto",
        help="JD 输入模式: auto=自动爬取实习僧收藏页(默认), file=从文件读取, manual=手动输入"
    )
    parser.add_argument(
        "--max-jobs", type=int, default=30,
        help="自动爬取模式下的最大岗位数量（默认30）"
    )
    parser.add_argument(
        "--mode", type=str, choices=["full", "analyze", "optimize"],
        default="full",
        help="运行模式: full=完整流程, analyze=仅分析简历, optimize=从缓存继续优化"
    )
    parser.add_argument(
        "--analysis-cache", type=str, default=None,
        help="已有的简历分析 JSON 文件路径（跳过重新分析）"
    )
    parser.add_argument(
        "--jobs-cache", type=str, default=None,
        help="已有的岗位分析 JSON 文件路径（跳过重新分析）"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None,
        help="输出目录路径"
    )

    return parser.parse_args()


def main():
    """主入口"""
    args = parse_args()

    # 覆盖输出目录
    if args.output_dir:
        Settings.OUTPUT_DIR = Path(args.output_dir)

    try:
        if args.mode == "full":
            run_full_pipeline(args)
        elif args.mode == "analyze":
            run_analyze_only(args)
        elif args.mode == "optimize":
            run_optimize_only(args)
    except KeyboardInterrupt:
        print("\n\n⏹  用户中断，正在退出...")
        sys.exit(0)
    except ValueError as e:
        print(f"\n❌ 配置错误: {e}")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"运行出错: {e}")
        print(f"\n❌ 运行出错: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
