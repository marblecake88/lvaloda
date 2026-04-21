from datetime import date, datetime
from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    telegram_id: Mapped[int] = mapped_column(Integer, unique=True, index=True)
    username: Mapped[str | None] = mapped_column(String(64))
    first_name: Mapped[str | None] = mapped_column(String(128))
    reminder_time: Mapped[str | None] = mapped_column(String(5))  # "19:00"
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["ChatSession"]] = relationship(back_populates="user")
    saved_words: Mapped[list["SavedWord"]] = relationship(back_populates="user")
    topic_sessions: Mapped[list["TopicSession"]] = relationship(back_populates="user")


class ChatSession(Base):
    """A single conversation session — scenario chat OR exam simulation."""

    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    mode: Mapped[str] = mapped_column(String(16))  # "dialog" | "exam"
    scenario: Mapped[str] = mapped_column(String(64))  # scenario key or topic key
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime)

    user: Mapped[User] = relationship(back_populates="sessions")
    messages: Mapped[list["Message"]] = relationship(
        back_populates="session", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(16))  # "user" | "assistant" | "system"
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


class TopicSession(Base):
    """Анти-повтор для экзамен-режима: какие 'углы' темы уже отработаны."""

    __tablename__ = "topic_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(64), index=True)
    covered_angles: Mapped[list[str]] = mapped_column(JSON, default=list)
    fluency_score: Mapped[int | None] = mapped_column(Integer)
    report: Mapped[dict | None] = mapped_column(JSON)  # full JSON report from LLM
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="topic_sessions")


class SavedWord(Base):
    __tablename__ = "saved_words"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    word_lv: Mapped[str] = mapped_column(String(128))
    translation_ru: Mapped[str] = mapped_column(String(256))
    example: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="saved_words")


class UnnaturalPhrase(Base):
    """Авто-лог из `💡 Dabiskāk:` блоков в репликах ассистента."""

    __tablename__ = "unnatural_phrases"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"))
    said: Mapped[str] = mapped_column(Text)  # что сказал ученик
    better: Mapped[str] = mapped_column(Text)  # рекомендованный натуральный вариант
    note_ru: Mapped[str | None] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class DailyStats(Base):
    """Один ряд на (user, date). Стрик и статы считаются отсюда."""

    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint("user_id", "stat_date", name="uq_daily_stats"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    stat_date: Mapped[date] = mapped_column(Date, index=True)
    messages_sent: Mapped[int] = mapped_column(Integer, default=0)
    seconds_spent: Mapped[int] = mapped_column(Integer, default=0)
    topics: Mapped[list[str]] = mapped_column(JSON, default=list)


class Reflection(Base):
    __tablename__ = "reflections"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[int | None] = mapped_column(ForeignKey("chat_sessions.id"))
    text: Mapped[str] = mapped_column(Text)
    topic: Mapped[str | None] = mapped_column(String(64))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ShadowingSession(Base):
    __tablename__ = "shadowing_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    topic: Mapped[str] = mapped_column(String(64))
    phrases: Mapped[list[dict]] = mapped_column(JSON)  # [{lv, ru}, ...]
    progress_idx: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class PhraseRun(Base):
    """One completed pass through a phrases drill category."""

    __tablename__ = "phrase_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    category: Mapped[str] = mapped_column(String(64), index=True)
    total: Mapped[int] = mapped_column(Integer)
    known_count: Mapped[int] = mapped_column(Integer)
    duration_sec: Mapped[int | None] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )


class GeneratedPicture(Base):
    """Cached AI-generated pictures. Kept long-term (year+) so the user can
    browse past scenes and practice on them again without re-paying for gen.
    """

    __tablename__ = "generated_pictures"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    scene_key: Mapped[str] = mapped_column(String(64), index=True)
    topic_lv: Mapped[str] = mapped_column(String(128))
    topic_ru: Mapped[str] = mapped_column(String(128))
    prompt_lv: Mapped[str] = mapped_column(Text)
    image_b64: Mapped[str] = mapped_column(Text)  # base64-encoded PNG/JPEG
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, index=True
    )
