#!/usr/bin/env python3
"""
Test script for context preservation during mode switches
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

def test_context_preservation():
    """Test context preservation during mode switches"""
    try:
        from app_utils.ai_studio.models import ConversationState, UISettings
        from app_utils.ai_studio.enhanced_state_manager import EnhancedStateManager
        from app_utils.ai_studio.components.model_selector import ModelSelector
        
        print("Testing context preservation during mode switches...")
        
        # Test different mode switch scenarios
        mode_switch_scenarios = [
            # (from_model, to_model, should_preserve_context)
            ("models/gemini-flash-latest", "models/gemini-3-pro-image-preview", True),  # Chat to Vision
            ("models/gemini-3-pro-image-preview", "models/gemini-flash-latest", True),  # Vision to Chat
            ("models/gemini-3-pro-preview", "models/gemini-3-pro-image-preview", True),  # Chat to Vision
        ]
        
        for from_model, to_model, should_preserve in mode_switch_scenarios:
            print(f"  Testing switch from {from_model} to {to_model}")
            
            # Create fresh state manager and model selector
            state_manager = EnhancedStateManager()
            model_selector = ModelSelector()
            
            # Initialize with starting model
            state_manager.update_model(from_model)
            
            # Add conversation context
            test_messages = [
                "Hello, I need help with my e-commerce business",
                "Can you analyze this product image?",
                "What are the best practices for Amazon listings?"
            ]
            
            # Add messages to conversation
            for i, msg_content in enumerate(test_messages):
                msg_id = state_manager.add_user_message(msg_content)
                ai_response = f"Response {i+1} from {from_model}"
                state_manager.add_ai_message(ai_response, from_model)
            
            # Get initial state
            initial_state = state_manager.get_state()
            initial_message_count = len(initial_state.messages)
            initial_messages = [msg.content for msg in initial_state.messages]
            
            # Perform model switch
            state_manager.update_model(to_model)
            
            # Get state after switch
            switched_state = state_manager.get_state()
            
            # Verify context preservation
            if should_preserve:
                # Message count should be preserved
                assert len(switched_state.messages) == initial_message_count, \
                    f"Message count changed during mode switch from {from_model} to {to_model}. " \
                    f"Expected: {initial_message_count}, Got: {len(switched_state.messages)}"
                
                # Message content should be preserved
                switched_messages = [msg.content for msg in switched_state.messages]
                assert switched_messages == initial_messages, \
                    f"Message content changed during mode switch from {from_model} to {to_model}"
                
                # Model should be updated
                assert switched_state.current_model == to_model, \
                    f"Model not updated correctly. Expected: {to_model}, Got: {switched_state.current_model}"
                
                print(f"    ✓ Context preserved correctly for {from_model} -> {to_model}")
        
        print("✅ Context preservation test PASSED!")
        return True
        
    except Exception as e:
        print(f"❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_context_preservation()
    exit(0 if success else 1)