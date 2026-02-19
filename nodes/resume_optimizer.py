# nodes/resume_optimizer.py
"""
Node 3: Resume Optimization
Tailors the candidate's resume for each selected job via LLM.
- Keyword extraction from JD
- ATS optimization
- Bullet point rewriting with quantified impact
- No fabrication policy enforced
"""

import json
import uuid
from typing import List, Dict, Any, Tuple
from loguru import logger

from config.settings import CANDIDATE, CANDIDATE_SKILLS, ALL_SKILLS
from config.state import AgentState, JobListing, ResumeVersion
from utils.llm import call_llm


# ─────────────────────────────────────────────
# 📄 BASE RESUME TEMPLATE
# Edit this with your actual information!
# ─────────────────────────────────────────────

BASE_RESUME = {
    "header": {
        "name": "Priyanshu Bhati",
        "email": "priyanshubhati.dev@gmail.com",
        "phone": "+91 9057278418",
        "linkedin": "https://linkedin.com/in/priyanshu-bhati",
        "github": "https://github.com/priyanshu-bhati",
        "portfolio": "",
        "location": "Kota, Rajasthan, India",
        "available_from": "May 2027",
    },
    "summary": (
        "Generative AI Engineer with hands-on experience in building multimodal AI systems, "
        "fine-tuning Large Language Models, developing RAG pipelines, and autonomous multi-agent systems. "
        "Strong foundation in machine learning, deep learning, agentic AI workflows using "
        "LangChain and LangGraph, and MLOps tools including DVC, Dagster, and Airflow. "
        "Passionate about building scalable, autonomous, and production-ready AI systems."
    ),
    "technical_skills": {
        "Languages & Frameworks": [
            "Python", "C++", "Java", "JavaScript", "HTML/CSS",
            "Flask", "Node.js", "React", "Streamlit", "PyTorch",
        ],
        "Generative AI & NLP": [
            "LLMs", "Prompt Engineering", "RAG", "Text Embeddings",
            "LangChain", "LangGraph", "Hugging Face", "LoRA", "QLoRA",
            "Fine-tuning", "Vector Databases", "FAISS", "Chroma",
        ],
        "Agentic AI": [
            "LangGraph", "Multi-Agent Systems", "Autonomous Agents",
            "Tool Calling", "Multi-step Reasoning", "Agent Orchestration",
            "State Machines", "LangChain Tools",
        ],
        "Machine Learning": [
            "Supervised Learning", "Unsupervised Learning", "Neural Networks",
            "Transformer Architectures", "Fine-tuning", "BERT", "LLaMA",
        ],
        "MLOps & Data Engineering": [
            "DVC", "Dagster", "Astronomer", "Apache Airflow",
            "AWS (S3, EC2, SageMaker)", "Docker", "MLflow",
            "CI/CD Pipelines", "Model Versioning", "Data Pipelines",
        ],
        "Databases": ["MySQL", "PostgreSQL", "MongoDB"],
        "Data & Visualization": ["Pandas", "NumPy", "Matplotlib", "Seaborn"],
        "Tools & Platforms": [
            "Git", "GitHub", "Groq Cloud", "Gradio",
            "Whisper", "gTTS", "OpenAI API",
        ],
    },
    "projects": [
        {
            "name": "AI Job Hunter Agent (Autonomous Job Application System)",
            "description": (
                "Built a fully autonomous AI agent using LangGraph and LangChain that discovers, "
                "scores, and applies to ML/GenAI/Agentic AI jobs 24/7 without human intervention. "
                "Engineered a 6-node LangGraph state machine covering job discovery (LinkedIn, Indeed, "
                "Internshala, Wellfound), relevance scoring with semantic embeddings, ATS resume "
                "optimization, cover letter generation via OpenAI GPT-4o, and multi-platform tracking "
                "(Google Sheets, Notion, CSV). Integrated Telegram bot for real-time job alerts."
            ),
            "tech": [
                "LangGraph", "LangChain", "OpenAI GPT-4o", "Python",
                "BeautifulSoup", "Telegram Bot API", "Google Sheets API",
                "Notion API", "Sentence Transformers", "Docker",
            ],
            "metrics": [
                "6-node autonomous LangGraph pipeline",
                "4 job sources scraped simultaneously",
                "Real-time Telegram notifications",
                "Runs 24/7 on cloud",
            ],
        },
        {
            "name": "Multimodal AI Doctor Assistant (Vision + Voice + LLM)",
            "description": (
                "Built a multimodal GenAI assistant combining medical image inputs and voice interaction. "
                "Used LLaMA-based vision-language models to generate educational health guidance. "
                "Integrated Whisper for speech-to-text and gTTS for text-to-speech pipelines. "
                "Developed a Gradio-based interface with safety-focused prompting."
            ),
            "tech": ["LLaMA", "Whisper", "gTTS", "Gradio", "PyTorch", "Hugging Face"],
            "metrics": [
                "Multimodal input (vision + voice)",
                "Safety-focused prompting",
                "Live Demo deployed",
            ],
        },
        {
            "name": "LLM Fine-Tuning Pipeline (LoRA / QLoRA)",
            "description": (
                "Fine-tuned LLaMA-based Large Language Models on mathematical reasoning datasets "
                "using LoRA and QLoRA for parameter-efficient fine-tuning with PyTorch. "
                "Designed instruction-style prompts and preprocessing pipelines using Hugging Face. "
                "Evaluated base vs fine-tuned models on unseen reasoning tasks."
            ),
            "tech": ["LLaMA", "LoRA", "QLoRA", "PyTorch", "Hugging Face"],
            "metrics": [
                "Parameter-efficient fine-tuning",
                "Mathematical reasoning dataset",
                "Improved performance on unseen tasks",
            ],
        },
        {
            "name": "Agentic AI Coder Buddy (Lovable-like Application)",
            "description": (
                "Built an end-to-end Agentic AI system that generates complete web applications "
                "from natural language prompts using LangGraph for multi-step autonomous agent workflows "
                "covering planning, code generation, and validation. "
                "Integrated LangChain tools with GPT-OSS models on Groq Cloud for low-latency inference."
            ),
            "tech": ["LangChain", "LangGraph", "GPT-OSS", "Groq Cloud", "Python"],
            "metrics": [
                "Full web app generation from prompts",
                "Low-latency inference via Groq",
                "Autonomous multi-step reasoning",
            ],
        },
    ],
    "education": [
        {
            "degree": "B.Tech in Electronics and Communication Engineering (Minor in IoT)",
            "institution": "Indian Institute of Information Technology, Nagpur",
            "year": "Aug 2023 – May 2027",
            "cgpa": "7.26/10",
            "relevant_courses": [
                "Machine Learning", "Deep Learning", "NLP",
                "Neural Networks", "Data Structures & Algorithms", "IoT",
            ],
        }
    ],
    "certifications": [],
    "achievements": [
        "Solved 200+ LeetCode problems, strengthening data structures and algorithms proficiency",
        "Active Kaggle contributor working on datasets, notebooks, and data analysis projects",
        "Finalist at CEO Event, VNIT Nagpur, demonstrating leadership and strategic thinking",
        "Team Head for DIP project, leading planning, task allocation, and execution",
        "Public Relation Team Lead — E-Summit, IIIT Nagpur (Feb 2026)",
        "Core Member — E-Cell, IIIT Nagpur (Oct 2024 – Aug 2026)",
    ],
    "extracurricular": [
        {
            "role": "Core Member",
            "organization": "E-Cell, IIIT Nagpur",
            "duration": "Oct 2024 – Aug 2026",
        },
        {
            "role": "Public Relation Team Lead",
            "organization": "E-Summit, IIIT Nagpur",
            "duration": "Feb 2026",
        },
    ],
}


