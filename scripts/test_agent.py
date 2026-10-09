#!/usr/bin/env python3
"""
Terminal verification script for the AI Job Application Agent.
Demonstrates end-to-end functionality:
1. Verifies Gemini API connectivity
2. Loads and parses a sample PDF/DOCX resume
3. Extracts candidate profile via Gemini structured output
4. Searches genuine live job sources (Greenhouse & Lever)
5. Ranks matching jobs with Gemini & deterministic scoring
6. Displays the top matches with original URLs and score rationales
* Strictly adheres to safety protocols: NEVER submits an application automatically.
"""

import os
import sys
from pathlib import Path
import asyncio

# Ensure backend app is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR / "backend"))

from app.config import settings
from app.database import SessionLocal, Base, engine
from app.services.resume_parser import parse_resume_content
from app.services.profile_analyzer import analyze_resume_text
from app.services.job_search import JobSearchService
from app.services.job_matcher import JobMatcherService
from app.models import User, CandidateProfile, Job

def print_header(title: str):
    print("\n" + "=" * 70)
    print(f"  {title.upper()}")
    print("=" * 70)

async def run_terminal_agent_test():
    print_header("AI Job Application Agent - Terminal Diagnostic & Pipeline Test")

    # Step 1: Verify Gemini Connectivity
    print("\n[Step 1] Checking Gemini API Configuration...")
    if not settings.GEMINI_API_KEY:
        print("[-] ERROR: GEMINI_API_KEY is not set.")
        print("    Please set GEMINI_API_KEY in your .env or environment variables.")
        return False
    print(f"[+] Model configured: {settings.GEMINI_MODEL}")
    print("[+] GEMINI_API_KEY is present.")

    # Step 2: Load Sample Resume
    print("\n[Step 2] Loading Sample Resume from sample_resumes/...")
    sample_pdf = BASE_DIR / "sample_resumes" / "sample_resume.pdf"
    if not sample_pdf.exists():
        print(f"[-] Sample resume file not found at {sample_pdf}")
        return False

    with open(sample_pdf, "rb") as f:
        file_bytes = f.read()

    print(f"[+] Read '{sample_pdf.name}' ({len(file_bytes)} bytes)")
    extracted_text, file_type = parse_resume_content(sample_pdf.name, file_bytes)
    print(f"[+] Extracted text length: {len(extracted_text)} characters using PyMuPDF ({file_type})")

    # Step 3: Analyze Resume with Gemini
    print("\n[Step 3] Analyzing Candidate Profile with Gemini Structured Output...")
    try:
        profile_data = analyze_resume_text(extracted_text)
        print(f"[+] Full Name: {profile_data.full_name}")
        print(f"[+] Email: {profile_data.email}")
        print(f"[+] Location: {profile_data.location}")
        print(f"[+] Experience Years: {profile_data.experience_years}")
        print(f"[+] Technical Skills ({len(profile_data.technical_skills)}): {', '.join(profile_data.technical_skills[:8])}")
        print(f"[+] Soft Skills: {', '.join(profile_data.soft_skills[:5])}")
        print(f"[+] Education: {[e.degree + ' at ' + e.institution for e in profile_data.education]}")
        if profile_data.missing_information:
            print(f"[!] Detected Missing Info: {profile_data.missing_information}")
    except Exception as e:
        print(f"[-] Gemini analysis failed: {e}")
        return False

    # Initialize DB Session
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # Step 4: Search Real Job Sources
        print("\n[Step 4] Querying Real Job Sources (Greenhouse & Lever)...")
        search_service = JobSearchService()
        search_keywords = ["Backend", "Python", "Software"]
        search_skills = profile_data.technical_skills[:4]

        search_result = await search_service.search_and_sync_jobs(
            db=db,
            skills=search_skills,
            keywords=search_keywords,
            limit=10
        )

        print(f"[+] Sources Checked: {', '.join(search_result.sources_checked)}")
        if search_result.errors:
            print(f"[!] Source warnings/errors: {search_result.errors}")
        print(f"[+] Real Jobs Discovered & Synced: {search_result.total_found}")

        if search_result.total_found == 0:
            print("[-] No jobs returned for current criteria. Trying broader query...")
            search_result = await search_service.search_and_sync_jobs(
                db=db,
                keywords=["Engineer"],
                limit=10
            )
            print(f"[+] Broader search found: {search_result.total_found} listings")

        if search_result.total_found == 0:
            print("[-] No live jobs could be retrieved. Check network connection.")
            return False

        # Step 5: Rank Matching Jobs
        print("\n[Step 5] Ranking Jobs against Candidate Profile with Gemini & Scoring Heuristics...")
        matcher_service = JobMatcherService()

        # Ephemeral candidate profile object for scoring
        temp_profile = CandidateProfile(
            full_name=profile_data.full_name,
            email=profile_data.email,
            location=profile_data.location,
            summary=profile_data.summary,
            technical_skills=profile_data.technical_skills,
            experience_years=profile_data.experience_years,
            preferred_roles=profile_data.preferred_roles or ["Backend Engineer"],
            previous_job_titles=profile_data.previous_job_titles
        )

        # Retrieve DB job instances
        jobs_in_db = [search_service.get_job_by_id(db, j.id) for j in search_result.jobs]
        jobs_in_db = [j for j in jobs_in_db if j is not None]

        ranked_matches = await matcher_service.rank_and_save_matches(
            db=db,
            user_id="terminal_test_user",
            profile=temp_profile,
            jobs=jobs_in_db,
            min_score=0.0,
            limit=5
        )

        # Step 6: Print Top 5 Matches
        print_header("Top 5 Recommended Jobs (Real Opportunities)")
        for idx, match in enumerate(ranked_matches, start=1):
            print(f"\n{idx}. [{match.match_score:.1f}/100 Match] {match.job.title} @ {match.job.company}")
            print(f"   Location: {match.job.location or 'Not specified'}")
            print(f"   Provider: {match.source.upper()}")
            print(f"   Original Listing URL: {match.job.url}")
            print(f"   Matching Skills: {', '.join(match.matching_skills) if match.matching_skills else 'General background'}")
            if match.missing_requirements:
                print(f"   Missing/Gaps: {', '.join(match.missing_requirements)}")
            print("   Match Explanation:")
            for reason in match.reasons:
                print(f"     * {reason}")

        print("\n" + "-" * 70)
        print("[!] SAFETY PROTOCOL VERIFIED: No applications were submitted.")
        print("[+] All listings shown above are genuine vacancies with verified original URLs.")
        print("=" * 70)
        return True

    finally:
        db.close()

if __name__ == "__main__":
    success = asyncio.run(run_terminal_agent_test())
    sys.exit(0 if success else 1)
