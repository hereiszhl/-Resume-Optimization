"""常量定义：能力维度、评分标准、岗位类别等"""

# ========== 简历能力评估维度 ==========
SKILL_DIMENSIONS = {
    "technical_depth": "技术深度 - 编程语言/框架/工具的掌握程度",
    "project_quality": "项目质量 - 项目的复杂度、完成度和影响力",
    "research_ability": "科研能力 - 论文发表、学术项目、研究方法",
    "expression_clarity": "表达清晰度 - 简历描述的专业性和条理性",
    "education_background": "学历背景 - 学校层次、专业匹配度、GPA",
    "internship_experience": "实习经验 - 实习数量、质量和相关性",
    "soft_skills": "软技能 - 领导力、团队协作、沟通能力",
    "achievement_quantification": "成果量化 - 数据驱动的成果描述程度",
}

# 评分等级说明
SCORE_LEVELS = {
    (1, 3): "基础水平，需要重点提升",
    (4, 5): "一般水平，有提升空间",
    (6, 7): "良好水平，可以进一步优化",
    (8, 9): "优秀水平，保持并突出",
    (10, 10): "卓越水平，核心竞争力",
}

# ========== 简历模块定义 ==========
RESUME_SECTIONS = [
    "基本信息",
    "教育背景",
    "实习/工作经历",
    "项目经历",
    "科研经历",
    "技能清单",
    "获奖与荣誉",
    "社团/志愿者活动",
    "自我评价",
]

# ========== 岗位类别参考（LLM 可自由扩展） ==========
JOB_CATEGORY_EXAMPLES = [
    "后端开发",
    "前端开发",
    "数据分析/数据科学",
    "算法工程师",
    "产品经理",
    "测试开发",
    "运维/DevOps",
    "人工智能/机器学习",
    "GIS开发/空间数据分析",
    "项目管理",
]

# ========== STAR 法则模板 ==========
STAR_TEMPLATE = {
    "Situation": "项目背景与面临的问题",
    "Task": "你的具体任务和目标",
    "Action": "你采取的关键行动和方法",
    "Result": "取得的量化成果和影响",
}

# ========== 优化策略类型 ==========
OPTIMIZATION_STRATEGIES = [
    "keyword_alignment",       # 关键词对齐：确保简历包含 JD 中的核心关键词
    "star_rewrite",            # STAR 重写：用 STAR 法则优化经历描述
    "quantification",          # 量化增强：将模糊描述转为数据驱动的表述
    "structure_optimization",  # 结构优化：调整简历模块顺序和篇幅分配
    "highlight_core",          # 核心突出：根据目标岗位突出最相关的能力
    "gap_filling",             # 缺口填补：识别缺失经历并建议补充方向
]