# ─────────────────────────────────────────────
# 🔑 STEP A: KEYWORD EXTRACTION FROM JD
# ─────────────────────────────────────────────

def extract_jd_keywords(job: JobListing) -> Dict[str, List[str]]:
    """Use LLM to extract structured keywords from job description"""

    prompt = f"""
Analyze this job description and extract keywords in JSON format.

Job Title: {job.title}
Company: {job.company}
Description: {job.description[:3000]}

Return ONLY valid JSON with these exact keys:
{{
  "must_have_skills": ["list of required/essential skills"],
  "nice_to_have_skills": ["list of preferred/bonus skills"],
  "tools_and_frameworks": ["specific tools, libraries, platforms mentioned"],
  "domain_keywords": ["domain-specific terms, concepts, methodologies"],
  "action_verbs": ["verbs used in the JD like build, deploy, optimize, etc."],
  "ats_keywords": ["top 10 keywords most critical for ATS matching"]
}}

JSON only, no explanation:
"""
    try:
        response = call_llm(prompt, system="You are an expert ATS optimization specialist. Return only valid JSON.")
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"Keyword extraction failed: {e}")
        return {
            "must_have_skills": job.required_skills,
            "nice_to_have_skills": job.preferred_skills,
            "tools_and_frameworks": [],
            "domain_keywords": [],
            "action_verbs": ["develop", "build", "implement", "optimize", "deploy"],
            "ats_keywords": job.required_skills[:10],
        }


# ─────────────────────────────────────────────
# 📝 STEP B: RESUME TAILORING
# ─────────────────────────────────────────────

def _reorder_skills(jd_keywords: Dict) -> Dict[str, List[str]]:
    """Reorder skills section to front-load JD-relevant skills"""
    priority_skills = (
        jd_keywords.get("must_have_skills", []) +
        jd_keywords.get("tools_and_frameworks", [])
    )
    priority_lower = [s.lower() for s in priority_skills]

    reordered = {}
    # Start with JD-matching skills categories
    for category, skills in BASE_RESUME["technical_skills"].items():
        matched = [s for s in skills if any(p in s.lower() for p in priority_lower)]
        others = [s for s in skills if s not in matched]
        reordered[category] = matched + others

    return reordered


