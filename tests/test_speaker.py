from unittest.mock import patch, MagicMock


def test_speak_calls_elevenlabs():
    with patch("speaker._get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.text_to_speech.convert.return_value = [b"fake-audio"]
        mock_get_client.return_value = mock_client

        with patch("speaker.AudioSegment") as mock_audio_seg:
            mock_seg = MagicMock()
            mock_seg.channels = 1
            mock_seg.frame_rate = 44100
            mock_seg.get_array_of_samples.return_value = [0] * 100
            mock_audio_seg.from_mp3.return_value = mock_seg

            with patch("speaker.sd"):
                from speaker import speak
                speak("Bonjour", api_key="test-key")

        mock_client.text_to_speech.convert.assert_called_once()
        call_kwargs = mock_client.text_to_speech.convert.call_args[1]
        assert call_kwargs["text"] == "Bonjour"
        assert call_kwargs["model_id"] == "eleven_turbo_v2_5"
