from types import SimpleNamespace

from mayzfact.matching import hook_slot_map


def test_hook_slot_map():
    bounds = [(0.0, 2.1), (2.1, 4.0), (4.0, 9.9), (9.9, 10.4), (10.4, 12.0), (12.0, 14.0)]
    slots = [SimpleNamespace(index=i, start_s=a, end_s=b) for i, (a, b) in enumerate(bounds)]
    assert hook_slot_map(slots, 6, 10.0) == {0: 0, 1: 1, 2: 2, 3: 3}
    assert hook_slot_map(slots, 2, 10.0) == {0: 0, 1: 1}
    assert hook_slot_map(slots, 0, 10.0) == {}




def test_hook_slot_map_skips_shot_that_runs_past_hook_area():
    # Kasus i2xag: shot "Number five, horseshoe crab" mulai 9.74 tapi jalan sampai 12.45.
    slots = [SimpleNamespace(index=i, start_s=a, end_s=b) for i, (a, b) in enumerate([(0.0, 3.41), (3.41, 6.46), (6.46, 9.74), (9.74, 12.45)])]
    assert hook_slot_map(slots, 6, 10.0) == {0: 0, 1: 1, 2: 2}
