# scop: kernel min v1.2.8
from telethon import events
import subprocess
import core.lib.loader.module_base as loader

class Fastfetch(loader.ModuleBase):
    name = 'fastfetch'
    description: dict = {'ru': 'вывод информации о системе через fastfetch', 'en': 'display system information using fastfetch', 'linux': 'cmd: fastfetch on modules'}
    version = '1.0.0'
    author = '@Hairpin00'
    
    @loader.command('fastfetch')
    async def cmd_fastfetch(self, event: events.NewMessage.Event) -> None:
        try:
            result = subprocess.run(
                "fastfetch | sed 's/\\x1B\\[[0-9;?]*[a-zA-Z]//g'",
                shell=True,
                capture_output=True,
                text=True,
                timeout=10
            )

            output = result.stdout.strip()

            if not output:
                await event.edit('⛈️ **fastfetch не найден!**\n\n'
                               'Установите его:\n'
                               '• Termux: `pkg install fastfetch`\n'
                               '• Ubuntu/Debian: `sudo apt install fastfetch`\n'
                               '• Arch: `sudo pacman -S fastfetch`\n'
                               '• macOS: `brew install fastfetch`')
                return

            if len(output) > 4000:
                output = output[:4000] + "\n... (вывод обрезан)"

            await event.edit(f'<pre>\n{output}</pre>', parse_mode='html')

        except subprocess.TimeoutExpired:
            await event.edit('⛈️ **Таймаут выполнения команды!**')
        except Exception as e:
            await event.edit(f'⛈️ **Ошибка:**\n```\n{str(e)}\n```')
