from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth_utils import optional_user
from app.db import get_db
from app.models import Chapter, ReaderProgress, Story, User
from app.schemas import ChapterOut, CharacterOut, StoryOut
from app.services import analytics
from app.services.billing import is_premium

router = APIRouter(prefix="/v1/stories", tags=["stories"])


def story_to_out(story: Story, continue_chapter_id: str | None = None) -> StoryOut:
    return StoryOut(
        id=story.id,
        title=story.title,
        slug=story.slug,
        language=story.language,
        genre=story.genre,
        blurb=story.blurb,
        status=story.status,
        target_chapters=story.target_chapters,
        age_rating=story.age_rating,
        free_chapter_count=story.free_chapter_count,
        characters=[CharacterOut.model_validate(c) for c in story.characters],
        continue_chapter_id=continue_chapter_id,
    )


@router.get("", response_model=list[StoryOut])
def list_stories(db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    stories = db.query(Story).filter_by(status="published").all()
    progress = {}
    if user:
        for p in db.query(ReaderProgress).filter_by(user_id=user.id).all():
            progress[p.story_id] = p.chapter_id
    return [story_to_out(s, progress.get(s.id)) for s in stories]


@router.get("/{story_id}", response_model=StoryOut)
def get_story(story_id: str, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    cont = None
    if user:
        p = db.query(ReaderProgress).filter_by(user_id=user.id, story_id=story_id).first()
        cont = p.chapter_id if p else None
        analytics.emit(db, "story_open", {"story_id": story_id}, user.id)
    return story_to_out(story, cont)


@router.get("/{story_id}/chapters", response_model=list[ChapterOut])
def list_chapters(story_id: str, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    story = db.get(Story, story_id)
    premium = bool(user and is_premium(db, user.id))
    out = []
    for ch in story.chapters:
        locked = ch.chapter_number > story.free_chapter_count and not premium
        out.append(
            ChapterOut(
                id=ch.id,
                chapter_number=ch.chapter_number,
                title=ch.title,
                status=ch.status,
                locked=locked,
                closing_line=ch.closing_line,
            )
        )
    return out


@router.get("/{story_id}/chapters/{chapter_id}", response_model=ChapterOut)
def get_chapter(story_id: str, chapter_id: str, db: Session = Depends(get_db), user: User | None = Depends(optional_user)):
    ch = db.get(Chapter, chapter_id)
    story = db.get(Story, story_id)
    premium = bool(user and is_premium(db, user.id))
    return ChapterOut(
        id=ch.id,
        chapter_number=ch.chapter_number,
        title=ch.title,
        status=ch.status,
        locked=ch.chapter_number > story.free_chapter_count and not premium,
        closing_line=ch.closing_line,
    )
