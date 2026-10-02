from types import SimpleNamespace

from mayzfact.matching import hook_slot_map, match_label, rerank_key, top_k


def test_top_k_is_stable():
    assert top_k([0.2, 0.9, 0.9, 0.1], 3) == [1, 2, 0]
    assert top_k([], 3) == []


def test_match_label():
    assert match_label(0.85, 0.85) == "exact"
    assert match_label(0.849, 0.85) == "similar"


def test_hook_slot_map():
    slots = [SimpleNamespace(index=i, start_s=s) for i, s in enumerate([0.0, 2.1, 4.0, 9.9, 10.0, 12.0])]
    assert hook_slot_map(slots, 6, 10.0) == {0: 0, 1: 1, 2: 2, 3: 3}
    assert hook_slot_map(slots, 2, 10.0) == {0: 0, 1: 1}
    assert hook_slot_map(slots, 0, 10.0) == {}


def test_rerank_key_prefers_score_but_puts_tier3_last():
    items = {"blurry_best": (0.30, 3, 0), "good": (0.25, 1, 1), "better": (0.28, 2, 0)}
    assert sorted(items, key=lambda name: rerank_key(*items[name])) == ["better", "good", "blurry_best"]
