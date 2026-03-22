"""
实习僧网站爬虫：自动抓取收藏页的岗位详情。

流程：
1. 首次运行：打开浏览器让用户手动登录，登录后自动保存 Cookie
2. 后续运行：自动加载 Cookie，无需重复登录
3. 访问收藏页，提取所有收藏岗位的链接
4. 逐个访问岗位详情页，提取职位描述（JD）
"""

import json
import time
from pathlib import Path
from typing import List, Dict, Optional
from utils.logger import logger

# Cookie 存储路径
COOKIE_PATH = Path(__file__).resolve().parent.parent / "data" / "shixiseng_cookies.json"

# 实习僧收藏页 URL
COLLECT_URL = "https://resume.shixiseng.com/my/collect"

# 请求间隔（秒），避免触发反爬
REQUEST_DELAY = 2.0


def _save_cookies(page, cookie_path: Path):
    """保存浏览器 Cookie"""
    cookies = page.context.cookies()
    cookie_path.parent.mkdir(parents=True, exist_ok=True)
    with open(cookie_path, "w", encoding="utf-8") as f:
        json.dump(cookies, f, ensure_ascii=False, indent=2)
    logger.info(f"[WebScraper] Cookie 已保存: {cookie_path}")


def _load_cookies(context, cookie_path: Path) -> bool:
    """加载已保存的 Cookie"""
    if not cookie_path.exists():
        return False
    try:
        with open(cookie_path, "r", encoding="utf-8") as f:
            cookies = json.load(f)
        context.add_cookies(cookies)
        logger.info(f"[WebScraper] 已加载 Cookie: {cookie_path}")
        return True
    except Exception as e:
        logger.warning(f"[WebScraper] Cookie 加载失败: {e}")
        return False


def _manual_login(playwright) -> "BrowserContext":
    """
    打开浏览器让用户手动登录。
    登录成功后自动保存 Cookie。
    """
    print("\n" + "=" * 60)
    print("[WebScraper] 首次使用需要手动登录实习僧")
    print("=" * 60)
    print("即将打开浏览器，请完成以下步骤：")
    print("  1. 在打开的浏览器中登录实习僧账号")
    print("  2. 登录成功后，确认页面显示你的用户信息")
    print("  3. 回到终端按 Enter 键继续")
    print("=" * 60)

    browser = playwright.chromium.launch(headless=False, channel="msedge")
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    page = context.new_page()
    try:
        page.goto("https://www.shixiseng.com/login", wait_until="domcontentloaded", timeout=60000)
    except Exception:
        pass  # 登录页超时不影响手动操作

    input("\n>>> 登录完成后，请按 Enter 键继续...")

    # 保存 Cookie
    _save_cookies(page, COOKIE_PATH)

    return browser, context, page


