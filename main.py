import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict

from database import db, create_document, get_documents
from schemas import Student, Resource, Assessment, AssessmentResponse, MoodEntry, ContactMessage, TeamMember

app = FastAPI(title="IT Student Mental Health API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "IT Student Mental Health API running"}

@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
            response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
            response["connection_status"] = "Connected"
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️ Connected but Error: {str(e)[:80]}"
        else:
            response["database"] = "⚠️ Available but not initialized"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:80]}"
    return response

# -------- Seed data (idempotent reads) --------
ASSESSMENTS: Dict[str, Assessment] = {
    "phq9": Assessment(
        key="phq9",
        title="PHQ-9 Depression Questionnaire",
        description="Screens for the presence and severity of depression over the last two weeks."
    ),
    "gad7": Assessment(
        key="gad7",
        title="GAD-7 Anxiety Questionnaire",
        description="Measures severity of generalized anxiety over the last two weeks."
    )
}

PHQ9_WEIGHTS = [0,1,2,3]
GAD7_WEIGHTS = [0,1,2,3]

PHQ9_SEVERITY = [
    (0, 4, "Minimal"),
    (5, 9, "Mild"),
    (10, 14, "Moderate"),
    (15, 19, "Moderately Severe"),
    (20, 27, "Severe"),
]

GAD7_SEVERITY = [
    (0, 4, "Minimal"),
    (5, 9, "Mild"),
    (10, 14, "Moderate"),
    (15, 21, "Severe"),
]

def severity_from_score(score: int, bands):
    for lo, hi, label in bands:
        if lo <= score <= hi:
            return label
    return "Unknown"

# -------- API: Assessments --------
@app.get("/api/assessments", response_model=List[Assessment])
def list_assessments():
    return list(ASSESSMENTS.values())

@app.post("/api/assessments/submit", response_model=AssessmentResponse)
def submit_assessment(payload: AssessmentResponse):
    key = payload.assessment_key
    if key not in ASSESSMENTS:
        raise HTTPException(status_code=400, detail="Unknown assessment key")

    # validate answers list length (standard: PHQ-9 has 9 items, GAD-7 has 7)
    required_len = 9 if key == "phq9" else 7
    if len(payload.answers) != required_len:
        raise HTTPException(status_code=400, detail=f"Expected {required_len} answers")

    # compute score (each answer expected 0..3)
    if key == "phq9":
        score = sum(PHQ9_WEIGHTS[a] for a in payload.answers)
        band = PHQ9_SEVERITY
    else:
        score = sum(GAD7_WEIGHTS[a] for a in payload.answers)
        band = GAD7_SEVERITY

    payload.score = score
    payload.severity = severity_from_score(score, band)

    try:
        create_document("assessmentresponse", payload)
    except Exception:
        # still return result even if DB not available
        pass

    return payload

# -------- API: Mood tracker (interactive tool) --------
@app.post("/api/mood", response_model=MoodEntry)
def add_mood(entry: MoodEntry):
    try:
        create_document("moodentry", entry)
    except Exception:
        pass
    return entry

@app.get("/api/mood/stats")
def mood_stats():
    try:
        docs = get_documents("moodentry")
        total = len(docs)
        counts: Dict[str, int] = {}
        for d in docs:
            m = d.get("mood", "unknown")
            counts[m] = counts.get(m, 0) + 1
        return {"total": total, "counts": counts}
    except Exception:
        # Fallback with zeros when DB is missing
        return {"total": 0, "counts": {}}

# -------- API: Resources --------
@app.get("/api/resources", response_model=List[Resource])
def get_resources():
    try:
        docs = get_documents("resource")
        # crude mapping
        mapped = []
        for d in docs:
            mapped.append(Resource(
                title=d.get("title",""),
                description=d.get("description",""),
                url=d.get("url",""),
                category=d.get("category","article")
            ))
        if mapped:
            return mapped
    except Exception:
        pass

    # default seed if db empty/unavailable
    return [
        Resource(title="Coping with Exam Stress (IT)", description="Practical steps for managing deadlines and exams.", url="https://www.mind.org.uk/" , category="guide"),
        Resource(title="Understanding Burnout", description="Signs and strategies for students in tech.", url="https://www.helpguide.org/", category="article"),
        Resource(title="Breathing Exercise", description="4-7-8 guided breathing timer.", url="https://www.boxbreathingapp.com/", category="tool"),
        Resource(title="24/7 Helpline", description="Immediate assistance if you’re in crisis.", url="https://988lifeline.org/", category="helpline"),
    ]

# -------- API: Team --------
@app.get("/api/team", response_model=List[TeamMember])
def get_team():
    try:
        docs = get_documents("teammember")
        out = []
        for d in docs:
            out.append(TeamMember(name=d.get("name",""), role=d.get("role",""), bio=d.get("bio"), avatar=d.get("avatar")))
        if out:
            return out
    except Exception:
        pass
    return [
        TeamMember(name="Ava Patel", role="Clinical Advisor", bio="Guides assessment criteria"),
        TeamMember(name="Liam Chen", role="Data Analyst", bio="Turns mood logs into insight"),
        TeamMember(name="Sara Gomez", role="Frontend", bio="Designs interactive tools"),
        TeamMember(name="Noah Singh", role="Backend", bio="APIs and data layer"),
    ]

# -------- API: Contact --------
@app.post("/api/contact")
def send_contact(msg: ContactMessage):
    try:
        create_document("contactmessage", msg)
    except Exception:
        pass
    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
