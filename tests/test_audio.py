import numpy as np


def test_is_silent_returns_true_for_quiet_audio():
    from audio import is_silent

    quiet = np.zeros(1600, dtype=np.float32)
    assert is_silent(quiet, threshold=0.01) is True


def test_is_silent_returns_false_for_loud_audio():
    from audio import is_silent

    loud = np.ones(1600, dtype=np.float32) * 0.5
    assert is_silent(loud, threshold=0.01) is False


def test_is_silent_at_boundary():
    from audio import is_silent

    boundary = np.ones(1600, dtype=np.float32) * 0.01
    assert is_silent(boundary, threshold=0.01) is False

    just_below = np.ones(1600, dtype=np.float32) * 0.009
    assert is_silent(just_below, threshold=0.01) is True
