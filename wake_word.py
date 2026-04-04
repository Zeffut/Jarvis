import numpy as np
import pvporcupine
import sounddevice as sd


class WakeWordListener:
    def __init__(self, access_key: str):
        self.porcupine = pvporcupine.create(
            access_key=access_key,
            keywords=["jarvis"],
        )
        self.frame_length = self.porcupine.frame_length
        self.sample_rate = self.porcupine.sample_rate

    def listen(self) -> None:
        """Block until 'Jarvis' is detected."""
        print("\n🟢 En écoute...")

        with sd.InputStream(
            samplerate=self.sample_rate,
            channels=1,
            dtype="int16",
            blocksize=self.frame_length,
        ) as stream:
            while True:
                audio_frame, _ = stream.read(self.frame_length)
                pcm = audio_frame.flatten()
                keyword_index = self.porcupine.process(pcm)
                if keyword_index >= 0:
                    print("🎙️  Je vous écoute...")
                    return

    def cleanup(self) -> None:
        self.porcupine.delete()
