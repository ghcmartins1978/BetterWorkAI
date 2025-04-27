"""
Webcam capture module with privacy features.
This module is used to capture video from the webcam, apply privacy filters,
and provide frames for processing by other components.
"""

import os
import time
import threading
import logging
import tempfile
import base64
from io import BytesIO
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

import cv2
import numpy as np
from PIL import Image

logger = logging.getLogger(__name__)

class WebcamCapture:
    """
    Handles webcam capture with privacy-preserving filters.
    """
    def __init__(self, settings):
        """
        Initialize the webcam capture system.
        
        Args:
            settings: Application settings object
        """
        self.settings = settings
        self.is_capturing = False
        self.capture_thread = None
        self.camera = None
        self.current_frame = None
        self.frame_lock = threading.Lock()
        self.last_frame_time = 0
        self.privacy_mode = settings.get_setting('webcam_privacy_mode', default='blur')  # blur, pixelate, silhouette, none
        self.blur_strength = settings.get_setting('webcam_blur_strength', default=15)
        self.pixelate_factor = settings.get_setting('webcam_pixelate_factor', default=15)
        
    def start_capture(self):
        """Start webcam capture"""
        if self.is_capturing:
            logger.warning("Webcam capture already running")
            return
        
        self.is_capturing = True
        self.capture_thread = threading.Thread(target=self._capture_loop)
        self.capture_thread.daemon = True
        self.capture_thread.start()
        logger.info("Webcam capture started")
    
    def stop_capture(self):
        """Stop webcam capture"""
        self.is_capturing = False
        if self.capture_thread:
            self.capture_thread.join(timeout=2.0)
            self.capture_thread = None
        
        # Release the camera if it was opened
        if self.camera:
            self.camera.release()
            self.camera = None
            
        logger.info("Webcam capture stopped")
    
    def _capture_loop(self):
        """Main video capture loop running in a background thread"""
        try:
            # Find and open the camera
            self.camera = cv2.VideoCapture(0)
            if not self.camera.isOpened():
                logger.error("Failed to open webcam")
                self.is_capturing = False
                return
                
            logger.info("Webcam opened successfully")
            
            # Get camera properties
            width = int(self.camera.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(self.camera.get(cv2.CAP_PROP_FRAME_HEIGHT))
            fps = self.camera.get(cv2.CAP_PROP_FPS)
            
            logger.info(f"Webcam resolution: {width}x{height}, FPS: {fps}")
            
            # Main capture loop
            while self.is_capturing:
                # Capture frame
                ret, frame = self.camera.read()
                if not ret:
                    logger.warning("Failed to capture frame from webcam")
                    time.sleep(0.1)
                    continue
                
                # Apply privacy filter if enabled
                if self.privacy_mode != 'none':
                    frame = self._apply_privacy_filter(frame)
                
                # Store the processed frame
                with self.frame_lock:
                    self.current_frame = frame
                    self.last_frame_time = time.time()
                
                # Avoid using too much CPU
                time.sleep(1.0 / 30)  # Cap at 30 FPS
                
        except Exception as e:
            logger.error(f"Error in webcam capture loop: {e}")
            self.is_capturing = False
        finally:
            # Release the camera if it was opened
            if self.camera:
                self.camera.release()
                self.camera = None
                
            logger.info("Webcam resources released")
    
    def _apply_privacy_filter(self, frame: np.ndarray) -> np.ndarray:
        """
        Apply the selected privacy filter to the frame.
        
        Args:
            frame: Input video frame (BGR format)
            
        Returns:
            Processed frame with privacy filter applied
        """
        try:
            if self.privacy_mode == 'blur':
                return self._apply_blur(frame)
            elif self.privacy_mode == 'pixelate':
                return self._apply_pixelate(frame)
            elif self.privacy_mode == 'silhouette':
                return self._apply_silhouette(frame)
            else:
                return frame
        except Exception as e:
            logger.error(f"Error applying privacy filter: {e}")
            return frame
    
    def _apply_blur(self, frame: np.ndarray) -> np.ndarray:
        """Apply Gaussian blur to the frame"""
        return cv2.GaussianBlur(frame, (self.blur_strength, self.blur_strength), 0)
    
    def _apply_pixelate(self, frame: np.ndarray) -> np.ndarray:
        """Pixelate the frame by downscaling and upscaling"""
        h, w = frame.shape[:2]
        factor = self.pixelate_factor
        
        # Resize down
        small = cv2.resize(frame, (w // factor, h // factor), 
                          interpolation=cv2.INTER_LINEAR)
        
        # Resize back up using nearest-neighbor interpolation
        return cv2.resize(small, (w, h), interpolation=cv2.INTER_NEAREST)
    
    def _apply_silhouette(self, frame: np.ndarray) -> np.ndarray:
        """Extract silhouette from the frame"""
        # Convert to grayscale
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Apply threshold
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        
        # Create a 3-channel silhouette by stacking the threshold
        silhouette = cv2.merge([thresh, thresh, thresh])
        
        return silhouette
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the most recent frame.
        
        Returns:
            Current frame or None if no frame is available
        """
        with self.frame_lock:
            if self.current_frame is not None:
                return self.current_frame.copy()
        return None
    
    def get_frame_as_base64(self) -> Optional[str]:
        """
        Get the current frame as base64 encoded JPEG.
        
        Returns:
            Base64 encoded string or None if no frame is available
        """
        frame = self.get_current_frame()
        if frame is None:
            return None
            
        # Convert to JPEG
        _, buffer = cv2.imencode('.jpg', frame)
        
        # Convert to base64
        base64_image = base64.b64encode(buffer).decode('utf-8')
        
        return base64_image
    
    def save_frame(self, output_path: str) -> bool:
        """
        Save the current frame to a file.
        
        Args:
            output_path: Path to save the image
            
        Returns:
            True if successful, False otherwise
        """
        frame = self.get_current_frame()
        if frame is None:
            return False
            
        try:
            cv2.imwrite(output_path, frame)
            return True
        except Exception as e:
            logger.error(f"Error saving frame: {e}")
            return False
    
    def detect_faces(self) -> List[Dict[str, Any]]:
        """
        Detect faces in the current frame.
        
        Returns:
            List of dictionaries containing face information (coordinates, etc.)
        """
        frame = self.get_current_frame()
        if frame is None:
            return []
            
        try:
            # Load Haar cascade for face detection
            face_cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
            face_cascade = cv2.CascadeClassifier(face_cascade_path)
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Detect faces
            faces = face_cascade.detectMultiScale(gray, 1.1, 4)
            
            # Format results
            results = []
            for (x, y, w, h) in faces:
                results.append({
                    'x': int(x),
                    'y': int(y),
                    'width': int(w),
                    'height': int(h),
                    'timestamp': datetime.now().isoformat()
                })
            
            return results
        except Exception as e:
            logger.error(f"Error detecting faces: {e}")
            return []