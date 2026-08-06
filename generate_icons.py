#!/usr/bin/env python3
"""
Generate app icons for PWA
Run: python generate_icons.py
"""

from PIL import Image, ImageDraw, ImageFont

def create_icon(size, filename):
    """Create a simple icon"""
    # Create image with gradient background
    img = Image.new('RGB', (size, size), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw gradient background
    for y in range(size):
        # Calculate color for this row
        ratio = y / size
        r = int(30 + (42 - 30) * ratio)
        g = int(60 + (82 - 60) * ratio)
        b = int(114 + (152 - 114) * ratio)
        draw.line([(0, y), (size, y)], fill=(r, g, b))
    
    # Draw icon (⚖️ scale symbol)
    scale_size = int(size * 0.6)
    scale_x = (size - scale_size) // 2
    scale_y = (size - scale_size) // 2
    
    # Draw weighing scale
    # Base
    base_height = int(scale_size * 0.1)
    draw.rectangle([
        (scale_x, scale_y + scale_size - base_height),
        (scale_x + scale_size, scale_y + scale_size)
    ], fill='white')
    
    # Pole
    pole_width = int(scale_size * 0.1)
    pole_x = scale_x + (scale_size - pole_width) // 2
    draw.rectangle([
        (pole_x, scale_y + scale_size // 3),
        (pole_x + pole_width, scale_y + scale_size - base_height)
    ], fill='white')
    
    # Balance beam
    beam_height = int(scale_size * 0.08)
    draw.rectangle([
        (scale_x, scale_y + scale_size // 3),
        (scale_x + scale_size, scale_y + scale_size // 3 + beam_height)
    ], fill='white')
    
    # Left pan
    pan_width = int(scale_size * 0.35)
    pan_height = int(scale_size * 0.15)
    draw.ellipse([
        (scale_x, scale_y + scale_size // 3 + beam_height),
        (scale_x + pan_width, scale_y + scale_size // 3 + beam_height + pan_height)
    ], fill='white', outline='white')
    
    # Right pan
    draw.ellipse([
        (scale_x + scale_size - pan_width, scale_y + scale_size // 3 + beam_height),
        (scale_x + scale_size, scale_y + scale_size // 3 + beam_height + pan_height)
    ], fill='white', outline='white')
    
    # Save
    img.save(filename, 'PNG', optimize=True)
    print(f'✅ Created {filename}')

if __name__ == '__main__':
    import os
    
    # Create static directory if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')
    
    # Generate icons
    create_icon(192, 'static/icon-192.png')
    create_icon(512, 'static/icon-512.png')
    
    print('\n✅ Icons created successfully!')
    print('Files: static/icon-192.png, static/icon-512.png')
