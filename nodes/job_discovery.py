# nodes/job_discovery.py
"""
Node 1: Job Discovery
Scrapes multiple free job sources and filters for eligible roles.
Sources: Internshala, Indeed, Wellfound, LinkedIn
"""

import hashlib
import time
import random
from datetime import datetime, timedelta
from typing import List, Dict, Any

import requests
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from loguru import logger

from config.settings import (
    SEARCH_QUERIES, JOB_MAX_AGE_DAYS, BLACKLIST_KEYWORDS,
    CANDIDATE, SCRAPE_SOURCES
)
from config.state import AgentState, JobListing


# ─────────────────────────────────────────────
# 🔧 SCRAPER UTILITIES
# ─────────────────────────────────────────────

ua = UserAgent()

def _headers() -> Dict:
    return {
        "User-Agent": ua.random,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

def _safe_get(url: str, retries: int = 3) -> requests.Response | None:
    for attempt in range(retries):
        try:
            resp = requests.get(url, headers=_headers(), timeout=15)
            if resp.status_code == 200:
                return resp
        except Exception as e:
            logger.warning(f"Request failed ({attempt+1}/{retries}): {e}")
        time.sleep(random.uniform(1.5, 3.5))
    return None

def _job_id(title: str, company: str) -> str:
    return hashlib.md5(f"{title}{company}".encode()).hexdigest()[:10]

def _is_blacklisted(text: str) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in BLACKLIST_KEYWORDS)

