"""
爬虫测试脚本：测试翻页功能和完整爬取流程。
用法: python test_scraper.py
"""
import sys, os, time, json
os.environ['PYTHONIOENCODING'] = 'utf-8'
try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)
os.chdir(SCRIPT_DIR)

from utils.web_scraper import scrape_collected_jobs

def main():
    print("=" * 60)
    print("爬虫翻页测试")
    print("=" * 60)

    # 调用爬虫主入口，设置最大 30 个岗位
    results = scrape_collected_jobs(max_jobs=30)

    print(f"\n{'=' * 60}")
    print(f"爬取结果汇总: 共 {len(results)} 个岗位")
    print("=" * 60)

    for i, job in enumerate(results, 1):
        desc_len = len(job.get("description", ""))
        print(f"  [{i}] {job['title']} ({job.get('company', '?')}) - JD {desc_len} 字符")

    # 保存测试结果
    output_path = os.path.join(SCRIPT_DIR, "outputs", "test_scraper_results.json")
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n结果已保存: {output_path}")

if __name__ == "__main__":
    main()
