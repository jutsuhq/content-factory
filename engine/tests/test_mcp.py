import pytest

from factory.mcp import server as tools
from factory.mcp import view
from factory.mcp.server import merge_script

BEATS = {
    "hook": "Что если",
    "cta": "Подпишись",
    "style": "toon-homestead",
    "voice": True,
    "language": "ru",
    "beats": [
        {"counter": "ЧАС 1", "caption": "темно", "seconds": 7, "vo": "Ночь.", "state": "dark sky"},
        {"counter": "ГОД 1", "caption": "холодно", "seconds": 8, "state": "snow"},
    ],
}
EP = {"slug": "moon", "status": "review", "title": "Луна", "beats": BEATS, "video": "out/moon.mp4", "series": "moon"}


def test_merge_patches_beats_by_number_and_keeps_the_rest():
    b = merge_script(BEATS, {"hook": "Новый", "beats": {"2": {"vo": "Снег."}}})
    assert b["hook"] == "Новый" and b["beats"][1] == {**BEATS["beats"][1], "vo": "Снег."}
    assert b["beats"][0] == BEATS["beats"][0] and "vo" not in BEATS["beats"][1]  # the original is untouched
    assert merge_script(BEATS, {"beats": BEATS["beats"][:1]})["beats"] == BEATS["beats"][:1]
    with pytest.raises(ValueError):
        merge_script(BEATS, {"beats": {"3": {"vo": "x"}}})


def test_episode_text_leaves_image_prompts_out_unless_asked():
    text = view.episode(EP, {"ok": True, "checks": [{"level": "info", "id": "music", "message": "music: x"}]})
    assert "1. ЧАС 1 | темно | 7s" in text and "vo: Ночь." in text and "qa: ok" in text
    assert "dark sky" not in text and "dark sky" in view.episode(EP, full=True)
    assert text.splitlines()[-1].startswith("next: watch the video")


def test_qa_lists_only_problems():
    qa = {
        "ok": False,
        "checks": [
            {"level": "warn", "id": "voice-gap", "message": "2.1s of silence", "beat": 3},
            {"level": "info", "id": "music", "message": "music: x"},
        ],
    }
    assert view.qa_lines(qa) == ["qa:", "  warn beat 3: 2.1s of silence"]


def test_job_line_is_one_short_line():
    job = {"id": 7, "kind": "generate", "slug": "moon", "status": "failed", "error": "Traceback\n" + "x " * 400}
    line = view.job_line(job)
    assert "\n" not in line and len(line) < 300
    running = {"id": 8, "kind": "stages", "slug": "moon", "status": "running", "progress": 0.42, "stage": "render"}
    assert view.job_line(running) == "job 8 stages moon · running 42% (render)"


def test_the_skill_reaches_any_mcp_client_without_its_front_matter():
    text = tools.catalog("skill")
    assert text.startswith("# Make a video") and "61" in text
    assert tools.make_video("a what-if about friction").endswith("a what-if about friction")
