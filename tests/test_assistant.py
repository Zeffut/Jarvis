from assistant import Assistant


def test_assistant_init():
    asst = Assistant(model="haiku")
    assert asst.model == "haiku"
    assert asst.proc is not None
    asst.reset()


def test_assistant_reset():
    asst = Assistant()
    asst.reset()
    assert asst.proc is None
