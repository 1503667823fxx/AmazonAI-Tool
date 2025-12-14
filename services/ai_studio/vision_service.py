import streamlit as st
import io
import base64
import time
from typing import Optional, Tuple, Dict, Any, List
from PIL import Image
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

class ImageGenerationResult:
    """Enhanced result object for image generation operations"""
    def __init__(self, image_data: Optional[bytes] = None, error: Optional[str] = None):
        self.image_data = image_data
        self.error = error
        self.success = image_data is not None
        self.generation_time = None
        self.model_used = None
        self.prompt_used = None
        self.reference_indicator = None
        
    def get_preview_data(self) -> Optional[str]:
        """Get base64 encoded image data for preview"""
        if self.image_data:
            return base64.b64encode(self.image_data).decode()
        return None
    
    def get_download_data(self) -> Optional[bytes]:
        """Get raw image data for download"""
        return self.image_data

class StudioVisionService:
    def __init__(self, api_key):
        self.api_key = api_key or st.secrets.get("GOOGLE_API_KEY")
        if self.api_key:
            genai.configure(api_key=self.api_key)
        
        # Enhanced configuration
        self.max_retries = 3
        self.retry_delay = 1.0
        self.supported_formats = ['JPEG', 'PNG', 'WEBP']
        self.max_image_size = 20 * 1024 * 1024  # 20MB

    def resolve_reference_image(self, current_msg: Dict[str, Any], message_history: List[Dict[str, Any]]) -> Tuple[Optional[Image.Image], Optional[str]]:
        """
        Enhanced reference image resolution with better visual feedback and error handling
        
        Args:
            current_msg: Current user message with potential reference images
            message_history: Previous conversation messages
            
        Returns:
            Tuple of (reference_image, indicator_text)
        """
        try:
            # 1. Priority: Use user-uploaded images from current message
            if current_msg.get("ref_images") and len(current_msg["ref_images"]) > 0:
                ref_images = current_msg["ref_images"]
                
                # Handle multiple images - validate each and use the first valid one
                for i, ref_img in enumerate(ref_images):
                    try:
                        if self._validate_reference_image(ref_img):
                            indicator = f"📸 Using uploaded reference image"
                            if hasattr(ref_img, 'name'):
                                indicator += f": {ref_img.name}"
                            
                            # Add info about multiple images if applicable
                            if len(ref_images) > 1:
                                indicator += f" (image {i+1} of {len(ref_images)})"
                                
                            return ref_img, indicator
                        else:
                            # Log validation failure for this image
                            if hasattr(ref_img, 'name'):
                                st.warning(f"Skipping invalid image: {ref_img.name}")
                            continue
                            
                    except Exception as img_error:
                        # Log error for this specific image and continue to next
                        img_name = getattr(ref_img, 'name', f'image_{i+1}')
                        st.warning(f"Error processing {img_name}: {str(img_error)}")
                        continue
                
                # If we get here, no valid images were found
                return None, f"⚠️ None of the {len(ref_images)} uploaded images could be validated"
            
            # 2. Visual relay: Check for previous AI-generated images (iterative editing)
            if len(message_history) >= 1:
                # Look for the most recent AI message with image result
                for i in range(len(message_history) - 1, -1, -1):
                    prev_msg = message_history[i]
                    
                    if (prev_msg.get("role") == "model" and 
                        prev_msg.get("type") == "image_result" and 
                        prev_msg.get("hd_data")):
                        
                        try:
                            prev_bytes = prev_msg["hd_data"]
                            img = Image.open(io.BytesIO(prev_bytes))
                            
                            # Validate the previous image
                            if self._validate_image_data(prev_bytes):
                                indicator = "🔗 Auto-referencing previous generated image (iterative editing)"
                                return img, indicator
                            else:
                                continue  # Try next image in history
                                
                        except Exception as e:
                            st.warning(f"Could not load previous image: {str(e)}")
                            continue
            
            return None, None
            
        except Exception as e:
            st.error(f"Error resolving reference image: {str(e)}")
            return None, f"❌ Reference resolution error: {str(e)}"
    
    def _validate_reference_image(self, ref_img) -> bool:
        """Validate reference image for quality and format"""
        try:
            # Case 1: PIL Image object
            if isinstance(ref_img, Image.Image):
                width, height = ref_img.size  # This is a tuple (width, height)
                if width < 64 or height < 64:
                    st.warning("Reference image too small (minimum 64x64 pixels)")
                    return False
                if width > 4096 or height > 4096:
                    st.warning("Reference image too large (maximum 4096x4096 pixels)")
                    return False
                return True
            
            # Case 2: Streamlit uploaded file with file size and read capability
            elif hasattr(ref_img, 'size') and hasattr(ref_img, 'read'):
                # Check file size if it's an integer (file size in bytes)
                if isinstance(ref_img.size, int):
                    if ref_img.size > self.max_image_size:
                        st.warning(f"Reference image too large: {ref_img.size / (1024*1024):.1f}MB (max: {self.max_image_size / (1024*1024):.1f}MB)")
                        return False
                
                # Try to open as PIL Image for dimension validation
                try:
                    current_pos = ref_img.tell() if hasattr(ref_img, 'tell') else 0
                    
                    # Read and validate as PIL Image
                    img = Image.open(ref_img)
                    width, height = img.size
                    
                    # Reset file position
                    if hasattr(ref_img, 'seek'):
                        ref_img.seek(current_pos)
                    
                    # Validate dimensions
                    if width < 64 or height < 64:
                        st.warning("Reference image too small (minimum 64x64 pixels)")
                        return False
                    if width > 4096 or height > 4096:
                        st.warning("Reference image too large (maximum 4096x4096 pixels)")
                        return False
                    
                    return True
                    
                except Exception as img_error:
                    st.warning(f"Cannot validate uploaded file as image: {str(img_error)}")
                    return False
            
            # Case 3: Other objects - try to handle gracefully
            else:
                # If we can't validate it properly, assume it's valid
                # This prevents crashes while still allowing functionality
                return True
            
        except Exception as e:
            st.warning(f"Reference image validation error: {str(e)}")
            # Return True to allow functionality even if validation fails
            return True
    
    def _validate_image_data(self, image_data: bytes) -> bool:
        """Validate raw image data"""
        try:
            if len(image_data) < 100:  # Too small to be a valid image
                return False
            if len(image_data) > self.max_image_size:
                return False
            
            # Try to open as PIL Image to validate format
            img = Image.open(io.BytesIO(image_data))
            return img.format in self.supported_formats
            
        except Exception:
            return False

    def generate_image_with_progress(self, prompt: str, model_name: str, ref_image=None, 
                                   progress_callback=None) -> ImageGenerationResult:
        """
        Enhanced image generation with progress indicators and better error handling
        
        Args:
            prompt: Text prompt for image generation
            model_name: Model to use for generation
            ref_image: Optional reference image
            progress_callback: Optional callback for progress updates
            
        Returns:
            ImageGenerationResult with enhanced metadata
        """
        result = ImageGenerationResult()
        result.prompt_used = prompt
        result.model_used = model_name
        
        start_time = time.time()
        
        try:
            # Validate inputs
            if not prompt or len(prompt.strip()) < 3:
                result.error = "Prompt too short (minimum 3 characters)"
                return result
            
            if not self.api_key:
                result.error = "API key not configured"
                return result
            
            # Update progress
            if progress_callback:
                progress_callback("Initializing model...", 0.1)
            
            model = genai.GenerativeModel(model_name)
            inputs = [prompt]
            
            # Process reference image if provided
            if ref_image:
                if progress_callback:
                    progress_callback("Processing reference image...", 0.2)
                
                # Validate reference image with enhanced error handling
                try:
                    if not self._validate_reference_image(ref_image):
                        result.error = "Invalid reference image"
                        return result
                except Exception as validation_error:
                    result.error = f"Reference image validation error: {str(validation_error)}"
                    st.error(f"🔍 Validation error details: {str(validation_error)}")
                    return result
                
                inputs.append(ref_image)
                result.reference_indicator = "🔗 Using reference image for generation"
            
            # Configure generation parameters
            config = genai.types.GenerationConfig(
                temperature=0.7,
                candidate_count=1
            )
            
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            }
            
            # Generate image with retry logic
            for attempt in range(self.max_retries):
                try:
                    if progress_callback:
                        progress_callback(f"Generating image (attempt {attempt + 1}/{self.max_retries})...", 0.3 + (attempt * 0.2))
                    
                    response = model.generate_content(
                        inputs, 
                        generation_config=config, 
                        safety_settings=safety_settings
                    )
                    
                    if progress_callback:
                        progress_callback("Processing response...", 0.8)
                    
                    # Extract image data from response
                    if response.parts:
                        for part in response.parts:
                            if hasattr(part, "inline_data") and part.inline_data:
                                image_data = part.inline_data.data
                                
                                # Validate generated image
                                if self._validate_image_data(image_data):
                                    result.image_data = image_data
                                    result.generation_time = time.time() - start_time
                                    
                                    if progress_callback:
                                        progress_callback("Image generation complete!", 1.0)
                                    
                                    return result
                                else:
                                    result.error = "Generated image validation failed"
                                    return result
                    
                    # No image data in response
                    if attempt < self.max_retries - 1:
                        if progress_callback:
                            progress_callback(f"Retrying generation...", 0.4 + (attempt * 0.2))
                        time.sleep(self.retry_delay)
                        continue
                    else:
                        result.error = "No image data in response after all retries"
                        return result
                        
                except Exception as e:
                    if attempt < self.max_retries - 1:
                        if progress_callback:
                            progress_callback(f"Retrying after error: {str(e)}", 0.4 + (attempt * 0.2))
                        time.sleep(self.retry_delay * (attempt + 1))  # Exponential backoff
                        continue
                    else:
                        result.error = f"Generation failed after {self.max_retries} attempts: {str(e)}"
                        return result
            
        except Exception as e:
            result.error = f"Unexpected error: {str(e)}"
            return result
        
        result.error = "Unknown generation failure"
        return result
    
    def generate_image(self, prompt: str, model_name: str, ref_image=None) -> Optional[bytes]:
        """
        Legacy method for backward compatibility
        """
        result = self.generate_image_with_progress(prompt, model_name, ref_image)
        return result.image_data
    
    def create_high_quality_preview(self, image_data: bytes, max_size: Tuple[int, int] = (1024, 1024)) -> Optional[bytes]:
        """
        Create high-quality preview image with zoom support
        
        Args:
            image_data: Raw image data
            max_size: Maximum dimensions for preview
            
        Returns:
            Optimized preview image data
        """
        try:
            img = Image.open(io.BytesIO(image_data))
            
            # Maintain aspect ratio while resizing
            img.thumbnail(max_size, Image.Resampling.LANCZOS)
            
            # Save as high-quality JPEG for preview
            preview_buffer = io.BytesIO()
            img.save(preview_buffer, format='JPEG', quality=95, optimize=True)
            
            return preview_buffer.getvalue()
            
        except Exception as e:
            st.error(f"Preview generation error: {str(e)}")
            return None
    
    def get_image_metadata(self, image_data: bytes) -> Dict[str, Any]:
        """
        Extract metadata from image for better user feedback
        
        Args:
            image_data: Raw image data
            
        Returns:
            Dictionary with image metadata
        """
        try:
            img = Image.open(io.BytesIO(image_data))
            
            return {
                'format': img.format,
                'size': img.size,
                'mode': img.mode,
                'file_size': len(image_data),
                'file_size_mb': len(image_data) / (1024 * 1024),
                'aspect_ratio': img.size[0] / img.size[1] if img.size[1] > 0 else 1.0
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def supports_iterative_editing(self) -> bool:
        """Check if the service supports iterative editing workflows"""
        return True
    
    def get_generation_capabilities(self) -> Dict[str, Any]:
        """Get information about generation capabilities"""
        return {
            'max_retries': self.max_retries,
            'supported_formats': self.supported_formats,
            'max_image_size_mb': self.max_image_size / (1024 * 1024),
            'supports_reference_images': True,
            'supports_iterative_editing': True,
            'supports_progress_tracking': True,
            'supports_high_quality_preview': True
        }
