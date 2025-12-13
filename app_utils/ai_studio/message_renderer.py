import streamlit as st
from app_utils.ai_studio.tools import process_image_for_download
from typing import Dict, Any, List, Optional

def show_image_modal(image_bytes, title="Preview"):
    @st.dialog("🔍 图片预览")
    def _dialog_content():
        st.image(image_bytes, caption=title, use_container_width=True)
    _dialog_content()

class ResponsiveMessageRenderer:
    """Enhanced message renderer with responsive layout support"""
    
    def __init__(self):
        self.responsive_enabled = True
        self.message_density = "comfortable"
        self._inject_responsive_styles()
    
    def _inject_responsive_styles(self):
        """Inject responsive styles for message rendering"""
        st.markdown("""
        <style>
        /* Responsive Message Renderer Styles */
        .message-container {
            width: 100%;
            margin-bottom: 1rem;
        }
        
        .message-content {
            word-wrap: break-word;
            overflow-wrap: break-word;
        }
        
        .image-grid-responsive {
            display: grid;
            gap: 0.5rem;
            margin: 0.5rem 0;
        }
        
        /* Responsive grid layouts */
        @media (max-width: 480px) {
            .image-grid-responsive {
                grid-template-columns: repeat(1, 1fr);
            }
        }
        
        @media (min-width: 481px) and (max-width: 768px) {
            .image-grid-responsive {
                grid-template-columns: repeat(2, 1fr);
            }
        }
        
        @media (min-width: 769px) {
            .image-grid-responsive {
                grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
                max-width: 480px;
            }
        }
        
        .image-thumbnail-responsive {
            border-radius: 0.5rem;
            overflow: hidden;
            aspect-ratio: 1;
            background: #f3f4f6;
        }
        
        .image-thumbnail-responsive img {
            width: 100%;
            height: 100%;
            object-fit: cover;
        }
        
        /* Action buttons responsive */
        .action-buttons-responsive {
            display: flex;
            gap: 0.5rem;
            margin-top: 0.5rem;
            flex-wrap: wrap;
        }
        
        @media (max-width: 480px) {
            .action-buttons-responsive {
                flex-direction: column;
            }
            
            .action-buttons-responsive button {
                width: 100%;
            }
        }
        
        /* Typography responsive */
        .message-text-responsive {
            font-size: 1rem;
            line-height: 1.5;
        }
        
        @media (max-width: 480px) {
            .message-text-responsive {
                font-size: 0.9rem;
                line-height: 1.4;
            }
        }
        
        /* Image result responsive */
        .image-result-responsive {
            max-width: 100%;
            border-radius: 0.75rem;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
        }
        
        @media (max-width: 768px) {
            .image-result-responsive {
                width: 100% !important;
                height: auto !important;
            }
        }
        </style>
        """, unsafe_allow_html=True)
    
    def render_message_responsive(self, idx: int, msg: Dict[str, Any], 
                                on_delete: callable, on_regen: callable = None) -> None:
        """Render a message with responsive layout"""
        
        with st.chat_message(msg["role"]):
            # Render reference images with responsive grid
            if msg.get("ref_images"):
                self._render_reference_images_responsive(msg["ref_images"])
            
            # Render message content based on type
            if msg.get("type") == "image_result":
                self._render_image_result_responsive(msg, idx, on_delete)
            else:
                self._render_text_message_responsive(msg, idx, on_delete, on_regen)
    
    def _render_reference_images_responsive(self, ref_images: List) -> None:
        """Render reference images with responsive grid layout"""
        
        num_images = len(ref_images)
        
        if num_images == 1:
            # Single image - full width
            st.image(ref_images[0], use_container_width=True)
        elif num_images <= 4:
            # Small number of images - use columns
            cols = st.columns(min(num_images, 2))  # Max 2 columns on mobile
            for i, img in enumerate(ref_images):
                with cols[i % len(cols)]:
                    st.image(img, use_container_width=True)
        else:
            # Many images - use CSS grid
            st.markdown('<div class="image-grid-responsive">', unsafe_allow_html=True)
            
            # Create grid items
            for i, img in enumerate(ref_images):
                img_html = f'''
                <div class="image-thumbnail-responsive">
                    <img src="data:image/png;base64,{img}" alt="Reference image {i+1}">
                </div>
                '''
                st.markdown(img_html, unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
    
    def _render_image_result_responsive(self, msg: Dict[str, Any], idx: int, on_delete: callable) -> None:
        """Render image generation result with responsive controls"""
        
        key_pfx = f"msg_{msg['id']}"
        
        # Display image with responsive sizing
        st.markdown('<div class="image-result-container">', unsafe_allow_html=True)
        st.image(msg["content"], use_container_width=True, caption="Generated Image")
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Responsive action buttons
        col1, col2, col3 = st.columns([1, 1, 2])
        
        with col1:
            if st.button("🔍 View", key=f"{key_pfx}_zoom", use_container_width=True):
                show_image_modal(msg["hd_data"], f"Result-{msg['id']}")
        
        with col2:
            final_bytes, mime = process_image_for_download(msg["hd_data"], format="JPEG")
            st.download_button(
                "📥 Save", 
                data=final_bytes, 
                file_name=f"gen_{msg['id']}.jpg", 
                mime=mime, 
                key=f"{key_pfx}_dl",
                use_container_width=True
            )
        
        with col3:
            if st.button("🗑️ Delete", key=f"{key_pfx}_del", use_container_width=True):
                on_delete(idx)
    
    def _render_text_message_responsive(self, msg: Dict[str, Any], idx: int, 
                                      on_delete: callable, on_regen: callable = None) -> None:
        """Render text message with responsive layout"""
        
        key_pfx = f"msg_{msg['id']}"
        
        # Render message content with responsive typography
        st.markdown(f'<div class="message-text-responsive">{msg["content"]}</div>', 
                   unsafe_allow_html=True)
        
        # Responsive action buttons
        if msg["role"] == "model" and on_regen:
            col1, col2, col3 = st.columns([1, 1, 4])
        else:
            col1, col2 = st.columns([1, 5])
            col3 = None
        
        with col1:
            if st.button("🗑️", key=f"{key_pfx}_del_t", help="Delete message", use_container_width=True):
                on_delete(idx)
        
        if col3 and msg["role"] == "model" and on_regen:
            with col2:
                if st.button("🔄", key=f"{key_pfx}_rg", help="Regenerate", use_container_width=True):
                    on_regen(idx)
    
    def set_responsive_enabled(self, enabled: bool) -> None:
        """Enable or disable responsive rendering"""
        self.responsive_enabled = enabled
    
    def set_message_density(self, density: str) -> None:
        """Set message density for responsive layout"""
        if density in ["compact", "comfortable", "spacious"]:
            self.message_density = density


# Create global instance
responsive_renderer = ResponsiveMessageRenderer()


def render_studio_message(idx, msg, on_delete, on_regen):
    """Legacy function that uses the responsive renderer"""
    responsive_renderer.render_message_responsive(idx, msg, on_delete, on_regen)
