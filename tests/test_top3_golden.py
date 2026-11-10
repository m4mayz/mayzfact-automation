import json
from pathlib import Path

import pytest

from mayzfact.steps.script import check_script
from mayzfact.steps.timeline import build_timeline
from mayzfact.text import script_text
from mayzfact.timing import beat_timings
from tests.factories import fake_alignment
from tests.top3_fixtures import SOURCE_TEXT, playful_script, top3_script

GOLDEN = Path(__file__).parent / "golden"


def _scene_timeline():
    from tests.test_cta_scene import timeline_fixture

    script, alignment, clips = timeline_fixture(24)
    return build_timeline(
        clips,
        24,
        .5,
        script=script,
        alignment=alignment,
        audio={
            "bgm": "audio/bgm/mystery.mp3",
            "bgm_main": "audio/bgm/main.mp3",
            "sfx": {
                k: f"audio/sfx/{k}.mp3"
                for k in [
                    "hook",
                    "number",
                    "subject",
                    "cut",
                    "click",
                    "hook_cut",
                    "item_reveal",
                    "extra_a",
                ]
            },
        },
        log=lambda _: None,
    )


def _fixture_timeline():
    script = top3_script().model_dump()
    alignment = fake_alignment(script_text(script["beats"]), 38.5)
    times = beat_timings([b["text"] for b in script["beats"]], alignment, 38.5)
    clips = {
        "shots": [
            dict(
                file=f"clips/shot_{i}.mp4",
                kind="video",
                start_s=t["start_s"],
                end_s=t["end_s"],
                width=1080,
                height=1920,
                beat=i,
            )
            for i, t in enumerate(times)
        ]
    }
    return build_timeline(clips, 38.5, .5, script=script, alignment=alignment, log=lambda _: None)


def _multi_rule_invalid():
    script = top3_script()
    script.beats = [beat.model_copy(update={"media": "video"}) for beat in script.beats]
    script.beats[2].text = "They can sprint briefly across water with quick feet and remarkable balance."
    script.beats[3].queries = []
    return script


def _check_messages():
    cases = {"valid": top3_script(), "playful": playful_script(), "multi": _multi_rule_invalid()}
    return {name: check_script(script, SOURCE_TEXT)[0] for name, script in cases.items()}


CASES = {
    "top3_timeline_scene.json": _scene_timeline,
    "top3_timeline_fixture.json": _fixture_timeline,
    "top3_check_script.json": _check_messages,
}


@pytest.mark.parametrize("name", CASES)
def test_top3_output_matches_golden(name):
    assert CASES[name]() == json.loads((GOLDEN / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    GOLDEN.mkdir(exist_ok=True)
    for name, case in CASES.items():
        (GOLDEN / name).write_text(json.dumps(case(), indent=2, ensure_ascii=False), encoding="utf-8")
