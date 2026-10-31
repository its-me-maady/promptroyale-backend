from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

class College(Base):
    __tablename__ = "colleges"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    domain = Column(String(100), unique=True, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    departments = relationship("Department", back_populates="college")
    users = relationship("User", back_populates="college")


class Department(Base):
    __tablename__ = "departments"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False)

    college = relationship("College", back_populates="departments")
    subjects = relationship("Subject", back_populates="department")
    users = relationship("User", back_populates="department")


class Subject(Base):
    __tablename__ = "subjects"

    id = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=False)
    name = Column(String(200), nullable=False)
    code = Column(String(50), nullable=False, index=True)
    description = Column(Text, default="")

    department = relationship("Department", back_populates="subjects")
    memberships = relationship("SubjectMembership", back_populates="subject")
    documents = relationship("Document", back_populates="subject")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    college_id = Column(Integer, ForeignKey("colleges.id"), nullable=False)
    department_id = Column(Integer, ForeignKey("departments.id"), nullable=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(200), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(50), nullable=False)  # 'student', 'department_user', 'college_admin'
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(UTC))

    college = relationship("College", back_populates="users")
    department = relationship("Department", back_populates="users")
    memberships = relationship("SubjectMembership", back_populates="student")


class SubjectMembership(Base):
    __tablename__ = "subject_memberships"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    added_at = Column(DateTime, default=lambda: datetime.now(UTC))

    student = relationship("User", back_populates="memberships")
    subject = relationship("Subject", back_populates="memberships")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey("subjects.id"), nullable=False)
    title = Column(String(255), nullable=False)
    file_type = Column(String(50), default="text")
    processing_status = Column(String(50), default="available")  # 'pending', 'processing', 'available', 'failed'
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


class BattleUsageCounter(Base):
    __tablename__ = "battle_usage_counters"

    id = Column(Integer, primary_key=True, index=True)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    date_str = Column(String(20), nullable=False, index=True)  # YYYY-MM-DD
    battle_count = Column(Integer, default=0)
