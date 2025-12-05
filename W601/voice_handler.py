"""
Voice Input Handler Module
Handles WebSocket-based real-time voice input and speech-to-text conversion
"""
import asyncio
import base64
import json
import io
import wave
import tempfile
from typing import Optional, Callable, AsyncGenerator
from pathlib import Path

# Speech recognition
try:
    import speech_recognition as sr
    SPEECH_RECOGNITION_AVAILABLE = True
except ImportError:
    SPEECH_RECOGNITION_AVAILABLE = False

# OpenAI Whisper API
from openai import OpenAI
import config


class VoiceHandler:
    """Handle voice input and convert to text"""
    
    def __init__(self):
        self.recognizer = sr.Recognizer() if SPEECH_RECOGNITION_AVAILABLE else None
        self.openai_client = OpenAI(
            api_key=config.OPENAI_API_KEY,
            base_url=config.OPENAI_BASE_URL
        ) if config.OPENAI_API_KEY else None
        
        # Audio buffer for streaming
        self.audio_buffer = bytearray()
        self.sample_rate = 16000
        self.sample_width = 2  # 16-bit audio
        self.channels = 1
        
    async def process_audio_chunk(self, audio_data: bytes) -> None:
        """Process incoming audio chunk from WebSocket"""
        self.audio_buffer.extend(audio_data)
        
    def clear_buffer(self) -> None:
        """Clear the audio buffer"""
        self.audio_buffer = bytearray()
        
    async def transcribe_buffer(self) -> str:
        """Transcribe the accumulated audio buffer"""
        if not self.audio_buffer:
            return ""
            
        # Convert buffer to WAV format
        wav_data = self._create_wav_from_buffer()
        
        # Try OpenAI Whisper first
        if self.openai_client:
            text = await self._transcribe_with_whisper(wav_data)
            if text:
                return text
                
        # Fallback to local speech recognition
        if self.recognizer:
            text = await self._transcribe_with_local(wav_data)
            if text:
                return text
                
        return ""
    
    def _create_wav_from_buffer(self) -> bytes:
        """Create WAV file from audio buffer"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.sample_width)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(bytes(self.audio_buffer))
            
        wav_buffer.seek(0)
        return wav_buffer.read()
    
    async def _transcribe_with_whisper(self, wav_data: bytes) -> Optional[str]:
        """Transcribe using OpenAI Whisper API"""
        try:
            # Create temp file for API
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as tmp:
                tmp.write(wav_data)
                tmp_path = tmp.name
                
            with open(tmp_path, 'rb') as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="zh"  # Support Chinese
                )
                
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
            
            return response.text
            
        except Exception as e:
            print(f"Whisper transcription error: {e}")
            return None
    
    async def _transcribe_with_local(self, wav_data: bytes) -> Optional[str]:
        """Transcribe using local speech recognition"""
        if not self.recognizer:
            return None
            
        try:
            # Create AudioData from WAV
            wav_buffer = io.BytesIO(wav_data)
            with sr.AudioFile(wav_buffer) as source:
                audio = self.recognizer.record(source)
                
            # Try Google Speech Recognition (free tier)
            text = self.recognizer.recognize_google(audio, language='zh-CN')
            return text
            
        except sr.UnknownValueError:
            return ""
        except sr.RequestError as e:
            print(f"Local recognition error: {e}")
            return None
        except Exception as e:
            print(f"Recognition error: {e}")
            return None


class WebSocketVoiceSession:
    """Manage a WebSocket voice input session"""
    
    def __init__(self, websocket, on_transcription: Callable):
        self.websocket = websocket
        self.on_transcription = on_transcription
        self.voice_handler = VoiceHandler()
        self.is_recording = False
        self.silence_threshold = 1.0  # seconds of silence to trigger transcription
        self.last_audio_time = None
        
    async def start_recording(self):
        """Start recording session"""
        self.is_recording = True
        self.voice_handler.clear_buffer()
        await self._send_status("recording_started")
        
    async def stop_recording(self) -> str:
        """Stop recording and get transcription"""
        self.is_recording = False
        text = await self.voice_handler.transcribe_buffer()
        self.voice_handler.clear_buffer()
        await self._send_status("recording_stopped", {"text": text})
        return text
        
    async def handle_audio_data(self, data: dict):
        """Handle incoming audio data from WebSocket"""
        if not self.is_recording:
            return
            
        # Decode base64 audio data
        audio_bytes = base64.b64decode(data.get('audio', ''))
        await self.voice_handler.process_audio_chunk(audio_bytes)
        
        # Update last audio time
        import time
        self.last_audio_time = time.time()
        
    async def handle_message(self, message: str) -> Optional[str]:
        """Handle WebSocket message"""
        try:
            data = json.loads(message)
            msg_type = data.get('type')
            
            if msg_type == 'start_recording':
                await self.start_recording()
                
            elif msg_type == 'stop_recording':
                text = await self.stop_recording()
                if text and self.on_transcription:
                    await self.on_transcription(text)
                return text
                
            elif msg_type == 'audio_data':
                await self.handle_audio_data(data)
                
            elif msg_type == 'ping':
                await self._send_status("pong")
                
        except json.JSONDecodeError:
            await self._send_error("Invalid JSON message")
        except Exception as e:
            await self._send_error(str(e))
            
        return None
    
    async def _send_status(self, status: str, extra: dict = None):
        """Send status message to client"""
        message = {"type": "status", "status": status}
        if extra:
            message.update(extra)
        await self.websocket.send_json(message)
        
    async def _send_error(self, error: str):
        """Send error message to client"""
        await self.websocket.send_json({
            "type": "error",
            "error": error
        })


class AudioStreamProcessor:
    """Process audio streams for voice-activity detection"""
    
    def __init__(self, sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.energy_threshold = 300  # Adjust based on environment
        
    def detect_speech(self, audio_chunk: bytes) -> bool:
        """Detect if audio chunk contains speech"""
        import struct
        
        # Calculate RMS energy
        samples = struct.unpack(f'{len(audio_chunk)//2}h', audio_chunk)
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
        
        return rms > self.energy_threshold
    
    def get_audio_level(self, audio_chunk: bytes) -> float:
        """Get normalized audio level (0-1)"""
        import struct
        
        samples = struct.unpack(f'{len(audio_chunk)//2}h', audio_chunk)
        rms = (sum(s**2 for s in samples) / len(samples)) ** 0.5
        
        # Normalize to 0-1 range (assuming 16-bit audio max)
        return min(rms / 32768.0, 1.0)

