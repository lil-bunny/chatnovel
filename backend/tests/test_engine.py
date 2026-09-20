from fastapi.testclient import TestClient

from app.generate import next_batch
from app.llm import MockProvider
from app.main import app
from app.seed_story import CHAPTERS

client = TestClient(app)


def test_health():
    r = client.get("/health")
    assert r.json()["ok"] is True


def test_story_has_adult_leads_and_chapters():
    data = client.get("/v1/story").json()
    ages = [c["age"] for c in data["characters"]]
    assert min(ages) >= 18
    assert len(data["chapters"]) == 10
    assert data["first_person"] == "Deb"
    assert data["second_person"] == "Visha"
    assert "১৮৫০" in data["blurb"]


def test_canned_chapter_one_is_period():
    ch = CHAPTERS[0]
    speakers = {m.get("speaker") for m in ch["messages"] if m.get("kind") != "scene_marker"}
    assert speakers <= {"Deb", "Visha"}
    bodies = " ".join(m["body"] for m in ch["messages"])
    assert "আষাঢ়" in bodies
    assert "প্রদীপ" in bodies


def test_directed_pipeline_speakers():
    import asyncio

    data = asyncio.run(next_batch(0, [], 0, provider=MockProvider()))
    assert data["llm"] is True
    assert data["messages"]
    speakers = {m.get("speaker") for m in data["messages"] if m.get("kind") != "scene_marker"}
    assert speakers <= {"Deb", "Visha"}
    assert isinstance(data["tension"], int)


def test_home_is_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Deb লিখছে" in r.text
    assert "Deb · Visha" in r.text
    assert "১৮৫০" in r.text
    assert "/static/theme.mp3" in r.text
    assert "নিরব" in r.text
