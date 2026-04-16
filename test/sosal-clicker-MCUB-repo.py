# scop: kernel min v1.2.6.1
from typing import Any
from telethon import events

import utils
from core.lib.loader.module_base import ModuleBase, command, callback, on_install
# NOTE:
# модуль пока для dev ветки, потому что main ещё не обновился до 1.2.6.1 (щас main v1.1.6.1 и не поддерживает class style modules или ModuleBase)
# модуль чтоб показать новый стиль с class вместо register функции (с lsp сервером удобно пиздец, плюс всё понятно)

class SosalClicker(ModuleBase):
    """class-style modules MCUB: sosal clicker (рофл если что)"""

    name = "sosal-clicker-MCUB-repo"
    version = "v1"  # noqe: ignore[not use 'format X.X.X']
    description = {"ru": "сосал кликер", "en": "sosal clicker"}
    author = "нн шмелька, @Hairpin00"  # noqe: ignore[not use 'only_username']

    # self.strings не будет так как мне лень их писать эти ваши стринги ебаные

    async def on_load(self) -> None:
        """load sosal count"""
        self._sosal_count = 0
        saved = await self.db.db_get(self.name, "sosal_count")
        if saved is None:
            await self.db.db_set(self.name, "sosal_count", 0)
            self._sosal_count = 0
        else:
            self._sosal_count = int(saved)

        self.log.debug(f"{self.name} -> on_load: OK")

    async def _update_count(self, reset=False) -> bool:
        """update _sosal_count + 1 and db
        args:
            reset = False -> update _sosal_count, True -> reset _sosal_count to 0
        return:
            bool -> failed: `False`, if success `True`
        """
        if reset:
            self._sosal_count = 0
            try:
                await self.db.db_set(self.name, "sosal_count", 0)
            except Exception as err:
                self.log.error(f"update_count (reset) failed: {err}")
                return False
            return True

        self._sosal_count += 1
        try:
            await self.db.db_set(self.name, "sosal_count", self._sosal_count)
        except Exception as err:
            self.log.error(f"update_count failed: {err}")
            return False
        return True

    @command("отсос", doc_en="otsosat", doc_ru="отсосать", alias=["otsos"])
    async def otsos_command(self, message: events.NewMessage.Event) -> None:
        _true = await self._update_count()
        if not _true:
            await utils.answer(
                message,
                "<b>не удачный отсос (чот с db, не моя проблема)</b>",
                as_html=True,
            )
            return
        if self._sosal_count == 69:  # дипспик сказал сделать
            self.log.info("внезапный рестарт юзербота, мухахахахаха")
            await utils.answer(
                message,
                "<b><i>ойоойоййо, 69 классное цисло, вчесть его ребут юзербота\nпора сбросить uptime kernel нахуй, прости если копил годами)))))</i></b>",
                as_html=True,
            )
            await utils.restart_kernel(self.kernel)
            return

        await utils.answer(message, f"сосём ({self._sosal_count})")

    @command(
        "сосалстатус",
        alias=["sosalstats"],
        doc={"ru": "скок ты раз сасал", "en": "show sosal status"},
    )
    async def sosal_status_command(self, message: events.NewMessage.Event) -> None:
        text_sosal = f"""<b>sosal stats:</b> {self._sosal_count}"""
        await utils.answer(message, text_sosal, as_html=True)

    @command(
        "сосалкликер",
        doc={
            "en": "inline clicker, click = 1 sosal count",
            "ru": "инлайн сосал кликер, один клик = один сосал count",
        },
        alias=['sosalclicker']
    )
    async def sosal_clicker_command(self, message: events.NewMessage.Event) -> None:
        btn = [[self.Button.inline("Click", self.on_click)]]  # add self.Button v1.2.6.1
        await self.kernel._inline.inline_form(
            message.chat_id,
            f"<b>Sosal count:</b> {self._sosal_count}\n<blockquote>1 click = one sosal count</blockquote>",
            buttons=btn,
        )  # noqe: ignore[use 'kernel._inline']

    @command(
        "сосалрезет",
        doc={"ru": "сбросить сосал count", "en": "reset sosal cont"},
        alias=["sosalreset"],
    )
    async def sosal_reset_command(self, message: events.NewMessage.Event) -> None:
        _true = await self._update_count(reset=True)
        if not _true:
            await utils.answer(
                message, "<b>reset sosal count FAILED!</b>", as_html=True
            )
            return
        await utils.answer(
            message,
            "<b>Сосал опыт обнулён.\n<blockquote>Теперь ты опять девственник в мире отсосов</blockquote></b>",  # author DeepSeek, или дипсик, его строчка
            as_html=True,
        )

    @callback()  # noqe: ignore[use '@callback not args']
    # можно без но я напишу и даже без аргументов, типа ttl=300)
    async def on_click(self, call: Any) -> None:
        """handler for click the button"""

        btn = [[self.Button.inline("Click", self.on_click)]]
        _true = await self._update_count()
        if not _true:
            await call.answer("ои чот не так")
            await utils.answer(
                call,
                "<b>не удачный отсос (чот с db, не моя проблема)</b>",
                as_html=True,
            )
            return

        if self._sosal_count == 69:
            self.log.info("внезапный рестарт юзербота, мухахахахаха")
            await utils.answer(
                call,
                "<b><i>ойоойоййо, 69 классное цисло, вчесть его ребут юзербота\nпора сбросить uptime kernel нахуй, прости если копил годами)))))</i></b>",
                as_html=True,
            )
            await utils.restart_kernel(self.kernel)
            return

        await utils.answer(
            call,
            f"<b>Sosal count:</b> {self._sosal_count}\n<blockquote>1 click = one sosal count</blockquote>",
            as_html=True,
            buttons=btn,
        )
