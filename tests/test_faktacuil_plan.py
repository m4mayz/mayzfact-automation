import shutil

import pytest

from mayzfact.steps.plan import run_plan
from mayzfact.store import RunPaths
from mayzfact.text import script_text
from tests.factories import fake_alignment
from tests.faktacuil_fixtures import faktacuil_script

SOURCE = dict(video_id="abcdefghijk", duration_s=2, transcript=[
    dict(text="Cats love boxes.", start=0, duration=0.5), dict(text="Small spaces feel safe.", start=0.6, duration=0.6)])


@pytest.fixture
def plan(tmp_path, cut_video):
    script = faktacuil_script().model_dump()
    tts = dict(duration_s=25, alignment=fake_alignment(script_text(script["beats"]), 25))
    return run_plan(RunPaths(tmp_path / "run"), script, tts, SOURCE, max_shot_s=2.0, hook_seconds=0.0,
                    download_source=lambda vid, dest: shutil.copyfile(cut_video, dest), log=lambda m: None)


def test_cta_block_beats_need_links_in_brief(plan):
    """Gaya FaktaBor: pill like di atas klip beneran, jadi shot CTA diisi link kayak shot lain (bukan AUTO CTA)."""
    cta = [s for s in plan["shots"] if s["beat"] in (4, 5)]
    assert cta and not any(s.get("auto_cta") for s in cta)
    assert all(s["keywords"]["en"] == ["cat in box", "cat cardboard box"] and s["subject"] == "" for s in cta)
    assert all(s["group"] == "cta" for s in cta)
    group = next(g for g in plan["groups"] if g["id"] == "cta")
    assert group["label"] == "CTA" and not group.get("auto_cta")
    assert not any(g.get("auto_cta") for g in plan["groups"])


def test_non_cta_shots_keep_their_queries_and_are_not_auto_cta(plan):
    other = [s for s in plan["shots"] if s["beat"] not in (4, 5)]
    assert other and not any(s.get("auto_cta") for s in other)
    assert all(s["keywords"]["en"] == ["cat in box", "cat cardboard box"] for s in other)


def test_no_countdown_rank_or_hook_in_faktacuil_plan(plan):
    assert all(s["countdown"] is None and s["source_rank"] is None for s in plan["shots"])
    assert all(s["hook_segment"] is None for s in plan["shots"]) and plan["segments"] == []


def test_cta_beat_subject_is_cleared_even_if_script_sets_one(tmp_path, cut_video):
    script = faktacuil_script().model_dump()
    script["beats"][4]["subject"] = "cat"
    tts = dict(duration_s=25, alignment=fake_alignment(script_text(script["beats"]), 25))
    data = run_plan(RunPaths(tmp_path / "run"), script, tts, SOURCE, max_shot_s=2.0, hook_seconds=0.0,
                    download_source=lambda vid, dest: shutil.copyfile(cut_video, dest), log=lambda m: None)
    assert all(s["subject"] == "" for s in data["shots"] if s["beat"] in (4, 5))
