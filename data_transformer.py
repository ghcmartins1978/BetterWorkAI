"""
Data Transformer Module for BettermanAI

This module provides functions for transforming different types of data (images, audio, PDFs)
into formats that can be analyzed by LLMs. It serves as a bridge between raw data and AI analysis.
"""

import os
import base64
import tempfile
import logging
from io import BytesIO
from typing import Dict, Any, Optional, List, Tuple, Union
from datetime import datetime

import cv2
import numpy as np
from PIL import Image
import requests

# For OCR functionality
try:
    import pytesseract
    HAS_TESSERACT = True
except ImportError:
    HAS_TESSERACT = False

# For PDF processing
try:
    from pdfminer.high_level import extract_text
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False

# For OpenAI integration
try:
    from openai import OpenAI
    HAS_OPENAI = True
except ImportError:
    HAS_OPENAI = False

# For Claude/Anthropic integration
try:
    from anthropic import Anthropic
    HAS_ANTHROPIC = True
except ImportError:
    HAS_ANTHROPIC = False

logger = logging.getLogger(__name__)

class DataTransformer:
    """
    Handles transformation of various data types into formats usable by LLMs.
    """
    def __init__(self, settings):
        """
        Initialize the data transformer.
        
        Args:
            settings: Application settings object
        """
        self.settings = settings
        self.openai_client = None
        self.anthropic_client = None
        
        # Initialize OpenAI client if available
        if HAS_OPENAI:
            api_key = os.environ.get('OPENAI_API_KEY')
            if api_key:
                self.openai_client = OpenAI(api_key=api_key)
                logger.info("OpenAI client initialized for data transformation")
        
        # Initialize Anthropic client if available
        if HAS_ANTHROPIC:
            api_key = os.environ.get('ANTHROPIC_API_KEY')
            if api_key:
                self.anthropic_client = Anthropic(api_key=api_key)
                logger.info("Anthropic client initialized for data transformation")
    
    def transform_image(self, image_data: Union[str, bytes, np.ndarray]) -> Dict[str, Any]:
        """
        Transform an image into a textual description using AI.
        
        Args:
            image_data: Image data as a base64 string, bytes, or numpy array
            
        Returns:
            Dictionary containing transformation results
        """
        # Convert input to base64 encoded string if it's not already
        if isinstance(image_data, np.ndarray):
            # Convert OpenCV image (numpy array) to base64
            _, buffer = cv2.imencode('.jpg', image_data)
            image_base64 = base64.b64encode(buffer).decode('utf-8')
        elif isinstance(image_data, bytes):
            # Convert bytes to base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')
        elif isinstance(image_data, str) and image_data.startswith('data:image'):
            # Extract base64 part from data URL
            image_base64 = image_data.split(',')[1]
        else:
            # Assume it's already a base64 string
            image_base64 = image_data
        
        # First try to use OpenAI for image analysis
        if self.openai_client:
            return self._describe_image_with_openai(image_base64)
        # Then try Anthropic if available
        elif self.anthropic_client:
            return self._describe_image_with_anthropic(image_base64)
        # Fall back to OCR if available
        elif HAS_TESSERACT:
            return self._extract_text_with_ocr(image_base64)
        else:
            return {
                "success": False,
                "text": "",
                "error": "No image analysis services available",
                "timestamp": datetime.now().isoformat()
            }
    
    def transform_audio(self, audio_data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Transform audio data into text using speech-to-text.
        
        Args:
            audio_data: Audio data as a file path or bytes
            
        Returns:
            Dictionary containing transformation results
        """
        temp_filename = None
        try:
            # Create a temporary file if audio_data is bytes
            if isinstance(audio_data, bytes):
                temp_filename = tempfile.mktemp(suffix='.wav')
                with open(temp_filename, 'wb') as f:
                    f.write(audio_data)
                audio_file_path = temp_filename
            else:
                # Assume it's a file path
                audio_file_path = audio_data
            
            # Use OpenAI's Whisper API if available
            if self.openai_client:
                return self._transcribe_audio_with_openai(audio_file_path)
            else:
                return {
                    "success": False,
                    "text": "",
                    "error": "No audio transcription services available",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error in audio transformation: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            # Clean up the temporary file
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except:
                    pass
    
    def transform_pdf(self, pdf_data: Union[str, bytes]) -> Dict[str, Any]:
        """
        Extract text from a PDF document.
        
        Args:
            pdf_data: PDF data as a file path or bytes
            
        Returns:
            Dictionary containing transformation results
        """
        temp_filename = None
        try:
            # Create a temporary file if pdf_data is bytes
            if isinstance(pdf_data, bytes):
                temp_filename = tempfile.mktemp(suffix='.pdf')
                with open(temp_filename, 'wb') as f:
                    f.write(pdf_data)
                pdf_file_path = temp_filename
            else:
                # Assume it's a file path
                pdf_file_path = pdf_data
            
            # Use pdfminer if available
            if HAS_PDFMINER:
                text = extract_text(pdf_file_path)
                return {
                    "success": True,
                    "text": text,
                    "pages": len(text.split('\f')) if text else 0,
                    "engine": "pdfminer",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "success": False,
                    "text": "",
                    "error": "PDF extraction library not available",
                    "timestamp": datetime.now().isoformat()
                }
        except Exception as e:
            logger.error(f"Error in PDF transformation: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
        finally:
            # Clean up the temporary file
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except:
                    pass
    
    def _describe_image_with_openai(self, image_base64: str) -> Dict[str, Any]:
        """
        Generate a description of an image using OpenAI's vision capabilities.
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dictionary containing description and metadata
        """
        try:
            # the newest OpenAI model is "gpt-4o" which was released May 13, 2024.
            # do not change this unless explicitly requested by the user
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Describe this image in detail, including any visible text, key elements, and context."
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"}
                            }
                        ]
                    }
                ],
                max_tokens=300
            )
            
            return {
                "success": True,
                "text": response.choices[0].message.content,
                "engine": "openai-vision",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"OpenAI image description error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "engine": "openai-vision",
                "timestamp": datetime.now().isoformat()
            }
    
    def _describe_image_with_anthropic(self, image_base64: str) -> Dict[str, Any]:
        """
        Generate a description of an image using Anthropic's vision capabilities.
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dictionary containing description and metadata
        """
        try:
            # the newest Anthropic model is "claude-3-5-sonnet-20241022" which was released October 22, 2024
            # do not change this unless explicitly requested by the user
            message = self.anthropic_client.messages.create(
                model="claude-3-5-sonnet-20241022",
                max_tokens=300,
                content=[
                    {
                        "type": "text",
                        "text": "Describe this image in detail, including any visible text, key elements, and context."
                    },
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": image_base64
                        }
                    }
                ]
            )
            
            return {
                "success": True,
                "text": message.content[0].text,
                "engine": "anthropic-vision",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Anthropic image description error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "engine": "anthropic-vision",
                "timestamp": datetime.now().isoformat()
            }
    
    def _extract_text_with_ocr(self, image_base64: str) -> Dict[str, Any]:
        """
        Extract text from an image using OCR (Optical Character Recognition).
        
        Args:
            image_base64: Base64 encoded image
            
        Returns:
            Dictionary containing extracted text and metadata
        """
        try:
            # Convert base64 to image
            image_bytes = base64.b64decode(image_base64)
            image = Image.open(BytesIO(image_bytes))
            
            # Use pytesseract for OCR
            text = pytesseract.image_to_string(image)
            
            return {
                "success": True,
                "text": text,
                "engine": "tesseract-ocr",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"OCR error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "engine": "tesseract-ocr",
                "timestamp": datetime.now().isoformat()
            }
    
    def _transcribe_audio_with_openai(self, audio_file_path: str) -> Dict[str, Any]:
        """
        Transcribe audio using OpenAI's Whisper API.
        
        Args:
            audio_file_path: Path to the audio file
            
        Returns:
            Dictionary containing transcription and metadata
        """
        try:
            with open(audio_file_path, "rb") as audio_file:
                response = self.openai_client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language="en"  # Can be made configurable
                )
            
            return {
                "success": True,
                "text": response.text,
                "engine": "openai-whisper",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"OpenAI transcription error: {e}")
            return {
                "success": False,
                "text": "",
                "error": str(e),
                "engine": "openai-whisper",
                "timestamp": datetime.now().isoformat()
            }

# API routes for the data transformer
def register_data_transformer_routes(app, data_transformer):
    """
    Register Flask routes for the data transformer API.
    
    Args:
        app: Flask application
        data_transformer: DataTransformer instance
    """
    @app.route('/api/transform/image', methods=['POST'])
    def transform_image_api():
        """API endpoint to transform an image"""
        from flask import request, jsonify
        
        # Check if image data is provided
        if 'image' not in request.files and 'image_base64' not in request.form:
            return jsonify({
                "success": False,
                "error": "No image provided"
            }), 400
        
        try:
            # Get image data
            if 'image' in request.files:
                image_file = request.files['image']
                image_data = image_file.read()
            else:
                image_data = request.form['image_base64']
            
            # Transform the image
            result = data_transformer.transform_image(image_data)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in image transformation API: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/transform/audio', methods=['POST'])
    def transform_audio_api():
        """API endpoint to transform audio"""
        from flask import request, jsonify
        
        # Check if audio data is provided
        if 'audio' not in request.files:
            return jsonify({
                "success": False,
                "error": "No audio file provided"
            }), 400
        
        try:
            # Get audio data
            audio_file = request.files['audio']
            audio_data = audio_file.read()
            
            # Transform the audio
            result = data_transformer.transform_audio(audio_data)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in audio transformation API: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500
    
    @app.route('/api/transform/pdf', methods=['POST'])
    def transform_pdf_api():
        """API endpoint to transform a PDF"""
        from flask import request, jsonify
        
        # Check if PDF data is provided
        if 'pdf' not in request.files:
            return jsonify({
                "success": False,
                "error": "No PDF file provided"
            }), 400
        
        try:
            # Get PDF data
            pdf_file = request.files['pdf']
            pdf_data = pdf_file.read()
            
            # Transform the PDF
            result = data_transformer.transform_pdf(pdf_data)
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in PDF transformation API: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500

    @app.route('/api/transform/url', methods=['POST'])
    def transform_url_api():
        """API endpoint to transform content from a URL"""
        from flask import request, jsonify
        import requests
        from trafilatura import fetch_url, extract
        
        # Check if URL is provided
        if 'url' not in request.form:
            return jsonify({
                "success": False,
                "error": "No URL provided"
            }), 400
        
        url = request.form['url']
        content_type = request.form.get('content_type', 'auto')
        
        try:
            # Fetch the content
            response = requests.get(url, stream=True, timeout=10)
            
            # Auto-detect content type if not specified
            if content_type == 'auto':
                mime_type = response.headers.get('Content-Type', '').split(';')[0].strip()
                if 'image' in mime_type:
                    content_type = 'image'
                elif 'audio' in mime_type:
                    content_type = 'audio'
                elif 'pdf' in mime_type:
                    content_type = 'pdf'
                elif 'text/html' in mime_type:
                    content_type = 'webpage'
                else:
                    content_type = 'text'
            
            # Transform based on content type
            if content_type == 'image':
                image_data = response.content
                result = data_transformer.transform_image(image_data)
            elif content_type == 'audio':
                audio_data = response.content
                result = data_transformer.transform_audio(audio_data)
            elif content_type == 'pdf':
                pdf_data = response.content
                result = data_transformer.transform_pdf(pdf_data)
            elif content_type == 'webpage':
                # Use trafilatura to extract main content from webpage
                downloaded = fetch_url(url)
                text = extract(downloaded)
                result = {
                    "success": True,
                    "text": text,
                    "engine": "trafilatura",
                    "timestamp": datetime.now().isoformat()
                }
            else:
                # Plain text
                text = response.text
                result = {
                    "success": True,
                    "text": text,
                    "engine": "direct",
                    "timestamp": datetime.now().isoformat()
                }
            
            return jsonify(result)
        except Exception as e:
            logger.error(f"Error in URL transformation API: {e}")
            return jsonify({
                "success": False,
                "error": str(e)
            }), 500