def _auto_login(playwright) -> "BrowserContext":
    """
    使用已保存的 Cookie 自动登录。
    """
    browser = playwright.chromium.launch(headless=True, channel="msedge")
    context = browser.new_context(
        viewport={"width": 1280, "height": 800},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    _load_cookies(context, COOKIE_PATH)
    page = context.new_page()
    return browser, context, page


def _extract_jobs_from_current_page(page) -> List[Dict[str, str]]:
    """
    从当前页面提取岗位链接（不涉及导航）。
    
    Returns:
        [{"title": ..., "company": ..., "url": ..., "meta": ...}]
    """
    jobs = []

    # 实习僧收藏页的岗位卡片结构
    job_cards = page.query_selector_all(
        ".intern-wrap .intern-detail__job, .job-info, .position-item, "
        ".collect-list .job-item, .intern-item"
    )

    if not job_cards:
        # 备用方案：直接提取所有链接中包含 /intern/ 或 /job/ 的
        logger.info("[WebScraper] 尝试从页面链接中提取岗位...")
        all_links = page.query_selector_all("a[href]")
        seen_urls = set()
        for link in all_links:
            href = link.get_attribute("href") or ""
            text = (link.inner_text() or "").strip()
            if ("/intern/" in href or "/job/" in href) and text and href not in seen_urls:
                full_url = href if href.startswith("http") else f"https://www.shixiseng.com{href}"
                seen_urls.add(full_url)
                jobs.append({
                    "title": text[:50],
                    "company": "",
                    "url": full_url,
                    "meta": "",
                })
    else:
        for card in job_cards:
            try:
                title_el = card.query_selector("a")
                title = (title_el.inner_text() if title_el else "").strip()
                href = (title_el.get_attribute("href") if title_el else "") or ""
                full_url = href if href.startswith("http") else f"https://www.shixiseng.com{href}"

                company_el = card.query_selector(".company-name, .com-name, .company")
                company = (company_el.inner_text() if company_el else "").strip()

                if title and href:
                    jobs.append({
                        "title": title[:50],
                        "company": company,
                        "url": full_url,
                        "meta": "",
                    })
            except Exception as e:
                logger.debug(f"[WebScraper] 解析岗位卡片失败: {e}")

    return jobs


def _extract_job_links(page, max_pages: int = 10) -> List[Dict[str, str]]:
    """
    从收藏页提取所有岗位的链接和基本信息（支持翻页）。
    
    Args:
        max_pages: 最大翻页数量，防止无限循环
    
    Returns:
        [{"title": "岗位名称", "company": "公司", "url": "详情页链接", "meta": "薪资等信息"}]
    """
    logger.info(f"[WebScraper] 访问收藏页: {COLLECT_URL}")
    try:
        page.goto(COLLECT_URL, wait_until="domcontentloaded", timeout=60000)
    except Exception as e:
        logger.warning(f"[WebScraper] 收藏页导航超时，继续执行: {e}")
    time.sleep(5)

    # 检查是否需要登录
    if "login" in page.url.lower():
        logger.warning("[WebScraper] Cookie 已过期，需要重新登录")
        return []

    all_jobs = []
    seen_urls = set()
    current_page = 1

    while current_page <= max_pages:
        logger.info(f"[WebScraper] 正在提取第 {current_page} 页的岗位...")

        # 滚动到底部加载所有内容
        _scroll_to_bottom(page)

        # 提取当前页的岗位
        page_jobs = _extract_jobs_from_current_page(page)
        new_count = 0
        for job in page_jobs:
            if job["url"] not in seen_urls:
                seen_urls.add(job["url"])
                all_jobs.append(job)
                new_count += 1

        logger.info(f"[WebScraper] 第 {current_page} 页：提取到 {len(page_jobs)} 个岗位（新增 {new_count}）")

        if new_count == 0 and current_page > 1:
            logger.info("[WebScraper] 当前页无新岗位，停止翻页")
            break

        # 尝试翻页：查找"下一页"按钮或下一个页码链接
        next_clicked = False

        # 方案 1: 找 "下一页" 按钮/链接
        next_selectors = [
            "a:has-text('下一页')",
            "button:has-text('下一页')",
            "li.next a",
            ".pagination .next a",
            ".page-next a",
            "a.next",
        ]
        for selector in next_selectors:
            try:
                next_btn = page.query_selector(selector)
                if next_btn and next_btn.is_visible():
                    # 检查是否被禁用
                    parent = next_btn.evaluate_handle("el => el.parentElement")
                    parent_class = parent.evaluate("el => el.className") if parent else ""
                    if "disabled" in str(parent_class).lower():
                        logger.info("[WebScraper] '下一页'按钮已禁用，已到最后一页")
                        break
                    next_btn.click()
                    time.sleep(3)
                    next_clicked = True
                    logger.info(f"[WebScraper] 已点击'{selector}'翻页")
                    break
            except Exception as e:
                logger.debug(f"[WebScraper] 选择器 {selector} 翻页失败: {e}")
                continue

        # 方案 2: 点击下一个页码数字（如 "2", "3" ...）
        if not next_clicked:
            next_page_num = current_page + 1
            try:
                # 尝试查找分页区域的页码链接
                page_links = page.query_selector_all("a")
                for pl in page_links:
                    text = (pl.inner_text() or "").strip()
                    if text == str(next_page_num):
                        # 确认这是分页区域的链接（而不是其他数字链接）
                        href = pl.get_attribute("href") or ""
                        # 分页通常包含 page 参数或在 pagination 容器内
                        parent_html = pl.evaluate("el => el.parentElement ? el.parentElement.outerHTML.substring(0, 200) : ''")
                        if ("page" in href.lower() or "页" in parent_html or
                            "paginat" in parent_html.lower() or "上一页" in parent_html or
                            "下一页" in parent_html):
                            pl.click()
                            time.sleep(3)
                            next_clicked = True
                            logger.info(f"[WebScraper] 已点击页码 {next_page_num} 翻页")
                            break
            except Exception as e:
                logger.debug(f"[WebScraper] 按页码翻页失败: {e}")

        if not next_clicked:
            logger.info(f"[WebScraper] 未找到下一页按钮，翻页结束（共 {current_page} 页）")
            break

        current_page += 1

    logger.info(f"[WebScraper] 从收藏页共提取到 {len(all_jobs)} 个岗位链接（共 {current_page} 页）")
    return all_jobs


def _extract_job_detail(page, job_info: Dict[str, str]) -> Optional[Dict[str, str]]:
    """
    访问岗位详情页，提取职位描述（JD）。
    
    Returns:
        {"title": ..., "company": ..., "url": ..., "description": ..., "requirements": ...}
    """
    url = job_info["url"]
    logger.info(f"[WebScraper] 正在抓取: {job_info['title']} -> {url}")

    try:
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
        except Exception as e:
            logger.warning(f"[WebScraper] 详情页导航超时: {e}")
        time.sleep(REQUEST_DELAY)

        # 提取页面标题
        title = job_info["title"]
        title_el = page.query_selector("h1, .job-title, .intern-title, .new_job_name")
        if title_el:
            title = title_el.inner_text().strip() or title

        # 提取公司名
        company = job_info.get("company", "")
        company_el = page.query_selector(".com-name, .company-name, .com_intro .com-title, a.com-name")
        if company_el:
            company = company_el.inner_text().strip() or company

        # 提取薪资、地点等元信息
        meta_info = ""
        meta_el = page.query_selector(".job-msg, .intern-detail__meta, .job_msg")
        if meta_el:
            meta_info = meta_el.inner_text().strip()

        # 提取职位描述（核心内容）
        description = ""
        # 实习僧详情页的 JD 通常在 .job_detail, .job-des, .intern-detail__content 等容器中
        desc_selectors = [
            ".job_detail",
            ".job-des",
            ".intern-detail__content",
            ".job-content",
            ".detail-content",
            ".job_good_list",
            "div.markdown-body",
        ]
        for selector in desc_selectors:
            desc_el = page.query_selector(selector)
            if desc_el:
                description = desc_el.inner_text().strip()
                if len(description) > 50:  # 确保内容足够长
                    break

        # 如果上面的选择器都没找到，尝试获取主内容区域的全部文本
        if len(description) < 50:
            main_el = page.query_selector("main, .main-content, #app, .job-detail-box")
            if main_el:
                description = main_el.inner_text().strip()

        if not description:
            logger.warning(f"[WebScraper] 未能提取到 JD 内容: {title}")
            return None

        result = {
            "title": title,
            "company": company,
            "url": url,
            "meta": meta_info,
            "description": description,
        }

        logger.info(f"[WebScraper] 已提取: {title} ({company}) - {len(description)} 字符")
        return result

    except Exception as e:
        logger.error(f"[WebScraper] 抓取失败 [{job_info['title']}]: {e}")
        return None


def _scroll_to_bottom(page, max_scrolls: int = 10):
    """滚动到页面底部以触发懒加载"""
    for i in range(max_scrolls):
        prev_height = page.evaluate("document.body.scrollHeight")
        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        time.sleep(1)
        new_height = page.evaluate("document.body.scrollHeight")
        if new_height == prev_height:
            break


def scrape_collected_jobs(max_jobs: int = 30) -> List[Dict[str, str]]:
    """
    主入口：爬取实习僧收藏页的所有岗位详情。
    
    Args:
        max_jobs: 最大爬取岗位数量
    
    Returns:
        [{title, company, url, description, meta}, ...]
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise ImportError(
            "请先安装 Playwright:\n"
            "  pip install playwright\n"
            "  playwright install chromium"
        )

    logger.info("[WebScraper] 开始爬取实习僧收藏岗位...")

    with sync_playwright() as pw:
        # Step 1: 登录
        has_cookies = COOKIE_PATH.exists()
        if has_cookies:
            logger.info("[WebScraper] 检测到已保存的 Cookie，尝试自动登录...")
            browser, context, page = _auto_login(pw)

            # 验证 Cookie 是否有效
            try:
                page.goto(COLLECT_URL, wait_until="domcontentloaded", timeout=60000)
            except Exception as e:
                logger.warning(f"[WebScraper] 收藏页导航超时，继续执行: {e}")
            time.sleep(5)
            if "login" in page.url.lower():
                logger.warning("[WebScraper] Cookie 已过期，需要重新登录")
                browser.close()
                browser, context, page = _manual_login(pw)
        else:
            browser, context, page = _manual_login(pw)

        try:
            # Step 2: 提取收藏页岗位链接
            job_links = _extract_job_links(page)
            if not job_links:
                logger.warning("[WebScraper] 未在收藏页找到岗位，尝试截图调试...")
                debug_path = Path(__file__).resolve().parent.parent / "outputs" / "debug_collect_page.png"
                debug_path.parent.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(debug_path))
                logger.info(f"[WebScraper] 页面截图已保存: {debug_path}")

                # 打印页面 HTML 片段用于调试
                html_snippet = page.content()[:3000]
                logger.debug(f"[WebScraper] 页面 HTML 片段:\n{html_snippet}")

                browser.close()
                return []

            # 限制数量
            job_links = job_links[:max_jobs]
            logger.info(f"[WebScraper] 将爬取 {len(job_links)} 个岗位详情...")

            # Step 3: 逐个访问详情页
            results = []
            for i, job_info in enumerate(job_links, 1):
                print(f"  [{i}/{len(job_links)}] 正在抓取: {job_info['title']}")
                detail = _extract_job_detail(page, job_info)
                if detail:
                    results.append(detail)
                time.sleep(REQUEST_DELAY)

            # Step 4: 更新 Cookie（延长有效期）
            _save_cookies(page, COOKIE_PATH)

            logger.info(f"[WebScraper] 爬取完成: 共获取 {len(results)}/{len(job_links)} 个岗位详情")

            # Step 5: 保存原始数据
            raw_path = Path(__file__).resolve().parent.parent / "outputs" / "scraped_jobs_raw.json"
            raw_path.parent.mkdir(parents=True, exist_ok=True)
            with open(raw_path, "w", encoding="utf-8") as f:
                json.dump(results, f, ensure_ascii=False, indent=2)
            logger.info(f"[WebScraper] 原始数据已保存: {raw_path}")

            return results

        finally:
            browser.close()