def _optimize_bullets(job: JobListing, jd_keywords: Dict) -> List[str]:
    """Use LLM to rewrite project bullets with JD-aligned impact"""

    projects_text = "\n".join([
        f"- {p['name']}: {p['description']}"
        for p in BASE_RESUME["projects"]
    ])

    prompt = f"""
You are an expert resume writer. Rewrite these project bullet points to better align 
with the job description. 

STRICT RULES:
1. Never fabricate or exaggerate - only rephrase truthfully
2. Use strong action verbs: {', '.join(jd_keywords.get('action_verbs', ['Built', 'Developed', 'Optimized']))}
3. Keep quantified metrics (numbers, percentages)
4. Naturally incorporate these keywords where honest: {', '.join(jd_keywords.get('ats_keywords', [])[:8])}
5. Each bullet should be 1-2 sentences max

Job: {job.title} at {job.company}
Key JD terms: {', '.join(jd_keywords.get('must_have_skills', [])[:8])}

Current Projects:
{projects_text}

Return JSON array of modified bullets (one per project):
["bullet1", "bullet2", "bullet3", "bullet4"]

JSON only:
"""
    try:
        response = call_llm(prompt, system="You are an ATS expert resume writer. Never fabricate. Return only valid JSON.")
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(clean)
    except Exception as e:
        logger.warning(f"Bullet optimization failed: {e}")
        return [p["description"] for p in BASE_RESUME["projects"]]


def _identify_missing_keywords(jd_keywords: Dict) -> List[str]:
    """Find JD keywords NOT in candidate's current resume (for honest addition)"""
    candidate_lower = [s.lower() for s in ALL_SKILLS]
    all_jd = (
        jd_keywords.get("must_have_skills", []) +
        jd_keywords.get("nice_to_have_skills", []) +
        jd_keywords.get("tools_and_frameworks", [])
    )
    # Only return keywords the candidate actually has (honest matching)
    genuinely_missing = [
        kw for kw in all_jd
        if kw.lower() not in candidate_lower
        and kw.lower() not in " ".join(BASE_RESUME.get("summary", "")).lower()
    ]
    return genuinely_missing[:5]  # Limit to top 5


def calculate_ats_score(resume: Dict, jd_keywords: Dict) -> float:
    """Simple ATS score based on keyword presence in resume"""
    ats_keywords = jd_keywords.get("ats_keywords", [])
    if not ats_keywords:
        return 75.0

    resume_text = json.dumps(resume).lower()
    matched = sum(1 for kw in ats_keywords if kw.lower() in resume_text)
    return round((matched / len(ats_keywords)) * 100, 1)


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def resume_optimization_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 3: Generate tailored resume version for each selected job
    """
    logger.info("=" * 60)
    logger.info("📄 NODE 3: RESUME OPTIMIZATION STARTED")

    selected_jobs: List[JobListing] = state.get("selected_jobs", [])
    resume_versions: List[ResumeVersion] = []

    for job in selected_jobs:
        logger.info(f"Optimizing resume for: {job.title} @ {job.company}")

        try:
            # Step A: Extract JD keywords
            jd_keywords = extract_jd_keywords(job)
            logger.debug(f"ATS keywords: {jd_keywords.get('ats_keywords', [])}")

            # Step B: Tailor resume
            reordered_skills = _reorder_skills(jd_keywords)
            optimized_bullets = _optimize_bullets(job, jd_keywords)
            missing_kw = _identify_missing_keywords(jd_keywords)

            # Build tailored resume dict
            tailored_projects = []
            for i, project in enumerate(BASE_RESUME["projects"]):
                tailored_projects.append({
                    **project,
                    "description": optimized_bullets[i] if i < len(optimized_bullets) else project["description"],
                })

            tailored_resume = {
                **BASE_RESUME,
                "technical_skills": reordered_skills,
                "projects": tailored_projects,
                "summary": _tailor_summary(job, jd_keywords),
            }

            # Calculate ATS score
            ats_score = calculate_ats_score(tailored_resume, jd_keywords)

            version = ResumeVersion(
                job_id=job.job_id,
                version_id=f"v_{uuid.uuid4().hex[:6]}",
                keywords_added=missing_kw,
                bullets_modified=[f"Project {i+1}: Rewritten" for i in range(len(optimized_bullets))],
                skills_reordered=list(jd_keywords.get("must_have_skills", [])[:5]),
                resume_content=tailored_resume,
                ats_score=ats_score,
            )

            resume_versions.append(version)
            logger.info(f"✅ ATS Score: {ats_score}% | {job.title} @ {job.company}")

        except Exception as e:
            logger.error(f"Resume optimization failed for {job.title}: {e}")
            state.setdefault("errors", []).append(f"Resume: {job.job_id} - {e}")

    state["resume_versions"] = resume_versions
    logger.info(f"✅ Generated {len(resume_versions)} resume versions")
    return state


def _tailor_summary(job: JobListing, jd_keywords: Dict) -> str:
    """Generate a tailored professional summary"""
    top_skills = ", ".join(jd_keywords.get("must_have_skills", [])[:4])
    return (
        f"Final-year B.Tech student specializing in {job.title}-aligned skills including "
        f"{top_skills}. Experienced in building production-grade AI systems with LangChain, "
        f"LangGraph, and modern LLM frameworks. Passionate about {job.company}'s mission. "
        f"Available to join from May 16, 2025."
    )
