import os
from PIL import Image

# Define paths
ORIG_DIR = "./"
ICON_ORIG = os.path.join(ORIG_DIR, "icon.png")
LOGO_ORIG = os.path.join(ORIG_DIR, "logo.png")
BRANDS_DIR = "../../brands/custom_integrations/kr_eta"

def resize_icon():
    if not os.path.exists(ICON_ORIG):
        print(f"Error: {ICON_ORIG} not found.")
        return

    print(f"Processing {ICON_ORIG}...")
    with Image.open(ICON_ORIG) as img:
        # Validate square aspect ratio
        if img.width != img.height:
            print(f"Warning: Icon is not square ({img.width}x{img.height}). Resizing anyway.")
        
        # icon.png: 256x256
        img.resize((256, 256), Image.Resampling.LANCZOS).save(os.path.join(BRANDS_DIR, "icon.png"))
        print(f"Created icon.png (256x256)")

        # icon@2x.png: 512x512
        img.resize((512, 512), Image.Resampling.LANCZOS).save(os.path.join(BRANDS_DIR, "icon@2x.png"))
        print(f"Created icon@2x.png (512x512)")

def resize_logo():
    if not os.path.exists(LOGO_ORIG):
        print(f"Error: {LOGO_ORIG} not found.")
        return

    print(f"Processing {LOGO_ORIG}...")
    with Image.open(LOGO_ORIG) as img:
        width, height = img.size
        aspect_ratio = width / height

        # logo.png: shortest side max 256
        if width < height:
            new_width = 256
            new_height = int(new_width / aspect_ratio)
        else:
            new_height = 256
            new_width = int(new_height * aspect_ratio)
        
        img.resize((new_width, new_height), Image.Resampling.LANCZOS).save(os.path.join(BRANDS_DIR, "logo.png"))
        print(f"Created logo.png ({new_width}x{new_height})")

        # logo@2x.png: shortest side max 512
        if width < height:
            new_width_2x = 512
            new_height_2x = int(new_width_2x / aspect_ratio)
        else:
            new_height_2x = 512
            new_width_2x = int(new_height_2x * aspect_ratio)

        img.resize((new_width_2x, new_height_2x), Image.Resampling.LANCZOS).save(os.path.join(BRANDS_DIR, "logo@2x.png"))
        print(f"Created logo@2x.png ({new_width_2x}x{new_height_2x})")

if __name__ == "__main__":
    resize_icon()
    resize_logo()
