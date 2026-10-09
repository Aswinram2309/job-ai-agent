import httpx
import pytest

def test_live_backend_e2e():
    base = "http://127.0.0.1:8000"
    client = httpx.Client(base_url=base, timeout=30.0)

    # 1. Register unique user
    import time
    unique_email = f"candidate_{int(time.time())}@example.com"
    reg = client.post("/api/auth/register", json={
        "email": unique_email,
        "password": "Password123!",
        "full_name": "Test Candidate"
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload text resume
    txt_content = b"""Test Candidate
Email: candidate@example.com
Location: Remote
Skills: Python, FastAPI, Docker, PostgreSQL, React
Experience: 4 years backend development
Education: B.S. in Computer Science
"""
    upload_resp = client.post(
        "/api/resumes/analyze",
        headers=headers,
        files={"file": ("resume.txt", txt_content, "text/plain")}
    )
    assert upload_resp.status_code == 200
    extracted = upload_resp.json()
    assert "extracted_profile" in extracted

    # 3. Search Jobs
    search_resp = client.post("/api/jobs/search", headers=headers, json={
        "keywords": ["Engineer"],
        "limit": 5
    })
    assert search_resp.status_code == 200
    jobs = search_resp.json()["jobs"]
    assert len(jobs) > 0

    first_job = jobs[0]
    job_id = first_job["id"]

    # 4. Match Jobs
    match_resp = client.post("/api/jobs/match", headers=headers, json={
        "job_ids": [job_id],
        "limit": 1
    })
    assert match_resp.status_code == 200
    matches = match_resp.json()["matches"]
    assert len(matches) > 0
    assert matches[0]["match_score"] >= 0

    # 5. Save Job
    save_resp = client.post(f"/api/jobs/{job_id}/save", headers=headers)
    assert save_resp.status_code == 200
    assert save_resp.json()["status"] == "saved"

    # 6. Approve Application
    appr_resp = client.post(f"/api/jobs/{job_id}/approve", headers=headers, json={
        "answers": {"work_auth": "Yes", "notice": "Immediate"},
        "confirmed": True
    })
    assert appr_resp.status_code == 200

    # 7. Get application
    apps_resp = client.get("/api/applications", headers=headers)
    assert apps_resp.status_code == 200
    apps = apps_resp.json()
    assert len(apps) > 0
    app_id = apps[0]["id"]

    # 8. Submit Application (Safe Review Mode: must not fake submission)
    sub_resp = client.post(f"/api/applications/{app_id}/submit", headers=headers)
    assert sub_resp.status_code == 200
    # Must be ready_to_apply with safe review guidance
    assert sub_resp.json()["status"] == "ready_to_apply"
    assert sub_resp.json()["submitted_at"] is None

    # 9. Mark Manually Applied
    man_resp = client.post(f"/api/applications/{app_id}/manual-apply", headers=headers, json={
        "notes": "Submitted via official portal link",
        "reference_id": "PORTAL-98765"
    })
    assert man_resp.status_code == 200
    assert man_resp.json()["status"] == "manually_applied"
    assert man_resp.json()["submission_reference"] == "PORTAL-98765"

    # 10. Dashboard Stats
    stats_resp = client.get("/api/dashboard/stats", headers=headers)
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["has_resume"] is True
    assert stats["applications_submitted"] >= 1
