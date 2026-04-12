import os
from unidecode import unidecode
from PIL import ImageDraw, Image, ImageFont, ImageChops
from pyrogram import filters, enums
from pyrogram.types import (
    ChatMemberUpdated,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from logging import getLogger
from ShrutiMusic import app, LOGGER
from ShrutiMusic.misc import SUDOERS
from ShrutiMusic.utils.database import db

try:
    wlcm = db.welcome
except Exception:
    from ShrutiMusic.utils.database import welcome as wlcm

LOGGER = getLogger(__name__)


class temp:
    ME = None
    CURRENT = 2
    CANCEL = False
    MELCOW = {}
    U_NAME = None
    B_NAME = None


# ── Helper: Profile pic ko circle mein crop karo ────────────────────────────
def circle(pfp, size=(680, 680)):
    pfp = pfp.resize(size, Image.LANCZOS).convert("RGBA")
    bigsize = (pfp.size[0] * 3, pfp.size[1] * 3)
    mask = Image.new("L", bigsize, 0)
    draw = ImageDraw.Draw(mask)
    draw.ellipse((0, 0) + bigsize, fill=255)
    mask = mask.resize(pfp.size, Image.LANCZOS)
    mask = ImageChops.darker(mask, pfp.split()[-1])
    pfp.putalpha(mask)
    return pfp


# ── Welcome image generator ──────────────────────────────────────────────────
def welcomepic(pic, user, chat, id, uname):
    # Local path se background load (2560x1707)
    background = Image.open("ShrutiMusic/assets/welcome.png").convert("RGBA")
    bg_w, bg_h = background.size  # 2560, 1707

    # ────────────────────────────────────────────────────────────────────────
    # Profile Picture → Right side golden circle
    # Circle center: ~(1932, 802), ring inner radius ~340px
    # ────────────────────────────────────────────────────────────────────────
    pfp_size = 680                          # golden ring ke andar fit
    try:
        pfp = Image.open(pic).convert("RGBA")
    except Exception:
        pfp = Image.open("ShrutiMusic/assets/upic.png").convert("RGBA")

    pfp = circle(pfp, size=(pfp_size, pfp_size))

    cx    = 1932                            # ← circle center X (left/right)
    cy    = 802                             # ← circle center Y (upar/neeche)
    pfp_x = cx - pfp_size // 2             # 1592
    pfp_y = cy - pfp_size // 2             # 462
    background.paste(pfp, (pfp_x, pfp_y), pfp)

    # ────────────────────────────────────────────────────────────────────────
    # Text → Left side neon rectangle box
    # Box area: x 153–1216, y 452–1263  |  center: (684, 857)
    # ────────────────────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(background)

    try:
        font = ImageFont.truetype("ShrutiMusic/assets/font.ttf", size=72)
    except Exception:
        font = ImageFont.load_default()

    # 3 lines ko box ke center mein vertically center karo
    line_gap     = 130                      # ← lines ke beech gap
    total_h      = line_gap * 2
    text_x       = 230                      # ← box ke andar left margin
    text_start_y = 727                      # ← (box_center_y - total_h // 2)

    uname_str  = f"@{uname}" if uname else "Not Set"
    name_clean = unidecode(user)[:18]       # lambe naam trim

    draw.text(
        (text_x, text_start_y),
        f"✦ Name  :  {name_clean}",
        fill="white",
        font=font,
    )
    draw.text(
        (text_x, text_start_y + line_gap),
        f"✦ ID       :  {id}",
        fill="white",
        font=font,
    )
    draw.text(
        (text_x, text_start_y + line_gap * 2),
        f"✦ User   :  {uname_str}",
        fill="white",
        font=font,
    )

    # Save
    os.makedirs("downloads", exist_ok=True)
    output_path = f"downloads/welcome#{id}.png"
    background.save(output_path)
    return output_path


# ── Command: /welcome on | off ───────────────────────────────────────────────
@app.on_message(filters.command("welcome") & ~filters.private)
async def auto_state(_, message):
    usage = "<b>❖ ᴜsᴀɢᴇ ➥</b> /welcome [on|off]"

    if len(message.command) == 1:
        return await message.reply_text(usage)

    chat_id = message.chat.id
    user    = await app.get_chat_member(chat_id, message.from_user.id)

    if user.status in (
        enums.ChatMemberStatus.ADMINISTRATOR,
        enums.ChatMemberStatus.OWNER,
    ):
        A     = await wlcm.find_one({"chat_id": chat_id})
        state = message.text.split(None, 1)[1].strip().lower()

        if state == "on":
            if A and not A.get("disabled", False):
                return await message.reply_text("✦ Special Welcome Already Enabled")
            await wlcm.update_one(
                {"chat_id": chat_id},
                {"$set": {"disabled": False}},
                upsert=True,
            )
            await message.reply_text(
                f"✦ Enabled Special Welcome in {message.chat.title}"
            )

        elif state == "off":
            if A and A.get("disabled", False):
                return await message.reply_text("✦ Special Welcome Already Disabled")
            await wlcm.update_one(
                {"chat_id": chat_id},
                {"$set": {"disabled": True}},
                upsert=True,
            )
            await message.reply_text(
                f"✦ Disabled Special Welcome in {message.chat.title}"
            )

        else:
            await message.reply_text(usage)
    else:
        await message.reply("✦ Only Admins Can Use This Command")


# ── Event: Naya member join kare to welcome bhejo ───────────────────────────
@app.on_chat_member_updated(filters.group, group=-3)
async def greet_group(_, member: ChatMemberUpdated):
    chat_id = member.chat.id
    A       = await wlcm.find_one({"chat_id": chat_id})

    # Welcome disabled hai to return
    if A and A.get("disabled", False):
        return

    # Sirf naye members ke liye
    if (
        not member.new_chat_member
        or member.new_chat_member.status in {"banned", "left", "restricted"}
        or (
            member.old_chat_member
            and member.old_chat_member.status
            not in {
                enums.ChatMemberStatus.BANNED,
                enums.ChatMemberStatus.LEFT,
                enums.ChatMemberStatus.RESTRICTED,
            }
        )
    ):
        return

    user = (
        member.new_chat_member.user
        if member.new_chat_member
        else member.from_user
    )

    # Profile picture download karo
    try:
        pic = await app.download_media(
            user.photo.big_file_id,
            file_name=f"downloads/pp{user.id}.png",
        )
    except AttributeError:
        pic = "ShrutiMusic/assets/upic.png"

    # Purana welcome message delete karo
    if temp.MELCOW.get(f"welcome-{chat_id}") is not None:
        try:
            await temp.MELCOW[f"welcome-{chat_id}"].delete()
        except Exception as e:
            LOGGER.error(e)

    # Welcome image banao aur bhejo
    try:
        welcomeimg = welcomepic(
            pic,
            user.first_name,
            member.chat.title,
            user.id,
            user.username,
        )

        temp.MELCOW[f"welcome-{chat_id}"] = await app.send_photo(
            chat_id,
            photo=welcomeimg,
            caption=(
                f"<blockquote><b>✬ 𝐖ᴇʟᴄσᴍᴇ {user.mention} ɪɴ σᴜʀ ɢʀσᴜᴘ 💐</b>\n"
                f"</blockquote><blockquote><b>✬ 𝐆ʀσᴜᴘ » {member.chat.title}\n"
                f"✬ 𝐔sᴇʀ ɪᴅ » {user.id}\n"
                f"✬ 𝐔sᴇʀɴɑᴍᴇ » @{user.username if user.username else 'ɴᴏᴛ sᴇᴛ'}</b>\n"
                f"</blockquote><blockquote><b><u>❖ 𝐇σᴘᴇ ʏσᴜ ғɪɴᴅ ɢσσᴅ ᴠɪʙᴇs, "
                f"ɴᴇᴡ ғʀɪᴇɴᴅs, ᴧɴᴅ ʟσᴛs σғ ғᴜɴ ʜᴇʀᴇ ! 💞</u></b>\n"
                f"</blockquote><blockquote><b>❖ 𝐌ᴧᴅє ʙʏ » "
                f'<a href="https://t.me/Anya_Bots">˹𝐀ɴʏᴀ ꭙ 𝐁ᴏᴛs˼</a></b></blockquote>'
            ),
            reply_markup=InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            "✙ 𝐀ᴅᴅ 𝐌є 𝐈η 𝐘συʀ 𝐆ʀσυᴘ ✙",
                            url=f"https://t.me/{app.username}?startgroup=True",
                        )
                    ]
                ]
            ),
        )

    except Exception as e:
        LOGGER.error(e)

    # Temporary files cleanup
    try:
        os.remove(f"downloads/welcome#{user.id}.png")
    except Exception:
        pass
    try:
        os.remove(f"downloads/pp{user.id}.png")
    except Exception:
        pass
