from datetime import datetime, timezone
from typing import Optional
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import JSON

from app.db import Base


def uid() -> str:
    return str(uuid4())


def now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String)
    auth_provider: Mapped[str] = mapped_column(String, default="email")
    language: Mapped[str] = mapped_column(String, default="bn")
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    progress: Mapped[list["ReaderProgress"]] = relationship(back_populates="user")
    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="user")


class Story(Base):
    __tablename__ = "stories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    title: Mapped[str] = mapped_column(String)
    slug: Mapped[str] = mapped_column(String, unique=True, index=True)
    language: Mapped[str] = mapped_column(String, default="bn")
    genre: Mapped[str] = mapped_column(String, default="romance")
    blurb: Mapped[str] = mapped_column(Text, default="")
    cover_url: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft|published
    target_chapters: Mapped[int] = mapped_column(Integer, default=10)
    age_rating: Mapped[str] = mapped_column(String, default="18+")
    bible_json: Mapped[dict] = mapped_column(JSON, default=dict)
    free_chapter_count: Mapped[int] = mapped_column(Integer, default=2)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    characters: Mapped[list["Character"]] = relationship(back_populates="story")
    chapters: Mapped[list["Chapter"]] = relationship(back_populates="story", order_by="Chapter.chapter_number")
    plot_threads: Mapped[list["PlotThread"]] = relationship(back_populates="story")
    memories: Mapped[list["Memory"]] = relationship(back_populates="story")
    relationships: Mapped[list["Relationship"]] = relationship(back_populates="story")


class Character(Base):
    __tablename__ = "characters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    name: Mapped[str] = mapped_column(String)
    age: Mapped[int] = mapped_column(Integer)
    pronouns: Mapped[str] = mapped_column(String, default="she/her")
    role: Mapped[str] = mapped_column(String, default="lead")
    personality_json: Mapped[dict] = mapped_column(JSON, default=dict)
    speech_style_json: Mapped[dict] = mapped_column(JSON, default=dict)
    goals_json: Mapped[list] = mapped_column(JSON, default=list)
    fears_json: Mapped[list] = mapped_column(JSON, default=list)
    secrets_json: Mapped[list] = mapped_column(JSON, default=list)
    avatar_hue: Mapped[int] = mapped_column(Integer, default=200)

    story: Mapped[Story] = relationship(back_populates="characters")
    messages: Mapped[list["Message"]] = relationship(back_populates="character")


class Relationship(Base):
    __tablename__ = "relationships"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    character_a_id: Mapped[str] = mapped_column(ForeignKey("characters.id"))
    character_b_id: Mapped[str] = mapped_column(ForeignKey("characters.id"))
    state_json: Mapped[dict] = mapped_column(JSON, default=dict)

    story: Mapped[Story] = relationship(back_populates="relationships")


class Chapter(Base):
    __tablename__ = "chapters"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    chapter_number: Mapped[int] = mapped_column(Integer)
    title: Mapped[str] = mapped_column(String)
    outline_json: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String, default="draft")  # draft|ready|complete
    closing_line: Mapped[str] = mapped_column(Text, default="")

    story: Mapped[Story] = relationship(back_populates="chapters")
    scenes: Mapped[list["Scene"]] = relationship(back_populates="chapter", order_by="Scene.sequence_number")


class Scene(Base):
    __tablename__ = "scenes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    chapter_id: Mapped[str] = mapped_column(ForeignKey("chapters.id"))
    sequence_number: Mapped[int] = mapped_column(Integer)
    scene_state_json: Mapped[dict] = mapped_column(JSON, default=dict)
    summary: Mapped[str] = mapped_column(Text, default="")
    generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    chapter: Mapped[Chapter] = relationship(back_populates="scenes")
    messages: Mapped[list["Message"]] = relationship(back_populates="scene", order_by="Message.message_index")
    emotions: Mapped[list["CharacterEmotion"]] = relationship(back_populates="scene")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"))
    character_id: Mapped[Optional[str]] = mapped_column(ForeignKey("characters.id"), nullable=True)
    message_index: Mapped[int] = mapped_column(Integer)
    body: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String, default="text")  # text|scene_marker|deleted|chapter_end
    sent_at_story_time: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    metadata_json: Mapped[dict] = mapped_column(JSON, default=dict)

    scene: Mapped[Scene] = relationship(back_populates="messages")
    character: Mapped[Optional[Character]] = relationship(back_populates="messages")


class CharacterEmotion(Base):
    __tablename__ = "character_emotions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    scene_id: Mapped[str] = mapped_column(ForeignKey("scenes.id"))
    character_id: Mapped[str] = mapped_column(ForeignKey("characters.id"))
    affection: Mapped[int] = mapped_column(Integer, default=0)
    trust: Mapped[int] = mapped_column(Integer, default=0)
    longing: Mapped[int] = mapped_column(Integer, default=0)
    fear: Mapped[int] = mapped_column(Integer, default=0)
    jealousy: Mapped[int] = mapped_column(Integer, default=0)
    pride: Mapped[int] = mapped_column(Integer, default=0)
    vulnerability: Mapped[int] = mapped_column(Integer, default=0)
    frustration: Mapped[int] = mapped_column(Integer, default=0)
    hope: Mapped[int] = mapped_column(Integer, default=0)
    resentment: Mapped[int] = mapped_column(Integer, default=0)

    scene: Mapped[Scene] = relationship(back_populates="emotions")


class PlotThread(Base):
    __tablename__ = "plot_threads"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    name: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String, default="active")  # active|inactive|resolved
    stakes: Mapped[str] = mapped_column(Text, default="")
    involved_characters: Mapped[list] = mapped_column(JSON, default=list)
    last_touched_scene_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    severity: Mapped[int] = mapped_column(Integer, default=40)

    story: Mapped[Story] = relationship(back_populates="plot_threads")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    type: Mapped[str] = mapped_column(String)  # canonical|event|ephemeral
    content: Mapped[str] = mapped_column(Text)
    source_scene_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    importance: Mapped[int] = mapped_column(Integer, default=50)
    embedding: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)

    story: Mapped[Story] = relationship(back_populates="memories")


class ReaderProgress(Base):
    __tablename__ = "reader_progress"
    __table_args__ = (UniqueConstraint("user_id", "story_id"),)

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    story_id: Mapped[str] = mapped_column(ForeignKey("stories.id"))
    chapter_id: Mapped[Optional[str]] = mapped_column(ForeignKey("chapters.id"), nullable=True)
    last_message_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    completion_percent: Mapped[float] = mapped_column(Float, default=0)
    last_read_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)

    user: Mapped[User] = relationship(back_populates="progress")


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    provider: Mapped[str] = mapped_column(String, default="stub")
    product_id: Mapped[str] = mapped_column(String, default="premium_monthly")
    status: Mapped[str] = mapped_column(String, default="active")  # active|canceled|expired
    renewal_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped[User] = relationship(back_populates="subscriptions")


class AnalyticsEvent(Base):
    __tablename__ = "analytics_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=uid)
    user_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    name: Mapped[str] = mapped_column(String, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
