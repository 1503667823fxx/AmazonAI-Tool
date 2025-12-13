#!/usr/bin/env python3
"""
Property-based test for conversation navigation efficiency using Hypothesis
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from hypothesis import given, strategies as st, settings
from hypothesis.strategies import integers, lists
from typing import List
import time

from app_utils.ai_studio.models import ConversationState, create_user_message, create_ai_message
from app_utils.ai_studio.components.chat_container import ChatContainer

@given(
    conversation_lengths=integers(min_value=1, max_value=50),
    navigation_operations=lists(
        st.sampled_from(["scroll_to_bottom", "find_message", "jump_to_index"]),
        min_size=1,
        max_size=5
    )
)
@settings(max_examples=10)
def test_navigation_performance_scaling_property(conversation_lengths: int, navigation_operations: List[str]):
    """
    Property test: Navigation performance scales efficiently with conversation length
    **Feature: ai-studio-enhancement, Property 13: Conversation navigation efficiency**
    **Validates: Requirements 5.5**
    """
    
    # Create conversation of specified length
    test_state = ConversationState()
    messages = []
    
    for i in range(conversation_lengths):
        if i % 2 == 0:
            msg = create_user_message(f"User message {i}", str(i))
        else:
            msg = create_ai_message(f"Assistant response {i}", str(i), "test-model")
        
        messages.append(msg)
        test_state.add_message(msg)
    
    chat_container = ChatContainer()
    
    # Test navigation operations
    for operation in navigation_operations:
        start_time = time.time()
        
        if operation == "scroll_to_bottom":
            # Test auto-scroll functionality
            chat_container.auto_scroll_to_bottom()
            
        elif operation == "find_message":
            # Simulate message finding (would be search functionality)
            if messages:
                target_id = messages[len(messages) // 2].id  # Find middle message
                found = any(msg.id == target_id for msg in test_state.messages)
                assert found == True, "Message search should find existing message"
            
        elif operation == "jump_to_index":
            # Simulate jumping to specific message index
            if messages:
                target_index = min(len(messages) // 2, len(messages) - 1)
                target_message = test_state.messages[target_index]
                assert target_message is not None, "Should be able to access message by index"
        
        end_time = time.time()
        operation_time = end_time - start_time
        
        # Navigation operations should be fast regardless of conversation length
        assert operation_time < 0.01, \
            f"Navigation operation '{operation}' took too long: {operation_time}s for {conversation_lengths} messages"

@given(
    large_conversation_sizes=integers(min_value=20, max_value=100)
)
@settings(max_examples=10)
def test_large_conversation_navigation_efficiency_property(large_conversation_sizes: int):
    """
    Property test: Navigation efficiency for large conversations
    **Feature: ai-studio-enhancement, Property 13: Conversation navigation efficiency**
    **Validates: Requirements 5.5**
    """
    
    # Create large conversation
    test_state = ConversationState()
    
    for i in range(large_conversation_sizes):
        content = f"Message {i} with test pattern"
        
        if i % 2 == 0:
            msg = create_user_message(content, str(i))
        else:
            msg = create_ai_message(content, str(i), "test-model")
        
        test_state.add_message(msg)
    
    # Test message access performance
    start_time = time.time()
    
    # Access messages at various positions
    positions_to_test = [0, len(test_state.messages) // 4, len(test_state.messages) // 2, 
                       3 * len(test_state.messages) // 4, len(test_state.messages) - 1]
    
    for pos in positions_to_test:
        if pos < len(test_state.messages):
            message = test_state.messages[pos]
            assert message is not None, f"Should be able to access message at position {pos}"
            assert hasattr(message, 'id'), "Accessed message should have ID"
            assert hasattr(message, 'content'), "Accessed message should have content"
    
    end_time = time.time()
    access_time = end_time - start_time
    
    # Message access should be O(1) and very fast even for large conversations
    assert access_time < 0.005, \
        f"Message access took too long: {access_time}s for {large_conversation_sizes} messages"
    
    # Test search performance
    start_time = time.time()
    
    # Search for messages containing a pattern
    matching_messages = [
        msg for msg in test_state.messages 
        if "test pattern" in msg.content.lower()
    ]
    
    end_time = time.time()
    search_time = end_time - start_time
    
    # Search should be reasonably fast even for large conversations
    assert search_time < 0.1, \
        f"Search took too long: {search_time}s for {large_conversation_sizes} messages"
    
    # Verify search results are correct
    assert len(matching_messages) == large_conversation_sizes, \
        "All messages should match the search pattern"

@given(
    conversation_sizes=integers(min_value=1, max_value=30)
)
@settings(max_examples=10)
def test_message_management_performance_consistency_property(conversation_sizes: int):
    """
    Property test: Message management operations maintain consistent performance
    **Feature: ai-studio-enhancement, Property 13: Conversation navigation efficiency**
    **Validates: Requirements 5.5**
    """
    
    # Create conversation of specified size
    test_state = ConversationState()
    
    for i in range(conversation_sizes):
        if i % 2 == 0:
            msg = create_user_message(f"Message {i}", str(i))
        else:
            msg = create_ai_message(f"Response {i}", str(i), "test-model")
        
        test_state.add_message(msg)
    
    # Test deletion performance
    if test_state.messages:
        target_message = test_state.messages[0]
        
        start_time = time.time()
        success = test_state.remove_message(target_message.id)
        end_time = time.time()
        
        deletion_time = end_time - start_time
        
        # Deletion should be fast regardless of conversation size
        assert deletion_time < 0.01, \
            f"Message deletion took too long: {deletion_time}s for conversation size {conversation_sizes}"
        
        assert success == True, "Message deletion should succeed"
    
    # Test undo performance
    if len(test_state.messages) >= 2:
        start_time = time.time()
        undo_success = test_state.undo_last_turn()
        end_time = time.time()
        
        undo_time = end_time - start_time
        
        # Undo should be fast regardless of conversation size
        assert undo_time < 0.01, \
            f"Undo operation took too long: {undo_time}s for conversation size {conversation_sizes}"
    
    # Verify final state is valid
    for msg in test_state.messages:
        assert hasattr(msg, 'id'), "Message should have ID after operations"
        assert hasattr(msg, 'role'), "Message should have role after operations"

def test_navigation_method_availability():
    """
    Test that required navigation methods are available and properly structured
    """
    
    chat_container = ChatContainer()
    
    # Verify essential navigation methods exist
    required_methods = [
        'auto_scroll_to_bottom',
        'render_conversation',
        'set_auto_scroll'
    ]
    
    for method_name in required_methods:
        assert hasattr(chat_container, method_name), \
            f"ChatContainer should have {method_name} method"
        
        assert callable(getattr(chat_container, method_name)), \
            f"{method_name} should be callable"
    
    # Test method configuration
    chat_container.set_auto_scroll(True)
    assert chat_container.auto_scroll_enabled == True, \
        "Auto-scroll setting should be configurable"
    
    chat_container.set_auto_scroll(False)
    assert chat_container.auto_scroll_enabled == False, \
        "Auto-scroll should be disableable"

if __name__ == "__main__":
    print("Running conversation navigation efficiency property tests...")
    
    try:
        print("Testing navigation performance scaling...")
        test_navigation_performance_scaling_property()
        print("âœ?Navigation performance scaling property test passed")
        
        print("Testing large conversation navigation efficiency...")
        test_large_conversation_navigation_efficiency_property()
        print("âœ?Large conversation navigation efficiency property test passed")
        
        print("Testing message management performance consistency...")
        test_message_management_performance_consistency_property()
        print("âœ?Message management performance consistency property test passed")
        
        print("Testing navigation method availability...")
        test_navigation_method_availability()
        print("âœ?Navigation method availability test passed")
        
        print("\nðŸŽ‰ All conversation navigation efficiency property tests passed!")
        
    except Exception as e:
        print(f"\nâ?Property test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
