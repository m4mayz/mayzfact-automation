import numpy as np

from mayzfact.voice_onset import STEP_S, snap_word_starts, voice_envelope


def env_with_voice(total_s, voiced):
    """Envelope 10 ms: 0 di jeda, 1000 di rentang `voiced` [(mulai, selesai)]."""
    env = np.zeros(int(total_s / STEP_S))
    for start, end in voiced:
        env[int(start / STEP_S):int(end / STEP_S)] = 1000.0
    return env


def test_snap_word_starts_moves_start_to_first_voice():
    words = [{"text": "luck!", "start_s": 0.0, "end_s": 0.5},
             {"text": "Number", "start_s": 0.6, "end_s": 1.5},   # alignment ikut ngitung jeda sebelum kata
             {"text": "five,", "start_s": 1.5, "end_s": 1.9}]
    env = env_with_voice(2.0, [(0.0, 0.45), (1.3, 1.45), (1.55, 1.8)])
    snapped = snap_word_starts(words, env)
    assert [w["start_s"] for w in snapped] == [0.0, 1.3, 1.55]
    assert snapped[1]["end_s"] == 1.5 and words[1]["start_s"] == 0.6  # input nggak diubah


def test_snap_keeps_start_when_word_has_no_voice():
    words = [{"text": "x", "start_s": 0.2, "end_s": 0.4}]
    assert snap_word_starts(words, env_with_voice(1.0, []))[0]["start_s"] == 0.2


def test_voice_envelope_reads_audio(sine_mp3):
    env = voice_envelope(sine_mp3)
    assert len(env) > 10 and env.max() > 0
