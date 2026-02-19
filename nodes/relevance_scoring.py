# nodes/relevance_scoring.py
"""
Node 2: Job Relevance Scoring
Scores each job based on skill overlap, tech stack alignment, and eligibility.
Uses semantic embeddings + keyword matching.
"""

from typing import List, Dict
from loguru import logger

from config.settings import (
    CANDIDATE_SKILLS, ALL_SKILLS, MIN_RELEVANCE_SCORE,
    PREFERRED_COMPANY_KEYWORDS, BLACKLIST_KEYWORDS
)
from config.state import AgentState, JobListing


# ─────────────────────────────────────────────
# 📊 SCORING COMPONENTS
# ─────────────────────────────────────────────

def _skill_overlap_score(job: JobListing) -> float:
    """
    Component 1: What % of required job skills does the candidate have?
    Returns 0-40 points.
    """
    if not job.required_skills:
        return 20.0  # Default if no skills listed

    candidate_lower = [s.lower() for s in ALL_SKILLS]
    matched = sum(
        1 for skill in job.required_skills
        if skill.lower() in candidate_lower
    )
    overlap = matched / len(job.required_skills) if job.required_skills else 0
    return round(overlap * 40, 2)


def _experience_match_score(job: JobListing) -> float:
    """
    Component 2: Does the experience requirement match fresher?
    Returns 0-25 points.
    """
    exp_text = (job.experience_required or "").lower()
    description = (job.description or "").lower()
    combined = exp_text + " " + description

    if any(kw in combined for kw in ["intern", "fresher", "0-1", "entry", "graduate", "trainee"]):
        return 25.0
    if any(kw in combined for kw in ["1-2 year", "1+ year", "junior"]):
        return 18.0
    if any(kw in combined for kw in ["2+ year", "2-3 year"]):
        return 8.0
    if any(kw in combined for kw in ["3+", "4+", "5+", "senior", "lead"]):
        return 0.0
    return 15.0  # Ambiguous - give partial credit


def _tech_stack_score(job: JobListing) -> float:
    """
    Component 3: Alignment with ML/GenAI/Agentic stack.
    Returns 0-25 points.
    """
    priority_tech = [
        "langchain", "langgraph", "llm", "rag", "pytorch", "transformers",
        "huggingface", "openai", "generative", "agent", "vector", "fine-tun",
        "mistral", "llama", "gpt", "embedding", "langsmith"
    ]

    desc_lower = (job.description or "").lower()
    skill_lower = [s.lower() for s in job.required_skills + job.preferred_skills]
    all_text = desc_lower + " ".join(skill_lower)

    matches = sum(1 for tech in priority_tech if tech in all_text)
    score = min(matches * 3, 25)
    return float(score)


def _company_preference_score(job: JobListing) -> float:
    """
    Component 4: Is this an AI-first startup?
    Returns 0-10 points.
    """
    company_lower = job.company.lower()
    desc_lower = (job.description or "").lower()
    combined = company_lower + " " + desc_lower

    matches = sum(1 for kw in PREFERRED_COMPANY_KEYWORDS if kw.lower() in combined)
    return min(matches * 2, 10)


def _eligibility_score(job: JobListing) -> float:
    """
    Bonus: Remote work + joining flexibility.
    Returns 0-10 points.
    """
    score = 0.0
    if job.work_mode in ["Remote", "Hybrid"]:
        score += 5.0
    if job.joining_date_flexible:
        score += 5.0
    return score


def _is_disqualified(job: JobListing) -> bool:
    """Hard disqualification check"""
    combined = (
        (job.title or "") + " " +
        (job.description or "") + " " +
        (job.experience_required or "")
    ).lower()

    return any(kw.lower() in combined for kw in BLACKLIST_KEYWORDS)


# ─────────────────────────────────────────────
# 🔢 SEMANTIC SCORING (optional enhancement)
# ─────────────────────────────────────────────

def _semantic_similarity(job: JobListing, embeddings_model) -> float:
    """
    Compute semantic similarity between job description
    and candidate's skill profile using embeddings.
    Returns 0-10 bonus points.
    """
    try:
        candidate_profile = (
            "Machine learning engineer with expertise in: " +
            ", ".join(ALL_SKILLS[:30])
        )
        job_text = job.description[:500] if job.description else job.title

        emb_candidate = embeddings_model.embed_query(candidate_profile)
        emb_job = embeddings_model.embed_query(job_text)

        # Cosine similarity
        from sklearn.metrics.pairwise import cosine_similarity
        import numpy as np
        sim = cosine_similarity([emb_candidate], [emb_job])[0][0]
        return round(sim * 10, 2)
    except Exception as e:
        logger.debug(f"Semantic scoring failed: {e}")
        return 5.0  # Default bonus


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def relevance_scoring_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 2: Score all filtered jobs, select those ≥ MIN_RELEVANCE_SCORE
    """
    logger.info("=" * 60)
    logger.info("📊 NODE 2: RELEVANCE SCORING STARTED")

    jobs: List[JobListing] = state.get("filtered_jobs", [])

    # Try to load embeddings for semantic scoring
    embeddings_model = None
    try:
        from utils.llm import get_embeddings
        embeddings_model = get_embeddings()
        logger.info("Embeddings model loaded for semantic scoring")
    except Exception as e:
        logger.warning(f"Could not load embeddings, using keyword scoring only: {e}")

    scored_jobs = []

    for job in jobs:
        # Hard disqualification
        if _is_disqualified(job):
            logger.debug(f"DISQUALIFIED: {job.title} at {job.company}")
            continue

        # Calculate component scores
        s1 = _skill_overlap_score(job)      # 0-40
        s2 = _experience_match_score(job)   # 0-25
        s3 = _tech_stack_score(job)         # 0-25
        s4 = _company_preference_score(job) # 0-10

        base_score = s1 + s2 + s3 + s4      # 0-100

        # Optional semantic bonus
        semantic_bonus = 0.0
        if embeddings_model:
            semantic_bonus = _semantic_similarity(job, embeddings_model)

        final_score = min(base_score + semantic_bonus * 0.1, 100)
        job.relevance_score = round(final_score, 1)

        logger.info(
            f"Score {job.relevance_score:.1f}% | "
            f"[Skills:{s1:.0f} Exp:{s2:.0f} Tech:{s3:.0f} Co:{s4:.0f}] | "
            f"{job.title} @ {job.company}"
        )
        scored_jobs.append(job)

    # Sort by score descending
    scored_jobs.sort(key=lambda j: j.relevance_score, reverse=True)

    # Filter to qualifying jobs
    selected = [j for j in scored_jobs if j.relevance_score >= MIN_RELEVANCE_SCORE]

    logger.info(f"✅ Jobs scored: {len(scored_jobs)} | Qualifying (≥{MIN_RELEVANCE_SCORE}%): {len(selected)}")

    state["scored_jobs"] = scored_jobs
    state["selected_jobs"] = selected
    return state
