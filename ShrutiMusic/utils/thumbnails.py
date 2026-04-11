

import os
import re
import aiofiles
import aiohttp
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from py_yt import VideosSearch
from config import YOUTUBE_IMG_URL as FAILED

# ── Canvas ───────────────────────────────────────────────────────────────────
CANVAS_W, CANVAS_H = 1280, 800

# ── Frosted glass panel ───────────────────────────────────────────────────────
PANEL_W, PANEL_H = 900, 670
PANEL_X          = (CANVAS_W - PANEL_W) // 2    # 190
PANEL_Y          = (CANVAS_H - PANEL_H) // 2    # 65
PANEL_RADIUS     = 40
PANEL_ALPHA      = 200
# 0-255  (higher = more opaque white)

# ── Song thumbnail inside panel ───────────────────────────────────────────────
THUMB_W, THUMB_H = 848, 477
THUMB_X          = PANEL_X + (PANEL_W - THUMB_W) // 2
THUMB_Y          = PANEL_Y + 26
THUMB_RADIUS     = 18

# ── Text ─────────────────────────────────────────────────────────────────────
TEXT_LEFT = PANEL_X + 40
TITLE_Y   = THUMB_Y + THUMB_H + 22
META_Y    = TITLE_Y + 48

# ── Progress bar ──────────────────────────────────────────────────────────────
BAR_X         = PANEL_X + 40
BAR_Y         = META_Y + 44
BAR_TOTAL_LEN = PANEL_W - 80        # 700 px wide
BAR_RED_RATIO = 0.58
BAR_RED_LEN   = int(BAR_TOTAL_LEN * BAR_RED_RATIO)
BAR_DOT_R     = 9

# ── Icons row ─────────────────────────────────────────────────────────────────
ICONS_W, ICONS_H = 420, 48
ICONS_X = PANEL_X + (PANEL_W - ICONS_W) // 2
ICONS_Y = BAR_Y + 52

# ── Branding ──────────────────────────────────────────────────────────────────
BRAND_TEXT      = "Kelly Music"
BRAND_FONT_SIZE = 30

# ── Cache ─────────────────────────────────────────────────────────────────────
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

MAX_TITLE_WIDTH = PANEL_W - 80


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def trim_to_width(text: str, font: ImageFont.FreeTypeFont, max_w: int) -> str:
    ellipsis = "…"
    if font.getlength(text) <= max_w:
        return text
    for i in range(len(text) - 1, 0, -1):
        if font.getlength(text[:i] + ellipsis) <= max_w:
            return text[:i] + ellipsis
    return ellipsis


def rounded_paste(base: Image.Image, layer: Image.Image, pos: tuple, radius: int):
    """Paste layer onto base with a rounded-rectangle alpha mask."""
    mask = Image.new("L", layer.size, 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, *layer.size), radius, fill=255)
    base.paste(layer, pos, mask)


def draw_frosted_panel(bg: Image.Image,
                       x: int, y: int, w: int, h: int,
                       radius: int, alpha: int):
    """
    Crop the blurred bg area, composite a white frost layer on top,
    then paste back with a rounded mask + a thin white border ring.
    """
    region         = bg.crop((x, y, x + w, y + h)).convert("RGBA")
    blurred_region = region.filter(ImageFilter.GaussianBlur(18))
    frost          = Image.new("RGBA", (w, h), (255, 255, 255, alpha))
    frosted        = Image.alpha_composite(blurred_region, frost)

    # Rounded mask
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w, h), radius, fill=255)
    bg.paste(frosted, (x, y), mask)

    # White border ring
    border = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    ImageDraw.Draw(border).rounded_rectangle(
        (0, 0, w - 1, h - 1), radius,
        outline=(255, 255, 255, 160), width=3
    )
    bg.paste(border, (x, y), border)


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

