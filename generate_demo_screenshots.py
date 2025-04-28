from PIL import Image, ImageDraw, ImageFont
import os

# Make sure the directories exist
os.makedirs('data/screenshots', exist_ok=True)
os.makedirs('static/screenshots', exist_ok=True)

def create_demo_screenshot(filename, title, width=800, height=600, color=(240, 240, 240), text_color=(30, 30, 30)):
    """Create a simple demonstration screenshot with text"""
    img = Image.new('RGB', (width, height), color)
    draw = ImageDraw.Draw(img)
    
    # Try to use a font, fall back to default if not available
    try:
        font = ImageFont.truetype("arial.ttf", 24)
    except IOError:
        font = ImageFont.load_default()
    
    # Draw title
    # In newer versions of PIL, we use textbbox instead of textsize
    try:
        left, top, right, bottom = draw.textbbox((0, 0), title, font=font)
        textwidth = right - left
        textheight = bottom - top
    except AttributeError:
        # Fall back for older PIL versions
        textwidth, textheight = draw.textsize(title, font=font)
        
    x = (width - textwidth) // 2
    y = (height - textheight) // 2
    draw.text((x, y), title, font=font, fill=text_color)
    
    # Save the image
    img.save(f"data/screenshots/{filename}")
    
    # Also create a symlink in static/screenshots
    try:
        src = os.path.abspath(f"data/screenshots/{filename}")
        dst = os.path.join('static/screenshots', filename)
        if os.path.exists(dst):
            os.remove(dst)
        os.symlink(src, dst)
    except Exception as e:
        print(f"Error creating symlink: {e}")
    
    return f"data/screenshots/{filename}"

# Create email automation screenshots
create_demo_screenshot("email_before.png", "Email Inbox - Before Automation")
create_demo_screenshot("email_after.png", "Email Inbox - After Automation (Files Moved)")
create_demo_screenshot("email_diff.png", "Email Automation - Difference Visualization", color=(200, 220, 255))

create_demo_screenshot("email_before2.png", "Another Email Inbox - Before Automation")
create_demo_screenshot("email_after2.png", "Another Email Inbox - After Automation (Files Moved)")
create_demo_screenshot("email_diff2.png", "Another Email Automation - Difference Visualization", color=(200, 220, 255))

create_demo_screenshot("email_before_failed.png", "Email Inbox - Failed Automation (Before)")
create_demo_screenshot("email_after_failed.png", "Email Inbox - Failed Automation (After, Minimal Change)")
create_demo_screenshot("email_diff_failed.png", "Email Automation - Failed Difference (2.1% Change)", color=(255, 200, 200))

# Create report generator screenshots
create_demo_screenshot("report_before.png", "Report Generator - Before Automation")
create_demo_screenshot("report_after.png", "Report Generator - After Automation (Report Generated)")
create_demo_screenshot("report_diff.png", "Report Generator - Difference Visualization", color=(200, 255, 220))

print("Demo screenshots generated successfully!")