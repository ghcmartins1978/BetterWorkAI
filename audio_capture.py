"""
Microphone capture module with ring-buffer and STT functionality.
This module is used to capture audio from the microphone, store it in a ring buffer,
and convert speech to text using either OpenAI's Whisper API or a local STT engine.
"""

import os
import time
import threading
import collections
import logging
import base64
import json
import wave
import numpy as np
import pyaudio
import soundfile as sf
from typing import Optional, Dict, Any, Deque, Tuple
from datetime import datetime
import tempfile

# The STT processing can use either OpenAI's API or a local engine based on user preference
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

logger = logging.getLogger(__name__)

class AudioRingBuffer:
    """
    A ring buffer for storing audio data.
    This allows us to keep a rolling window of recent audio.
    """
    def __init__(self, max_size: int = 10):
        """
        Initialize the ring buffer.
        
        Args:
            max_size: Maximum number of audio chunks to store (each chunk is typically 1-2 seconds)
        """
        self.buffer: Deque[bytes] = collections.deque(maxlen=max_size)
        self.lock = threading.Lock()
    
    def add(self, audio_chunk: bytes):
        """
        Add an audio chunk to the buffer.
        
        Args:
            audio_chunk: Raw audio data bytes
        """
        with self.lock:
            self.buffer.append(audio_chunk)
    
    def get_all(self) -> bytes:
        """
        Get all audio data in the buffer as a single bytes object.
        
        Returns:
            Combined audio data
        """
        with self.lock:
            return b''.join(self.buffer)
    
    def clear(self):
        """Clear the buffer"""
        with self.lock:
            self.buffer.clear()
    
    def size(self) -> int:
        """
        Get the current size of the buffer.
        
        Returns:
            Number of chunks in the buffer
        """
        with self.lock:
            return len(self.buffer)


