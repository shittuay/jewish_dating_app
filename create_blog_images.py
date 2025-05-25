from PIL import Image, ImageDraw, ImageFont
import os

def create_blog_image(filename, title, category, size=(800, 400), bg_color=(41, 128, 185), text_color=(255, 255, 255)):
    # Create a new image with the specified background color
    image = Image.new('RGB', size, bg_color)
    draw = ImageDraw.Draw(image)
    
    # Try to load a font, fall back to default if not available
    try:
        title_font = ImageFont.truetype("arial.ttf", 36)
        category_font = ImageFont.truetype("arial.ttf", 24)
    except:
        title_font = ImageFont.load_default()
        category_font = ImageFont.load_default()
    
    # Add category badge
    category_padding = 20
    category_text = f" {category} "
    category_bbox = draw.textbbox((0, 0), category_text, font=category_font)
    category_width = category_bbox[2] - category_bbox[0]
    category_height = category_bbox[3] - category_bbox[1]
    
    # Draw category badge
    category_x = size[0] - category_width - category_padding
    category_y = category_padding
    draw.rectangle(
        [(category_x - 10, category_y - 5), 
         (category_x + category_width + 10, category_y + category_height + 5)],
        fill=(52, 152, 219)
    )
    draw.text((category_x, category_y), category_text, font=category_font, fill=text_color)
    
    # Add title (wrapped to fit width)
    title_padding = 40
    max_width = size[0] - (2 * title_padding)
    words = title.split()
    lines = []
    current_line = []
    
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=title_font)
        if bbox[2] - bbox[0] <= max_width:
            current_line.append(word)
        else:
            lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    
    # Draw title lines
    y = (size[1] - (len(lines) * (title_font.size + 10))) // 2
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=title_font)
        x = (size[0] - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, font=title_font, fill=text_color)
        y += title_font.size + 10
    
    # Save the image
    os.makedirs('static/blog', exist_ok=True)
    image.save(f'static/blog/{filename}')

# Create the three blog images
create_blog_image(
    'digital_love.jpg',
    'Finding Love in the Digital Age:\nA Jewish Perspective',
    'Dating Tips',
    bg_color=(41, 128, 185)  # Blue
)

create_blog_image(
    'shared_values.jpg',
    'The Importance of Shared Values\nin Jewish Dating',
    'Relationships',
    bg_color=(39, 174, 96)  # Green
)

create_blog_image(
    'modern_dating.jpg',
    'Navigating Modern Dating\nas an Observant Jew',
    'Lifestyle',
    bg_color=(155, 89, 182)  # Purple
) 