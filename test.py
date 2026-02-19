# test.py

print("🚀 Starting tests...")

# ── Test 1: OpenAI ──────────────────────────
print("\n1. Testing OpenAI...")
try:
    from utils.llm import call_llm
    response = call_llm("say hello in one sentence")
    print(f"✅ OpenAI OK: {response}")
except Exception as e:
    print(f"❌ OpenAI Failed: {e}")

# ── Test 2: Telegram ────────────────────────
print("\n2. Testing Telegram...")
try:
    from utils.telegram_notifier import test_telegram
    test_telegram()
    print("✅ Telegram OK - check your phone!")
except Exception as e:
    print(f"❌ Telegram Failed: {e}")

# ── Test 3: Google Sheets ───────────────────
print("\n3. Testing Google Sheets...")
try:
    import gspread
    from google.oauth2.service_account import Credentials
    creds = Credentials.from_service_account_file(
        "credentials.json",
        scopes=["https://www.googleapis.com/auth/spreadsheets"]
    )
    client = gspread.authorize(creds)
    print("✅ Google Sheets OK")
except Exception as e:
    print(f"❌ Google Sheets Failed: {e}")

# ── Test 4: Notion ──────────────────────────
print("\n4. Testing Notion...")
try:
    import os
    from dotenv import load_dotenv
    load_dotenv()
    from notion_client import Client
    notion = Client(auth=os.getenv("NOTION_TOKEN"))
    db = notion.databases.retrieve(os.getenv("NOTION_DATABASE_ID"))
    print(f"✅ Notion OK: {db['title'][0]['plain_text']}")
except Exception as e:
    print(f"❌ Notion Failed: {e}")

# ── Test 5: Job Scraping ────────────────────
print("\n5. Testing Job Scraping...")
try:
    from nodes.job_discovery import scrape_internshala
    jobs = scrape_internshala("Machine Learning Intern")
    print(f"✅ Internshala OK: {len(jobs)} jobs found")
    for j in jobs[:2]:
        print(f"   - {j['title']} @ {j['company']}")
except Exception as e:
    print(f"❌ Scraping Failed: {e}")

# ── Test 6: LinkedIn ────────────────────────
print("\n6. Testing LinkedIn...")
try:
    from nodes.job_discovery import scrape_linkedin
    jobs = scrape_linkedin("Machine Learning Intern")
    print(f"✅ LinkedIn OK: {len(jobs)} jobs found")
    for j in jobs[:2]:
        print(f"   - {j['title']} @ {j['company']}")
except Exception as e:
    print(f"❌ LinkedIn Failed: {e}")

# ── Test 7: Resume Optimizer ────────────────
print("\n7. Testing Resume Optimizer...")
try:
    from nodes.resume_optimizer import BASE_RESUME
    print(f"✅ Resume OK")
    print(f"   Name: {BASE_RESUME['header']['name']}")
    print(f"   Projects: {len(BASE_RESUME['projects'])}")
    print(f"   Skills: {list(BASE_RESUME['technical_skills'].keys())}")
except Exception as e:
    print(f"❌ Resume Failed: {e}")

print("\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
print("✅ All tests complete!")
print("Run: python cli.py run")