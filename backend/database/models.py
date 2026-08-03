from sqlalchemy import Column, DateTime, String, Integer, ForeignKey, Text, Boolean, UniqueConstraint
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from datetime import datetime
from .database import Base


# Session storage table
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    session_id = Column(String,primary_key=True)

    title = Column(String, nullable=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    user_id = Column(Integer, ForeignKey("users.id"),nullable=False)

    user = relationship("User", back_populates="chat_sessions"
    )

    messages = relationship("Message", back_populates="session", cascade="all, delete")

# Messages storage table
class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String, ForeignKey("chat_sessions.session_id"))
    role = Column(String)
    content = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship(
        "ChatSession",
        back_populates="messages"
    )

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)

    username = Column(String, unique=True, nullable=False)

    email = Column(String, unique=True, nullable=False)

    hashed_password = Column(Text, nullable=False)

    is_verified = Column(Boolean, default=False)

    disabled = Column(Boolean, default=False)

    chat_sessions = relationship("ChatSession", back_populates="user", cascade="all, delete")

class Document(Base):
    __tablename__ = "documents"

    __table_args__ = (
        UniqueConstraint("user_id", "filename", name="uq_user_filename"),
    )

    id = Column(Integer, primary_key=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

class Chunk(Base):
    __tablename__ = "chunks"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    chunk_text = Column(Text, nullable=False)
    page = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())