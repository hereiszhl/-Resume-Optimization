"""从已有 JSON 重新生成 Markdown 报告（修复 match_percentage 归一化问题）"""
import sys, os
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from pathlib import Path
from models.schemas import ResumeOptimizationPlan
from utils.report_generator import generate_markdown_report
from utils.helpers import load_json

json_path = Path("outputs/optimization_20260226_211123.json")
data = load_json(json_path)

# Pydantic 模型会触发 field_validator，自动归一化 match_percentage
plan = ResumeOptimizationPlan(**data)

# 验证修复
for opt in plan.optimizations:
    mp = opt.gap_analysis.match_percentage
    print(f"  {opt.job_category.category_name}: match_percentage = {mp} -> {mp:.0%}")

md_path = Path("outputs/optimization_report_20260226_211123.md")
generate_markdown_report(plan, md_path)
print(f"\n报告已重新生成: {md_path}")
