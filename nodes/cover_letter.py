# nodes/cover_letter.py
"""
Node 4: Cover Letter Generator
Generates tailored, professional cover letters per job using LLM.
"""

from typing import List
from loguru import logger

from config.settings import CANDIDATE
from config.state import AgentState, JobListing, CoverLetter, ResumeVersion
from utils.llm import call_llm


# ─────────────────────────────────────────────
# 📝 COVER LETTER PROMPT
# ─────────────────────────────────────────────

COVER_LETTER_SYSTEM_PROMPT = """
You are an expert career coach and professional writer specializing in tech/AI job applications.
Write compelling, concise cover letters that:
- Are 200-280 words (never longer)
- Sound human, not AI-generated
- Lead with specific value, not "I am applying for..."
- Reference the company's actual product/mission
- Highlight 2-3 most relevant projects with metrics
- End with a clear, confident call to action
- Mention availability date naturally
Avoid: generic phrases, excessive praise, "I believe", "I am passionate about"
"""

COVER_LETTER_TEMPLATE = """
Write a cover letter for this application:

CANDIDATE: {name}
EMAIL: {email}
LINKEDIN: {linkedin}
GITHUB: {github}
AVAILABLE FROM: May 16, 2025

JOB: {job_title}
COMPANY: {company}
WORK MODE: {work_mode}
LOCATION: {location}

JOB DESCRIPTION SUMMARY:
{jd_summary}

KEY REQUIRED SKILLS (to highlight naturally):
{required_skills}

CANDIDATE'S STRONGEST RELEVANT PROJECTS:
{top_projects}

CANDIDATE'S RELEVANT SKILLS:
{relevant_skills}

TONE: Professional, confident, concise. No fluff.
FORMAT: 3 paragraphs max. Opening → Value/Projects → Closing CTA.
No "Dear Hiring Manager" intro - start with the hook directly.

Write the cover letter:
"""


# ─────────────────────────────────────────────
# 🔧 HELPERS
# ─────────────────────────────────────────────

def _get_top_projects(job: JobListing, resume: dict) -> str:
    """Select 2-3 most relevant projects based on job type"""
    projects = resume.get("projects", [])
    desc_lower = (job.description or "").lower()

    # Score projects by relevance to this job
    scored = []
    for p in projects:
        score = 0
        tech_text = " ".join(p.get("tech", [])).lower()
        proj_desc = p.get("description", "").lower()

        for req_skill in job.required_skills:
            if req_skill.lower() in tech_text or req_skill.lower() in proj_desc:
                score += 2

        # Bonus for agentic/genai specific projects
        if any(kw in tech_text for kw in ["langgraph", "agent", "rag", "langchain"]):
            score += 3

        scored.append((score, p))

    scored.sort(key=lambda x: x[0], reverse=True)
    top = scored[:2]

    result = []
    for _, p in top:
        metrics = " | ".join(p.get("metrics", [])[:2])
        result.append(f"• {p['name']}: {p['description'][:120]}... [{metrics}]")

    return "\n".join(result)


def _get_relevant_skills(job: JobListing, resume: dict) -> str:
    """Get flat list of candidate skills relevant to this job"""
    all_candidate = []
    for skills in resume.get("technical_skills", {}).values():
        all_candidate.extend(skills)

    relevant = [
        s for s in all_candidate
        if any(req.lower() in s.lower() for req in job.required_skills)
    ][:12]

    if not relevant:
        relevant = all_candidate[:12]

    return ", ".join(relevant)


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def cover_letter_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 4: Generate tailored cover letters for selected jobs
    """
    logger.info("=" * 60)
    logger.info("✉️  NODE 4: COVER LETTER GENERATION STARTED")

    selected_jobs: List[JobListing] = state.get("selected_jobs", [])
    resume_versions: List[ResumeVersion] = state.get("resume_versions", [])
    cover_letters: List[CoverLetter] = []

    # Map resume versions by job_id
    resume_map = {rv.job_id: rv for rv in resume_versions}

    for job in selected_jobs:
        logger.info(f"Writing cover letter for: {job.title} @ {job.company}")

        try:
            resume_version = resume_map.get(job.job_id)
            resume_content = resume_version.resume_content if resume_version else {}

            top_projects = _get_top_projects(job, resume_content)
            relevant_skills = _get_relevant_skills(job, resume_content)

            prompt = COVER_LETTER_TEMPLATE.format(
                name=CANDIDATE["name"],
                email=CANDIDATE["email"],
                linkedin=CANDIDATE["linkedin"],
                github=CANDIDATE["github"],
                job_title=job.title,
                company=job.company,
                work_mode=job.work_mode,
                location=job.location,
                jd_summary=job.description[:800] if job.description else f"{job.title} role",
                required_skills=", ".join(job.required_skills[:10]),
                top_projects=top_projects,
                relevant_skills=relevant_skills,
            )

            content = call_llm(prompt, system=COVER_LETTER_SYSTEM_PROMPT)
            word_count = len(content.split())

            cl = CoverLetter(
                job_id=job.job_id,
                content=content,
                word_count=word_count,
            )
            cover_letters.append(cl)
            logger.info(f"✅ Cover letter: {word_count} words | {job.title} @ {job.company}")

        except Exception as e:
            logger.error(f"Cover letter failed for {job.title}: {e}")
            state.setdefault("errors", []).append(f"CoverLetter: {job.job_id} - {e}")

    state["cover_letters"] = cover_letters
    logger.info(f"✅ Generated {len(cover_letters)} cover letters")
    return state
