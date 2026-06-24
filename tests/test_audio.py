import numpy as np


def test_is_silent_returns_true_for_quiet_audio():
    from audio import is_silent

    quiet = np.zeros(1600, dtype=np.float32)
    assert is_silent(quiet, threshold=0.01) is True


def test_is_silent_returns_false_for_loud_audio():
    from audio import is_silent

    loud = np.ones(1600, dtype=np.float32) * 0.5
    assert is_silent(loud, threshold=0.01) is False


def test_is_silent_around_threshold():
    # On évite l'égalité flottante pile au seuil (fragile en float32) :
    # juste au-dessus = pas silencieux, juste en dessous = silencieux.
    from audio import is_silent

    above = np.ones(1600, dtype=np.float32) * 0.011
    assert is_silent(above, threshold=0.01) is False

    just_below = np.ones(1600, dtype=np.float32) * 0.009
    assert is_silent(just_below, threshold=0.01) is True
