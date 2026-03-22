"""Prompt 模板定义：各 Agent 不同阶段的提示词模板"""


# ========== Resume Reading Agent Prompts ==========

RESUME_PARSE_PROMPT = """请分析以下简历内容，进行结构化解析和多维度能力评估。

## 简历原文
```
{resume_text}
```

## 输出要求
请严格按以下 JSON 格式输出分析结果：

```json
{{
    "name": "姓名",
    "phone": "电话",
    "email": "邮箱",
    "location": "所在地",
    "education": [
        {{
            "school": "学校名称",
            "degree": "学位",
            "major": "专业",
            "gpa": "GPA（如有）",
            "start_date": "入学时间",
            "end_date": "毕业时间",
            "highlights": ["奖学金", "排名等"]
        }}
    ],
    "internships": [
        {{
            "title": "职位名称",
            "organization": "公司名称",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "description": "原始描述",
            "key_points": ["要点1", "要点2"],
            "technologies": ["技术1", "技术2"]
        }}
    ],
    "projects": [
        {{
            "title": "项目名称",
            "organization": "所属机构",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "description": "原始描述",
            "key_points": ["要点1", "要点2"],
            "technologies": ["技术1", "技术2"]
        }}
    ],
    "research": [
        {{
            "title": "科研主题",
            "organization": "实验室/机构",
            "start_date": "开始时间",
            "end_date": "结束时间",
            "description": "描述",
            "key_points": ["要点"],
            "technologies": ["方法/工具"]
        }}
    ],
    "skills": [
        {{
            "category": "技能类别",
            "skills": ["技能1", "技能2"],
            "proficiency": "熟练程度"
        }}
    ],
    "awards": ["获奖1", "获奖2"],
    "activities": ["活动1", "活动2"],
    "self_evaluation": "自我评价原文",
    "skill_scores": [
        {{
            "dimension": "技术深度",
            "score": 7,
            "evidence": "评分依据（引用简历原文）",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "项目质量",
            "score": 6,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "科研能力",
            "score": 5,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "表达清晰度",
            "score": 6,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "学历背景",
            "score": 7,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "实习经验",
            "score": 5,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "软技能",
            "score": 6,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }},
        {{
            "dimension": "成果量化",
            "score": 4,
            "evidence": "评分依据",
            "suggestion": "提升建议"
        }}
    ],
    "overall_score": 5.8,
    "strengths": ["优势1", "优势2", "优势3"],
    "weaknesses": ["不足1", "不足2", "不足3"],
    "summary": "简历整体评价摘要（100字以内）"
}}
```

请直接输出 JSON，不要输出其他内容。"""


# ========== Job Requirement Agent Prompts ==========

JOB_CLASSIFICATION_PROMPT = """请分析以下多个岗位描述，将它们智能分类，并总结每个类别的核心需求。

## 岗位描述列表
{job_descriptions}

## 候选人简历概要（用于初步匹配度评估）
{resume_summary}

## 输出要求
请严格按以下 JSON 格式输出：

```json
{{
    "total_jobs": {total_jobs},
    "categories": [
        {{
            "category_name": "类别名称（如'后端开发'）",
            "job_count": 3,
            "representative_titles": ["岗位1", "岗位2"],
            "core_requirements": ["必须具备的核心技能/要求"],
            "preferred_requirements": ["加分项/优先考虑"],
            "common_responsibilities": ["共性职责描述"],
            "key_keywords": ["高频关键词"],
            "optimization_focus": ["针对该类别的简历优化重点方向"],
            "match_score": 0.65
        }}
    ],
    "common_trends": ["跨类别的共同行业趋势和雇主偏好"]
}}
```

## 注意事项
1. 类别数量根据实际岗位差异性决定（通常 2-5 个）
2. match_score 是基于候选人简历的初步匹配度评估（0-1）
3. optimization_focus 要针对候选人的具体情况提出优化建议方向
4. 请直接输出 JSON，不要输出其他内容。"""


JOB_MANUAL_INPUT_PROMPT = """我将逐个提供岗位描述信息。请帮我记录并分析。

当前是第 {job_index} 个岗位：

## 岗位信息
{job_text}

请提取以下结构化信息，以 JSON 格式返回：

```json
{{
    "title": "岗位名称",
    "company": "公司名称",
    "location": "工作地点",
    "salary": "薪资范围",
    "requirements": ["要求1", "要求2"],
    "responsibilities": ["职责1", "职责2"],
    "keywords": ["关键词1", "关键词2"]
}}
```

请直接输出 JSON，不要输出其他内容。"""


# ========== Resume Optimize Agent Prompts ==========

OPTIMIZE_INITIAL_PROMPT = """## 简历优化任务

### 目标岗位类别
**{category_name}**

### 该类别岗位的核心需求
{core_requirements}

### 加分项
{preferred_requirements}

### 高频关键词
{key_keywords}

### 建议优化方向
{optimization_focus}

### 候选人当前简历概要
{resume_summary}

### 候选人多维度能力评分
{skill_scores}

---

请执行以下步骤，为候选人针对 **{category_name}** 类别的岗位进行简历优化：

1. **差距分析（Gap Analysis）**
   - 列出候选人已具备的匹配技能
   - 列出候选人缺失的关键技能
   - 指出需要补充的经历方向
   - 计算当前匹配百分比

2. **分模块优化**
   对简历的每个模块（教育背景、实习经历、项目经历、技能清单等）：
   - 引用原始内容
   - 给出优化后的版本（使用 STAR 法则、量化数据、关键词对齐）
   - 说明修改理由和使用的策略

3. **整体建议**
   - 简历结构调整建议（模块顺序、篇幅分配）
   - 需要候选人补充的信息（具体提问）
   - 关键亮点总结

请用详细的中文回答，条理清晰地展示分析结果。如果某些经历需要更多细节来优化，请直接向用户提问。"""


OPTIMIZE_FOLLOWUP_PROMPT = """感谢你提供的补充信息：

{user_input}

请基于这些新信息，继续完善针对 **{category_name}** 类别的简历优化方案。特别关注：

1. 将新信息融入对应的简历模块
2. 使用 STAR 法则和量化数据优化描述
3. 确保与目标岗位的关键词对齐
4. 更新匹配度评估

如果还需要更多信息，请继续提问。"""


OPTIMIZE_FINAL_PROMPT = """请输出针对 **{category_name}** 类别的最终优化结果，严格按以下 JSON 格式：

```json
{{
    "gap_analysis": {{
        "matched_skills": ["已匹配技能"],
        "missing_skills": ["缺失技能"],
        "improvement_areas": ["建议提升领域"],
        "experience_gaps": ["经历缺口"],
        "match_percentage": 0.72
    }},
    "optimized_sections": [
        {{
            "section_name": "模块名称",
            "original_content": "原始内容",
            "optimized_content": "优化后内容",
            "change_rationale": "修改理由",
            "strategy_used": ["使用的策略"]
        }}
    ],
    "key_highlights": ["优化后的关键亮点"],
    "additional_suggestions": ["补充建议"],
    "overall_improvement": "整体提升总结（200字以内）"
}}
```

请直接输出 JSON，不要输出其他内容。"""
