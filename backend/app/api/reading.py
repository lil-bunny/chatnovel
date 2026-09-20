import asyncio
import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth_utils import current_user
from app.db import get_db
from app.models import Chapter, Message, ReaderProgress, Scene, Story, User
from app.schemas import MessageOut, NextBatchOut, ReadingStateOut
from app.services import analytics
from app.services.billing import is_premium
from app.services.story_engine.orchestrator import generate_batch

router = APIRouter(prefix="/v1/reading", tags=["reading"])


def message_out(m: Message) -> MessageOut:
    speaker = m.character.name if m.character else (m.metadata_json or {}).get("speaker")
    return MessageOut(
        id=m.id,
        scene_id=m.scene_id,
        character_id=m.character_id,
        speaker=speaker,
        message_index=m.message_index,
        body=m.body,
        kind=m.kind,
        sent_at_story_time=m.sent_at_story_time,
        metadata_json=m.metadata_json or {},
    )


def chapter_messages(db: Session, chapter: Chapter) -> list[Message]:
    scenes = db.query(Scene).filter_by(chapter_id=chapter.id).order_by(Scene.sequence_number).all()
    msgs = []
    for s in scenes:
        msgs.extend(sorted(s.messages, key=lambda m: m.message_index))
    return msgs


def get_or_progress(db: Session, user: User, story: Story) -> ReaderProgress:
    p = db.query(ReaderProgress).filter_by(user_id=user.id, story_id=story.id).first()
    if p:
        return p
    first = db.query(Chapter).filter_by(story_id=story.id, chapter_number=1).first()
    p = ReaderProgress(user_id=user.id, story_id=story.id, chapter_id=first.id if first else None)
    db.add(p)
    db.flush()
    return p


def chapter_requires_premium(chapter_number: int, free_count: int, premium: bool) -> bool:
    return chapter_number > free_count and not premium


def locked(db: Session, user: User, story: Story, chapter: Chapter) -> bool:
    return chapter_requires_premium(chapter.chapter_number, story.free_chapter_count, is_premium(db, user.id))


@router.get("/{story_id}/state", response_model=ReadingStateOut)
def reading_state(story_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    p = get_or_progress(db, user, story)
    chapter = db.get(Chapter, p.chapter_id) if p.chapter_id else None
    return ReadingStateOut(
        story_id=story.id,
        chapter_id=p.chapter_id,
        last_message_id=p.last_message_id,
        completion_percent=p.completion_percent,
        premium=is_premium(db, user.id),
        current_chapter=chapter.chapter_number if chapter else 1,
        tension=int((chapter.outline_json or {}).get("escalation_target") or 20) if chapter else 20,
    )


@router.post("/{story_id}/start", response_model=ReadingStateOut)
def start_reading(story_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    p = get_or_progress(db, user, story)
    analytics.emit(db, "chapter_start", {"story_id": story_id, "chapter_id": p.chapter_id}, user.id)
    analytics.emit(db, "first_message_read", {"story_id": story_id}, user.id)
    return reading_state(story_id, user, db)


@router.post("/{story_id}/ack")
def ack(story_id: str, last_message_id: str, user: User = Depends(current_user), db: Session = Depends(get_db)):
    story = db.get(Story, story_id)
    p = get_or_progress(db, user, story)
    p.last_message_id = last_message_id
    chapter = db.get(Chapter, p.chapter_id) if p.chapter_id else None
    if chapter:
        msgs = chapter_messages(db, chapter)
        if msgs:
            idx = next((i for i, m in enumerate(msgs) if m.id == last_message_id), 0)
            p.completion_percent = round(100 * (idx + 1) / max(len(msgs), 1), 2)
    analytics.emit(db, "messages_read_per_session", {"story_id": story_id, "last_message_id": last_message_id}, user.id)
    return {"ok": True, "completion_percent": p.completion_percent}


@router.get("/{story_id}/next", response_model=NextBatchOut)
async def next_batch(
    story_id: str,
    chapter_id: str | None = None,
    after: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    story = db.get(Story, story_id)
    if not story:
        raise HTTPException(404, "Story not found")
    p = get_or_progress(db, user, story)
    chapter = db.get(Chapter, chapter_id or p.chapter_id)
    if not chapter or chapter.story_id != story.id:
        raise HTTPException(404, "Chapter not found")
    if locked(db, user, story, chapter):
        analytics.emit(db, "subscription_view", {"story_id": story_id, "chapter_id": chapter.id}, user.id)
        return NextBatchOut(messages=[], paywalled=True, chapter_complete=False)

    p.chapter_id = chapter.id
    msgs = chapter_messages(db, chapter)
    cursor = after
    if cursor:
        seen = {m.id: i for i, m in enumerate(msgs)}
        start = seen.get(cursor, -1) + 1
        unread = msgs[start:]
    else:
        unread = msgs

    if unread:
        batch = unread[:8]
        exhausted = len(unread) <= 8
        if batch:
            p.last_message_id = batch[-1].id
        nxt = None
        if exhausted:
            nxt = (
                db.query(Chapter)
                .filter_by(story_id=story.id, chapter_number=chapter.chapter_number + 1)
                .first()
            )
        return NextBatchOut(
            messages=[message_out(m) for m in batch],
            chapter_complete=exhausted,
            closing_line=chapter.closing_line,
            next_chapter_id=nxt.id if nxt else None,
        )

    # All authored messages consumed.
    if chapter.status == "complete" or msgs:
        nxt = db.query(Chapter).filter_by(story_id=story.id, chapter_number=chapter.chapter_number + 1).first()
        analytics.emit(db, "chapter_complete", {"story_id": story_id, "chapter_id": chapter.id}, user.id)
        return NextBatchOut(
            messages=[],
            chapter_complete=True,
            closing_line=chapter.closing_line,
            next_chapter_id=nxt.id if nxt else None,
        )

    generated, _beat = await generate_batch(db, story, chapter)
    return NextBatchOut(messages=[message_out(m) for m in generated], closing_line=chapter.closing_line)


@router.get("/{story_id}/stream")
async def stream(
    story_id: str,
    chapter_id: str | None = None,
    user: User = Depends(current_user),
    db: Session = Depends(get_db),
):
    batch = await next_batch(story_id, chapter_id, None, user, db)

    async def events():
        if batch.paywalled:
            yield f"event: paywall\ndata: {json.dumps({'paywalled': True})}\n\n"
            return
        if batch.chapter_complete:
            yield f"event: chapter_end\ndata: {json.dumps(batch.model_dump())}\n\n"
            return
        for m in batch.messages:
            if m.kind == "text" and m.speaker:
                yield f"event: typing\ndata: {json.dumps({'speaker': m.speaker})}\n\n"
                await asyncio.sleep(0)
            payload = m.model_dump()
            yield f"event: message\ndata: {json.dumps(payload, ensure_ascii=False)}\n\n"
        if batch.chapter_complete:
            yield f"event: chapter_end\ndata: {json.dumps(batch.model_dump())}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream")
