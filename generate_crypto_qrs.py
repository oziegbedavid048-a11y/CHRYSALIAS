import urllib.request
import urllib.parse
import io
from PIL import Image, ImageDraw, ImageFont

def generate_qr_with_logo(text, coin_symbol, output_path, bg_color="#FFFFFF", fg_color="#002b49", coin_color=None):
    if coin_color is None:
        coin_color = "#f7931a" if coin_symbol == "BTC" else "#26a17b"
        
    # 1. Fetch high-res QR code with Error Correction Level H (30% damage/overlay tolerance)
    url = f"https://quickchart.io/qr?text={urllib.parse.quote(text)}&size=500&ecLevel=H&margin=2&dark={fg_color.replace('#','')}&light={bg_color.replace('#','')}"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        qr_bytes = response.read()
    
    qr_img = Image.open(io.BytesIO(qr_bytes)).convert("RGBA")
    w, h = qr_img.size
    
    # 2. Draw a central rounded icon badge for the crypto logo
    logo_size = int(w * 0.22) # 22% of total width (safely within Error Correction H 30% limit)
    logo_box = Image.new("RGBA", (logo_size, logo_size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(logo_box)
    
    # Draw solid white circular background with subtle dark border
    draw.ellipse([0, 0, logo_size, logo_size], fill="#FFFFFF", outline="#E2E8F0", width=3)
    
    # Draw inner colored circle
    margin = int(logo_size * 0.08)
    draw.ellipse([margin, margin, logo_size - margin, logo_size - margin], fill=coin_color)
    
    # Draw logo symbol in middle (₿ for BTC, ₮ for USDT)
    symbol = "₿" if coin_symbol == "BTC" else "₮"
    
    # Try loading bold font, fallback to default font
    try:
        font = ImageFont.truetype("arialbd.ttf", int(logo_size * 0.52))
    except Exception:
        try:
            font = ImageFont.truetype("arial.ttf", int(logo_size * 0.52))
        except Exception:
            font = ImageFont.load_default()
            
    bbox = draw.textbbox((0, 0), symbol, font=font)
    text_w = bbox[2] - bbox[0]
    text_h = bbox[3] - bbox[1]
    text_x = (logo_size - text_w) / 2 - bbox[0]
    text_y = (logo_size - text_h) / 2 - bbox[1]
    
    draw.text((text_x, text_y), symbol, fill="#FFFFFF", font=font)
    
    # 3. Overlay central logo badge on center of QR code
    pos_x = (w - logo_size) // 2
    pos_y = (h - logo_size) // 2
    qr_img.paste(logo_box, (pos_x, pos_y), logo_box)
    
    # Save final image
    qr_img.save(output_path, "PNG")
    print(f"Generated {output_path} successfully for {coin_symbol}")

if __name__ == "__main__":
    generate_qr_with_logo("1FXHP6uBYa9sBUjftccasRdVkP45AZ7HHu", "BTC", "build/images/btc-qr.png")
    generate_qr_with_logo("0x64816F70884f27a1E4F0909da1a57CE260B08986", "USDT", "build/images/usdt-qr.png")
