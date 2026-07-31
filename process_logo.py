from PIL import Image

def remove_background(input_path, output_path):
    img = Image.open(input_path).convert("RGBA")
    datas = img.getdata()

    new_data = []
    for item in datas:
        # Check if pixel is white or near-white (background)
        r, g, b, a = item
        if r > 240 and g > 240 and b > 240:
            new_data.append((255, 255, 255, 0))  # Transparent
        else:
            new_data.append(item)

    img.putdata(new_data)
    
    # Crop to non-transparent bounding box
    bbox = img.getbbox()
    if bbox:
        img = img.crop(bbox)

    # Add a small padding around the icon
    padding = 10
    new_width = img.width + (padding * 2)
    new_height = img.height + (padding * 2)
    padded_img = Image.new("RGBA", (new_width, new_height), (0, 0, 0, 0))
    padded_img.paste(img, (padding, padding))

    padded_img.save(output_path, "PNG")
    print(f"Processed logo saved to {output_path}")

if __name__ == "__main__":
    remove_background("build/images/chrysalias-logo.png", "build/images/chrysalias-logo-icon.png")
