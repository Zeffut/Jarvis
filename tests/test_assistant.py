from assistant import Assistant


def test_assistant_init():
    asst = Assistant(model="haiku")
    assert asst.model == "haiku"
    assert asst.session_id is None


def test_assistant_reset():
    asst = Assistant()
    asst.session_id = "test-session"
    asst.reset()
    assert asst.session_id is None
