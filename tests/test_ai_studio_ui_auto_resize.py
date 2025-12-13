#!/usr/bin/env python3

import sys
sys.path.append('.')

print("Testing input field auto-resize properties...")

def test_auto_resize_height_calculation():
    """Test auto-resize height calculation logic"""
    
    class MockInputPanel:
        """Mock InputPanel for testing auto-resize logic"""
        
        def __init__(self):
            self.auto_resize_enabled = True
        
        def get_input_field_height(self, content: str) -> int:
            """Calculate appropriate height for input field based on content"""
            
            if not self.auto_resize_enabled:
                return 40  # Default height in pixels
            
            # Calculate height based on content length and line breaks
            lines = content.count('\n') + 1
            base_height = 40
            line_height = 20
            max_height = 200  # Maximum height in pixels
            
            calculated_height = base_height + (lines - 1) * line_height
            return min(calculated_height, max_height)
        
        def enable_auto_resize(self):
            self.auto_resize_enabled = True
        
        def disable_auto_resize(self):
            self.auto_resize_enabled = False
        
        def is_auto_resize_enabled(self) -> bool:
            return self.auto_resize_enabled
    
    input_panel = MockInputPanel()
    
    # Test 1: Single line text
    single_line = "Hello world"
    height = input_panel.get_input_field_height(single_line)
    print(f"Single line height: {height}")
    assert height == 40, f"Single line should be 40px, got {height}"
    
    # Test 2: Multi-line text
    multi_line = "Line 1\nLine 2\nLine 3"
    height = input_panel.get_input_field_height(multi_line)
    expected = 40 + 2 * 20  # base + 2 additional lines
    print(f"Multi-line height: {height}, expected: {expected}")
    assert height == expected, f"Multi-line should be {expected}px, got {height}"
    
    # Test 3: Empty content
    empty = ""
    height = input_panel.get_input_field_height(empty)
    print(f"Empty content height: {height}")
    assert height == 40, f"Empty content should be 40px, got {height}"
    
    # Test 4: Maximum height limit
    many_lines = '\n'.join(['line'] * 20)  # 20 lines
    height = input_panel.get_input_field_height(many_lines)
    print(f"Many lines height: {height}")
    assert height == 200, f"Many lines should be capped at 200px, got {height}"
    
    # Test 5: Auto-resize disabled
    input_panel.disable_auto_resize()
    height = input_panel.get_input_field_height(multi_line)
    print(f"Disabled auto-resize height: {height}")
    assert height == 40, f"Disabled auto-resize should be 40px, got {height}"
    
    # Test 6: Re-enable auto-resize
    input_panel.enable_auto_resize()
    assert input_panel.is_auto_resize_enabled() == True, "Auto-resize should be enabled"
    
    height = input_panel.get_input_field_height(multi_line)
    expected = 40 + 2 * 20
    print(f"Re-enabled auto-resize height: {height}")
    assert height == expected, f"Re-enabled should calculate correctly: {expected}px, got {height}"
    
    print("✓ All auto-resize tests passed!")
    return True

def test_keyboard_interaction_handling():
    """Test keyboard interaction handling logic"""
    
    class MockInputPanel:
        """Mock InputPanel for testing keyboard handling"""
        
        def handle_keyboard_shortcuts(self, key_event: str) -> bool:
            """Handle keyboard shortcuts for input"""
            
            if key_event == "Enter":
                return True  # Send message
            elif key_event == "Shift+Enter":
                return False  # New line
            elif key_event == "Escape":
                return False  # Handle escape
            elif key_event in ["Ctrl+A", "Cmd+A"]:
                return False  # Select all
            
            return False
        
        def validate_keyboard_input(self, key_event: str, content: str) -> bool:
            """Validate keyboard input before processing"""
            
            valid_keys = ["Enter", "Shift+Enter", "Escape", "Ctrl+A", "Cmd+A"]
            
            if key_event not in valid_keys:
                return False
            
            # Don't allow empty submissions with Enter
            if key_event == "Enter" and not content.strip():
                return False
            
            return True
        
        def handle_enter_key_submission(self, content: str) -> bool:
            """Handle Enter key submission with validation"""
            
            if not content or not content.strip():
                return False
            
            return True
    
    input_panel = MockInputPanel()
    
    # Test 1: Enter key with valid content
    should_submit = input_panel.handle_keyboard_shortcuts("Enter")
    print(f"Enter key handling: {should_submit}")
    assert should_submit == True, "Enter should submit message"
    
    # Test 2: Shift+Enter key
    should_submit = input_panel.handle_keyboard_shortcuts("Shift+Enter")
    print(f"Shift+Enter handling: {should_submit}")
    assert should_submit == False, "Shift+Enter should not submit (new line)"
    
    # Test 3: Validation with valid content
    is_valid = input_panel.validate_keyboard_input("Enter", "Hello world")
    print(f"Valid content validation: {is_valid}")
    assert is_valid == True, "Enter with valid content should be valid"
    
    # Test 4: Validation with empty content
    is_valid = input_panel.validate_keyboard_input("Enter", "")
    print(f"Empty content validation: {is_valid}")
    assert is_valid == False, "Enter with empty content should be invalid"
    
    # Test 5: Invalid key
    is_valid = input_panel.validate_keyboard_input("F1", "content")
    print(f"Invalid key validation: {is_valid}")
    assert is_valid == False, "Invalid key should be invalid"
    
    # Test 6: Enter submission validation
    should_submit = input_panel.handle_enter_key_submission("Hello")
    print(f"Enter submission with content: {should_submit}")
    assert should_submit == True, "Should submit with valid content"
    
    should_submit = input_panel.handle_enter_key_submission("")
    print(f"Enter submission empty: {should_submit}")
    assert should_submit == False, "Should not submit empty content"
    
    print("✓ All keyboard interaction tests passed!")
    return True

if __name__ == "__main__":
    try:
        test_auto_resize_height_calculation()
        test_keyboard_interaction_handling()
        
        print("All input field property tests passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)