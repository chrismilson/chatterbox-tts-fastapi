import argparse
import glob
import io
import os
import sys
import torchaudio as ta
import uvicorn

from chatterbox.tts import ChatterboxTTS
from fastapi import FastAPI
from fastapi.responses import StreamingResponse
from loguru import logger
from pydantic import BaseModel

MODEL = ChatterboxTTS.from_pretrained(device="cuda")
print(MODEL.sr)

class GenerateSpeechRequest(BaseModel):
    input: str
    model: str # Any value will use chatterboxTTS
    voice: str
    exaggeration: float = 0.5
    temperature: float = 0.5
    cfg_weight: float = 0.5

class ChatterboxAPI(FastAPI):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.voices = {}
        
        @self.get("/health")
        async def health():
            return {"status": "ok"}

        @self.get("/v1/api/voices")
        async def get_voices():
            return self.voices_list()
        
        @self.post("/v1/audio/speech", response_class=StreamingResponse)
        async def generate_speech(request: GenerateSpeechRequest):
            wav = MODEL.generate(
                request.input,
                audio_prompt_path=f"voices/{request.voice}.wav",
                exaggeration=request.exaggeration,
                temperature=request.temperature,
                cfg_weight=request.cfg_weight,
            )

            # TODO Can this be streamed as it is generated?
            buffer = io.BytesIO()
            ta.save(buffer, wav, MODEL.sr, format="wav")
            buffer.seek(0)

            return StreamingResponse(buffer, media_type="audio/wav")
        
    def register_voice(self, name):
        self.voices[name] = name
    
    def deregister_voice(self, name):
        if name in self.voices:
            del self.voices[name]

    def voice_info(self, voice):
        return {
            "id": voice,
            "object": "voice",
            "created": 0,
            "owned_by": "user",
        }

    def voices_list(self):
        return {
            "object": "list",
            "data": [self.voice_info(voice) for voice in set(self.voices.keys())]
        }

app = ChatterboxAPI()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Chatterbox-TTS API Server",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("-P", "--port", action="store", default=8080, help="Server TCP port")
    parser.add_argument("-H", "--host", action="store", default="0.0.0.0", help="Host to listen on")
    parser.add_argument("-L", "--log-level", default="INFO", choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"], help="Log level")

    args = parser.parse_args()

    # Load voices
    for voice_path in glob.glob('voices/*.wav'):
        voice = os.path.splitext(os.path.basename(voice_path))[0]
        app.register_voice(voice)

    logger.remove()
    logger.add(sink=sys.stderr, level=args.log_level)

    uvicorn.run(app, host=args.host, port=args.port)