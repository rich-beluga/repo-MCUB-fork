# =======================================
#   _  __         __  __           _
#  | |/ /___     |  \/  | ___   __| |___
#  | ' // _ \    | |\/| |/ _ \ / _` / __|
#  | . \  __/    | |  | | (_) | (_| \__ \
#  |_|\_\___|    |_|  |_|\___/ \__,_|___/
#           @ke_mods
# =======================================
#
#  LICENSE: CC BY-ND 4.0 (Attribution-NoDerivatives 4.0 International)
#  --------------------------------------
#  https://creativecommons.org/licenses/by-nd/4.0/legalcode
# =======================================
# meta developer: @ke_mods
# scop: kernel min v1.3.0

from __future__ import annotations

import asyncio
import io
from typing import Any

import requests
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont, ImageOps

import utils
from core.lib.loader.module_base import ModuleBase, command
from core.lib.loader.module_config import (
    Choice,
    ConfigValue,
    ModuleConfig,
    Placeholders,
    Secret,
    String,
)


class Banners:
    def __init__(
        self,
        title: str,
        artists: str | list[str],
        track_cover: bytes,
        font_url: str,
    ) -> None:
        self.title = title or "Unknown"
        self.artists = ", ".join(artists) if isinstance(artists, list) else artists
        self.artists = self.artists or "Unknown"
        self.track_cover = track_cover
        self.font_url = font_url

    @staticmethod
    def _request_bytes(url: str) -> bytes:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _get_font(size: int, font_bytes: bytes) -> ImageFont.ImageFont:
        try:
            return ImageFont.truetype(io.BytesIO(font_bytes), size)
        except Exception:
            for path in ("DejaVuSans-Bold.ttf", "arial.ttf"):
                try:
                    return ImageFont.truetype(path, size)
                except Exception:
                    continue
            return ImageFont.load_default()

    @staticmethod
    def _ellipsize(text: str, font: ImageFont.ImageFont, max_width: int) -> str:
        text = str(text or "")
        if font.getlength(text) <= max_width:
            return text

        ellipsis = "…"
        while text and font.getlength(text + ellipsis) > max_width:
            text = text[:-1]
        return (text + ellipsis) if text else ellipsis

    def _prepare_cover(self, size: int, radius: int) -> Image.Image:
        try:
            cover = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
            cover = ImageOps.fit(cover, (size, size), method=Image.Resampling.LANCZOS)
        except Exception:
            cover = Image.new("RGBA", (size, size), (24, 24, 24, 255))

        mask = Image.new("L", (size, size), 0)
        draw = ImageDraw.Draw(mask)
        draw.rounded_rectangle((0, 0, size, size), radius=radius, fill=255)

        output = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        output.paste(cover, (0, 0), mask=mask)
        return output

    def _prepare_background(self, width: int, height: int) -> Image.Image:
        try:
            bg = Image.open(io.BytesIO(self.track_cover)).convert("RGBA")
            bg = ImageOps.fit(bg, (width, height), method=Image.Resampling.BICUBIC)
        except Exception:
            bg = Image.new("RGBA", (width, height), (18, 18, 18, 255))

        bg = bg.filter(ImageFilter.GaussianBlur(radius=20))
        bg = ImageEnhance.Brightness(bg).enhance(0.4)
        return bg

    def _font_bytes(self) -> bytes:
        if not self.font_url:
            return b""
        try:
            return self._request_bytes(self.font_url)
        except Exception:
            return b""

    def horizontal(self) -> io.BytesIO:
        width, height = 1500, 600
        padding = 60
        cover_size = 480

        font_bytes = self._font_bytes()
        title_font = self._get_font(55, font_bytes)
        artist_font = self._get_font(45, font_bytes)
        lfm_font = self._get_font(55, font_bytes)

        img = self._prepare_background(width, height)
        draw = ImageDraw.Draw(img)

        cover = self._prepare_cover(cover_size, 30)
        img.paste(cover, (padding, (height - cover_size) // 2), cover)

        text_x = padding + cover_size + 60
        text_y_start = 100
        text_width_limit = width - text_x - padding

        display_title = self._ellipsize(self.title, title_font, text_width_limit)
        display_artist = self._ellipsize(self.artists, artist_font, text_width_limit)

        draw.text((text_x, text_y_start), display_title, font=title_font, fill="white")
        draw.text(
            (text_x, text_y_start + 70),
            display_artist,
            font=artist_font,
            fill="#B3B3B3",
        )
        draw.text((text_x, 430), "last.fm", font=lfm_font, fill="white")

        return self._to_png(img)

    def vertical(self) -> io.BytesIO:
        width, height = 1000, 1300
        padding = 60
        cover_size = 800

        font_bytes = self._font_bytes()
        title_font = self._get_font(60, font_bytes)
        artist_font = self._get_font(45, font_bytes)
        lfm_font = self._get_font(60, font_bytes)

        img = self._prepare_background(width, height)
        draw = ImageDraw.Draw(img)

        cover = self._prepare_cover(cover_size, 40)
        cover_x = (width - cover_size) // 2
        cover_y = 100
        img.paste(cover, (cover_x, cover_y), cover)

        text_area_y = cover_y + cover_size + 60
        text_width_limit = width - (padding * 2)

        display_title = self._ellipsize(self.title, title_font, text_width_limit)
        display_artist = self._ellipsize(self.artists, artist_font, text_width_limit)

        title_w = title_font.getlength(display_title)
        draw.text(
            ((width - title_w) / 2, text_area_y),
            display_title,
            font=title_font,
            fill="white",
        )

        artist_w = artist_font.getlength(display_artist)
        draw.text(
            ((width - artist_w) / 2, text_area_y + 75),
            display_artist,
            font=artist_font,
            fill="#B3B3B3",
        )

        lfm_w = lfm_font.getlength("last.fm")
        draw.text(
            ((width - lfm_w) / 2, text_area_y + 180),
            "last.fm",
            font=lfm_font,
            fill="white",
        )

        return self._to_png(img)

    @staticmethod
    def _to_png(img: Image.Image) -> io.BytesIO:
        by = io.BytesIO()
        img.save(by, format="PNG")
        by.seek(0)
        by.name = "banner.png"
        return by


class LastFmMod(ModuleBase):
    """Module for Last.fm now playing banners."""

    name = "LastFm"
    description = {
        "en": "Module for Last.fm now playing banners",
        "ru": "Модуль для баннеров текущего трека Last.fm",
    }
    version = "1.1.1"
    author = "@ke_mods"
    dependencies = ["pillow", "requests"]

    strings = {
        "en": {
            "no_track": "<emoji document_id=5465665476971471368>❌</emoji> <b>No track is currently playing</b>",
            "nick_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Put your nickname from last.fm</b>",
            "uploading": "<emoji document_id=5841359499146825803>🕔</emoji> <i>Uploading banner...</i>",
            "api_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Last.fm API error:</b> <code>{error}</code>",
        },
        "ru": {
            "no_track": "<emoji document_id=5465665476971471368>❌</emoji> <b>Сейчас ничего не играет</b>",
            "nick_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Укажите ваш никнейм с Last.fm</b>",
            "uploading": "<emoji document_id=5841359499146825803>🕔</emoji> <i>Загрузка баннера...</i>",
            "api_error": "<emoji document_id=5465665476971471368>❌</emoji> <b>Ошибка Last.fm API:</b> <code>{error}</code>",
        },
    }

    config = ModuleConfig(
        ConfigValue(
            "username",
            "",
            description="Your username from Last.fm",
            validator=String(default=""),
        ),
        ConfigValue(
            "custom_text",
            "<emoji document_id=5413612466208799435>🤩</emoji> <b>{lastfm_song_name}</b> — <b>{lastfm_song_artist}</b>",
            description=(
                "Caption template. Available placeholders:\n"
                "{lastfm_song_name}, {lastfm_song_artist}, {lastfm_song_album}, "
                "{lastfm_song_url}, {lastfm_cover_url}, {lastfm_username}"
            ),
            validator=Placeholders(
                default="<emoji document_id=5413612466208799435>🤩</emoji> <b>{lastfm_song_name}</b> — <b>{lastfm_song_artist}</b>",
                placeholder_scope="LastFm",
            ),
        ),
        ConfigValue(
            "placeholders",
            "",
            description="Available placeholders (auto-generated, read-only)",
            validator=String(default=""),
        ),
        ConfigValue(
            "status_text",
            None,
            description='text loading message',
            validator=String(
                default=None
                )
        ),
        ConfigValue(
            "font",
            "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf",
            description="Custom font URL (ttf)",
            validator=String(
                default="https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf"
            ),
        ),
        ConfigValue(
            "banner_version",
            "horizontal",
            description="Banner version",
            validator=Choice(choices=["horizontal", "vertical"], default="horizontal"),
        ),
        ConfigValue(
            "fallback_cover",
            "https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png",
            description="Fallback cover URL if track has no image",
            validator=String(
                default="https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png"
            ),
        ),
        ConfigValue(
            "api_key",
            "460cda35be2fbf4f28e8ea7a38580730",
            description="Last.fm API key",
            validator=Secret(default="460cda35be2fbf4f28e8ea7a38580730"),
        ),
    )

    async def on_load(self) -> None:
        await super().on_load()
        defaults = {
            "username": "",
            "custom_text": "<emoji document_id=5413612466208799435>🤩</emoji> <b>{lastfm_song_name}</b> — <b>{lastfm_song_artist}</b>",
            "font": "https://raw.githubusercontent.com/kamekuro/assets/master/fonts/Onest-Bold.ttf",
            "banner_version": "horizontal",
            "fallback_cover": "https://lastfm.freetls.fastly.net/i/u/300x300/2a96cbd8b46e442fc41c2b86b821562f.png",
            "api_key": "460cda35be2fbf4f28e8ea7a38580730",
            "status_text": None,
            "placeholders": "",
        }
        config_dict = await self.kernel.get_module_config(self.name, defaults)
        utils.register_decorated_placeholders(self.name, self)
        config_dict["placeholders"] = utils.format_placeholders(self.name)
        self.config.from_dict(config_dict)
        self.kernel.store_module_config_schema(self.name, self.config)
        await self.kernel.save_module_config(self.name, self.config.to_dict())

    async def on_unload(self) -> None:
        utils.unregister_scope(self.name)

    @staticmethod
    def _get_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
        response = requests.get(url, params=params, timeout=20)
        response.raise_for_status()
        return response.json()

    @staticmethod
    def _get_bytes(url: str) -> bytes:
        response = requests.get(url, timeout=20)
        response.raise_for_status()
        return response.content

    @staticmethod
    def _find_cover_url(track: dict[str, Any]) -> str | None:
        images = track.get("image") or []
        for size in ("extralarge", "large", "medium", "small"):
            for image in images:
                if image.get("size") == size and image.get("#text"):
                    return image["#text"]
        return None

    async def _fetch_now_playing(self, username: str, api_key: str) -> dict[str, Any] | None:
        data = await asyncio.to_thread(
            self._get_json,
            "https://ws.audioscrobbler.com/2.0/",
            {
                "method": "user.getrecenttracks",
                "nowplaying": "true",
                "user": username,
                "api_key": api_key,
                "format": "json",
                "limit": 1,
            },
        )
        tracks = data.get("recenttracks", {}).get("track", [])
        for track in tracks:
            if track.get("@attr", {}).get("nowplaying") == "true":
                return track
        return None

    async def _lastfm_placeholder_data(self, data: dict[str, Any]) -> dict[str, str]:
        cache_key = "__lastfm_placeholder_data"
        if cache_key in data:
            return data[cache_key]

        result = {
            "lastfm_song_name": "Unknown",
            "lastfm_song_artist": "Unknown",
            "lastfm_song_album": "Unknown",
            "lastfm_song_url": "",
            "lastfm_cover_url": "",
            "lastfm_username": utils.escape_html(
                str(self.config.get("username") or "").strip()
            ),
        }

        username = str(self.config.get("username") or "").strip()
        api_key = str(self.config.get("api_key") or "").strip()
        if not username or not api_key:
            data[cache_key] = result
            return result

        try:
            track = await self._fetch_now_playing(username, api_key)
        except Exception:
            data[cache_key] = result
            return result

        if not track:
            data[cache_key] = result
            return result

        cover_url = self._find_cover_url(track) or str(
            self.config.get("fallback_cover") or ""
        ).strip()
        result = {
            "lastfm_song_name": utils.escape_html(track.get("name") or "Unknown"),
            "lastfm_song_artist": utils.escape_html(
                track.get("artist", {}).get("#text") or "Unknown"
            ),
            "lastfm_song_album": utils.escape_html(
                track.get("album", {}).get("#text") or "Unknown"
            ),
            "lastfm_song_url": utils.escape_html(track.get("url") or ""),
            "lastfm_cover_url": utils.escape_html(cover_url),
            "lastfm_username": utils.escape_html(username),
        }
        data[cache_key] = result
        return result

    @utils.placeholders("lastfm_song_name", description="Current Last.fm track name")
    async def _placeholder_lastfm_song_name(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_song_name"):
            return str(data["lastfm_song_name"])
        return (await self._lastfm_placeholder_data(data))["lastfm_song_name"]

    @utils.placeholders("lastfm_song_artist", description="Current Last.fm track artist")
    async def _placeholder_lastfm_song_artist(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_song_artist"):
            return str(data["lastfm_song_artist"])
        return (await self._lastfm_placeholder_data(data))["lastfm_song_artist"]

    @utils.placeholders("lastfm_song_album", description="Current Last.fm track album")
    async def _placeholder_lastfm_song_album(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_song_album"):
            return str(data["lastfm_song_album"])
        return (await self._lastfm_placeholder_data(data))["lastfm_song_album"]

    @utils.placeholders("lastfm_song_url", description="Current Last.fm track URL")
    async def _placeholder_lastfm_song_url(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_song_url"):
            return str(data["lastfm_song_url"])
        return (await self._lastfm_placeholder_data(data))["lastfm_song_url"]

    @utils.placeholders("lastfm_cover_url", description="Current Last.fm track cover URL")
    async def _placeholder_lastfm_cover_url(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_cover_url"):
            return str(data["lastfm_cover_url"])
        return (await self._lastfm_placeholder_data(data))["lastfm_cover_url"]

    @utils.placeholders("lastfm_username", description="Configured Last.fm username")
    async def _placeholder_lastfm_username(self, data: dict[str, Any]) -> str:
        if data.get("lastfm_username"):
            return str(data["lastfm_username"])
        return (await self._lastfm_placeholder_data(data))["lastfm_username"]

    async def _caption(
        self,
        artist: str,
        name: str,
        album: str = "",
        song_url: str = "",
        cover_url: str = "",
        username: str = "",
    ) -> str:
        template = self.config.get("custom_text") or "{lastfm_song_artist} — {lastfm_song_name}"
        try:
            return await utils.resolve_placeholders(
                self.name,
                template,
                data={
                    "lastfm_song_artist": utils.escape_html(artist),
                    "lastfm_song_name": utils.escape_html(name),
                    "lastfm_song_album": utils.escape_html(album),
                    "lastfm_song_url": utils.escape_html(song_url),
                    "lastfm_cover_url": utils.escape_html(cover_url),
                    "lastfm_username": utils.escape_html(username),
                },
                strict=False,
            )
        except Exception:
            return f"<b>{utils.escape_html(name)}</b> — <b>{utils.escape_html(artist)}</b>"

    @command("nowplay", alias=["np"], doc_ru="показать текущий трек Last.fm", doc_en="show current Last.fm track")
    async def nowplay(self, event) -> None:
        username = str(self.config.get("username") or "").strip()
        if not username:
            await utils.answer(event, self.strings("nick_error"), as_html=True)
            return
        status_text = self.config.get('status_text') or self.strings('uploading')
        status = await event.edit(status_text, parse_mode='html')

        try:
            track = await self._fetch_now_playing(
                username,
                str(self.config.get("api_key") or "").strip(),
            )
            if not track:
                await utils.answer(status, self.strings("no_track"), as_html=True)
                return

            name = track.get("name") or "Unknown"
            artist = track.get("artist", {}).get("#text") or "Unknown"
            album = track.get("album", {}).get("#text") or ""
            song_url = track.get("url") or ""

            cover_url = self._find_cover_url(track) or str(
                self.config.get("fallback_cover") or ""
            ).strip()
            caption = await self._caption(
                artist,
                name,
                album=album,
                song_url=song_url,
                cover_url=cover_url,
                username=username,
            )
            if not cover_url:
                await utils.answer(status, caption, as_html=True)
                return

            cover_bytes = await asyncio.to_thread(self._get_bytes, cover_url)
            banner_version = self.config.get("banner_version")
            if banner_version not in ("horizontal", "vertical"):
                banner_version = "horizontal"

            banners = Banners(name, artist, cover_bytes, str(self.config.get("font") or ""))
            file = await asyncio.to_thread(getattr(banners, banner_version))

            await status.edit(caption, file=file, parse_mode='html')
        except Exception as e:
            self.log.error(f"Failed to build Last.fm banner: {e}")
            await utils.answer(
                status,
                self.strings("api_error", error=utils.escape_html(str(e))),
                as_html=True,
            )
# мкуб ратко
