"""Pydantic 数据模型定义：简历结构、岗位分类、优化结果等"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, field_validator


# ========== 简历解析相关模型 ==========

class EducationInfo(BaseModel):
    """教育背景"""
    school: str = Field(default="", description="学校名称")
    degree: str = Field(default="", description="学位（本科/硕士/博士）")
    major: str = Field(default="", description="专业")
    gpa: Optional[str] = Field(default=None, description="GPA/绩点")
    start_date: str = Field(default="", description="入学时间")
    end_date: str = Field(default="", description="毕业时间")
    highlights: List[str] = Field(default_factory=list, description="亮点（奖学金、排名等）")


class ExperienceItem(BaseModel):
    """经历条目（实习/项目/科研通用）"""
    title: str = Field(default="", description="标题/职位名称")
    organization: str = Field(default="", description="公司/机构名称")
    start_date: str = Field(default="", description="开始时间")
    end_date: str = Field(default="", description="结束时间")
    description: str = Field(default="", description="原始描述文本")
    key_points: List[str] = Field(default_factory=list, description="核心要点列表")
    technologies: List[str] = Field(default_factory=list, description="涉及的技术/工具")


class SkillItem(BaseModel):
    """技能条目"""
    category: str = Field(default="", description="技能类别（编程语言/框架/工具等）")
    skills: List[str] = Field(default_factory=list, description="具体技能列表")
    proficiency: str = Field(default="", description="熟练程度描述")


class SkillScore(BaseModel):
    """单个维度的能力评分"""
    dimension: str = Field(..., description="评估维度名称")
    score: int = Field(..., ge=1, le=10, description="评分（1-10）")
    evidence: str = Field(default="", description="评分依据")
    suggestion: str = Field(default="", description="提升建议")


class ResumeProfile(BaseModel):
    """简历完整结构化数据（Resume Reading Agent 的输出）"""
    # 基本信息
    name: str = Field(default="", description="姓名")
    phone: str = Field(default="", description="电话")
    email: str = Field(default="", description="邮箱")
    location: str = Field(default="", description="所在地")

    # 教育背景
    education: List[EducationInfo] = Field(default_factory=list, description="教育经历")

    # 经历
    internships: List[ExperienceItem] = Field(default_factory=list, description="实习/工作经历")
    projects: List[ExperienceItem] = Field(default_factory=list, description="项目经历")
    research: List[ExperienceItem] = Field(default_factory=list, description="科研经历")

    # 技能
    skills: List[SkillItem] = Field(default_factory=list, description="技能清单")

    # 其他
    awards: List[str] = Field(default_factory=list, description="获奖与荣誉")
    activities: List[str] = Field(default_factory=list, description="社团/志愿活动")
    self_evaluation: str = Field(default="", description="自我评价")

    # 能力评分（LLM 评估）
    skill_scores: List[SkillScore] = Field(default_factory=list, description="多维能力评分")
    overall_score: float = Field(default=0.0, description="综合评分（加权平均）")
    strengths: List[str] = Field(default_factory=list, description="核心优势")
    weaknesses: List[str] = Field(default_factory=list, description="待提升领域")
    summary: str = Field(default="", description="简历整体评价摘要")


# ========== 岗位分析相关模型 ==========

class JobDescription(BaseModel):
    """单个岗位描述"""
    title: str = Field(default="", description="岗位名称")
    company: str = Field(default="", description="公司名称")
    location: str = Field(default="", description="工作地点")
    salary: str = Field(default="", description="薪资范围")
    requirements: List[str] = Field(default_factory=list, description="岗位要求列表")
    responsibilities: List[str] = Field(default_factory=list, description="工作职责列表")
    keywords: List[str] = Field(default_factory=list, description="核心关键词")
    raw_text: str = Field(default="", description="原始 JD 文本")


class JobCategory(BaseModel):
    """岗位类别（聚类后的结果）"""
    category_name: str = Field(..., description="岗位类别名称，如'后端开发'")
    job_count: int = Field(default=0, description="该类别包含的岗位数量")
    representative_titles: List[str] = Field(default_factory=list, description="代表性岗位名称")
    core_requirements: List[str] = Field(default_factory=list, description="核心共性技能要求")
    preferred_requirements: List[str] = Field(default_factory=list, description="加分项/优先要求")
    common_responsibilities: List[str] = Field(default_factory=list, description="共性职责描述")
    key_keywords: List[str] = Field(default_factory=list, description="高频关键词")
    optimization_focus: List[str] = Field(default_factory=list, description="建议的简历优化重点方向")
    match_score: float = Field(default=0.0, description="与当前简历的初始匹配度 0-1")


class JobAnalysisResult(BaseModel):
    """Job Requirement Agent 的完整输出"""
    total_jobs: int = Field(default=0, description="总共分析的岗位数量")
    categories: List[JobCategory] = Field(default_factory=list, description="岗位类别列表")
    common_trends: List[str] = Field(default_factory=list, description="跨类别的共同趋势")
    raw_jobs: List[JobDescription] = Field(default_factory=list, description="原始岗位数据")


# ========== 优化结果相关模型 ==========

class OptimizedSection(BaseModel):
    """单个简历模块的优化结果"""
    section_name: str = Field(..., description="模块名称（如'项目经历'）")
    original_content: str = Field(default="", description="原始内容")
    optimized_content: str = Field(default="", description="优化后内容")
    change_rationale: str = Field(default="", description="修改理由")
    strategy_used: List[str] = Field(default_factory=list, description="使用的优化策略")


class GapAnalysis(BaseModel):
    """能力-需求差距分析"""
    matched_skills: List[str] = Field(default_factory=list, description="已匹配的技能")
    missing_skills: List[str] = Field(default_factory=list, description="缺失的技能")
    improvement_areas: List[str] = Field(default_factory=list, description="建议提升的领域")
    experience_gaps: List[str] = Field(default_factory=list, description="经历缺口（建议补充）")
    match_percentage: float = Field(default=0.0, description="匹配百分比(0-1)")

    @field_validator("match_percentage", mode="before")
    @classmethod
    def normalize_percentage(cls, v):
        """LLM 可能返回 72 或 0.72，统一归一化到 0-1 范围"""
        if isinstance(v, (int, float)) and v > 1:
            return v / 100.0
        return v


class CategoryOptimizationResult(BaseModel):
    """单个岗位类别的完整优化结果"""
    job_category: JobCategory = Field(..., description="目标岗位类别")
    gap_analysis: GapAnalysis = Field(default_factory=GapAnalysis, description="差距分析")
    optimized_sections: List[OptimizedSection] = Field(default_factory=list, description="各模块优化结果")
    key_highlights: List[str] = Field(default_factory=list, description="优化后的关键亮点")
    additional_suggestions: List[str] = Field(default_factory=list, description="补充建议")
    overall_improvement: str = Field(default="", description="整体提升总结")
    conversation_history: List[Dict[str, str]] = Field(default_factory=list, description="优化对话记录")


class ResumeOptimizationPlan(BaseModel):
    """顶层聚合结果：包含所有类别的优化方案"""
    original_resume_path: str = Field(default="", description="原始简历路径")
    resume_profile: Optional[ResumeProfile] = Field(default=None, description="简历分析结果")
    job_analysis: Optional[JobAnalysisResult] = Field(default=None, description="岗位分析结果")
    optimizations: List[CategoryOptimizationResult] = Field(default_factory=list, description="各类别优化结果")
    general_suggestions: List[str] = Field(default_factory=list, description="通用优化建议")
    generated_at: datetime = Field(default_factory=datetime.now, description="生成时间")

    class Config:
        json_encoders = {datetime: lambda v: v.isoformat()}
