from typing import Any, Optional

from pydantic import BaseModel, Field


class RegisterIn(BaseModel):
    email: str
    password: str
    language: str = "bn"


class LoginIn(BaseModel):
    email: str
    password: str


class TokenOut(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class CharacterOut(BaseModel):
    id: str
    name: str
    age: int
    pronouns: str
    role: str
    avatar_hue: int

    model_config = {"from_attributes": True}


class ChapterOut(BaseModel):
    id: str
    chapter_number: int
    title: str
    status: str
    locked: bool = False
    closing_line: str = ""

    model_config = {"from_attributes": True}


class StoryOut(BaseModel):
    id: str
    title: str
    slug: str
    language: str
    genre: str
    blurb: str
    status: str
    target_chapters: int
    age_rating: str
    free_chapter_count: int
    characters: list[CharacterOut] = []
    continue_chapter_id: Optional[str] = None

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: str
    scene_id: str
    character_id: Optional[str]
    speaker: Optional[str] = None
    message_index: int
    body: str
    kind: str
    sent_at_story_time: Optional[str]
    metadata: dict = Field(default_factory=dict, alias="metadata_json")

    model_config = {"from_attributes": True, "populate_by_name": True}


class ReadingStateOut(BaseModel):
    story_id: str
    chapter_id: Optional[str]
    last_message_id: Optional[str]
    completion_percent: float
    premium: bool
    current_chapter: int = 1
    tension: int = 20


class NextBatchOut(BaseModel):
    messages: list[MessageOut]
    chapter_complete: bool = False
    paywalled: bool = False
    closing_line: str = ""
    next_chapter_id: Optional[str] = None


class StoryBriefIn(BaseModel):
    title: str
    genre: str = "romance"
    setting: str = "Kolkata"
    target_chapters: int = 10
    blurb: str = ""
    characters: list[dict[str, Any]]
    literary_direction: str = "restrained Bengali romance"


class BillingMeOut(BaseModel):
    premium: bool
    status: str = "none"
    product_id: Optional[str] = None


class AnalyticsIn(BaseModel):
    name: str
    payload: dict[str, Any] = Field(default_factory=dict)