class AudioCapture:
    """
    Handles microphone capture with ring buffer storage and STT conversion.
    """
    def __init__(self, settings, buffer_size: int = 15, local_stt_model: Optional[str] = None):
        """
        Initialize the audio capture system.
        
        Args:
            settings: Application settings object
            buffer_size: Size of the ring buffer in seconds
            local_stt_model: Path to local STT model (if not using OpenAI)
        """
        self.settings = settings
        self.is_capturing = False
        self.capture_thread = None
        self.ring_buffer = AudioRingBuffer(max_size=buffer_size)
        self.local_stt_model = local_stt_model
        self.openai_client = None
        
        # Initialize OpenAI client if available and enabled
        if HAS_OPENAI and settings.get_setting('audio_use_openai_whisper', default=True):
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized for STT")
            else:
                logger.warning("OpenAI API key not found. Speech-to-text will not work.")
        
        # Initialize local STT model if specified
        if not self.openai_client and local_stt_model:
            try:
                # This would be implemented using a local STT engine library
                # For example, using Vosk, Whisper.cpp, or another local STT engine
                logger.info(f"Using local STT model: {local_stt_model}")
            except Exception as e:
                logger.error(f"Failed to initialize local STT model: {e}")
    
    def start_capture(self):
        """Start audio capture from the microphone"""
        if self.is_capturing:
            logger.warning("Audio capture already running")
            return
        
        self.is_capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        logger.info("Audio capture started")
    
    def stop_capture(self):
        """Stop audio capture"""
        self.is_capturing = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
            self.capture_thread = None
        logger.info("Audio capture stopped")
    
    def _capture_loop(self):
        """Main audio capture loop running in a background thread"""
        # Audio settings
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000  # 16kHz sampling rate, good for speech
        CHUNK_SIZE = 1024  # Number of frames per buffer
        
        audio = pyaudio.PyAudio()
        stream = None
        
        try:
            # Find the correct input device
            input_device_index = self._find_input_device(audio)
            if input_device_index is None:
                logger.error("No suitable input device found")
                self.is_capturing = False
                return
                
            # Open the microphone stream
            stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                input_device_index=input_device_index,
                frames_per_buffer=CHUNK_SIZE
            )
            
            logger.info(f"Audio capture started on device index {input_device_index}")
            
            # Main capture loop
            while self.is_capturing:
                # Read audio chunk from the microphone
                try:
                    chunk = stream.read(CHUNK_SIZE, exception_on_overflow=False)
                    self.ring_buffer.add(chunk)
                    
                    # Process the audio for trigger words or commands
                    self._process_audio_for_triggers()
                except IOError as e:
                    # Handle buffer overflow gracefully
                    logger.warning(f"Buffer overflow: {e}")
                    continue
                
        except Exception as e:
            logger.error(f"Error in audio capture loop: {e}")
            self.is_capturing = False
        finally:
            # Clean up resources
            if stream:
                stream.stop_stream()
                stream.close()
            audio.terminate()
            logger.info("Audio capture resources released")
            
    def _find_input_device(self, audio: pyaudio.PyAudio) -> Optional[int]:
        """
        Find a suitable input device (microphone).
        
        Args:
            audio: PyAudio instance
            
        Returns:
            Device index or None if no suitable device is found
        """
        # Get the default input device
        try:
            default_device_index = audio.get_default_input_device_info()['index']
            logger.info(f"Default input device index: {default_device_index}")
            return default_device_index
        except IOError:
            # If no default device, try to find any input device
            pass
            
        # If no default device or it failed, try to find any input device
        for i in range(audio.get_device_count()):
            device_info = audio.get_device_info_by_index(i)
            if device_info['maxInputChannels'] > 0:
                logger.info(f"Found input device: {device_info['name']} (index {i})")
                return i
                
        return None
    
    def _process_audio_for_triggers(self):
        """
        Process the captured audio for trigger words or commands.
        This can be used to detect wake words or commands without sending all audio to the STT service.
        """
        # This would be implemented using a keyword detection library
        # For now, we just simulate random triggers for testing
        pass
    
    def transcribe_buffer(self) -> Dict[str, Any]:
        """
        Transcribe the current audio buffer using STT.
        
        Returns:
            Dictionary containing transcription result and metadata
        """
        if self.ring_buffer.size() == 0:
            return {"text": "", "success": False, "error": "Buffer is empty"}
        
        # Get all audio data from the buffer
        audio_data = self.ring_buffer.get_all()
        
        # Audio format settings - these must match the capture settings
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000  # 16kHz sampling rate
        
        # Create a temporary WAV file with proper formatting
        temp_filename = None
        try:
            # Convert audio data to numpy array for processing
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            
            # Create a temporary file to store the WAV
            temp_filename = tempfile.mktemp(suffix='.wav')
            
            # Write the audio data to a properly formatted WAV file
            with wave.open(temp_filename, 'wb') as wf:
                wf.setnchannels(CHANNELS)
                wf.setsampwidth(pyaudio.get_sample_size(FORMAT))
                wf.setframerate(RATE)
                wf.writeframes(audio_data)
            
            logger.info(f"Created WAV file from buffer: {temp_filename} ({len(audio_array)} samples)")
            
            # Use OpenAI's Whisper API if available
            if self.openai_client:
                return self._transcribe_with_openai(temp_filename)
            elif self.local_stt_model:
                return self._transcribe_with_local_model(temp_filename)
            else:
                return {"text": "", "success": False, "error": "No STT engine available"}
        except Exception as e:
            logger.error(f"Error in transcription: {e}")
            return {"text": "", "success": False, "error": str(e)}
        finally:
            # Clean up the temporary file
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                    logger.debug(f"Deleted temporary file: {temp_filename}")
                except:
                    pass
    
    def _transcribe_with_openai(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI's Whisper API.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription result and metadata
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Can be made configurable
                )
            
            # Extract and return the transcription
            return {
                "text": response.text,
                "success": True,
                "engine": "openai-whisper",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"OpenAI transcription error: {e}")
            return {"text": "", "success": False, "error": str(e), "engine": "openai-whisper"}
    
    def _transcribe_with_local_model(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using a local STT model.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription result and metadata
        """
        # This would be implemented using a local STT engine
        # For example, Vosk, Whisper.cpp, or another local STT engine
        # For now, we return a placeholder result
        logger.info(f"Local transcription requested for {audio_file_path}")
        return {
            "text": "Local STT not yet implemented",
            "success": False,
            "engine": "local-model",
            "timestamp": datetime.now().isoformat()
        }