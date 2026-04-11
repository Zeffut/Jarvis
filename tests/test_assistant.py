from assistant import Assistant


def test_assistant_init():
    asst = Assistant(model="haiku")
    assert asst.model == "haiku"
    assert asst._session_id is None


def test_assistant_reset():
    asst = Assistant()
    asst._session_id = "fake-session"
    asst.reset(clear_session=True)
    assert asst._session_id is None


def test_assistant_reset_no_clear():
    asst = Assistant()
    asst._session_id = "fake-session"
    asst.reset(clear_session=False)
    assert asst._session_id == "fake-session"
