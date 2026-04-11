import asyncio
import random
import time

from pyrogram import filters
from pyrogram.enums import ChatType, ChatAction
from pyrogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message
from py_yt import VideosSearch
import config
from ShrutiMusic import app
from ShrutiMusic.misc import _boot_
from ShrutiMusic.plugins.sudo.sudoers import sudoers_list
from ShrutiMusic.utils.database import (
    add_served_chat,
    add_served_user,
    blacklisted_chats,
    get_lang,
    is_banned_user,
    is_on_off,
)
from ShrutiMusic.utils import bot_sys_stats
from ShrutiMusic.utils.decorators.language import LanguageStart
from ShrutiMusic.utils.formatters import get_readable_time
from ShrutiMusic.utils.inline import help_pannel_page1, private_panel, start_panel
from config import BANNED_USERS
from strings import get_string


# ─────────────────────────────────────────────
#  Assets  —  apne links yahan add karo
# ─────────────────────────────────────────────

STICKERS = [
    "CAACAgUAAx0CYlaJawABBy4vZaieO6T-Ayg3mD-JP-f0yxJngIkAAv0JAALVS_FWQY7kbQSaI-geBA",
    "CAACAgUAAx0CYlaJawABBy4jZaidvIXNPYnpAjNnKgzaHmh3cvoAAiwIAAIda2lVNdNI2QABHuVVHgQ",
    "CAACAgUAAxkBAAIBGWlPj2BophzDt6BnmyBS-NFtqg7XAAJ9EgACKim5VpulXSTMVLgrHgQ",
    "CAACAgUAAyEFAATKMLw9AAICtWlPj7tZxFmYVV_Ut4V9P1p2-3geAAIKDwACNyvhV0CesVynrgRUHgQ",
    "CAACAgUAAyEFAATKMLw9AAICtmlPj7sZ0HT2Rd3D1UqkzS3emXViAAJnDQACNIDgV5xhBUdt_f_OHgQ",
    "CAACAgUAAyEFAATKMLw9AAICt2lPj7u8HsJsaYzz7Ckcp050XNjUAALHDgACMBngVxP0ZbLYPzrdHgQ",
    "CAACAgUAAyEFAATKMLw9AAICvmlPj-rhVaQNL8BTBogN-zLj8tsJAAIeEQACa-ZBV7VQQVNCHMhKHgQ",
    "CAACAgUAAyEFAATKMLw9AAICwWlPkAp5D4ZAIfo5fO_GMUOhaYUUAAKaEQAC88upV61z2KeqfHoOHgQ",
]

EMOJIS = ["❤️", "😁", "👀", "⚡️", "🕊", "❤️‍🔥", "💅", "👻"]

# 20 image slots — apne links yahan replace karo
START_IMAGES = [
    "https://files.catbox.moe/dt3cul.jpg",   # 1
    "https://d.uguu.se/swAfSjgB.jpg",        # 2
    "https://d.uguu.se/fNYgGAqb.jpg",        # 3
    "https://n.uguu.se/kkZyxTuu.jpg",        # 4
    "https://h.uguu.se/kriwaMVV.jpg",        # 5
    "https://h.uguu.se/FkBwoXiZ.jpg",        # 6
    "https://h.uguu.se/OLlubfbz.jpg",        # 7
    "https://n.uguu.se/RNkVNuNM.jpg",        # 8
    "https://d.uguu.se/rYFrpERx.jpg",        # 9
    "https://o.uguu.se/RddWBCJG.jpg",        # 10
    "https://h.uguu.se/GTRaMdaT.jpg",        # 11
    "https://o.uguu.se/zaUKLFlH.jpg",        # 12
    "https://d.uguu.se/RfXMBmWH.jpg",        # 13
    "https://d.uguu.se/GednJKaH.jpg",        # 14
    "https://h.uguu.se/ziPuTJbg.jpg",        # 15
    "https://d.uguu.se/aBOqAbxH.jpg",        # 16
    "https://n.uguu.se/HMCkQVwJ.jpg",        # 17
    "https://n.uguu.se/awGffrQp.jpg",        # 18
    "https://n.uguu.se/hfLnzuMU.jpg",        # 19
    "https://n.uguu.se/urlcGvnb.jpg",        # 
]

