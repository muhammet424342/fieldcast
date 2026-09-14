"""Compose proof card + ffmpeg concat of title/steps/terminal/proof/end."""
import json
import os
import subprocess
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
CARDS = HERE / "cards"
FRAMES = HERE / "frames"
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


def fit(im, box_w, box_h):
    im = im.convert("RGB")
    scale = min(box_w / im.width, box_h / im.height)
    nw, nh = int(im.width * scale), int(im.height * scale)
    return im.resize((nw, nh), Image.Resampling.LANCZOS)


def crop_tx(path):
    im = Image.open(path).convert("RGB")
    # Drop Blockscout chrome: left nav + top banners + bottom ad.
    left = int(im.width * 0.20)
    top = int(im.height * 0.22)
    right = im.width - 16
    bottom = int(im.height * 0.88)
    return im.crop((left, top, right, bottom))


def make_proof():
    canvas = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(canvas)
    title_f = font(40, True)
    lab_f = font(22, True)
    small_f = font(18, False)
    t = "On-chain proof (Arbitrum Sepolia)"
    tw = d.textbbox((0, 0), t, font=title_f)[2]
    d.text(((W - tw) // 2, 36), t, font=title_f, fill=FG)

    specs = [
        (HERE / "tx_release_blockscout.png", "1. Vault release  0.01 USDC", 70),
        (HERE / "tx_payment_blockscout.png", "2. x402 payment  0.01 USDC  ·  HTTP 200", 70 + 500),
    ]
    for src, label, y in specs:
        d.text((80, y), label, font=lab_f, fill=GREEN)
        shot = fit(crop_tx(src), 1760, 430)
        x = (W - shot.width) // 2
        canvas.paste(shot, (x, y + 36))
    note = "Testnet. Both wallets are ours. Shows a working vault-gated agent payment, not outside customers."
    nw = d.textbbox((0, 0), note, font=small_f)[2]
    d.text(((W - nw) // 2, H - 48), note, font=small_f, fill=MUTED)
    out = CARDS / "03_proof.png"
    canvas.save(out)
    print("wrote", out)


def concat():
    durations = json.loads((FRAMES / "durations.json").read_text())
    frame_files = sorted(FRAMES.glob("*.png"))
    frame_files = [p for p in frame_files if p.name[0].isdigit()]
    if len(frame_files) != len(durations):
        raise SystemExit(f"frames {len(frame_files)} vs durations {len(durations)}")

    clips = [
        (CARDS / "01_title.png", 4.0),
        (CARDS / "02_steps.png", 7.0),
    ]
    clips += list(zip(frame_files, durations))
    clips += [
        (CARDS / "03_proof.png", 8.0),
        (CARDS / "04_end.png", 5.0),
    ]

    lst = HERE / "concat.txt"
    lines = []
    for path, dur in clips:
        p = path.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{p}'")
        lines.append(f"duration {dur:.3f}")
    # concat demuxer needs last file repeated
    last = clips[-1][0].resolve().as_posix().replace("'", r"'\''")
    lines.append(f"file '{last}'")
    lst.write_text("\n".join(lines) + "\n", encoding="utf-8")

    out = HERE / "arbitrum_demo.mp4"
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(lst),
        "-vf", "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30,format=yuv420p",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", "-movflags", "+faststart",
        str(out),
    ]
    print("ffmpeg", " ".join(cmd[-6:]))
    subprocess.check_call(cmd)
    print("wrote", out, out.stat().st_size)


if __name__ == "__main__":
    make_proof()
    concat()
