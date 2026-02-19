# config/settings.py
"""
Central configuration for Job Hunter AI Agent
"""

import os
from datetime import date
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────
# 🔑 API KEYS (set in .env file)
# ─────────────────────────────────────────────
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")   # gpt-4o-mini (cheap) or gpt-4o (best)
GOOGLE_SHEETS_CREDS = os.getenv("GOOGLE_SHEETS_CREDS_PATH", "credentials.json")
GOOGLE_SHEET_ID = os.getenv("GOOGLE_SHEET_ID", "")
NOTION_TOKEN = os.getenv("NOTION_TOKEN", "")
NOTION_DATABASE_ID = os.getenv("NOTION_DATABASE_ID", "")

# LLM fallback: "openai" | "ollama-mistral" | "ollama-llama"
LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "mistral")

# ─────────────────────────────────────────────
# 👤 CANDIDATE PROFILE
# ─────────────────────────────────────────────
CANDIDATE = {
    "name": os.getenv("CANDIDATE_NAME", "Your Name"),
    "email": os.getenv("CANDIDATE_EMAIL", "your@email.com"),
    "phone": os.getenv("CANDIDATE_PHONE", "+91-XXXXXXXXXX"),
    "linkedin": os.getenv("CANDIDATE_LINKEDIN", "linkedin.com/in/yourprofile"),
    "github": os.getenv("CANDIDATE_GITHUB", "github.com/yourusername"),
    "portfolio": os.getenv("CANDIDATE_PORTFOLIO", ""),
    "location": os.getenv("CANDIDATE_LOCATION", "India"),
    "status": "Final-year student / Fresher",
    "available_from": date(2025, 5, 16),
    "experience_years": 0,
}

# ─────────────────────────────────────────────
# 🎯 TARGET ROLES & SEARCH QUERIES
# ─────────────────────────────────────────────
TARGET_ROLES = [
    "Machine Learning Engineer",
    "Deep Learning Engineer",
    "Generative AI Engineer",
    "LLM Engineer",
    "AI Agent Developer",
    "AI Research Intern",
    "ML Intern",
    "GenAI Intern",
    "AI/ML Intern",
    "NLP Engineer",
]

SEARCH_QUERIES = [
    "Machine Learning Intern",
    "GenAI Intern",
    "LLM Engineer fresher",
    "AI Agent Developer entry level",
    "Generative AI intern",
    "Deep Learning intern",
    "NLP engineer fresher",
    "AI Research intern",
    "MLOps intern",
    "LangChain developer fresher",
]

WORK_MODES = ["Remote", "Hybrid", "Onsite"]
EXPERIENCE_LEVELS = ["Internship", "Entry Level", "Fresher", "0-1 year"]

# ─────────────────────────────────────────────
# 🛠 CANDIDATE TECH STACK (used for scoring)
# ─────────────────────────────────────────────
CANDIDATE_SKILLS = {
    "languages": ["Python", "C++", "Java", "JavaScript", "HTML/CSS"],
    "frameworks": ["Flask", "Node.js", "React", "Streamlit", "PyTorch"],
    "ml_frameworks": ["PyTorch", "Hugging Face", "scikit-learn", "BERT", "LLaMA"],
    "genai": [
        "LangChain", "LangGraph", "RAG", "Text Embeddings",
        "Prompt Engineering", "LoRA", "QLoRA", "LLMs",
        "Fine-tuning", "FAISS", "Chroma", "Vector Databases",
        "OpenAI API", "GPT-4o", "GPT-4o-mini",
    ],
    "agentic": [
        "LangGraph", "LangChain", "Multi-Agent Systems",
        "Autonomous Agents", "Tool Calling", "Multi-step Reasoning",
        "Agent Orchestration", "State Machines", "6-node Pipeline",
    ],
    "mlops": [
        "DVC", "Dagster", "Astronomer", "Apache Airflow",
        "AWS", "S3", "EC2", "SageMaker", "Docker",
        "MLflow", "CI/CD Pipelines", "Model Versioning", "Data Pipelines",
    ],
    "scraping": [
        "BeautifulSoup", "Requests", "Selenium",
        "LinkedIn Scraping", "Indeed Scraping", "Web Scraping",
    ],
    "apis": [
        "Telegram Bot API", "Google Sheets API", "Notion API",
        "OpenAI API", "REST APIs",
    ],
    "databases": ["MySQL", "PostgreSQL", "MongoDB"],
    "data": ["Pandas", "NumPy", "Matplotlib", "Seaborn"],
    "tools": [
        "Git", "GitHub", "Linux", "LeetCode",
        "Groq Cloud", "Gradio", "Whisper", "gTTS",
        "Sentence Transformers",
    ],
}

# Flatten for matching
ALL_SKILLS = [s for group in CANDIDATE_SKILLS.values() for s in group]

# ─────────────────────────────────────────────
# ⚙️ AGENT SETTINGS
# ─────────────────────────────────────────────
MIN_RELEVANCE_SCORE = 60        # Minimum score to proceed (%)
MAX_JOBS_PER_RUN = 20           # Max jobs to process per agent run
JOB_MAX_AGE_DAYS = 7            # Only jobs posted within last 7 days
OUTPUT_DIR = "output"
RESUME_TEMPLATE_PATH = "config/resume_template.json"
TRACKER_CSV_PATH = "output/application_tracker.csv"

# ─────────────────────────────────────────────
# 🌐 SCRAPING TARGETS
# ─────────────────────────────────────────────
SCRAPE_SOURCES = {
    "linkedin": True,
    "indeed": True,
    "internshala": True,
    "wellfound": True,
    "unstop": True,
    "company_pages": True,
}

# Preferred company types (AI-first)
PREFERRED_COMPANY_KEYWORDS = [
    "AI", "ML", "GenAI", "LLM", "Generative", "Agentic",
    "NLP", "Computer Vision", "Deep Learning", "SaaS", "startup",
]

# Blacklist: skip these companies/role keywords
BLACKLIST_KEYWORDS = [
    "senior", "lead", "principal", "staff", "director",
    "5+ years", "7+ years", "10+ years", "3+ years",
    "2+ years mandatory",
]