def _within_days(date_str: str, days: int = JOB_MAX_AGE_DAYS) -> bool:
    """Check if a date string is within N days. Returns True if unsure."""
    if not date_str:
        return True
    try:
        # Handle relative strings like "2 days ago", "1 week ago"
        if "hour" in date_str or "minute" in date_str or "second" in date_str:
            return True
        if "day" in date_str:
            n = int("".join(filter(str.isdigit, date_str))) if any(c.isdigit() for c in date_str) else 1
            return n <= days
        if "week" in date_str:
            n = int("".join(filter(str.isdigit, date_str))) if any(c.isdigit() for c in date_str) else 1
            return n * 7 <= days
        if "month" in date_str:
            return False
        # Try parsing absolute date
        for fmt in ["%Y-%m-%d", "%d %b %Y", "%B %d, %Y"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                return (datetime.now() - dt).days <= days
            except:
                continue
    except Exception:
        pass
    return True


# ─────────────────────────────────────────────
# 🌐 SOURCE 1: INTERNSHALA
# ─────────────────────────────────────────────

def scrape_internshala(query: str) -> List[Dict]:
    """Scrape Internshala for internships - great for Indian freshers"""
    jobs = []
    search_term = query.replace(" ", "-").lower()
    url = f"https://internshala.com/internships/{search_term}-internship/"

    resp = _safe_get(url)
    if not resp:
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    listings = soup.find_all("div", class_="individual_internship")

    for listing in listings[:10]:
        try:
            title = listing.find("h3", class_="job-internship-name")
            company = listing.find("p", class_="company-name")
            location = listing.find("div", id=lambda x: x and "location_names" in x)
            duration = listing.find("div", id=lambda x: x and "duration" in x)
            stipend = listing.find("span", class_="stipend")
            link_tag = listing.find("a", class_="view_detail_button")
            posted = listing.find("div", class_="status-inactive")

            title_text = title.get_text(strip=True) if title else "ML/AI Intern"
            company_text = company.get_text(strip=True) if company else "Unknown"
            loc_text = location.get_text(strip=True) if location else "India"
            link = "https://internshala.com" + link_tag["href"] if link_tag else url

            if _is_blacklisted(title_text):
                continue

            jobs.append({
                "job_id": _job_id(title_text, company_text),
                "title": title_text,
                "company": company_text,
                "location": loc_text,
                "work_mode": "Remote" if "remote" in loc_text.lower() else "Onsite",
                "job_url": link,
                "description": f"{title_text} at {company_text}. Duration: {duration.get_text(strip=True) if duration else 'N/A'}. Stipend: {stipend.get_text(strip=True) if stipend else 'N/A'}",
                "required_skills": [],
                "preferred_skills": [],
                "posted_date": posted.get_text(strip=True) if posted else "",
                "experience_required": "Fresher / Intern",
                "salary_range": stipend.get_text(strip=True) if stipend else None,
                "source": "internshala",
                "joining_date_flexible": True,
            })
        except Exception as e:
            logger.debug(f"Internshala parse error: {e}")
            continue

    logger.info(f"Internshala: found {len(jobs)} jobs for '{query}'")
    return jobs


# ─────────────────────────────────────────────
# 🌐 SOURCE 2: INDEED (via public search)
# ─────────────────────────────────────────────

def scrape_indeed(query: str, location: str = "India") -> List[Dict]:
    """Scrape Indeed job listings"""
    jobs = []
    q = query.replace(" ", "+")
    loc = location.replace(" ", "+")
    url = f"https://www.indeed.com/jobs?q={q}&l={loc}&fromage={JOB_MAX_AGE_DAYS}&explvl=entry_level"

    resp = _safe_get(url)
    if not resp:
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("div", class_=lambda x: x and "job_seen_beacon" in x)

    for card in cards[:10]:
        try:
            title = card.find("h2", class_=lambda x: x and "jobTitle" in x)
            company = card.find("span", {"data-testid": "company-name"})
            location_el = card.find("div", {"data-testid": "text-location"})
            date_el = card.find("span", {"data-testid": "myJobsStateDate"})
            link_el = card.find("a", class_=lambda x: x and "jcs-JobTitle" in x)

            title_text = title.get_text(strip=True) if title else query
            company_text = company.get_text(strip=True) if company else "Unknown"
            loc_text = location_el.get_text(strip=True) if location_el else location
            date_text = date_el.get_text(strip=True) if date_el else ""
            href = link_el["href"] if link_el else ""
            link = f"https://www.indeed.com{href}" if href.startswith("/") else href

            if _is_blacklisted(title_text):
                continue
            if not _within_days(date_text):
                continue

            jobs.append({
                "job_id": _job_id(title_text, company_text),
                "title": title_text,
                "company": company_text,
                "location": loc_text,
                "work_mode": "Remote" if "remote" in loc_text.lower() else "Onsite",
                "job_url": link,
                "description": f"{title_text} at {company_text}. Location: {loc_text}",
                "required_skills": [],
                "preferred_skills": [],
                "posted_date": date_text,
                "experience_required": "Entry Level",
                "salary_range": None,
                "source": "indeed",
                "joining_date_flexible": True,
            })
        except Exception as e:
            logger.debug(f"Indeed parse error: {e}")
            continue

    logger.info(f"Indeed: found {len(jobs)} jobs for '{query}'")
    return jobs


# ─────────────────────────────────────────────
# 🌐 SOURCE 3: WELLFOUND / ANGELLIST
# ─────────────────────────────────────────────

def scrape_wellfound(query: str) -> List[Dict]:
    """Scrape Wellfound (AngelList) - great for AI startups"""
    jobs = []
    search = query.replace(" ", "%20")
    url = f"https://wellfound.com/jobs?q={search}&role=engineer&type=full_time%2Cinternship"

    resp = _safe_get(url)
    if not resp:
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    job_cards = soup.find_all("div", attrs={"data-test": "StartupResult"})

    for card in job_cards[:8]:
        try:
            title_el = card.find("span", class_=lambda x: x and "title" in str(x).lower())
            company_el = card.find("h2")
            loc_el = card.find("span", class_=lambda x: x and "location" in str(x).lower())
            link_el = card.find("a", href=True)

            title_text = title_el.get_text(strip=True) if title_el else query
            company_text = company_el.get_text(strip=True) if company_el else "AI Startup"
            loc_text = loc_el.get_text(strip=True) if loc_el else "Remote"
            link = "https://wellfound.com" + link_el["href"] if link_el else url

            if _is_blacklisted(title_text):
                continue

            jobs.append({
                "job_id": _job_id(title_text, company_text),
                "title": title_text,
                "company": company_text,
                "location": loc_text,
                "work_mode": "Remote" if "remote" in loc_text.lower() else "Hybrid",
                "job_url": link,
                "description": f"{title_text} at {company_text}",
                "required_skills": [],
                "preferred_skills": [],
                "posted_date": "",
                "experience_required": "Entry Level / Intern",
                "salary_range": None,
                "source": "wellfound",
                "joining_date_flexible": True,
            })
        except Exception as e:
            logger.debug(f"Wellfound parse error: {e}")
            continue

    logger.info(f"Wellfound: found {len(jobs)} jobs for '{query}'")
    return jobs


# ─────────────────────────────────────────────
# 🌐 SOURCE 4: LINKEDIN (public job search)
# ─────────────────────────────────────────────

def scrape_linkedin(query: str, location: str = "India") -> List[Dict]:
    """
    Scrape LinkedIn public job listings (no login required).
    Uses LinkedIn's public jobs API endpoint.
    """
    jobs = []

    # LinkedIn public jobs search URL (no auth needed)
    search_query = query.replace(" ", "%20")
    location_query = location.replace(" ", "%20")

    # f=PP filters for entry level, tpr=r604800 = posted last 7 days
    url = (
        f"https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        f"?keywords={search_query}"
        f"&location={location_query}"
        f"&f_E=1%2C2"          # Experience: Internship + Entry level
        f"&f_TPR=r604800"      # Posted last 7 days (604800 seconds)
        f"&f_WT=2%2C1%2C3"     # Work type: Remote + Onsite + Hybrid
        f"&start=0"
    )

    headers = {
        "User-Agent": ua.random,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "en-US,en;q=0.9",
        "Referer": "https://www.linkedin.com/jobs/search/",
        "X-Requested-With": "XMLHttpRequest",
    }

    try:
        resp = requests.get(url, headers=headers, timeout=15)
        if resp.status_code != 200:
            logger.warning(f"LinkedIn returned {resp.status_code}")
            # Try fallback URL format
            return _scrape_linkedin_fallback(query, location)
    except Exception as e:
        logger.warning(f"LinkedIn request failed: {e}")
        return _scrape_linkedin_fallback(query, location)

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("div", class_="base-card")

    if not cards:
        # Try alternate card class
        cards = soup.find_all("li", class_=lambda x: x and "result-card" in str(x))

    for card in cards[:10]:
        try:
            title_el = card.find("h3", class_=lambda x: x and "base-search-card__title" in str(x))
            company_el = card.find("h4", class_=lambda x: x and "base-search-card__subtitle" in str(x))
            location_el = card.find("span", class_=lambda x: x and "job-search-card__location" in str(x))
            date_el = card.find("time")
            link_el = card.find("a", class_=lambda x: x and "base-card__full-link" in str(x))

            title_text = title_el.get_text(strip=True) if title_el else query
            company_text = company_el.get_text(strip=True) if company_el else "Unknown"
            loc_text = location_el.get_text(strip=True) if location_el else location
            date_text = date_el.get("datetime", "") if date_el else ""
            link = link_el["href"] if link_el else ""

            # Clean LinkedIn tracking params from URL
            if "?" in link:
                link = link.split("?")[0]

            if _is_blacklisted(title_text):
                continue
            if not _within_days(date_text):
                continue
            if not link:
                continue

            # Detect work mode from location text
            loc_lower = loc_text.lower()
            if "remote" in loc_lower:
                work_mode = "Remote"
            elif "hybrid" in loc_lower:
                work_mode = "Hybrid"
            else:
                work_mode = "Onsite"

            jobs.append({
                "job_id": _job_id(title_text, company_text),
                "title": title_text,
                "company": company_text,
                "location": loc_text,
                "work_mode": work_mode,
                "job_url": link,
                "description": f"{title_text} at {company_text}. Location: {loc_text}",
                "required_skills": [],
                "preferred_skills": [],
                "posted_date": date_text,
                "experience_required": "Entry Level / Intern",
                "salary_range": None,
                "source": "linkedin",
                "joining_date_flexible": True,
            })

        except Exception as e:
            logger.debug(f"LinkedIn parse error: {e}")
            continue

    logger.info(f"LinkedIn: found {len(jobs)} jobs for '{query}'")
    return jobs


def _scrape_linkedin_fallback(query: str, location: str = "India") -> List[Dict]:
    """
    Fallback: scrape LinkedIn public jobs page directly
    """
    jobs = []
    search_query = query.replace(" ", "%20")
    location_query = location.replace(" ", "%20")

    url = (
        f"https://www.linkedin.com/jobs/search/"
        f"?keywords={search_query}"
        f"&location={location_query}"
        f"&f_E=1%2C2"
        f"&f_TPR=r604800"
        f"&position=1&pageNum=0"
    )

    resp = _safe_get(url)
    if not resp:
        return jobs

    soup = BeautifulSoup(resp.text, "html.parser")
    cards = soup.find_all("div", class_="base-card")

    for card in cards[:10]:
        try:
            title_el = card.find("h3")
            company_el = card.find("h4")
            loc_el = card.find("span", class_=lambda x: x and "location" in str(x).lower())
            link_el = card.find("a", href=True)
            date_el = card.find("time")

            title_text = title_el.get_text(strip=True) if title_el else query
            company_text = company_el.get_text(strip=True) if company_el else "Unknown"
            loc_text = loc_el.get_text(strip=True) if loc_el else location
            link = link_el["href"].split("?")[0] if link_el else ""
            date_text = date_el.get("datetime", "") if date_el else ""

            if _is_blacklisted(title_text) or not link:
                continue

            loc_lower = loc_text.lower()
            work_mode = "Remote" if "remote" in loc_lower else ("Hybrid" if "hybrid" in loc_lower else "Onsite")

            jobs.append({
                "job_id": _job_id(title_text, company_text),
                "title": title_text,
                "company": company_text,
                "location": loc_text,
                "work_mode": work_mode,
                "job_url": link,
                "description": f"{title_text} at {company_text}. Location: {loc_text}",
                "required_skills": [],
                "preferred_skills": [],
                "posted_date": date_text,
                "experience_required": "Entry Level / Intern",
                "salary_range": None,
                "source": "linkedin",
                "joining_date_flexible": True,
            })
        except Exception as e:
            logger.debug(f"LinkedIn fallback parse error: {e}")
            continue

    logger.info(f"LinkedIn fallback: found {len(jobs)} jobs for '{query}'")
    return jobs


# ─────────────────────────────────────────────
# 🔍 JD ENRICHMENT VIA LLM
# ─────────────────────────────────────────────

def enrich_job_description(job: Dict, llm_func) -> Dict:
    """
    Use LLM to extract structured skills from raw job description.
    Called after scraping to populate required_skills, preferred_skills.
    """
    if not job.get("description") or len(job["description"]) < 50:
        return job

    prompt = f"""
Extract structured information from this job description.
Return ONLY valid JSON with these keys:
- required_skills: list of strings
- preferred_skills: list of strings  
- experience_required: string
- joining_date_flexible: boolean (true if no strict joining date or flexible)

Job: {job['title']} at {job['company']}
Description: {job['description'][:2000]}

JSON only, no markdown:
"""
    try:
        response = llm_func(prompt)
        import json
        clean = response.strip().replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean)
        job["required_skills"] = parsed.get("required_skills", [])
        job["preferred_skills"] = parsed.get("preferred_skills", [])
        job["experience_required"] = parsed.get("experience_required", job.get("experience_required", ""))
        job["joining_date_flexible"] = parsed.get("joining_date_flexible", True)
    except Exception as e:
        logger.debug(f"JD enrichment failed: {e}")
    return job


