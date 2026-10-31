from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    domain = Column(String(100), unique=True, index=True)
    service_tier = Column(String(50), default="academic_tier_1")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    departments = relationship("Department", back_populates="college", cascade="all, delete-orphan")
    users = relationship("User", back_populates="college")
    billing_snapshots = relationship("BillingSnapshot", back_populates="college", cascade="all, delete-orphan")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False)

    college = relationship("College", back_populates="departments")
    subjects = relationship("Subject", back_populates="department", cascade="all, delete-orphan")
    users = relationship("User", back_populates="department")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, default="")

    department = relationship("Department", back_populates="subjects")
    memberships = relationship("SubjectMembership", back_populates="subject", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="subject", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'student', 'department_user', 'college_admin'
    status = Column(String(50), default="active")  # 'active', 'suspended', 'deactivated' (SRS FR-2.4)
    is_active = Column(Boolean, default=True)
    activated_at = Column(DateTime, default=lambda: datetime.now(UTC))
    deactivated_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    college = relationship("College", back_populates="users")
    department = relationship("Department", back_populates="users")
    memberships = relationship("SubjectMembership", back_populates="student", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="student", cascade="all, delete-orphan")
    credentials = relationship("AIProviderCredential", back_populates="student", cascade="all, delete-orphan")


class SubjectMembership(Base):
    __tablename__ = "subject_memberships"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    status = Column(String(50), default="active")  # 'active', 'removed' (SRS FR-3.5)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=lambda: datetime.now(UTC))
    removed_at = Column(DateTime, nullable=True)

    student = relationship("User", back_populates="memberships")
    subject = relationship("Subject", back_populates="memberships")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    file_type = Column(String(50), default="text")
    processing_status = Column(String(50), default="available")  # 'pending', 'processing', 'available', 'failed'
    file_size_bytes = Column(Integer, default=0)
    page_count = Column(Integer, default=1)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    subject = relationship("Subject", back_populates="documents")
    chunks = relationship("DocumentChunk", back_populates="document", cascade="all, delete-orphan")


class DocumentChunk(Base):
    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, index=True)
    document_id = Column(Integer, ForeignKey("documents.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    chunk_index = Column(Integer, nullable=False)
    section_title = Column(String(255), default="")
    content = Column(Text, nullable=False)

    document = relationship("Document", back_populates="chunks")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), default="Academic Q&A")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))
    updated_at = Column(DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))

    student = relationship("User", back_populates="conversations")
    messages = relationship("ConversationMessage", back_populates="conversation", cascade="all, delete-orphan")


class ConversationMessage(Base):
    __tablename__ = "conversation_messages"

    id = Column(Integer, primary_key=True, index=True)
    conversation_id = Column(Integer, ForeignKey("conversations.id"), nullable=False)
    role = Column(String(50), nullable=False)  # 'user', 'assistant'
    content = Column(Text, nullable=False)
    citations_json = Column(Text, default="[]")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    conversation = relationship("Conversation", back_populates="messages")
    feedback = relationship("Feedback", back_populates="message", cascade="all, delete-orphan")


class Feedback(Base):
    __tablename__ = "feedback"

    id = Column(Integer, primary_key=True, index=True)
    message_id = Column(Integer, ForeignKey("conversation_messages.id"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    rating = Column(Integer, nullable=False)  # 1 (negative) to 5 (positive)
    comment = Column(Text, default="")
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    message = relationship("ConversationMessage", back_populates="feedback")


class AIProviderCredential(Base):
    __tablename__ = "ai_provider_credentials"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    provider = Column(String(50), default="gemini")
    encrypted_key = Column(Text, nullable=False)
    status = Column(String(50), default="active")  # 'active', 'revoked' (SRS FR-7)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    student = relationship("User", back_populates="credentials")


class UsageRecord(Base):
    __tablename__ = "usage_records"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=True)
    model_name = Column(String(100), default="gemini-1.5-flash")
    tokens_consumed = Column(Integer, default=0)
    timestamp = Column(DateTime, default=lambda: datetime.now(UTC))


class BillingSnapshot(Base):
    __tablename__ = "billing_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    snapshot_date = Column(String(20), nullable=False)  # YYYY-MM
    active_student_count = Column(Integer, default=0)
    monthly_token_quota = Column(Integer, default=1_000_000)
    tokens_consumed = Column(Integer, default=0)
    tier = Column(String(50), default="Academic Enterprise")

    college = relationship("College", back_populates="billing_snapshots")


class BattleUsageCounter(Base):
    __tablename__ = "battle_usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_str = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    battle_count = Column(Integer, default=0)
