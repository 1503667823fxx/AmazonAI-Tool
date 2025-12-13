#!/usr/bin/env python3
"""
Test the advanced conversation management implementation
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app_utils.ai_studio.enhanced_state_manager import EnhancedStateManager
from app_utils.ai_studio.models import ConversationState, create_user_message, create_ai_message
from app_utils.ai_studio.components.chat_container import ChatContainer

def test_enhanced_state_manager():
    """Test enhanced state manager functionality"""
    
    print("Testing enhanced state manager...")
    
    # Create state manager
    state_manager = EnhancedStateManager()
    
    # Create test conversation
    state = ConversationState()
    
    # Add messages
    for i in range(10):
        if i % 2 == 0:
            msg = create_user_message(f"User message {i}", str(i))
        else:
            msg = create_ai_message(f"AI response {i}", str(i), "test-model")
        
        state.add_message(msg)
    
    state_manager.update_state(state)
    
    # Test conversation statistics
    stats = state_manager.get_conversation_statistics()
    assert stats["total_messages"] == 10
    assert stats["user_messages"] == 5
    assert stats["ai_messages"] == 5
    print("✓ Conversation statistics working")
    
    # Test message search
    results = state_manager.search_messages("User message")
    assert len(results) == 5
    print("✓ Message search working")
    
    # Test batch deletion
    message_ids = [state.messages[0].id, state.messages[1].id]
    deleted_count = state_manager.delete_messages_batch(message_ids)
    assert deleted_count == 2
    assert len(state_manager.get_state().messages) == 8
    print("✓ Batch deletion working")
    
    # Test conversation trimming
    trimmed = state_manager.trim_conversation(5)
    assert trimmed == 3
    assert len(state_manager.get_state().messages) == 5
    print("✓ Conversation trimming working")

def test_chat_container_enhancements():
    """Test chat container enhancements"""
    
    print("Testing chat container enhancements...")
    
    chat_container = ChatContainer()
    
    # Test that new methods exist
    assert hasattr(chat_container, 'render_conversation_navigation')
    assert hasattr(chat_container, 'render_conversation_summary')
    assert hasattr(chat_container, 'enable_virtual_scrolling')
    print("✓ New chat container methods exist")
    
    # Test navigation settings
    chat_container.set_auto_scroll(True)
    assert chat_container.auto_scroll_enabled == True
    
    chat_container.set_message_actions(True)
    assert chat_container.message_actions_enabled == True
    print("✓ Chat container configuration working")

def test_conversation_management_integration():
    """Test integration of conversation management features"""
    
    print("Testing conversation management integration...")
    
    # Create a large conversation to test navigation features
    state = ConversationState()
    
    # Add many messages to test navigation
    for i in range(25):
        if i % 2 == 0:
            msg = create_user_message(f"User message {i} with test content", str(i))
        else:
            msg = create_ai_message(f"AI response {i} with test content", str(i), "test-model")
        
        state.add_message(msg)
    
    # Test message operations
    original_count = len(state.messages)
    
    # Test deletion
    success = state.remove_message("0")
    assert success == True
    assert len(state.messages) == original_count - 1
    print("✓ Message deletion working")
    
    # Test undo
    undo_success = state.undo_last_turn()
    assert undo_success == True
    print("✓ Undo operation working")
    
    # Test conversation coherence
    for i in range(len(state.messages) - 1):
        current = state.messages[i]
        next_msg = state.messages[i + 1]
        assert current.timestamp <= next_msg.timestamp
    print("✓ Conversation coherence maintained")

if __name__ == "__main__":
    try:
        test_enhanced_state_manager()
        test_chat_container_enhancements()
        test_conversation_management_integration()
        
        print("\n🎉 All conversation management tests passed!")
        print("✅ Advanced conversation management implementation is working correctly!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)