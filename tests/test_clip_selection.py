import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.clips import ShotSlot, choose_candidate, pick_for_slot, split_shots
from tests.factories import cand


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def candidates(self, kind, query):
        self.calls.append((kind, query))
        return list(self.results.get((kind, query), []))


def test_split_shots_respects_max_duration_and_media():
    timings = [{"start_s": 0.0, "end_s": 2.4}, {"start_s": 2.4, "end_s": 6.4}, {"start_s": 6.4, "end_s": 7.0}]
    beats = [{"media": "video"}, {"media": "photo"}, {"media": "video"}]
    slots = split_shots(timings, beats, 2.5)
    assert [(s.index, s.beat, s.start_s, s.end_s, s.media) for s in slots] == [
        (0, 0, 0.0, 2.4, "video"),
        (1, 1, 2.4, 4.4, "photo"),
        (2, 1, 4.4, 6.4, "photo"),
        (3, 2, 6.4, 7.0, "video"),
    ]


def test_split_shots_exact_multiple_is_not_split_further():
    slots = split_shots([{"start_s": 0.0, "end_s": 5.0}], [{"media": "video"}], 2.5)
    assert [(s.start_s, s.end_s) for s in slots] == [(0.0, 2.5), (2.5, 5.0)]


def test_choose_prefers_tier_then_rank_then_pexels():
    landscape_top = cand("pexels", "a", width=1920, height=1080, rank=0)
    portrait_lower = cand("pexels", "b", width=1080, height=1920, rank=5)
    assert choose_candidate([landscape_top, portrait_lower], set(), 2.0, 0.5) is portrait_lower
    pixabay_first = cand("pixabay", "x", rank=0)
    pexels_same_rank = cand("pexels", "y", rank=0)
    assert choose_candidate([pixabay_first, pexels_same_rank], set(), 2.0, 0.5) is pexels_same_rank


def test_choose_skips_used_and_short_videos_but_not_photos():
    used = cand("pexels", "used")
    short = cand("pexels", "short", duration_s=2.0)
    photo = cand("pexels", "photo", kind="photo")
    assert choose_candidate([used, short], {("pexels", "used")}, 2.9, 0.5) is None
    assert choose_candidate([short, photo], set(), 2.9, 0.5) is photo


def slot(media="video", start=0.0, end=2.0, beat=0):
    return ShotSlot(index=0, beat=beat, start_s=start, end_s=end, media=media)


BEAT = {"text": "Look at this crab.", "media": "video", "queries": ["horseshoe crab", "crab beach"]}


def test_pick_uses_next_query_when_first_is_empty():
    second = cand("pexels", "2")
    search = FakeSearch({("video", "crab beach"): [second]})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5) == (second, "crab beach")
    assert search.calls == [("video", "horseshoe crab"), ("video", "crab beach")]


def test_pick_falls_back_to_other_media_then_fallback_query():
    photo = cand("pexels", "p", kind="photo")
    assert pick_for_slot(slot(), BEAT, "animals", FakeSearch({("photo", "horseshoe crab"): [photo]}), set(), 0.5) == (photo, "horseshoe crab")
    generic = cand("pexels", "g")
    assert pick_for_slot(slot(), BEAT, "animals", FakeSearch({("video", "animals"): [generic]}), set(), 0.5) == (generic, "animals")


def test_pick_raises_when_nothing_found():
    with pytest.raises(PipelineError, match="Beat 1"):
        pick_for_slot(slot(), BEAT, "animals", FakeSearch({}), set(), 0.5)