# ─────────────────────────────────────────────
# 🔁 MAIN NODE FUNCTION
# ─────────────────────────────────────────────

def job_discovery_node(state: AgentState) -> AgentState:
    """
    LangGraph Node 1: Discover jobs from multiple sources
    Sources: Internshala + Indeed + Wellfound + LinkedIn
    """
    from utils.llm import call_llm
    logger.info("=" * 60)
    logger.info("🔍 NODE 1: JOB DISCOVERY STARTED")
    logger.info("Sources: Internshala | Indeed | Wellfound | LinkedIn")

    all_raw_jobs: List[Dict] = []
    seen_ids = set()

    queries = state.get("search_queries", SEARCH_QUERIES)

    for query in queries[:6]:  # Limit to avoid rate limiting
        logger.info(f"Searching: '{query}'")

        if SCRAPE_SOURCES.get("internshala"):
            for job in scrape_internshala(query):
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_raw_jobs.append(job)

        if SCRAPE_SOURCES.get("indeed"):
            for job in scrape_indeed(query):
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_raw_jobs.append(job)

        if SCRAPE_SOURCES.get("wellfound"):
            for job in scrape_wellfound(query):
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_raw_jobs.append(job)

        if SCRAPE_SOURCES.get("linkedin"):
            for job in scrape_linkedin(query):
                if job["job_id"] not in seen_ids:
                    seen_ids.add(job["job_id"])
                    all_raw_jobs.append(job)

        time.sleep(random.uniform(2, 4))  # Respectful crawling

    logger.info(f"Total raw jobs discovered: {len(all_raw_jobs)}")

    # Enrich with LLM skill extraction
    enriched = []
    for job in all_raw_jobs[:40]:  # Increased limit since we have more sources
        enriched.append(enrich_job_description(job, call_llm))

    # Convert to JobListing objects
    filtered = []
    for job in enriched:
        try:
            listing = JobListing(**job)
            filtered.append(listing)
        except Exception as e:
            logger.debug(f"Failed to parse job listing: {e}")

    logger.info(f"✅ Valid job listings: {len(filtered)}")

    state["raw_jobs"] = all_raw_jobs
    state["filtered_jobs"] = filtered
    return state
