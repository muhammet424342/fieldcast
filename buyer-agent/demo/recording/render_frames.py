"""Turn a `script -T` recording into timed PNG frames (1920x1080) for the demo video.

Output: frames/NNNN.png and frames/durations.json ([seconds per frame]).
Only the escapes this recording uses are handled (bold, bold green, reset); everything else is stripped.
"""
import json
import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = next((a for a in sys.argv[1:] if not a.startswith("--")), HERE)  # folder with session.log + timing.log
OUT = os.path.join(SRC, "frames")
W, H = 1920, 1080
PAD_X, PAD_Y, LINE_H = 72, 120, 34
MAX_COLS = 104
MAX_LINES = (H - PAD_Y - 90) // LINE_H

BG = (13, 17, 23)
FG = (201, 209, 217)
DIM = (125, 133, 144)
GREEN = (63, 185, 80)
AMBER = (210, 153, 34)
CYAN = (88, 166, 255)
WHITE = (240, 246, 252)

FONT = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 26)
FONT_B = ImageFont.truetype("C:/Windows/Fonts/consolab.ttf", 26)
ESC = re.compile(r"\x1b\[[0-9;]*m")


def load(session_path, timing_path):
    raw = open(session_path, "rb").read()
    body = raw[raw.index(b"\n") + 1:]  # skip "Script started ..." header line
    chunks, pos = [], 0
    for line in open(timing_path):
        delay, size = line.split()
        chunks.append((float(delay), body[pos:pos + int(size)].decode("utf-8", "replace")))
        pos += int(size)
    return chunks


def style(line):
    """Return (color, font) for a whole visible line."""
    plain = ESC.sub("", line)
    if plain.startswith("$ "):
        return WHITE, FONT_B
    if plain.startswith("decision: pay"):
        return GREEN, FONT_B
    if plain.startswith("decision: skip"):
        return AMBER, FONT_B
    if plain.startswith("paid "):
        return CYAN, FONT_B
    if "USDC on Base" in plain:
        return WHITE, FONT
    if "\x1b[1m" in line and not plain.startswith("$"):
        return WHITE, FONT_B
    return FG, FONT


def wrap(line):
    plain = ESC.sub("", line)
    if len(plain) <= MAX_COLS:
        return [line]
    return [plain[i:i + MAX_COLS] for i in range(0, len(plain), MAX_COLS)]


def visible_lines(text):
    text = text.replace("\r", "")
    lines = []
    for ln in text.split("\n"):
        if "TERM environment variable not set" in ln:
            continue
        lines.extend(wrap(ln))
    while lines and not ESC.sub("", lines[-1]).strip():
        lines.pop()
    return lines[-MAX_LINES:]


def draw(lines, path):
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    # window chrome
    d.rounded_rectangle([40, 36, W - 40, H - 36], radius=18, outline=(48, 54, 61), width=2)
    for i, c in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
        d.ellipse([72 + i * 34, 60, 92 + i * 34, 80], fill=c)
    d.text((W // 2, 70), os.environ.get("TITLE", "fieldcast-buyer-agent  —  Dynamic server wallet  ·  x402  ·  USDC on Base"),
           font=FONT, fill=DIM, anchor="mm")
    y = PAD_Y
    for ln in lines:
        color, font = style(ln)
        plain = ESC.sub("", ln)
        if plain.startswith("$ "):
            d.text((PAD_X, y), "$", font=FONT_B, fill=GREEN)
            d.text((PAD_X + 30, y), plain[2:], font=FONT_B, fill=WHITE)
        else:
            d.text((PAD_X, y), plain, font=font, fill=color)
        y += LINE_H
    img.save(path)


def main():
    chunks = load(os.path.join(SRC, "session.log"), os.path.join(SRC, "timing.log"))
    os.makedirs(OUT, exist_ok=True)
    text, durations = "", []
    for i, (delay, data) in enumerate(chunks):
        if "\x1b[H\x1b[2J" in data or "\x1b[2J" in data:
            text = ""
            data = re.sub(r"\x1b\[H|\x1b\[2J|\x1b\[3J", "", data)
        text += data
        draw(visible_lines(text), os.path.join(OUT, "%04d.png" % i))
        next_delay = chunks[i + 1][0] if i + 1 < len(chunks) else 4.0
        durations.append(round(max(next_delay, 0.6), 3))
    json.dump(durations, open(os.path.join(OUT, "durations.json"), "w"))
    print("frames:", len(durations), "total seconds:", round(sum(durations), 1))


def demo():
    assert style("\x1b[1;32m$\x1b[0m node buyer.mjs balance")[0] == WHITE
    assert style("decision: pay — verified")[0] == GREEN
    assert style("decision: skip — none")[0] == AMBER
    assert visible_lines("TERM environment variable not set.\r\nok\r\n\r\n") == ["ok"]
    assert len(wrap("x" * (MAX_COLS * 2 + 1))) == 3
    print("selftest ok")


if __name__ == "__main__":
    demo() if "--selftest" in sys.argv else main()
