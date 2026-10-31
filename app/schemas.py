from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    college_id: int
    department_id: int | None = None
    enrolled_subjects: list[int] = []


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# Subject Schemas
class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None = ""
    department_id: int
    document_count: int | None = 0
    enrolled_student_count: int | None = 0


class SubjectCreate(BaseModel):
    code: str
    name: str
    description: str = ""
    department_id: int | None = None


class SubjectUpdate(BaseModel):
    code: str | None = None
    name: str | None = None
    description: str | None = None


# Student Management Schemas
class StudentEnrolledSubject(BaseModel):
    id: int
    code: str
    name: str


class StudentDetailOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    status: str
    enrolled_subjects: list[int] = []
    enrolled_subject_details: list[StudentEnrolledSubject] = []


class StudentCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    initial_subject_ids: list[int] = []


class StudentUpdate(BaseModel):
    name: str | None = None
    status: str | None = None  # 'active', 'suspended', 'deactivated'


class SubjectEnrollmentRequest(BaseModel):
    subject_id: int


class SubjectStudentsOut(BaseModel):
    subject_id: int
    subject_code: str
    subject_name: str
    enrolled: list[StudentDetailOut]
    available_students: list[StudentDetailOut]


# Admin Governance Schemas
class StaffCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    department_id: int | None = None


class DepartmentCreate(BaseModel):
    name: str
    code: str
    staff_ids: list[int] = []
    faculty_name: str | None = None
    faculty_email: EmailStr | None = None
    faculty_password: str | None = None


class DepartmentUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    staff_ids: list[int] | None = None


class DepartmentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    college_id: int
    name: str
    code: str
    subject_count: int = 0
    faculty_count: int = 0
    lead_faculty_email: str | None = None
    assigned_staff_ids: list[int] = []


class BillingSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    snapshot_date: str
    active_student_count: int
    monthly_token_quota: int
    tokens_consumed: int
    tier: str


class AdminOverviewOut(BaseModel):
    college_id: int
    college_name: str
    college_domain: str
    department_count: int
    subject_count: int
    student_count: int
    faculty_count: int
    billing_snapshot: BillingSnapshotOut
    ai_status: str = "Connected (Gemini 1.5 Flash)"


class UserAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    name: str
    role: str
    status: str
    department_id: int | None = None
    department_name: str | None = None
    created_at: datetime


class UserStatusUpdate(BaseModel):
    status: str  # 'active', 'suspended', 'deactivated'


# Document Schemas
class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subject_id: int
    file_type: str
    processing_status: str


# Chat Schemas
class ChatQueryRequest(BaseModel):
    subject_id: int
    question: str


class Citation(BaseModel):
    document_title: str
    section_title: str
    snippet: str


class ChatQueryResponse(BaseModel):
    answer: str
    citations: list[Citation] = []
    is_insufficient_evidence: bool = False


# Quiz Battle Schemas
class QuizStartRequest(BaseModel):
    subject_id: int


class QuizQuestionOut(BaseModel):
    id: int
    question: str
    options: list[str]
    source_citation: str


class QuizStartResponse(BaseModel):
    battle_id: str
    subject_code: str
    subject_name: str
    time_limit_seconds: int = 60
    questions: list[QuizQuestionOut]


class QuizAnswerSubmission(BaseModel):
    question_id: int
    selected_option: int


class QuizSubmitRequest(BaseModel):
    battle_id: str
    answers: list[QuizAnswerSubmission]
    time_taken_seconds: int = 0


class QuizQuestionReview(BaseModel):
    question_id: int
    question: str
    selected_option: int
    correct_option: int
    explanation: str
    source_citation: str
    is_correct: bool


class QuizSubmitResponse(BaseModel):
    score: int
    total: int
    accuracy_percentage: float
    time_taken_seconds: int
    review: list[QuizQuestionReview]
