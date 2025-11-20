"""
Database Schemas for Mental Health App (IT Students)

Each Pydantic model corresponds to a MongoDB collection (lowercased class name).
"""

from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List, Literal
from datetime import datetime

# --- Users / Students ---
class Student(BaseModel):
    name: str = Field(..., description="Full name")
    email: EmailStr = Field(..., description="Email address")
    program: Optional[str] = Field(None, description="Program or major, e.g., CS, IT")
    year: Optional[int] = Field(None, ge=1, le=10, description="Study year/semester index")

# --- Educational resources ---
class Resource(BaseModel):
    title: str
    description: str
    url: str
    category: Literal["article", "video", "guide", "helpline", "tool"] = "article"

# --- Assessment definitions ---
class Assessment(BaseModel):
    key: Literal["phq9", "gad7"]
    title: str
    description: str

class AssessmentResponse(BaseModel):
    assessment_key: Literal["phq9", "gad7"]
    answers: List[int] = Field(..., description="List of integer answers in order")
    score: Optional[int] = None
    severity: Optional[str] = None
    student_email: Optional[EmailStr] = None

# --- Mood entries for interactive tool ---
class MoodEntry(BaseModel):
    mood: Literal["great", "good", "okay", "low", "down"]
    note: Optional[str] = None
    student_email: Optional[EmailStr] = None
    timestamp: Optional[datetime] = None

# --- Contact messages ---
class ContactMessage(BaseModel):
    name: str
    email: EmailStr
    subject: str
    message: str

# --- Team member (static seed acceptable) ---
class TeamMember(BaseModel):
    name: str
    role: str
    bio: Optional[str] = None
    avatar: Optional[str] = None
