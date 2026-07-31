from PIL import Image
import os

def remove_background(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        r, g, b, a = item
        # Check if pixel is white or near-white background
        if r > 235 and g > 235 and b > 235:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append(item)

    img.putdata(new_data)

    # Crop to bounding box
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Add small padding
    padding = 12
    new_width = img.width + (padding * 2)
    new_height = img.height + (padding * 2)
    padded_img = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    padded_img.paste(img, (padding, padding))

    padded_img.save(output_path, "PNG")
    print(f"Processed clean logo icon saved to {output_path}")

if __name__ == "__main__":
    src = r"C:\Users\David\.gemini\antigravity-ide\brain\4911b844-537a-420d-8908-b300c3004253\chrysalias_icon_mark_1785532572237.png"
    out = r"c:\Users\David\Desktop\ESCROW\build\images\chrysalias-logo-icon.png"
    remove_background(src, out)
