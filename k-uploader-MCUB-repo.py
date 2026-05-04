from __future__ import annotations

import asyncio
import io
from collections.abc import Callable
from typing import Any

import requests
from telethon import events

from core.lib.loader.module_base import ModuleBase, command


class UploadStatusError(Exception):
    pass


class UploaderModules(ModuleBase):
    name = "k:uploader"
    description = {
        "ru": "Загрузка файлов на разные файлообменники",
        "en": "Upload files to different file hosts",
    }
    version = "1.0.1"
    author = "@Hairpin00"
    dependencies = ["requests"]

    strings = {
        "ru": {
            "uploading": "⚡ **Загружаю файл...**",
            "reply_to_file": "❌ **Ответьте на файл!**",
            "download_failed": "❌ **Не удалось скачать файл**",
            "uploaded": "❤️ **Файл загружен!**\n\n🔥 **URL:** `{url}`",
            "error": "❌ **Ошибка при загрузке:** {error}",
            "url_not_found": "Не удалось найти URL",
            "help": (
                "📤 **Доступные сервисы для загрузки:**\n\n"
                "`.catbox` - catbox.moe\n"
                "`.envs` - envs.sh\n"
                "`.kappa` - kappa.lol\n"
                "`.0x0` - 0x0.st\n"
                "`.x0` - x0.at\n"
                "`.tmpfiles` - tmpfiles.org\n"
                "`.pomf` - pomf.lain.la\n"
                "`.bash` - bashupload.com\n\n"
                "**Использование:** Ответьте на файл командой и файл будет загружен."
            ),
        },
        "en": {
            "uploading": "⚡ **Uploading file...**",
            "reply_to_file": "❌ **Reply to a file!**",
            "download_failed": "❌ **Could not download file**",
            "uploaded": "❤️ **File uploaded!**\n\n🔥 **URL:** `{url}`",
            "error": "❌ **Upload error:** {error}",
            "url_not_found": "Could not find URL",
            "help": (
                "📤 **Available upload services:**\n\n"
                "`.catbox` - catbox.moe\n"
                "`.envs` - envs.sh\n"
                "`.kappa` - kappa.lol\n"
                "`.0x0` - 0x0.st\n"
                "`.x0` - x0.at\n"
                "`.tmpfiles` - tmpfiles.org\n"
                "`.pomf` - pomf.lain.la\n"
                "`.bash` - bashupload.com\n\n"
                "**Usage:** Reply to a file with a command and it will be uploaded."
            ),
        },
    }

    async def _get_file(self, event: events.NewMessage.Event) -> io.BytesIO | None:
        reply = await event.get_reply_message()
        if not reply:
            await self.edit(event, self.strings["reply_to_file"])
            return None

        if not getattr(reply, "media", None):
            file = io.BytesIO((getattr(reply, "raw_text", "") or "").encode("utf-8"))
            file.name = "text.txt"
            return file

        file_bytes = await self.client.download_media(reply.media, bytes)
        if not file_bytes:
            await self.edit(event, self.strings["download_failed"])
            return None

        file = io.BytesIO(file_bytes)
        file.name = self._reply_filename(reply)
        return file

    @staticmethod
    def _reply_filename(reply: Any) -> str:
        document = getattr(reply, "document", None)
        if document:
            for attr in getattr(document, "attributes", []) or []:
                file_name = getattr(attr, "file_name", None)
                if file_name:
                    return file_name
            return f"file_{getattr(reply, 'id', 'unknown')}"
        return f"file_{getattr(reply, 'id', 'unknown')}.jpg"

    async def _request(self, request_func: Callable[..., requests.Response], *args: Any, **kwargs: Any) -> requests.Response:
        return await asyncio.to_thread(request_func, *args, **kwargs)

    async def _upload(
        self,
        event: events.NewMessage.Event,
        source: str,
        uploader: Callable[[io.BytesIO], Any],
    ) -> None:
        await self.edit(event, self.strings["uploading"])
        file = await self._get_file(event)
        if not file:
            return

        try:
            url = await uploader(file)
            await self.edit(event, self.strings("uploaded", url=url))
        except UploadStatusError as exc:
            await self.edit(event, self.strings("error", error=str(exc)))
        except Exception as exc:
            await self.kernel.handle_error(exc, source=source, event=event)
            await self.edit(event, self.strings("error", error=str(exc)))

    @staticmethod
    def _raise_for_status(response: requests.Response) -> None:
        if not response.ok:
            raise UploadStatusError(str(response.status_code))

    @command("catbox", doc_ru="загрузить файл на catbox.moe", doc_en="upload file to catbox.moe")
    async def catbox_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(
                requests.post,
                "https://catbox.moe/user/api.php",
                files={"fileToUpload": file},
                data={"reqtype": "fileupload"},
            )
            self._raise_for_status(response)
            return response.text.strip()

        await self._upload(event, "catbox_handler", upload)

    @command("envs", doc_ru="загрузить файл на envs.sh", doc_en="upload file to envs.sh")
    async def envs_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(requests.post, "https://envs.sh", files={"file": file})
            self._raise_for_status(response)
            return response.text.strip()

        await self._upload(event, "envs_handler", upload)

    @command("kappa", doc_ru="загрузить файл на kappa.lol", doc_en="upload file to kappa.lol")
    async def kappa_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(requests.post, "https://kappa.lol/api/upload", files={"file": file})
            self._raise_for_status(response)
            data = response.json()
            return f"https://kappa.lol/{data['id']}"

        await self._upload(event, "kappa_handler", upload)

    @command("0x0", doc_ru="загрузить файл на 0x0.st", doc_en="upload file to 0x0.st")
    async def oxo_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(
                requests.post,
                "https://0x0.st",
                files={"file": file},
                data={"secret": True},
            )
            self._raise_for_status(response)
            return response.text.strip()

        await self._upload(event, "oxo_handler", upload)

    @command("x0", doc_ru="загрузить файл на x0.at", doc_en="upload file to x0.at")
    async def x0_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(requests.post, "https://x0.at", files={"file": file})
            self._raise_for_status(response)
            return response.text.strip()

        await self._upload(event, "x0_handler", upload)

    @command("tmpfiles", doc_ru="загрузить файл на tmpfiles.org", doc_en="upload file to tmpfiles.org")
    async def tmpfiles_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(
                requests.post,
                "https://tmpfiles.org/api/v1/upload",
                files={"file": file},
            )
            self._raise_for_status(response)
            return response.json()["data"]["url"]

        await self._upload(event, "tmpfiles_handler", upload)

    @command("pomf", doc_ru="загрузить файл на pomf.lain.la", doc_en="upload file to pomf.lain.la")
    async def pomf_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(
                requests.post,
                "https://pomf.lain.la/upload.php",
                files={"files[]": file},
            )
            self._raise_for_status(response)
            return response.json()["files"][0]["url"]

        await self._upload(event, "pomf_handler", upload)

    @command("bash", doc_ru="загрузить файл на bashupload.com", doc_en="upload file to bashupload.com")
    async def bash_handler(self, event: events.NewMessage.Event) -> None:
        async def upload(file: io.BytesIO) -> str:
            response = await self._request(requests.put, "https://bashupload.com", data=file.read())
            self._raise_for_status(response)
            urls = [line for line in response.text.split("\n") if "wget" in line]
            if not urls:
                raise UploadStatusError(self.strings["url_not_found"])
            return urls[0].split()[-1]

        await self._upload(event, "bash_handler", upload)

    @command("upload", doc_ru="список сервисов загрузки", doc_en="list upload services")
    async def upload_handler(self, event: events.NewMessage.Event) -> None:
        await self.edit(event, self.strings["help"])