# ─────────────────────────────────────────────
#  Helper: Anya-style intro sequence
# ─────────────────────────────────────────────

async def _do_intro(client, message: Message):
        """React → sticker (delete)."""

    # 1. React on the incoming message
    try:
        await message.react(random.choice(EMOJIS))
    except Exception:
        pass

    # 4. Sticker → delete
    sticker_msg = await message.reply_sticker(sticker=random.choice(STICKERS))
    await asyncio.sleep(0.3)
    await sticker_msg.delete()


# ─────────────────────────────────────────────
#  /start  —  Private
# ─────────────────────────────────────────────

@app.on_message(filters.command(["start"]) & filters.private & ~BANNED_USERS)
@LanguageStart
async def start_pm(client, message: Message, _):
    await add_served_user(message.from_user.id)

    # Anya-style intro (reaction + sticker)
    await _do_intro(client, message)

    if len(message.text.split()) > 1:
        name = message.text.split(None, 1)[1]

        # ── help
        if name[0:4] == "help":
            keyboard = help_pannel_page1(_)
            try:
                return await message.reply_photo(
                    photo=random.choice(START_IMAGES),
                    caption=_["help_1"].format(config.SUPPORT_GROUP),
                    reply_markup=keyboard,
                    message_effect_id=5159385139981059251,
                )
            except Exception:
                return await message.reply_photo(
                    photo=random.choice(START_IMAGES),
                    caption=_["help_1"].format(config.SUPPORT_GROUP),
                    reply_markup=keyboard,
                )

        # ── sudolist
        if name[0:3] == "sud":
            await sudoers_list(client=client, message=message, _=_)
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=(
                        f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>sᴜᴅᴏʟɪsᴛ</b>.\n\n"
                        f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                        f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}"
                    ),
                )
            return

        # ── track info
        if name[0:3] == "inf":
            m = await message.reply_text("🔎")
            query = str(name).replace("info_", "", 1)
            query = f"https://www.youtube.com/watch?v={query}"
            results = VideosSearch(query, limit=1)
            for result in (await results.next())["result"]:
                title = result["title"]
                duration = result["duration"]
                views = result["viewCount"]["short"]
                thumbnail = result["thumbnails"][0]["url"].split("?")[0]
                channellink = result["channel"]["link"]
                channel = result["channel"]["name"]
                link = result["link"]
                published = result["publishedTime"]
            searched_text = _["start_6"].format(
                title, duration, views, published, channellink, channel, app.mention
            )
            key = InlineKeyboardMarkup([[
                InlineKeyboardButton(text=_["S_B_8"], url=link),
                InlineKeyboardButton(text=_["S_B_9"], url=config.SUPPORT_GROUP),
            ]])
            await m.delete()
            try:
                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail,
                    caption=searched_text,
                    reply_markup=key,
                    message_effect_id=5159385139981059251,
                )
            except Exception:
                await app.send_photo(
                    chat_id=message.chat.id,
                    photo=thumbnail,
                    caption=searched_text,
                    reply_markup=key,
                )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=(
                        f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ ᴛᴏ ᴄʜᴇᴄᴋ <b>ᴛʀᴀᴄᴋ ɪɴғᴏʀᴍᴀᴛɪᴏɴ</b>.\n\n"
                        f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                        f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}"
                    ),
                )
            return

        # ── deep-link "start"
        if name == "start":
            out = private_panel(_)
            UP, CPU, RAM, DISK = await bot_sys_stats()
            try:
                await message.reply_photo(
                    photo=random.choice(START_IMAGES),
                    caption=_["start_2"].format(
                        message.from_user.mention, app.mention, UP, DISK, CPU, RAM
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                    message_effect_id=5159385139981059251,
                    has_spoiler=True,
                )
            except Exception:
                await message.reply_photo(
                    photo=random.choice(START_IMAGES),
                    caption=_["start_2"].format(
                        message.from_user.mention, app.mention, UP, DISK, CPU, RAM
                    ),
                    reply_markup=InlineKeyboardMarkup(out),
                    has_spoiler=True,
                )
            if await is_on_off(2):
                return await app.send_message(
                    chat_id=config.LOG_GROUP_ID,
                    text=(
                        f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n"
                        f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                        f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}"
                    ),
                )
    else:
        # ── plain /start (no deep-link)
        out = private_panel(_)
        UP, CPU, RAM, DISK = await bot_sys_stats()
        try:
            await message.reply_photo(
                photo=random.choice(START_IMAGES),
                caption=_["start_2"].format(
                    message.from_user.mention, app.mention, UP, DISK, CPU, RAM
                ),
                reply_markup=InlineKeyboardMarkup(out),
                message_effect_id=5159385139981059251,
            )
        except Exception:
            await message.reply_photo(
                photo=random.choice(START_IMAGES),
                caption=_["start_2"].format(
                    message.from_user.mention, app.mention, UP, DISK, CPU, RAM
                ),
                reply_markup=InlineKeyboardMarkup(out),
            )
        if await is_on_off(2):
            return await app.send_message(
                chat_id=config.LOG_GROUP_ID,
                text=(
                    f"{message.from_user.mention} ᴊᴜsᴛ sᴛᴀʀᴛᴇᴅ ᴛʜᴇ ʙᴏᴛ.\n\n"
                    f"<b>ᴜsᴇʀ ɪᴅ :</b> <code>{message.from_user.id}</code>\n"
                    f"<b>ᴜsᴇʀɴᴀᴍᴇ :</b> @{message.from_user.username}"
                ),
            )


