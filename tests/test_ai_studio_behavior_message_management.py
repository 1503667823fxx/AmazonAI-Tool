#!/usr/bin/env python3
"""
Property-based test for message management operations using Hypothesis
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '.'))

from hypothesis import given, strategies as st, settings
from hypothesis.strategies import text, lists, integers
from typing import List

from app_utils.ai_studio.models import ConversationState, create_user_message, create_ai_message

@given(
    conversation_scenarios=lists(
        st.tuples(
            st.sampled_from(["user", "assistant"]),  # message role
            text(min_size=1, max_size=50)           # message content
        ),
        min_size=2,
        max_size=10
    ),
    deletion_indices=lists(
        integers(min_value=0, max_value=9),
        min_size=1,
        max_size=3
    )
)
@settings(max_examples=10)
def test_message_deletion_coherence_property(conversation_scenarios: List[tuple], deletion_indices: List[int]):
    """
    Property test: Message deletion maintains conversation coherence for any conversation
    **Feature: ai-studio-enhancement, Property 12: Message management operations**
    **Validates: Requirements 5.1, 5.2, 5.4**
    """
    
    # Create test state
    test_state = ConversationState()
    
    # Build conversation
    messages = []
    for i, (role, content) in enumerate(conversation_scenarios):
        if role == "user":
            msg = create_user_message(content, str(i))
        else:
            msg = create_ai_message(content, str(i), "test-model")
        
        messages.append(msg)
        test_state.add_message(msg)
    
    original_count = len(test_state.messages)
    
    # Test deletion operations
    valid_indices = [idx for idx in deletion_indices if idx < len(test_state.messages)]
    
    for deletion_idx in valid_indices:
        if deletion_idx < len(test_state.messages):
            message_to_delete = test_state.messages[deletion_idx]
            message_id = message_to_delete.id
            
            # Perform deletion
            success = test_state.remove_message(message_id)
            
            # Verify deletion succeeded
            assert success == True, f"Deletion of message {message_id} should succeed"
            
            # Verify message is no longer in conversation
            remaining_ids = [msg.id for msg in test_state.messages]
            assert message_id not in remaining_ids, \
                f"Deleted message {message_id} should not be in conversation"
            
            # Verify conversation coherence - remaining messages should maintain order
            for i in range(len(test_state.messages) - 1):
                current_msg = test_state.messages[i]
                next_msg = test_state.messages[i + 1]
                
                # Timestamps should be in order
                assert current_msg.timestamp <= next_msg.timestamp, \
                    "Message timestamps should remain in chronological order after deletion"
            
            # Verify all remaining messages have valid structure
            for msg in test_state.messages:
                assert hasattr(msg, 'id'), "Remaining message should have ID"
                assert hasattr(msg, 'role'), "Remaining message should have role"
                assert hasattr(msg, 'content'), "Remaining message should have content"
                assert msg.role in ["user", "assistant"], f"Invalid role: {msg.role}"

@given(
    conversation_lengths=integers(min_value=2, max_value=10),
    undo_operations=integers(min_value=1, max_value=3)
)
@settings(max_examples=10)
def test_undo_operations_data_integrity_property(conversation_lengths: int, undo_operations: int):
    """
    Property test: Undo operations maintain data integrity across different conversation lengths
    **Feature: ai-studio-enhancement, Property 12: Message management operations**
    **Validates: Requirements 5.1, 5.2, 5.4**
    """
    
    # Create test conversation
    test_state = ConversationState()
    
    # Build alternating user-assistant conversation
    for i in range(conversation_lengths):
        if i % 2 == 0:
            msg = create_user_message(f"User message {i}", str(i))
        else:
            msg = create_ai_message(f"Assistant response {i}", str(i), "test-model")
        
        test_state.add_message(msg)
    
    original_messages = [msg.id for msg in test_state.messages]
    
    # Perform undo operations
    successful_undos = 0
    for _ in range(min(undo_operations, conversation_lengths // 2)):
        messages_before_undo = len(test_state.messages)
        
        # Perform undo (removes last user-assistant exchange)
        undo_success = test_state.undo_last_turn()
        
        if undo_success:
            successful_undos += 1
            messages_after_undo = len(test_state.messages)
            
            # Verify undo removed messages correctly
            # Should remove 1 or 2 messages (depending on conversation state)
            messages_removed = messages_before_undo - messages_after_undo
            assert messages_removed in [1, 2], \
                f"Undo should remove 1-2 messages, removed {messages_removed}"
            
            # Verify remaining messages maintain integrity
            for msg in test_state.messages:
                assert hasattr(msg, 'id'), "Remaining message should have ID"
                assert hasattr(msg, 'role'), "Remaining message should have role"
                assert hasattr(msg, 'content'), "Remaining message should have content"
                assert hasattr(msg, 'timestamp'), "Remaining message should have timestamp"
            
            # Verify message order is preserved
            for i in range(len(test_state.messages) - 1):
                current_msg = test_state.messages[i]
                next_msg = test_state.messages[i + 1]
                assert current_msg.timestamp <= next_msg.timestamp, \
                    "Message chronological order should be preserved after undo"
        else:
            # Undo should fail gracefully when no more turns to undo
            break
    
    # Verify final state integrity
    assert len(test_state.messages) >= 0, "Message count should never be negative"
    
    # All remaining message IDs should be from the original set
    remaining_ids = [msg.id for msg in test_state.messages]
    for msg_id in remaining_ids:
        assert msg_id in original_messages, \
            f"Remaining message ID {msg_id} should be from original conversation"

if __name__ == "__main__":
    print("Running message management property tests...")
    
    try:
        print("Testing message deletion coherence...")
        test_message_deletion_coherence_property()
        print("‚ú?Message deletion coherence property test passed")
        
        print("Testing undo operations data integrity...")
        test_undo_operations_data_integrity_property()
        print("‚ú?Undo operations data integrity property test passed")
        
        print("\nüéâ All message management property tests passed!")
        
    except Exception as e:
        print(f"\n‚ù?Property test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
