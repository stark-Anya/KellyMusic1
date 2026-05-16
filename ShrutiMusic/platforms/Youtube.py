import asyncio
import os
import re
from typing import Union
import yt_dlp
from pyrogram.enums import MessageEntityType
from pyrogram.types import Message
from ShrutiMusic.utils.formatters import time_to_seconds
from ShrutiMusic import LOGGER
import aiohttp

try:
    from py_yt import VideosSearch
except ImportError:
    from youtubesearchpython.__future__ import VideosSearch

try:
    from youtubesearchpython.__future__ import Playlist
    PLAYLIST_SUPPORT = True
except ImportError:
    PLAYLIST_SUPPORT = False

# ---------------------------------------------------------------------------
# API Configuration — set via environment variables or edit defaults below
# ---------------------------------------------------------------------------
API_URL = os.environ.get("SHRUTI_API_URL", "https://api.shrutibots.site")
API_KEY = os.environ.get("SHRUTI_API_KEY", "YOUR_API_KEY")  # Get From @SHRUTIAPIBOT

DOWNLOAD_DIR = "downloads"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def shell_cmd(cmd):
    proc = await asyncio.create_subprocess_shell(
        cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    out, errorz = await proc.communicate()
    if errorz:
        if "unavailable videos are hidden" in (errorz.decode("utf-8")).lower():
            return out.decode("utf-8")
        else:
            return errorz.decode("utf-8")
    return out.decode("utf-8")


def _extract_video_id(link: str) -> str:
    """Extract YouTube video ID from a full URL or return the raw ID."""
    return link.split("v=")[-1].split("&")[0] if "v=" in link else link


def _api_headers() -> dict:
    """Return common headers for API requests, including the API key if set."""
    headers = {}
    if API_KEY and API_KEY != "YOUR_API_KEY":
        headers["X-API-Key"] = API_KEY
    return headers


# ---------------------------------------------------------------------------
# Download Functions
# ---------------------------------------------------------------------------

async def download_song(link: str) -> str:
    """Download audio (mp3) via the Shruti API.

    The function first tries the direct-download endpoint (as used in the
    new Youtube.py).  If the server responds with a JSON body containing a
    ``download_token``, it falls back to the token-based streaming flow
    (original repo behaviour) so both API versions are supported.
    """
    video_id = _extract_video_id(link)
    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp3")

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    params = {"url": video_id, "type": "audio", "api_key": API_KEY}
    headers = _api_headers()

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None

                content_type = resp.headers.get("Content-Type", "")

                # --- Token-based flow (original repo API) ---
                if "application/json" in content_type:
                    data = await resp.json()
                    download_token = data.get("download_token")
                    if not download_token:
                        return None

                    stream_url = (
                        f"{API_URL}/stream/{video_id}"
                        f"?type=audio&token={download_token}&api_key={API_KEY}"
                    )
                    async with session.get(
                        stream_url,
                        timeout=aiohttp.ClientTimeout(total=300),
                        allow_redirects=False,
                    ) as file_resp:
                        if file_resp.status == 302:
                            redirect_url = file_resp.headers.get("Location")
                            if redirect_url:
                                async with session.get(redirect_url) as final:
                                    if final.status != 200:
                                        return None
                                    with open(file_path, "wb") as f:
                                        async for chunk in final.content.iter_chunked(131072):
                                            f.write(chunk)
                        elif file_resp.status == 200:
                            with open(file_path, "wb") as f:
                                async for chunk in file_resp.content.iter_chunked(131072):
                                    f.write(chunk)
                        else:
                            return None

                # --- Direct binary stream (new API) ---
                else:
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        return None

    except Exception as e:
        LOGGER(__name__).warning(f"download_song error: {e}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        return None


async def download_video(link: str) -> str:
    """Download video (mp4) via the Shruti API.

    Supports both direct-stream and token-based redirect flows.
    """
    video_id = _extract_video_id(link)
    if not video_id or len(video_id) < 3:
        return None

    os.makedirs(DOWNLOAD_DIR, exist_ok=True)
    file_path = os.path.join(DOWNLOAD_DIR, f"{video_id}.mp4")

    if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
        return file_path

    params = {"url": video_id, "type": "video", "api_key": API_KEY}
    headers = _api_headers()

    try:
        async with aiohttp.ClientSession(headers=headers) as session:
            async with session.get(
                f"{API_URL}/download",
                params=params,
                timeout=aiohttp.ClientTimeout(total=10),
            ) as resp:
                if resp.status != 200:
                    return None

                content_type = resp.headers.get("Content-Type", "")

                # --- Token-based flow ---
                if "application/json" in content_type:
                    data = await resp.json()
                    download_token = data.get("download_token")
                    if not download_token:
                        return None

                    stream_url = (
                        f"{API_URL}/stream/{video_id}"
                        f"?type=video&token={download_token}&api_key={API_KEY}"
                    )
                    async with session.get(
                        stream_url,
                        timeout=aiohttp.ClientTimeout(total=600),
                        allow_redirects=False,
                    ) as file_resp:
                        if file_resp.status == 302:
                            redirect_url = file_resp.headers.get("Location")
                            if redirect_url:
                                async with session.get(redirect_url) as final:
                                    if final.status != 200:
                                        return None
                                    with open(file_path, "wb") as f:
                                        async for chunk in final.content.iter_chunked(131072):
                                            f.write(chunk)
                        elif file_resp.status == 200:
                            with open(file_path, "wb") as f:
                                async for chunk in file_resp.content.iter_chunked(131072):
                                    f.write(chunk)
                        else:
                            return None

                # --- Direct binary stream ---
                else:
                    with open(file_path, "wb") as f:
                        async for chunk in resp.content.iter_chunked(131072):
                            f.write(chunk)

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            return file_path
        return None

    except Exception as e:
        LOGGER(__name__).warning(f"download_video error: {e}")
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
        return None


# ---------------------------------------------------------------------------
# Main API Class
# ---------------------------------------------------------------------------

class YouTubeAPI:
    def __init__(self):
        self.base = "https://www.youtube.com/watch?v="
        self.regex = r"(?:youtube\.com|youtu\.be)"
        self.status = "https://www.youtube.com/oembed?url="
        self.listbase = "https://youtube.com/playlist?list="
        self.reg = re.compile(r"\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])")

    async def exists(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        return bool(re.search(self.regex, link))

    async def url(self, message_1: Message) -> Union[str, None]:
        messages = [message_1]
        if message_1.reply_to_message:
            messages.append(message_1.reply_to_message)
        for message in messages:
            if message.entities:
                for entity in message.entities:
                    if entity.type == MessageEntityType.URL:
                        text = message.text or message.caption
                        return text[entity.offset: entity.offset + entity.length]
            elif message.caption_entities:
                for entity in message.caption_entities:
                    if entity.type == MessageEntityType.TEXT_LINK:
                        return entity.url
        return None

    async def details(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
            vidid = result["id"]
            duration_sec = int(time_to_seconds(duration_min)) if duration_min else 0
        return title, duration_min, duration_sec, thumbnail, vidid

    async def title(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["title"]

    async def duration(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["duration"]

    async def thumbnail(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            return result["thumbnails"][0]["url"].split("?")[0]

    async def video(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        try:
            downloaded_file = await download_video(link)
            if downloaded_file:
                return 1, downloaded_file
            return 0, "Video download failed"
        except Exception as e:
            return 0, f"Video download error: {e}"

    async def playlist(self, link, limit, user_id, videoid: Union[bool, str] = None):
        if videoid:
            link = self.listbase + link
        if "&" in link:
            link = link.split("&")[0]

        # Prefer Playlist API if available, else fall back to yt-dlp shell
        if PLAYLIST_SUPPORT:
            try:
                plist = await Playlist.get(link)
                videos = plist.get("videos") or []
                ids = []
                for data in videos[:limit]:
                    if not data:
                        continue
                    vid = data.get("id")
                    if not vid:
                        continue
                    ids.append(vid)
                return ids
            except Exception:
                pass

        # Fallback: yt-dlp shell command
        result_raw = await shell_cmd(
            f"yt-dlp -i --get-id --flat-playlist --playlist-end {limit} --skip-download {link}"
        )
        try:
            return [key for key in result_raw.split("\n") if key]
        except Exception:
            return []

    async def track(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        results = VideosSearch(link, limit=1)
        for result in (await results.next())["result"]:
            title = result["title"]
            duration_min = result["duration"]
            vidid = result["id"]
            yturl = result["link"]
            thumbnail = result["thumbnails"][0]["url"].split("?")[0]
        track_details = {
            "title": title,
            "link": yturl,
            "vidid": vidid,
            "duration_min": duration_min,
            "thumb": thumbnail,
        }
        return track_details, vidid

    async def formats(self, link: str, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        ytdl_opts = {"quiet": True}
        ydl = yt_dlp.YoutubeDL(ytdl_opts)
        with ydl:
            formats_available = []
            r = ydl.extract_info(link, download=False)
            for fmt in r["formats"]:
                try:
                    if "dash" not in str(fmt["format"]).lower():
                        formats_available.append(
                            {
                                "format": fmt["format"],
                                "filesize": fmt.get("filesize"),
                                "format_id": fmt["format_id"],
                                "ext": fmt["ext"],
                                "format_note": fmt["format_note"],
                                "yturl": link,
                            }
                        )
                except Exception:
                    continue
        return formats_available, link

    async def slider(self, link: str, query_type: int, videoid: Union[bool, str] = None):
        if videoid:
            link = self.base + link
        if "&" in link:
            link = link.split("&")[0]
        a = VideosSearch(link, limit=10)
        result = (await a.next()).get("result")
        title = result[query_type]["title"]
        duration_min = result[query_type]["duration"]
        vidid = result[query_type]["id"]
        thumbnail = result[query_type]["thumbnails"][0]["url"].split("?")[0]
        return title, duration_min, thumbnail, vidid

    async def download(
        self,
        link: str,
        mystic,
        video: Union[bool, str] = None,
        videoid: Union[bool, str] = None,
        songaudio: Union[bool, str] = None,
        songvideo: Union[bool, str] = None,
        format_id: Union[bool, str] = None,
        title: Union[bool, str] = None,
    ) -> str:
        if videoid:
            link = self.base + link
        try:
            if video:
                downloaded_file = await download_video(link)
            else:
                downloaded_file = await download_song(link)
            if downloaded_file:
                return downloaded_file, True
            return None, False
        except Exception:
            return None, False

    async def suggestions(self, keyword: str, limit: int = 2):
        """Return a list of video suggestions for a keyword."""
        try:
            results = VideosSearch(keyword, limit=limit + 10)
            data = (await results.next())["result"]
            return [
                {
                    "title": item["title"],
                    "id": item["id"],
                    "duration": item["duration"],
                    "thumb": item["thumbnails"][0]["url"].split("?")[0],
                }
                for item in data
            ][:limit]
        except Exception:
            return []


YouTube = YouTubeAPI()
