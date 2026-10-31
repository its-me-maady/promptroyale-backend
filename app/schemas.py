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


class SubjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    description: str | None = ""
    department_id: int
    document_count: int | None = 0


class DocumentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    subject_id: int
    file_type: str
    processing_status: str


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
    total: int = 10
    accuracy_percentage: float
    time_taken_seconds: int
    review: list[QuizQuestionReview]
