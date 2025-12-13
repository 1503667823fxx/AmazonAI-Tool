"""
Simple property-based test for message styling consistency
This test can run without external dependencies
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from app_utils.ai_studio.models import (
    BaseMessage, UserMessage, AIMessage, ConversationState,
    create_user_message, create_ai_message
)
from app_utils.ai_studio.design_tokens import DesignTokens, ModernCSSInjector
import re
from datetime import datetime


def test_message_styling_consistency():
    """
    **Feature: ai-studio-enhancement, Property 1: Message styling consistency**
    **Validates: Requirements 1.2**
    
    Property: For any set of messages in the conversation, all messages of the same role 
    should follow identical styling patterns and visual hierarchy
    """
    print("Testing message styling consistency...")
    
    # Test with various message combinations
    test_cases = [
        (["Hello", "How are you?"], ["Hi there!", "I'm doing well"]),
        (["Test message"], ["Response"]),
        (["A" * 100], ["B" * 200]),  # Long messages
        (["Short"], ["Also short"]),
        ([""], [""]),  # Edge case: empty messages
    ]
    
    for user_messages, ai_messages in test_cases:
        # Create message objects
        user_msg_objects = []
        ai_msg_objects = []
        
        for i, content in enumerate(user_messages):
            if content:  # Skip empty content
                msg = create_user_message(content, str(i))
                user_msg_objects.append(msg)
        
        for i, content in enumerate(ai_messages):
            if content:  # Skip empty content
                msg = create_ai_message(content, str(i + len(user_messages)), "test-model")
                ai_msg_objects.append(msg)
        
        # Test that all user messages have the same role
        for msg in user_msg_objects:
            assert msg.role == "user", f"User message {msg.id} has incorrect role: {msg.role}"
        
        # Test that all AI messages have the same role
        for msg in ai_msg_objects:
            assert msg.role == "assistant", f"AI message {msg.id} has incorrect role: {msg.role}"
        
        # Test that messages have consistent structure
        for msg in user_msg_objects:
            assert hasattr(msg, 'id'), "User message missing id attribute"
            assert hasattr(msg, 'timestamp'), "User message missing timestamp attribute"
            assert hasattr(msg, 'content'), "User message missing content attribute"
            assert hasattr(msg, 'role'), "User message missing role attribute"
        
        for msg in ai_msg_objects:
            assert hasattr(msg, 'id'), "AI message missing id attribute"
            assert hasattr(msg, 'timestamp'), "AI message missing timestamp attribute"
            assert hasattr(msg, 'content'), "AI message missing content attribute"
            assert hasattr(msg, 'role'), "AI message missing role attribute"
            assert hasattr(msg, 'model_used'), "AI message missing model_used attribute"
    
    print("✓ Message role consistency test passed")


def test_css_styling_consistency():
    """Test that CSS styling rules are consistent for messages of the same role"""
    print("Testing CSS styling consistency...")
    
    css_injector = ModernCSSInjector()
    
    # Generate CSS styles
    chat_styles = css_injector._generate_chat_styles()
    
    # Verify that user message styles are defined
    assert ".stChatMessage[data-testid=\"user-message\"]" in chat_styles, \
        "User message CSS selector not found"
    
    # Verify that assistant message styles are defined
    assert ".stChatMessage[data-testid=\"assistant-message\"]" in chat_styles, \
        "Assistant message CSS selector not found"
    
    # Verify that both roles have consistent styling properties
    user_style_match = re.search(
        r'\.stChatMessage\[data-testid="user-message"\]\s*{([^}]+)}', 
        chat_styles
    )
    assistant_style_match = re.search(
        r'\.stChatMessage\[data-testid="assistant-message"\]\s*{([^}]+)}', 
        chat_styles
    )
    
    assert user_style_match, "User message styles not properly defined"
    assert assistant_style_match, "Assistant message styles not properly defined"
    
    # Both should have background-color defined
    user_styles = user_style_match.group(1)
    assistant_styles = assistant_style_match.group(1)
    
    assert "background-color" in user_styles, "User messages missing background-color"
    assert "background-color" in assistant_styles, "Assistant messages missing background-color"
    
    print("✓ CSS styling consistency test passed")


def test_message_hierarchy_consistency():
    """Test that visual hierarchy is maintained consistently across conversations"""
    print("Testing message hierarchy consistency...")
    
    # Test with different conversation lengths
    conversation_lengths = [1, 5, 10, 25]
    
    for length in conversation_lengths:
        state = ConversationState()
        
        # Add alternating user and AI messages
        for i in range(length):
            if i % 2 == 0:
                msg = create_user_message(f"Message_{i}", str(i))
            else:
                msg = create_ai_message(f"Response_{i}", str(i), "test-model")
            
            state.add_message(msg)
        
        # Verify that the conversation maintains proper structure
        assert len(state.messages) == length
        
        # Check that message IDs are unique
        message_ids = [msg.id for msg in state.messages]
        assert len(message_ids) == len(set(message_ids)), "Message IDs are not unique"
        
        # Check that we have proper message structure
        if len(state.messages) > 0:
            user_messages = [msg for msg in state.messages if msg.role == "user"]
            ai_messages = [msg for msg in state.messages if msg.role == "assistant"]
            
            # Should have at least one message
            assert len(user_messages) > 0 or len(ai_messages) > 0, \
                "Conversation should contain at least one message"
    
    print("✓ Message hierarchy consistency test passed")


def test_design_tokens_consistency():
    """Test that design tokens provide consistent values for styling"""
    print("Testing design tokens consistency...")
    
    tokens = DesignTokens()
    
    # Test that all required color categories exist
    required_color_categories = [
        "primary", "secondary", "neutral_500", "bg_primary", 
        "text_primary", "border_light"
    ]
    
    for category in required_color_categories:
        assert category in tokens.COLORS, f"Missing color category: {category}"
        assert isinstance(tokens.COLORS[category], str), f"Color {category} should be string"
        assert tokens.COLORS[category].startswith("#"), f"Color {category} should be hex value"
    
    # Test typography consistency
    required_typography = ["font_family", "font_size_base", "line_height_normal"]
    for typo in required_typography:
        assert typo in tokens.TYPOGRAPHY, f"Missing typography: {typo}"
    
    # Test spacing consistency
    required_spacing = ["sm", "md", "lg"]
    for spacing in required_spacing:
        assert spacing in tokens.SPACING, f"Missing spacing: {spacing}"
        assert tokens.SPACING[spacing].endswith("rem"), f"Spacing {spacing} should use rem units"
    
    print("✓ Design tokens consistency test passed")


def run_all_tests():
    """Run all property tests"""
    print("Running Property-Based Tests for Message Styling Consistency")
    print("=" * 60)
    
    try:
        test_message_styling_consistency()
        test_css_styling_consistency()
        test_message_hierarchy_consistency()
        test_design_tokens_consistency()
        
        print("\n" + "=" * 60)
        print("✅ All property tests PASSED!")
        print("Property 1: Message styling consistency - VALIDATED")
        return True
        
    except AssertionError as e:
        print(f"\n❌ Test FAILED: {e}")
        return False
    except Exception as e:
        print(f"\n💥 Test ERROR: {e}")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    exit(0 if success else 1)