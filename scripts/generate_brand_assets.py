from PIL import Image, ImageDraw, ImageFont
import os

def create_placeholder_image(size, text, output_path, is_icon=True):
    # Create a new image with a white background
    image = Image.new('RGBA', size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(image)
    
    # Draw a light blue rectangle
    rect_color = (41, 128, 185, 200)  # Home Assistant-like blue
    draw.rectangle([0, 0, size[0]-1, size[1]-1], fill=rect_color, outline=(0, 0, 0, 255))
    
    # Add text
    font_size = min(size) // 8
    try:
        font = ImageFont.truetype("arial.ttf", font_size)
    except:
        font = ImageFont.load_default()
    
    text_bbox = draw.textbbox((0, 0), text, font=font)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]
    
    x = (size[0] - text_width) // 2
    y = (size[1] - text_height) // 2
    
    # Draw text with a slight shadow for better visibility
    draw.text((x+2, y+2), text, fill=(0, 0, 0, 128), font=font)
    draw.text((x, y), text, fill=(255, 255, 255, 255), font=font)
    
    # Save the image
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    image.save(output_path, 'PNG', optimize=True)

def main():
    base_path = "custom_components/timewise_guardian/brands"
    
    # Generate icon images
    create_placeholder_image((256, 256), "TWG\nIcon", f"{base_path}/icon.png", True)
    create_placeholder_image((512, 512), "TWG\nIcon\n2x", f"{base_path}/icon@2x.png", True)
    
    # Generate logo images (landscape format)
    create_placeholder_image((512, 256), "Timewise Guardian", f"{base_path}/logo.png", False)
    create_placeholder_image((1024, 512), "Timewise Guardian\n2x", f"{base_path}/logo@2x.png", False)

if __name__ == "__main__":
    main()
    print("Brand assets generated successfully!") 