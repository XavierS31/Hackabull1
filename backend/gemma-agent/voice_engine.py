import os
from dotenv import load_dotenv
from elevenlabs.client import ElevenLabs
from elevenlabs import stream

load_dotenv()

class VoiceEngine:
    def __init__(self):
        self.client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
        # Using the newest high-speed model for 2026
        self.model = "eleven_flash_v2_5"
        self.voice_id = "JBFqnCBsd6RMkjVDRZzb" # (George)

    def say(self, text: str):
        print(f"Generating audio for: {text[:30]}...")
        
        # This returns a generator of audio chunks
        audio_stream = self.client.text_to_speech.stream(
            text=text,
            voice_id=self.voice_id,
            model_id=self.model,
            # optimize_streaming_latency=4 provides the fastest response
            optimize_streaming_latency=4
        )

        # The stream() function pipes the audio directly to your speakers via mpv
        stream(audio_stream)

if __name__ == "__main__":
    engine = VoiceEngine()
    engine.say("System online. I am ready to scan the hardware QR codes.")