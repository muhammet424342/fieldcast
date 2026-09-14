"""1920x1080 title/how/end cards for the Arbitrum demo (not the RUNTIME/Base ones)."""
from PIL import Image, ImageDraw, ImageFont
import os

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "cards")
os.makedirs(OUT, exist_ok=True)
W, H = 1920, 1080
BG = (13, 17, 23)
FG = (240, 246, 252)
MUTED = (139, 148, 158)
BLUE = (88, 166, 255)
GREEN = (63, 185, 80)

def font(size, bold=False):
    name = "C:/Windows/Fonts/segoeuib.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf"
    try:
        return ImageFont.truetype(name, size)
    except OSError:
        return ImageFont.truetype("C:/Windows/Fonts/arial.ttf", size)

def card(path, lines):
    im = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(im)
    y = 340 if len(lines) <= 4 else 220
    for text, size, color, bold, gap in lines:
        f = font(size, bold)
        bbox = d.textbbox((0, 0), text, font=f)
        tw = bbox[2] - bbox[0]
        d.text(((W - tw) // 2, y), text, font=f, fill=color)
        y += gap
    im.save(path)
    print("wrote", path)

card(os.path.join(OUT, "01_title.png"), [
    ("Fieldcast Buyer Agent", 64, FG, True, 90),
    ("pays only for verified data, only from an on-chain budget", 32, MUTED, False, 80),
    ("AgentBudgetVault  ·  x402  ·  USDC on Arbitrum Sepolia", 28, BLUE, False, 120),
    ("Arbitrum Open House Singapore 2026", 22, MUTED, False, 40),
])
card(os.path.join(OUT, "02_steps.png"), [
    ("How it spends", 48, FG, True, 90),
    ("1.  AgentBudgetVault holds the USDC. Caps are on-chain.", 30, MUTED, False, 62),
    ("2.  Shipping notice has none of the fields  →  skip, $0.", 30, MUTED, False, 62),
    ("3.  Messy receipt quotes match the text  →  vault releases 0.01, then pay.", 30, MUTED, False, 62),
    ("The model cannot override the caps. No quote in the document = no payment.", 26, BLUE, False, 40),
])
card(os.path.join(OUT, "04_end.png"), [
    ("On-chain budget, verified data only", 48, FG, True, 90),
    ("Vault  0x2c48d7f3bd378d64b0ebe7f85d3ae94fcf3d004c", 26, MUTED, False, 56),
    ("Agent  0x126c57A501226D0f6dfc63E093A9aa928425333d", 26, MUTED, False, 80),
    ("HackQuest  ·  Promising Products  ·  Arbitrum Sepolia", 26, BLUE, False, 40),
])
