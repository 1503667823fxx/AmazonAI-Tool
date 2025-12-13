#!/usr/bin/env python3

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

print("Testing image grid layout properties...")

def test_grid_layout_calculation():
    """Test grid layout calculation logic"""
    
    def calculate_grid_dimensions(image_count, max_cols_per_row=4):
        """Calculate grid dimensions for given image count"""
        cols_per_row = min(max_cols_per_row, image_count)
        rows_needed = (image_count + cols_per_row - 1) // cols_per_row
        return cols_per_row, rows_needed
    
    # Test cases
    test_cases = [
        (1, 4, 1, 1),   # 1 image, max 4 cols -> 1x1 grid
        (3, 4, 3, 1),   # 3 images, max 4 cols -> 3x1 grid
        (4, 4, 4, 1),   # 4 images, max 4 cols -> 4x1 grid
        (5, 4, 4, 2),   # 5 images, max 4 cols -> 4x2 grid
        (8, 4, 4, 2),   # 8 images, max 4 cols -> 4x2 grid
        (9, 4, 4, 3),   # 9 images, max 4 cols -> 4x3 grid
        (12, 3, 3, 4),  # 12 images, max 3 cols -> 3x4 grid
    ]
    
    for image_count, max_cols, expected_cols, expected_rows in test_cases:
        cols, rows = calculate_grid_dimensions(image_count, max_cols)
        
        print(f"Images: {image_count}, Max cols: {max_cols} -> Grid: {cols}x{rows}")
        
        assert cols == expected_cols, f"Expected {expected_cols} cols, got {cols}"
        assert rows == expected_rows, f"Expected {expected_rows} rows, got {rows}"
        
        # Verify grid can accommodate all images
        total_slots = cols * rows
        assert total_slots >= image_count, f"Grid {cols}x{rows} cannot fit {image_count} images"
        
        # Verify efficient usage (no more than one row of empty slots)
        if rows > 1:
            min_required_rows = (image_count + cols - 1) // cols
            assert rows == min_required_rows, f"Grid should use minimum rows: {min_required_rows}, got {rows}"
    
    print("✓ Grid layout calculation tests passed!")

def test_responsive_grid_behavior():
    """Test responsive grid behavior"""
    
    def test_grid_properties(image_count, max_cols):
        """Test grid properties for given configuration"""
        cols = min(max_cols, image_count)
        rows = (image_count + cols - 1) // cols
        
        # Property 1: Never exceed column limit
        assert cols <= max_cols, f"Columns {cols} should not exceed max {max_cols}"
        
        # Property 2: Use available space efficiently
        if image_count <= max_cols:
            assert cols == image_count, f"Should use {image_count} columns for {image_count} images"
        else:
            assert cols == max_cols, f"Should use max columns {max_cols} when images exceed limit"
        
        # Property 3: Minimize rows
        min_possible_rows = (image_count + max_cols - 1) // max_cols
        assert rows == min_possible_rows, f"Should use minimum rows {min_possible_rows}, got {rows}"
        
        # Property 4: Handle edge cases
        if image_count == 1:
            assert cols == 1 and rows == 1, "Single image should use 1x1 grid"
        
        # Property 5: Last row should not be empty
        images_in_last_row = image_count % cols
        if images_in_last_row == 0 and image_count > 0:
            images_in_last_row = cols
        assert images_in_last_row > 0, "Last row should contain at least one image"
        
        return True
    
    # Test various configurations
    configurations = [
        (1, 1), (1, 2), (1, 4), (1, 6),
        (2, 2), (2, 4), (2, 6),
        (5, 3), (5, 4), (5, 6),
        (10, 3), (10, 4), (10, 6),
        (15, 4), (15, 5), (15, 6),
        (20, 4), (20, 5), (20, 6)
    ]
    
    for image_count, max_cols in configurations:
        print(f"Testing grid for {image_count} images with max {max_cols} columns...")
        test_grid_properties(image_count, max_cols)
    
    print("✓ Responsive grid behavior tests passed!")

def test_grid_spacing_consistency():
    """Test that grid spacing remains consistent"""
    
    def verify_grid_consistency(image_count, max_cols=4):
        """Verify grid consistency for given image count"""
        cols = min(max_cols, image_count)
        rows = (image_count + cols - 1) // cols
        
        # Test each row
        for row in range(rows):
            start_idx = row * cols
            end_idx = min(start_idx + cols, image_count)
            images_in_row = end_idx - start_idx
            
            # All rows except the last should be full
            if row < rows - 1:
                assert images_in_row == cols, f"Row {row} should have {cols} images, got {images_in_row}"
            else:
                # Last row should have remaining images
                expected_last_row = image_count % cols
                if expected_last_row == 0:
                    expected_last_row = cols
                assert images_in_row == expected_last_row, f"Last row should have {expected_last_row} images, got {images_in_row}"
        
        return True
    
    # Test various image counts
    for image_count in range(1, 21):
        print(f"Testing grid consistency for {image_count} images...")
        verify_grid_consistency(image_count)
    
    print("✓ Grid spacing consistency tests passed!")

if __name__ == "__main__":
    try:
        test_grid_layout_calculation()
        test_responsive_grid_behavior()
        test_grid_spacing_consistency()
        
        print("All image grid layout property tests passed!")
        sys.exit(0)
        
    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)