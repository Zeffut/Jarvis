from unittest.mock import patch, call


def test_speak_calls_say_with_correct_args():
    from speaker import speak

    with patch("speaker.subprocess.run") as mock_run:
        speak("Bonjour monsieur")
        mock_run.assert_called_once_with(
            ["say", "-v", "Thomas", "Bonjour monsieur"],
            check=True,
        )


def test_speak_with_custom_voice():
    from speaker import speak

    with patch("speaker.subprocess.run") as mock_run:
        speak("Hello", voice="Samantha")
        mock_run.assert_called_once_with(
            ["say", "-v", "Samantha", "Hello"],
            check=True,
        )
