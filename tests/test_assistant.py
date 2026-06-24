import pytest

import assistant as asst_mod
from assistant import Assistant, TOKEN, SENTENCE, TOOL_USE, _SENTENCE_BOUNDARY


@pytest.fixture
def assistant(monkeypatch):
    """Instancie Assistant sans effets de bord : pas de subprocess `claude`,
    pas de socket EventListener, pas de threads warmup/keepalive actifs."""
    monkeypatch.setattr(Assistant, "_start", lambda self: None)
    monkeypatch.setattr(Assistant, "_warmup", lambda self: None)
    monkeypatch.setattr(Assistant, "_keepalive_loop", lambda self: None)

    class _FakeListener:
        def __init__(self, *a, **k):
            pass

        def start(self):
            pass

        def stop(self):
            pass

    monkeypatch.setattr(asst_mod.ui_socket, "EventListener", _FakeListener)
    return Assistant()


def test_event_type_constants():
    # Contrat de yield consommé par main.py — ne doit pas dériver.
    assert (TOKEN, SENTENCE, TOOL_USE) == ("token", "sentence", "tool_use")


def test_init_state(assistant):
    # Le modèle est lu dans _start() via JARVIS_MODEL ; plus d'attribut .model
    # ni de _session_id (API historique supprimée).
    assert not hasattr(assistant, "model")
    assert not hasattr(assistant, "_session_id")
    assert assistant._proc is None


def test_reset_without_clear_is_noop(assistant):
    # Le subprocess reste warm : le contexte conversationnel persiste entre
    # deux wakes. reset(clear_session=False) ne doit PAS redémarrer.
    calls = []
    assistant._start = lambda: calls.append("start")
    assistant.reset(clear_session=False)
    assert calls == []


def test_reset_with_clear_restarts(assistant):
    # reset(clear_session=True) repart vierge → relance le subprocess.
    calls = []
    assistant._start = lambda: calls.append("start")
    assistant._proc = None  # rien à terminer
    assistant.reset(clear_session=True)
    assert calls == ["start"]


def test_sentence_boundary_does_not_split_decimals():
    # "Sonnet 4.6" : le point n'est pas suivi d'espace/newline → pas de coupe.
    assert _SENTENCE_BOUNDARY.search("Sonnet 4.6") is None


def test_sentence_boundary_splits_on_punctuation_then_space():
    m = _SENTENCE_BOUNDARY.search("Bonjour. Ca va ?")
    assert m is not None
    assert m.start() == 7  # le '.' suivi d'un espace
