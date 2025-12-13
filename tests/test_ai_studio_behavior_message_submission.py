#!/usr/bin/env python3
"""
Property test for message submission state management
**Feature: ai-studio-enhancement, Property 8: Message submission state management**
**Validates: Requirements 3.5**
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from hypothesis import given, strategies as st, settings
from hypothesis.strategies import text, lists, integers, booleans
from typing import List

# Import the modules we're testing
from app_utils.ai_studio.components.input_panel import InputPanel
from app_utils.ai_studio.enhanced_state_manager import state_manager


class TestMessageSubmissionStateManagement:
    """
    **Feature: ai-studio-enhancement, Property 8: Message submission state management**
    **Validates: Requirements 3.5**
    
    Property: For any message submission, the system should immediately clear the input 
    field and display appropriate processing states
    """
    
    @given(
        message_contents=lists(
            text(min_size=1, max_size=500),
            min_size=1,
            max_size=10
        )
    )
    @settings(max_examples=50)
    def test_input_clearing_on_submission(self, message_contents: List[str]):
        """
        Test that input field is cleared immediately upon message submission
        """
        input_panel = InputPanel()
        
        for content in message_contents:
            # Get initial state
            initial_state = state_manager.get_state()
            initial_uploader_key = initial_state.uploader_key_id
            
            # Simulate message submission
            input_panel._handle_message_submission(content)
            
            # Verify state changes after submission
            updated_state = state_manager.get_state()
            
            # Input clearing should be reflected by uploader key increment
            assert updated_state.uploader_key_id > initial_uploader_key, \
                f"Uploader key should increment after submission to clear input. " \
                f"Initial: {initial_uploader_key}, Updated: {updated_state.uploader_key_id}"
            
            # Upload queue should be cleared if it existed
            if hasattr(updated_state, 'upload_queue'):
                assert len(updated_state.upload_queue) == 0, \
                    "Upload queue should be cleared after message submission"
    
    @given(
        processing_states=lists(
            st.tuples(
                booleans(),  # is_streaming
                text(min_size=1, max_size=100)  # message_content
            ),
            min_size=1,
            max_size=8
        )
    )
    @settings(max_examples=50)
    def test_processing_state_display_consistency(self, processing_states: List[tuple]):
        """
        Test that appropriate processing states are displayed consistently after submission
        """
        for is_streaming, content in processing_states:
            # Set streaming state
            state_manager.set_streaming_state(is_streaming)
            
            # Verify streaming state is properly set
            current_state = state_manager.get_state()
            assert current_state.is_streaming == is_streaming, \
                f"Streaming state should be {is_streaming}, got {current_state.is_streaming}"
            
            # Verify state consistency
            assert isinstance(current_state.is_streaming, bool), \
                "Streaming state should be boolean"
    
    def test_submission_state_boundary_conditions(self):
        """
        Test submission state management at boundary conditions
        """
        input_panel = InputPanel()
        
        # Test empty content submission (should still clear input)
        initial_state = state_manager.get_state()
        initial_key = initial_state.uploader_key_id
        
        input_panel._handle_message_submission("")
        
        empty_state = state_manager.get_state()
        assert empty_state.uploader_key_id > initial_key, \
            "Even empty submission should clear input (increment uploader key)"
        
        # Test very long content
        long_content = "x" * 1000
        long_initial_key = empty_state.uploader_key_id
        
        input_panel._handle_message_submission(long_content)
        
        long_state = state_manager.get_state()
        assert long_state.uploader_key_id > long_initial_key, \
            "Long content submission should clear input"


def run_property_tests():
    """Run the property tests manually"""
    test_instance = TestMessageSubmissionStateManagement()
    
    print("Running Property 8: Message submission state management tests...")
    
    try:
        # Test 1: Input clearing
        print("  Testing input clearing on submission...")
        test_instance.test_input_clearing_on_submission(["Hello", "Test message", "Another test"])
        print("  âœ?Input clearing test passed")
        
        # Test 2: Processing state consistency
        print("  Testing processing state consistency...")
        test_instance.test_processing_state_display_consistency([(True, "streaming"), (False, "idle")])
        print("  âœ?Processing state test passed")
        
        # Test 3: Boundary conditions
        print("  Testing boundary conditions...")
        test_instance.test_submission_state_boundary_conditions()
        print("  âœ?Boundary conditions test passed")
        
        print("\nğŸ‰ All Property 8 tests passed!")
        return True
        
    except Exception as e:
        print(f"\nâ?Property test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_property_tests()
    sys.exit(0 if success else 1)
