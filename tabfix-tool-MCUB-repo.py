# author: @Hairpin00
# version: 2.2.0
# description: форматирование кода и исправление отступов
# requires: tabfix-tool

import os
import sys
import zipfile
import tempfile
import asyncio
from pathlib import Path

try:
    from tabfix import TabFixAPI, TabFixConfig, process_files, BatchResult
except ImportError as e:
    print(f"Import error: {e}")
    sys.exit(1)

from telethon import events, Button

def register(kernel):
    client = kernel.client
    processing_users = set()
    user_sessions = {}

    class UserSession:
        def __init__(self, user_id):
            self.user_id = user_id
            self.temp_dir = None
            self.processed_files = []
            self.current_batch = None
            self.config = TabFixConfig()
            self.api = TabFixAPI(config=self.config)
            self.zip_password = None

        def cleanup(self):
            if self.temp_dir and os.path.exists(self.temp_dir):
                import shutil
                shutil.rmtree(self.temp_dir)
            self.temp_dir = None
            self.processed_files = []
            self.current_batch = None
            self.zip_password = None

    def get_session(user_id):
        if user_id not in user_sessions:
            user_sessions[user_id] = UserSession(user_id)
        return user_sessions[user_id]

    async def extract_zip_with_password(zip_path, extract_dir, password):
        try:
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                if password:
                    zipf.setpassword(password.encode('utf-8'))

                extracted_files = []
                for file_info in zipf.infolist():
                    if not file_info.is_dir():
                        try:
                            zipf.extract(file_info, extract_dir)
                            extracted_files.append(Path(extract_dir) / file_info.filename)
                        except RuntimeError as e:
                            if "encrypted" in str(e) and password:
                                try:
                                    zipf.extract(file_info, extract_dir, pwd=password.encode('utf-8'))
                                    extracted_files.append(Path(extract_dir) / file_info.filename)
                                except:
                                    continue
                            continue
                        except:
                            continue

                return extracted_files, len(zipf.infolist())
        except Exception as e:
            return [], 0

    @kernel.register_command('tabfix')
    # форматирование кода и исправление отступов
    async def tabfix_handler(event):
        user_id = event.sender_id
        session = get_session(user_id)

        if user_id in processing_users:
            await event.edit("⏳ Уже идет обработка, подождите...")
            return

        args = event.text.split()[1:] if len(event.text.split()) > 1 else []

        if not args or args[0] == "help":
            help_text = (
                "📖 **TabFix Help**\n\n"
                "**Команды:**\n"
                "`.tabfix` [флаги] (ответ на файл/архив)\n"
                "`.tabfix batch` — запустить пакетную обработку\n"
                "`.tabfix cancel` — отменить обработку\n"
                "`.tabfix status` — статус обработки\n"
                "`.tabfix config` — показать настройки\n\n"
                "**Флаги:**\n"
                "• `-s N` — пробелов в табе (дефолт: 4)\n"
                "• `--json` — форматировать JSON\n"
                "• `--no-mixed` — не фиксить смешанные отступы\n"
                "• `--no-trail` — не удалять пробелы в конце\n"
                "• `--no-smart` — выкл. умную обработку\n"
                "• `--dry-run` — только проверка\n"
                "• `--zip` — вернуть архивом\n"
                "• `--password ПАРОЛЬ` — пароль для архива\n\n"
                "**Примеры:**\n"
                "`.tabfix -s 2 --json`\n"
                "`.tabfix --dry-run --password mypass`\n"
                "`.tabfix --zip --password 1234`\n"
                "`.tabfix batch` (затем отправьте файлы)"
            )
            await event.edit(help_text)
            return

        if args[0] == "cancel":
            if user_id in processing_users:
                processing_users.remove(user_id)
                session.cleanup()
                await event.edit("✅ Обработка отменена")
            else:
                await event.edit("⛈️ Нет активной обработки")
            return

        if args[0] == "status":
            if session.current_batch:
                batch = session.current_batch
                status_text = (
                    f"📊 **Статус обработки:**\n"
                    f"• Файлов: {batch.total_files}\n"
                    f"• Изменено: {batch.changed_files}\n"
                    f"• Ошибок: {batch.failed_files}\n"
                    f"• Время: {batch.duration:.1f}с"
                )
                await event.edit(status_text)
            else:
                await event.edit("📭 Нет активной обработки")
            return

        if args[0] == "config":
            config = session.config
            config_text = (
                f"⚙️ **Текущие настройки:**\n"
                f"• Пробелов в табе: {config.spaces}\n"
                f"• Исправлять смешанные: {config.fix_mixed}\n"
                f"• Удалять пробелы в конце: {config.fix_trailing}\n"
                f"• Умная обработка: {config.smart_processing}\n"
                f"• Форматировать JSON: {config.format_json}\n"
                f"• Режим проверки: {config.dry_run}"
            )
            await event.edit(config_text)
            return

        if args[0] == "batch":
            session.cleanup()
            session.temp_dir = tempfile.mkdtemp(prefix="tabfix_")
            await event.edit(
                "📦 **Пакетный режим активирован**\n"
                "Отправьте файлы или архив для обработки.\n"
                "Используйте `.tabfix process` чтобы начать обработку.\n"
                "Используйте `.tabfix cancel` для отмены."
            )
            return

        if args[0] == "process":
            if not session.temp_dir or not os.path.exists(session.temp_dir):
                await event.edit("⛈️ Сначала активируйте пакетный режим: `.tabfix batch`")
                return

            files = list(Path(session.temp_dir).rglob("*"))
            files = [f for f in files if f.is_file()]

            if not files:
                await event.edit("⛈️ Нет файлов для обработки")
                return

            processing_users.add(user_id)
            await event.edit(f"⏳ Обработка {len(files)} файлов...")

            try:
                results = process_files(files, config=session.config)
                session.current_batch = results

                changed_files = [r for r in results.individual_results if r.changed]

                if changed_files:
                    zip_path = Path(session.temp_dir) / "processed.zip"
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        if session.zip_password:
                            zipf.setpassword(session.zip_password.encode('utf-8'))
                        for result in changed_files:
                            zipf.write(result.filepath, result.filepath.name)

                    caption = (
                        f"📦 **Обработано файлов:** {results.total_files}\n"
                        f"📝 **Изменено:** {results.changed_files}\n"
                        f"⛈️ **Ошибок:** {results.failed_files}\n"
                        f"⏱️ **Время:** {results.duration:.1f}с"
                    )
                    if session.zip_password:
                        caption += f"\n🔐 **Пароль:** `{session.zip_password}`"

                    await client.send_file(
                        event.chat_id,
                        zip_path,
                        caption=caption
                    )
                    await event.delete()
                else:
                    status_text = (
                        f"📊 **Результаты:**\n"
                        f"• Всего файлов: {results.total_files}\n"
                        f"• Изменено: {results.changed_files}\n"
                        f"• Ошибок: {results.failed_files}\n"
                        f"• Время: {results.duration:.1f}с"
                    )
                    await event.edit(status_text)

            except Exception as e:
                await event.edit(f"⛈️ **Ошибка обработки:** {str(e)}")
            finally:
                processing_users.remove(user_id)
                session.cleanup()
            return

        opts = {
            "spaces": 4,
            "fix_mixed": True,
            "fix_trailing": True,
            "smart_processing": True,
            "format_json": False,
            "dry_run": False,
            "check_only": False,
            "return_zip": False,
            "password": None
        }

        i = 0
        while i < len(args):
            arg = args[i]
            if arg == "-s" and i + 1 < len(args):
                try:
                    opts["spaces"] = int(args[i + 1])
                    i += 1
                except ValueError:
                    pass
            elif arg == "--json":
                opts["format_json"] = True
            elif arg == "--no-mixed":
                opts["fix_mixed"] = False
            elif arg == "--no-trail":
                opts["fix_trailing"] = False
            elif arg == "--no-smart":
                opts["smart_processing"] = False
            elif arg == "--dry-run" or arg == "--check":
                opts["check_only"] = True
                opts["dry_run"] = True
            elif arg == "--zip":
                opts["return_zip"] = True
            elif arg == "--password" and i + 1 < len(args):
                opts["password"] = args[i + 1]
                session.zip_password = args[i + 1]
                i += 1
            i += 1

        if not event.is_reply:
            await event.edit(
                "**Ошибка:** Ответьте на файл или архив.\n"
                "Используйте `.tabfix help` для справки."
            )
            return

        reply = await event.get_reply_message()
        if not reply.document and not reply.file:
            await event.edit("**Ошибка:** Сообщение не содержит файл.")
            return

        processing_users.add(user_id)
        await event.edit("⏳ Обработка...")

        temp_dir = tempfile.mkdtemp(prefix="tabfix_")
        file_paths = []

        try:
            is_zip = False
            if reply.document and reply.document.mime_type in ['application/zip', 'application/x-zip-compressed']:
                is_zip = True
            elif reply.file and reply.file.name and reply.file.name.endswith('.zip'):
                is_zip = True

            if is_zip:
                zip_path = Path(temp_dir) / "archive.zip"
                await reply.download_media(zip_path)

                extracted_files, total_in_zip = await extract_zip_with_password(zip_path, temp_dir, opts["password"])
                file_paths = extracted_files

                if not file_paths and total_in_zip > 0:
                    if opts["password"]:
                        await event.edit(
                            "⛈️ **Не удалось извлечь файлы из архива!**\n"
                            "Возможные причины:\n"
                            "• Неверный пароль\n"
                            "• Архив поврежден\n"
                            "• Файлы зашифрованы другим методом"
                        )
                    else:
                        await event.edit(
                            "🔐 **Архив защищен паролем!**\n"
                            "Используйте флаг `--password ПАРОЛЬ`\n"
                            "Пример: `.tabfix --password 123 --zip`"
                        )
                    processing_users.remove(user_id)
                    if os.path.exists(temp_dir):
                        import shutil
                        shutil.rmtree(temp_dir)
                    return
            else:
                file_path = await reply.download_media(temp_dir)
                file_paths.append(Path(file_path))

            if not file_paths:
                await event.edit("⛈️ **Не удалось получить файлы для обработки**")
                processing_users.remove(user_id)
                if os.path.exists(temp_dir):
                    import shutil
                    shutil.rmtree(temp_dir)
                return

            session.config = TabFixConfig(
                spaces=opts["spaces"],
                fix_mixed=opts["fix_mixed"],
                fix_trailing=opts["fix_trailing"],
                smart_processing=opts["smart_processing"],
                format_json=opts["format_json"],
                dry_run=opts["dry_run"],
                check_only=opts["check_only"]
            )

            results = process_files(file_paths, config=session.config)
            session.current_batch = results

            if len(file_paths) == 1 and not opts["return_zip"]:
                result = results.individual_results[0]

                if result.errors:
                    await event.edit(f"⛈️ **Ошибка:** `{result.errors[0]}`")
                elif opts["check_only"] or opts["dry_run"]:
                    if result.needs_formatting or result.changed:
                        changes = result.changes if result.changes else ["требуется форматирование"]
                        await event.edit(f"📋 **Проверка:** {', '.join(changes)}")
                    else:
                        await event.edit("✅ Файл соответствует правилам.")
                else:
                    if result.changed:
                        changes_str = ", ".join(result.changes) if result.changes else "исправлено"
                        caption = f"📝 **Исправлено:** {changes_str}"
                        await client.send_file(event.chat_id, file_paths[0], caption=caption, reply_to=reply.id)
                        await event.delete()
                    else:
                        await event.edit("✅ Файл уже соответствует правилам.")
            else:
                changed_files = [r for r in results.individual_results if r.changed]

                if changed_files or opts["return_zip"]:
                    zip_path = Path(temp_dir) / "processed.zip"
                    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        if opts["password"]:
                            zipf.setpassword(opts["password"].encode('utf-8'))
                        for result in results.individual_results:
                            if result.filepath.exists():
                                arcname = result.filepath.relative_to(temp_dir) if result.filepath.is_relative_to(temp_dir) else result.filepath.name
                                zipf.write(result.filepath, arcname)

                    caption = (
                        f"📦 **Обработано файлов:** {results.total_files}\n"
                        f"📝 **Изменено:** {results.changed_files}\n"
                        f"⛈️ **Ошибок:** {results.failed_files}\n"
                        f"⏱️ **Время:** {results.duration:.1f}с"
                    )
                    if opts["password"]:
                        caption += f"\n🔐 **Пароль:** `{opts['password']}`"

                    await client.send_file(
                        event.chat_id,
                        zip_path,
                        caption=caption,
                        reply_to=reply.id
                    )
                    await event.delete()
                else:
                    status_text = (
                        f"📊 **Результаты:**\n"
                        f"• Всего файлов: {results.total_files}\n"
                        f"• Изменено: {results.changed_files}\n"
                        f"• Ошибок: {results.failed_files}\n"
                        f"• Время: {results.duration:.1f}с"
                    )
                    await event.edit(status_text)

        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            print(f"Debug: {error_details}")
            await event.edit(f"⛈️ **Критическая ошибка:** `{type(e).__name__}: {str(e)[:200]}`")
        finally:
            processing_users.remove(user_id)
            if os.path.exists(temp_dir):
                import shutil
                shutil.rmtree(temp_dir)

    @kernel.register.watcher(outgoing=True, only_pm=True)
    async def batch_file_handler(event):
        user_id = event.sender_id
        session = get_session(user_id)

        if not session.temp_dir or not os.path.exists(session.temp_dir):
            return

        if event.document or event.file:
            await event.edit("⏳ Сохраняю файл...")
            try:
                file_path = await event.download_media(session.temp_dir)
                file_name = Path(file_path).name

                if file_name.endswith('.zip'):
                    try:
                        extracted_files, _ = await extract_zip_with_password(file_path, session.temp_dir, session.zip_password)
                        os.remove(file_path)
                        if extracted_files:
                            await event.edit(f"✅ **Архив распакован! Извлечено {len(extracted_files)} файлов.**\nОтправьте еще файлы или `.tabfix process`")
                        else:
                            await event.edit(f"⛈️ **Не удалось распаковать архив!**\nПроверьте пароль или целостность архива.")
                    except Exception as e:
                        await event.edit(f"⛈️ **Ошибка распаковки архива:** {str(e)}")
                else:
                    await event.edit(f"✅ Файл `{file_name}` сохранен\nОтправьте еще файлы или `.tabfix process`")
            except Exception as e:
                await event.edit(f"⛈️ Ошибка сохранения: {str(e)}")
        elif event.message.text and event.message.text.startswith('.'):
            return
        elif event.message.text:
            session.cleanup()
            await event.edit("⛈️ Пакетный режим отменен")

    @kernel.register_command('tabfix_stats')
    # статистика модуля TabFix
    async def stats_handler(event):
        total_users = len(user_sessions)
        active_processing = len(processing_users)

        stats_text = (
            f"📈 **Статистика TabFix:**\n"
            f"• Всего пользователей: {total_users}\n"
            f"• Активных обработок: {active_processing}\n"
            f"• Версия модуля: 2.2\n"
            f"• Поддержка архивов: ✓\n"
            f"• Поддержка паролей: ✓\n"
            f"• Пакетная обработка: ✓"
        )

        buttons = [
            Button.inline("Очистить сессии", b"clear_sessions"),
            Button.inline("Справка", b"show_help")
        ]

        await event.edit(stats_text, buttons=buttons)

    async def clear_sessions_handler(event):
        for session in user_sessions.values():
            session.cleanup()
        user_sessions.clear()
        processing_users.clear()
        await event.edit("✅ Все сессии очищены")

    async def show_help_handler(event):
        help_text = (
            "📖 **TabFix Module v2.2**\n\n"
            "**Новый функционал:**\n"
            "• Пакетная обработка файлов\n"
            "• Поддержка ZIP архивов\n"
            "• Защищенные паролем архивы (--password)\n"
            "• Возврат в виде архива (--zip)\n"
            "• Статус обработки\n"
            "• Отмена операций\n"
            "• Статистика\n\n"
            "**Важно:** Для архивов с паролем используйте:\n"
            "`.tabfix --zip --password 123`\n\n"
            "Используйте `.tabfix help` для полной справки."
        )
        await event.edit(help_text)

    kernel.register_callback_handler('clear_sessions', clear_sessions_handler)
    kernel.register_callback_handler('show_help', show_help_handler)
