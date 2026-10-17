import pytest

from mayzfact.errors import PipelineError
from mayzfact.steps.clips import ShotSlot, choose_candidate, pick_for_slot
from tests.factories import cand


class FakeSearch:
    def __init__(self, results):
        self.results = results
        self.calls = []

    def candidates(self, kind, query):
        self.calls.append((kind, query))
        return list(self.results.get((kind, query), []))






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



def test_second_shot_of_a_beat_starts_from_the_second_query():
    first, second = cand("pexels", "1"), cand("pexels", "2")
    search = FakeSearch({("video", "horseshoe crab"): [first], ("video", "crab beach"): [second]})
    slot2 = ShotSlot(index=1, beat=0, start_s=2.0, end_s=4.0, media="video", part=1)
    assert pick_for_slot(slot2, BEAT, "animals", search, set(), 0.5) == (second, "crab beach")
    assert search.calls[0] == ("video", "crab beach")


class FixedScorer:
    def __init__(self, table):
        self.table = table
        self.calls = []

    def score(self, text, candidates):
        self.calls.append((text, [c.id for c in candidates]))
        return [self.table[c.id] for c in candidates]


def test_scorer_picks_best_scored_candidate_across_all_queries():
    low = cand("pexels", "low", rank=0)
    blurry = cand("pexels", "blurry", width=640, height=360, rank=1)
    high = cand("pixabay", "high", rank=3)
    search = FakeSearch({("video", "horseshoe crab"): [low, blurry], ("video", "crab beach"): [high]})
    scorer = FixedScorer({"low": 0.1, "blurry": 0.9, "high": 0.3})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer) == (high, "crab beach")
    assert search.calls == [("video", "horseshoe crab"), ("video", "crab beach")]
    assert scorer.calls == [("horseshoe crab", ["low", "blurry"]), ("crab beach", ["high"])]


class QueryScorer:
    """Skor ditentuin dari (query, id) biar kelihatan teks mana yang dipakai buat nilai kandidat."""

    def __init__(self, table):
        self.table = table
        self.texts = []

    def score(self, text, candidates):
        self.texts.append(text)
        return [self.table.get((text, c.id), 0.0) for c in candidates]


def test_rerank_scores_each_candidate_with_its_own_query():
    a, b = cand("pexels", "a"), cand("pexels", "b")
    search = FakeSearch({("video", "horseshoe crab"): [a], ("video", "crab beach"): [b]})
    scorer = QueryScorer({("horseshoe crab", "a"): 0.12, ("crab beach", "b"): 0.3})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer) == (b, "crab beach")
    assert sorted(set(scorer.texts)) == ["crab beach", "horseshoe crab"]


def test_low_relevance_video_switches_to_better_photo():
    video = cand("pexels", "v")
    photo = cand("pexels", "p", kind="photo")
    search = FakeSearch({("video", "horseshoe crab"): [video], ("photo", "horseshoe crab"): [photo]})
    scorer = QueryScorer({("horseshoe crab", "v"): 0.03, ("horseshoe crab", "p"): 0.15})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer) == (photo, "horseshoe crab")


def test_relevant_video_is_kept_even_if_photo_scores_higher():
    video = cand("pexels", "v")
    photo = cand("pexels", "p", kind="photo")
    search = FakeSearch({("video", "horseshoe crab"): [video], ("photo", "horseshoe crab"): [photo]})
    scorer = QueryScorer({("horseshoe crab", "v"): 0.12, ("horseshoe crab", "p"): 0.2})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer) == (video, "horseshoe crab")




def test_subject_is_used_as_scoring_text_and_drives_photo_fallback():
    video = cand("pexels", "v")
    photo = cand("pexels", "p", kind="photo")
    search = FakeSearch({("video", "horseshoe crab"): [video], ("photo", "horseshoe crab"): [photo]})
    scorer = QueryScorer({("sturgeon", "v"): 0.0, ("sturgeon", "p"): 0.13, ("horseshoe crab", "v"): 0.5})
    assert pick_for_slot(slot(), BEAT, "animals", search, set(), 0.5, scorer=scorer, subject="sturgeon") == (photo, "horseshoe crab")
    assert set(scorer.texts) == {"sturgeon"}