# ─────────────────────────────────────────────
#  /start  —  Group
# ─────────────────────────────────────────────

@app.on_message(filters.command(["start"]) & filters.group & ~BANNED_USERS)
@LanguageStart
async def start_gp(client, message: Message, _):
    out = start_panel(_)
    uptime = int(time.time() - _boot_)
    try:
        await message.reply_photo(
            photo=random.choice(START_IMAGES),
            caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
            reply_markup=InlineKeyboardMarkup(out),
            message_effect_id=5159385139981059251,
        )
    except Exception:
        await message.reply_photo(
            photo=random.choice(START_IMAGES),
            caption=_["start_1"].format(app.mention, get_readable_time(uptime)),
            reply_markup=InlineKeyboardMarkup(out),
        )
    return await add_served_chat(message.chat.id)


# ─────────────────────────────────────────────
#  Welcome (bot added to group)
# ─────────────────────────────────────────────

@app.on_message(filters.new_chat_members, group=-1)
async def welcome(client, message: Message):
    for member in message.new_chat_members:
        try:
            language = await get_lang(message.chat.id)
            _ = get_string(language)

            if await is_banned_user(member.id):
                try:
                    await message.chat.ban_member(member.id)
                except Exception:
                    pass

            if member.id == app.id:
                if message.chat.type != ChatType.SUPERGROUP:
                    await message.reply_text(_["start_4"])
                    return await app.leave_chat(message.chat.id)

                if message.chat.id in await blacklisted_chats():
                    await message.reply_text(
                        _["start_5"].format(
                            app.mention,
                            f"https://t.me/{app.username}?start=sudolist",
                            config.SUPPORT_GROUP,
                        ),
                        disable_web_page_preview=True,
                    )
                    return await app.leave_chat(message.chat.id)

                out = start_panel(_)
                try:
                    await message.reply_photo(
                        photo=random.choice(START_IMAGES),
                        caption=_["start_3"].format(
                            message.from_user.first_name,
                            app.mention,
                            message.chat.title,
                            app.mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(out),
                        message_effect_id=5159385139981059251,
                    )
                except Exception:
                    await message.reply_photo(
                        photo=random.choice(START_IMAGES),
                        caption=_["start_3"].format(
                            message.from_user.first_name,
                            app.mention,
                            message.chat.title,
                            app.mention,
                        ),
                        reply_markup=InlineKeyboardMarkup(out),
                    )
                await add_served_chat(message.chat.id)
                await message.stop_propagation()

        except Exception as ex:
            print(ex)
