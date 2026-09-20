from fastapi.testclient import TestClient

from app.generate import next_batch
from app.llm import MockProvider
from app.main import app
from app.plot import compose
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


def test_presets_list():
    data = client.get("/v1/presets").json()
    ids = {t["id"] for t in data["tropes"]}
    eras = {e["id"] for e in data["eras"]}
    assert {"slow_burn", "enemies_to_lovers", "arranged", "second_chance"} <= ids
    assert {"calcutta_1850", "modern", "sarat_era"} <= eras
    assert {h["id"] for h in data["heats"]} >= {"restrained", "erotic"}
    assert any(h["id"] == "erotic" and h["label"] == "কামুক" for h in data["heats"])
    assert not any("১৮+" in (h.get("label") or "") for h in data["heats"])


def test_plot_unknown_is_400():
    r = client.post("/v1/plot", json={"trope": "nope", "era": "nope"})
    assert r.status_code == 400


def test_compose_locks_deb_visha():
    import asyncio

    pack = asyncio.run(compose("enemies_to_lovers", "modern", "erotic", provider=MockProvider()))
    names = [c["name"] for c in pack["bible"]["characters"]]
    assert names == ["Deb", "Visha"]
    assert min(c["age"] for c in pack["bible"]["characters"]) >= 18
    assert len(pack["chapters"]) == 10
    assert pack["era_rules"]["channel"] == "chat"
    assert pack["era_rules"]["heat"] == "erotic"
    assert "intercourse" in pack["era_rules"]["heat_direction"]
    assert "opening dress" in pack["era_rules"]["heat_direction"]


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
    assert any(m.get("kind") == "action" for m in data["messages"])
    assert "দৃশ্য" in (data["messages"][0].get("slugline") or data["messages"][0]["body"])
    speakers = {m.get("speaker") for m in data["messages"] if m.get("kind") not in {"scene_marker", "action"}}
    assert speakers <= {"Deb", "Visha"}
    assert isinstance(data["tension"], int)


def test_generate_modern_pack_speakers():
    import asyncio

    pack = asyncio.run(compose("slow_burn", "modern", provider=MockProvider()))
    data = asyncio.run(next_batch(0, [], 0, pack=pack, provider=MockProvider()))
    speakers = {m.get("speaker") for m in data["messages"] if m.get("kind") not in {"scene_marker", "action"}}
    assert speakers <= {"Deb", "Visha"}


def test_favicon():
    r = client.get("/favicon.ico")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("image/")


def test_home_is_html():
    r = client.get("/")
    assert r.status_code == 200
    assert "text/html" in r.headers["content-type"]
    assert "Deb লিখছে" in r.text
    assert "Deb · Visha" in r.text
    assert "গল্প গড়ুন" in r.text
    assert "কামুক" in r.text
    assert "কামুক · ১৮+" not in r.text
    assert "white-space: pre-wrap" in r.text
    assert ".chip.on" in r.text
    assert "button:not(.ghost):not(.chip)" in r.text
    assert "aria-pressed" in r.text
    assert "/static/theme.mp3" in r.text
    assert "নিরব" in r.text


def test_erotic_prompts_require_body_and_never_fail_sex():
    from app.llm import prompts

    assert "opening dress" in prompts.SCENE_DIRECTOR or "opening cloth" in prompts.SCENE_DIRECTOR
    assert "4–8 sentence" in prompts.SCENE_DIRECTOR or "4-8 sentence" in prompts.SCENE_DIRECTOR
    assert "intercourse" in prompts.DIALOGUE
    assert "Never fail graphic adult sex" in prompts.CRITIC
    assert "fail fade-to-black" in prompts.CRITIC
    assert "Do not treat explicitness as an issue" in prompts.CRITIC
    assert "private-room" in prompts.CHAPTER_PLANNER


def test_erotic_generate_opens_cloth():
    import asyncio

    pack = asyncio.run(compose("slow_burn", "calcutta_1850", "erotic", provider=MockProvider()))
    data = asyncio.run(next_batch(0, [], 0, pack=pack, provider=MockProvider()))
    action = next(m for m in data["messages"] if m.get("kind") == "action")
    blob = " ".join(filter(None, [action.get("action"), action.get("blocking"), action.get("body")]))
    assert "blouse" in blob.lower() or "cloth" in blob.lower()
    assert "sex" in blob.lower()


def test_erotic_post_check_allows_graphic():
    from app.services.story_engine.safety import post_check

    post_check(["explicit sex between Deb and Visha"], heat="erotic")

