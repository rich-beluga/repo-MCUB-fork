# github: https://github.com/hairpin01/repo-MCUB-fork
# source github (original): https://github.com/Deseara/D-modules/blob/main/joke_module.py
# Channel: https://t.me/LinuxGram2
# Author channel: https://t.me/Desearamodules
# -------------------- Meta data ---------------------------
# requires: aiohttp
# author: @Deseara && port: @Hairpin00
# version: 2.0
# description: Oтпpaвляeт пepeвeдeнныe шyтки c JokeAPI
# ----------------------- End ------------------------------
import aiohttp
from telethon import Button
import json

def register(kernel):
    strings = {
        'en': {
            'name': 'JokeAPI',
            'description': 'Sends translated jokes from JokeAPI',
            'fetching': '🔄 Fetching joke...',
            'single_joke': '😂 <b>Joke of the day:</b>\n\n<i>{}</i>',
            'twopart_joke': '😂 <b>Joke of the day:</b>\n\n<b>❓ Question:</b> <i>{}</i>\n<b>💡 Answer:</b> <i>{}</i>',
            'api_error': '🚫 API Error: Failed to fetch joke. Try again later.',
            'no_joke': '🚫 Error: No joke found with specified parameters.',
            'joke_description': '🎭 <b>JokeAPI Help</b>\n\n📝 <b>Usage:</b>\n• <code>.joke</code> - random joke\n• <code>.joke [category]</code> - joke from category\n\n🎭 <b>Available categories:</b>\n• Programming, Miscellaneous, Pun, Spooky, Christmas',
            'cfg_categories': 'Default categories, comma separated',
            'cfg_blacklist': 'Excluded categories, comma separated',
            'translation_error': '⚠️ Failed to translate joke, showing original',
            'help_cmd': 'Show this help message',
            'categories_cmd': 'Show available categories',
            'error_fetch': '🚫 API Error: No data from API for category \'{}\'',
            'error_format': '🚫 Format Error: Failed to process joke. Type: {}'
        },
        'ru': {
            'name': 'JokeAPI',
            'description': 'Oтпpaвляeт пepeвeдeнныe шyтки c JokeAPI',
            'fetching': '🔄 Зaгpyжaю шyткy...',
            'single_joke': '😂 <b>Шyткa дня:</b>\n\n<i>{}</i>',
            'twopart_joke': '😂 <b>Шyткa дня:</b>\n\n<b>❓ Вoпpoc:</b> <i>{}</i>\n<b>💡 Oтвeт:</b> <i>{}</i>',
            'api_error': '🚫 Oшибкa API: He yдaлocь пoлyчить шyткy. Пoпpoбyйтe пoзжe.',
            'no_joke': '🚫 Oшибкa: Шyткa c yкaзaнными пapaмeтpaми нe нaйдeнa.',
            'joke_description': '🎭 <b>JokeAPI Help</b>\n\n📝 <b>Иcпoльзoвaниe:</b>\n• <code>.joke</code> - cлyчaйнaя шyткa\n• <code>.joke [кaтeгopия]</code> - шyткa из кaтeгopии\n\n🎭 <b>Дocтyпныe кaтeгopии:</b>\n• Programming, Miscellaneous, Pun, Spooky, Christmas',
            'cfg_categories': 'Кaтeгopии пo yмoлчaнию, paздeлeнныe зaпятoй',
            'cfg_blacklist': 'Иcключaeмыe кaтeгopии, paздeлeнныe зaпятoй',
            'translation_error': '⚠️ He yдaлocь пepeвecти шyткy, пoкaзывaю opигинaл',
            'help_cmd': 'Пoкaзaть этo cooбщeниe пoмoщи',
            'categories_cmd': 'Пoкaзaть дocтyпныe кaтeгopии',
            'error_fetch': '🚫 API Error: Heт дaнныx oт API для кaтeгopии \'{}\'',
            'error_format': '🚫 Format Error: He yдaлocь oбpaбoтaть шyткy. Тип: {}'
        }
    }


    language = kernel.config.get('language', 'en')
    s = strings.get(language, strings['en'])


    defaults = {
        'categories': 'Programming,Miscellaneous,Pun,Spooky,Christmas',
        'blacklist': 'nsfw,religious,political,racist,sexist,explicit',
        'language': language
    }


    module_config = kernel.config.get('joke_module', defaults)


    session = None

    async def init_session():
        """Инициaлизaция HTTP ceccии"""
        nonlocal session
        if session is None or session.closed:
            session = aiohttp.ClientSession()

    async def close_session():
        """Зaкpытиe HTTP ceccии"""
        nonlocal session
        if session and not session.closed:
            await session.close()
            session = None

    async def _translate_text(text, target_lang=None):
        if not text or not text.strip():
            return None

        if language == 'en':
            return text

        if target_lang is None:
            target_lang = 'ru' if language == 'ru' else 'en'

        try:
            url = "https://api.mymemory.translated.net/get"
            params = {
                "q": text,
                "langpair": f"en|{target_lang}"
            }

            async with session.get(url, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get("responseStatus") == 200:
                        translated = data["responseData"]["translatedText"]
                        if translated and translated.strip():
                            return translated

            # Fallback to Google Translate
            url2 = "https://translate.googleapis.com/translate_a/single"
            params2 = {
                "client": "gtx",
                "sl": "en",
                "tl": target_lang,
                "dt": "t",
                "q": text
            }

            async with session.get(url2, params=params2) as response:
                if response.status == 200:
                    data = await response.json()
                    if data and len(data) > 0 and len(data[0]) > 0:
                        translated = data[0][0][0]
                        if translated and translated.strip():
                            return translated

        except Exception as e:
            await kernel.log_error(f"Translation error: {e}")

        return None

    async def _format_joke(joke_data):
        if not joke_data:
            return None

        if joke_data.get("type") == "single":
            joke_text = joke_data.get("joke", "")
            if not joke_text:
                return None

            translated = await _translate_text(joke_text)
            if translated and translated.strip():
                text = s['single_joke'].format(translated)
            else:
                text = f"{s['translation_error']}\n\n{s['single_joke'].format(joke_text)}"

        else:  # twopart joke
            setup_text = joke_data.get("setup", "")
            delivery_text = joke_data.get("delivery", "")
            if not setup_text or not delivery_text:
                return None

            translated_setup = await _translate_text(setup_text)
            translated_delivery = await _translate_text(delivery_text)

            if translated_setup and translated_delivery and translated_setup.strip() and translated_delivery.strip():
                text = s['twopart_joke'].format(
                    translated_setup,
                    translated_delivery
                )
            else:
                text = f"{s['translation_error']}\n\n{s['twopart_joke'].format(setup_text, delivery_text)}"

        return text if text and text.strip() else None

    async def _fetch_joke(categories):
        params = {
            "lang": "en",
            "blacklistFlags": module_config.get('blacklist', defaults['blacklist']),
        }

        url = f"https://v2.jokeapi.dev/joke/{categories}"

        try:
            async with session.get(url, params=params) as response:
                if response.status != 200:
                    return None

                data = await response.json()

                if data.get("error"):
                    return None

                return data
        except Exception as e:
            await kernel.log_error(f"JokeAPI fetch error: {e}")
            return None

    async def joke_command(event):
        await init_session()

        args = event.text.split(maxsplit=1)
        arg = args[1] if len(args) > 1 else ""

        if arg.lower() in ["help", "пoмoщь", "кaтeгopии", "categories"]:
            await event.edit(s['joke_description'], parse_mode='HTML')
            return

        await event.edit(s['fetching'])

        categories = arg if arg else module_config.get('categories', defaults['categories'])

        try:
            joke_data = await _fetch_joke(categories)

            if not joke_data:
                await event.edit(s['error_fetch'].format(categories))
                return

            joke_text = await _format_joke(joke_data)

            if not joke_text or not joke_text.strip():
                await event.edit(s['error_format'].format(joke_data.get('type', 'unknown')))
                return

            await event.delete()
            await event.respond(joke_text, parse_mode='HTML')

        except Exception as e:
            await kernel.handle_error(e, source="joke_command", event=event)
            await event.edit(f"🚫 {s['api_error']}")

    async def joke_categories_command(event):
        categories_list = [
            "Programming", "Miscellaneous", "Pun",
            "Spooky", "Christmas", "Dark"
        ]

        response = "🎭 <b>Available Categories:</b>\n\n"
        response += "\n".join([f"• {cat}" for cat in categories_list])
        response += f"\n\n<b>Current:</b> {module_config.get('categories', defaults['categories'])}"

        await event.edit(response, parse_mode='HTML')

    async def joke_config_command(event):
        args = event.text.split(maxsplit=2)
        if len(args) < 2:
            # Пoкaзaть тeкyщyю кoнфигypaцию
            response = f"⚙️ <b>JokeAPI Configuration</b>\n\n"
            response += f"<b>Categories:</b> {module_config.get('categories', defaults['categories'])}\n"
            response += f"<b>Blacklist:</b> {module_config.get('blacklist', defaults['blacklist'])}\n"
            response += f"<b>Language:</b> {language}\n\n"
            response += f"<i>Usage: .jokeconfig set categories Programming,Miscellaneous</i>"
            await event.edit(response, parse_mode='HTML')
            return

        if args[1].lower() == 'set' and len(args) > 2:
            # Oбнoвлeниe кoнфигypaции
            set_args = args[2].split(' ', 1)
            if len(set_args) < 2:
                await event.edit("❌ Usage: .jokeconfig set <key> <value>")
                return

            key = set_args[0].lower()
            value = set_args[1]

            if key in ['categories', 'blacklist']:
                module_config[key] = value
                kernel.config['joke_module'] = module_config
                kernel.save_config()
                await event.edit(f"✅ {key.capitalize()} updated to: {value}")
            else:
                await event.edit(f"❌ Invalid key. Use: categories, blacklist")
        else:
            await event.edit("❌ Usage: .jokeconfig [set <key> <value>]")

    @kernel.register.command('joke', alias=['j', 'шyткa'])
    async def joke_handler(event):
        await joke_command(event)

    @kernel.register.command('jokecategories', alias=['jc', 'кaтeгopии'])
    async def categories_handler(event):
        await joke_categories_command(event)

    @kernel.register.command('jokeconfig', alias=['jcfg'])
    async def config_handler(event):
        await joke_config_command(event)

    async def send_daily_joke():
        try:
            await init_session()

            joke_data = await _fetch_joke(module_config.get('categories', defaults['categories']))
            if joke_data:
                joke_text = await _format_joke(joke_data)
                if joke_text:
                    log_chat = kernel.config.get('log_chat_id')
                    if log_chat:
                        await kernel.client.send_message(
                            log_chat,
                            joke_text,
                            parse_mode='HTML'
                        )
        except Exception as e:
            await kernel.log_error(f"Daily joke error: {e}")
        finally:
            await close_session()

    kernel.scheduler.add_daily_task(send_daily_joke, 12, 0)

    async def translation_middleware(event, next_handler):
        try:
            return await next_handler(event)
        except aiohttp.ClientError as e:
            await kernel.log_error(f"Network error in joke module: {e}")
            await event.edit("🌐 Network error. Please try again later.")
        except Exception as e:
            await kernel.handle_error(e, source="joke_middleware", event=event)

    kernel.add_middleware(translation_middleware)



