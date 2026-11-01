from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship
from app.db import Base

def utcnow():
    return datetime.now(timezone.utc)

class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String(36), primary_key=True)
    owner_id = Column(String(100), nullable=False, index=True)
    title = Column(String(200), nullable=False, default="New conversation")
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False)
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")

class Message(Base):
    __tablename__ = "messages"
    id = Column(String(36), primary_key=True)
    conversation_id = Column(String(36), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(20), nullable=False)
    content = Column(Text, nullable=False)
    model = Column(String(120), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow, nullable=False)
    conversation = relationship("Conversation", back_populates="messages")