async def gen_thumb(videoid: str) -> str:
    cache_path = os.path.join(CACHE_DIR, f"{videoid}_kelly.png")
    if os.path.exists(cache_path):
        return cache_path

    # ── Fetch metadata ────────────────────────────────────────────────────────
    results = VideosSearch(f"https://www.youtube.com/watch?v={videoid}", limit=1)
    try:
        results_data = await results.next()
        result_items = results_data.get("result", [])
        if not result_items:
            raise ValueError("No results found.")
        data      = result_items[0]
        title     = re.sub(r"\W+", " ", data.get("title", "Unsupported Title")).title()
        thumbnail = data.get("thumbnails", [{}])[0].get("url", FAILED)
        duration  = data.get("duration")
        views     = data.get("viewCount", {}).get("short", "Unknown Views")
        channel   = data.get("channel",   {}).get("name",  "Unknown Channel")
    except Exception:
        title, thumbnail, duration, views, channel = (
            "Unsupported Title", FAILED, None, "Unknown Views", "Unknown Channel"
        )

    is_live       = not duration or str(duration).strip().lower() in {"", "live", "live now"}
    duration_text = "Live" if is_live else (duration or "Unknown")

    # ── Download thumbnail ────────────────────────────────────────────────────
    thumb_path = os.path.join(CACHE_DIR, f"raw_{videoid}.png")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(thumbnail) as resp:
                if resp.status == 200:
                    async with aiofiles.open(thumb_path, "wb") as f:
                        await f.write(await resp.read())
    except Exception:
        return FAILED

    # ── Build canvas ──────────────────────────────────────────────────────────
    raw = Image.open(thumb_path).convert("RGBA")

    # 1. Blurred background (full canvas)
    bg = raw.resize((CANVAS_W, CANVAS_H), Image.LANCZOS)
    bg = bg.filter(ImageFilter.GaussianBlur(22))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)

    # 2. Frosted glass card
    draw_frosted_panel(bg, PANEL_X, PANEL_Y, PANEL_W, PANEL_H, PANEL_RADIUS, PANEL_ALPHA)

    # 3. Song thumbnail (sharp, inside card)
    thumb_img = raw.resize((THUMB_W, THUMB_H), Image.LANCZOS)
    rounded_paste(bg, thumb_img, (THUMB_X, THUMB_Y), THUMB_RADIUS)

    # ── Fonts ─────────────────────────────────────────────────────────────────
    try:
        font_title = ImageFont.truetype("ShrutiMusic/assets/font.ttf",  32)
        font_meta  = ImageFont.truetype("ShrutiMusic/assets/font2.ttf", 20)
        font_time  = ImageFont.truetype("ShrutiMusic/assets/font2.ttf", 18)
        font_brand = ImageFont.truetype("ShrutiMusic/assets/font.ttf",  BRAND_FONT_SIZE)
    except OSError:
        font_title = font_meta = font_time = font_brand = ImageFont.load_default()

    draw = ImageDraw.Draw(bg)

    # ── Title ─────────────────────────────────────────────────────────────────
    draw.text(
        (TEXT_LEFT, TITLE_Y),
        trim_to_width(title, font_title, MAX_TITLE_WIDTH),
        fill=(15, 15, 15),
        font=font_title
    )

    # ── Meta ──────────────────────────────────────────────────────────────────
    draw.text(
        (TEXT_LEFT, META_Y),
        f"YouTube  |  {views}",
        fill=(60, 60, 60),
        font=font_meta
    )

    # ── Progress bar ──────────────────────────────────────────────────────────
    # Gray track
    draw.rounded_rectangle(
        [(BAR_X, BAR_Y - 4), (BAR_X + BAR_TOTAL_LEN, BAR_Y + 4)],
        radius=4, fill=(185, 185, 185)
    )
    # Red played portion
    draw.rounded_rectangle(
        [(BAR_X, BAR_Y - 4), (BAR_X + BAR_RED_LEN, BAR_Y + 4)],
        radius=4, fill=(220, 30, 30)
    )
    # Playhead dot
    dot_cx = BAR_X + BAR_RED_LEN
    draw.ellipse(
        [(dot_cx - BAR_DOT_R, BAR_Y - BAR_DOT_R),
         (dot_cx + BAR_DOT_R, BAR_Y + BAR_DOT_R)],
        fill=(220, 30, 30)
    )
    # Time labels
    time_y = BAR_Y + BAR_DOT_R + 7
    draw.text((BAR_X, time_y), "00:00", fill=(40, 40, 40), font=font_time)

    end_bbox = draw.textbbox((0, 0), duration_text, font=font_time)
    end_w    = end_bbox[2] - end_bbox[0]
    draw.text(
        (BAR_X + BAR_TOTAL_LEN - end_w, time_y),
        duration_text,
        fill=(220, 30, 30) if is_live else (40, 40, 40),
        font=font_time
    )

    # ── Play icons ────────────────────────────────────────────────────────────
    icons_path = "ShrutiMusic/assets/play_icons.png"
    if os.path.isfile(icons_path):
        ic = Image.open(icons_path).resize((ICONS_W, ICONS_H)).convert("RGBA")
        r, g, b, a = ic.split()
        dark_ic = Image.merge("RGBA", (
            r.point(lambda _: 20),
            g.point(lambda _: 20),
            b.point(lambda _: 20),
            a
        ))
        bg.paste(dark_ic, (ICONS_X, ICONS_Y), dark_ic)

    # ── Branding: "Kelly Music 🎶" top-right ──────────────────────────────────
    brand_bbox = draw.textbbox((0, 0), BRAND_TEXT, font=font_brand)
    brand_w    = brand_bbox[2] - brand_bbox[0]
    brand_x    = CANVAS_W - brand_w - 20
    brand_y    = 16

    # Drop shadow for legibility
    draw.text((brand_x + 2, brand_y + 2), BRAND_TEXT,
              fill=(0, 0, 0, 130), font=font_brand)
    draw.text((brand_x, brand_y), BRAND_TEXT,
              fill=(255, 255, 255), font=font_brand)

    # ── Save ──────────────────────────────────────────────────────────────────
    try:
        os.remove(thumb_path)
    except OSError:
        pass

    bg.convert("RGB").save(cache_path, quality=95)
    return cache_path
