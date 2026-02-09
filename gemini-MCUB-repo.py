# requires: google.generativeai, pytz
# author: @Hairpin00
# version: 1.0.5
# description: gemini
import asyncio
import random
import json
import html
import io
import os
import re
from datetime import datetime
from pathlib import Path
import pytz
from telethon import Button

try:
    import google.generativeai as genai
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

def register(kernel):
    client = kernel.client
    
    class GeminiModule:
        def __init__(self):
            self.config = {
                "api_keys": [],
                "model": "gemini-1.5-flash",
                "temperature": 1.0,
                "max_history_length": 20,
                "impersonation_reply_chance": 0.2,
                "system_prompt": "",
                "gauto_in_pm": False,
                "timezone": "Europe/Moscow",
                "use_expandable": True,
                "max_response_length": 1500,
                "use_inline": False,
                "show_buttons": True,
                "inline_bot_username": kernel.config.get('inline_bot_username'),
            }
            
            self.conversations = {}
            self.gauto_conversations = {}
            self.impersonation_chats = set()
            self.last_user_by_chat = {}
            self.last_message_by_chat = {}
            self.data_dir = Path("gemini_data")
            self.data_dir.mkdir(exist_ok=True)
            
            self.me = None
            self.current_api_key_index = 0
            
        async def initialize(self):
            self.me = await client.get_me()
            await self.load_config()
            await self.load_data()
            
        async def load_config(self):
            config_file = self.data_dir / "config.json"
            if config_file.exists():
                try:
                    with open(config_file, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                        for key in self.config:
                            if key in loaded_config:
                                self.config[key] = loaded_config[key]
                except Exception as e:
                    await kernel.handle_error(e, source="gemini_load_config")
        
        async def save_config(self):
            config_file = self.data_dir / "config.json"
            try:
                with open(config_file, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                await kernel.handle_error(e, source="gemini_save_config")
        
        async def load_data(self):
            try:
                conv_file = self.data_dir / "conversations.json"
                if conv_file.exists():
                    with open(conv_file, 'r', encoding='utf-8') as f:
                        self.conversations = json.load(f)
                
                gauto_file = self.data_dir / "gauto_conversations.json"
                if gauto_file.exists():
                    with open(gauto_file, 'r', encoding='utf-8') as f:
                        self.gauto_conversations = json.load(f)
                
                imp_file = self.data_dir / "impersonation_chats.json"
                if imp_file.exists():
                    with open(imp_file, 'r', encoding='utf-8') as f:
                        self.impersonation_chats = set(json.load(f))
            except Exception as e:
                await kernel.handle_error(e, source="gemini_load_data")
        
        async def save_data(self, data_type="all"):
            try:
                if data_type in ["all", "conversations"]:
                    conv_file = self.data_dir / "conversations.json"
                    with open(conv_file, 'w', encoding='utf-8') as f:
                        json.dump(self.conversations, f, ensure_ascii=False, indent=2)
                
                if data_type in ["all", "gauto"]:
                    gauto_file = self.data_dir / "gauto_conversations.json"
                    with open(gauto_file, 'w', encoding='utf-8') as f:
                        json.dump(self.gauto_conversations, f, ensure_ascii=False, indent=2)
                
                if data_type in ["all", "impersonation"]:
                    imp_file = self.data_dir / "impersonation_chats.json"
                    with open(imp_file, 'w', encoding='utf-8') as f:
                        json.dump(list(self.impersonation_chats), f, ensure_ascii=False, indent=2)
            except Exception as e:
                await kernel.handle_error(e, source="gemini_save_data")
        
        def _get_args(self, event):
            text = event.text
            prefix = kernel.custom_prefix
            if text.startswith(prefix):
                text = text[len(prefix):]
            parts = text.split(maxsplit=1)
            if len(parts) > 1:
                return parts[1].strip()
            return ""
        
        def _get_conversation_history(self, chat_id, gauto=False):
            conversations = self.gauto_conversations if gauto else self.conversations
            chat_key = str(chat_id)
            return conversations.get(chat_key, [])
        
        def _update_conversation_history(self, chat_id, user_message, ai_response, gauto=False):
            conversations = self.gauto_conversations if gauto else self.conversations
            chat_key = str(chat_id)
            
            if chat_key not in conversations:
                conversations[chat_key] = []
            
            conversations[chat_key].append({
                'role': 'user',
                'content': user_message,
                'timestamp': datetime.now().isoformat()
            })
            
            conversations[chat_key].append({
                'role': 'assistant',
                'content': ai_response,
                'timestamp': datetime.now().isoformat()
            })
            
            max_len = self.config["max_history_length"]
            if max_len > 0 and len(conversations[chat_key]) > max_len * 2:
                conversations[chat_key] = conversations[chat_key][-max_len * 2:]
        
        def _clear_conversation_history(self, chat_id, gauto=False):
            conversations = self.gauto_conversations if gauto else self.conversations
            chat_key = str(chat_id)
            if chat_key in conversations:
                del conversations[chat_key]
        
        async def _prepare_prompt(self, event, custom_text=None):
            prompt_parts = []
            
            reply = await event.get_reply_message()
            
            if reply and reply.text:
                try:
                    from telethon.utils import get_display_name
                    reply_sender = await reply.get_sender()
                    reply_name = get_display_name(reply_sender) if reply_sender else "Unknown"
                    reply_text = self._clean_text(reply.text)
                    prompt_parts.append(f"{reply_name}: {reply_text}")
                except Exception:
                    reply_text = self._clean_text(reply.text)
                    prompt_parts.append(f"Ответ на: {reply_text}")
            
            user_text = custom_text if custom_text is not None else self._get_args(event)
            if user_text:
                try:
                    from telethon.utils import get_display_name
                    current_sender = await event.get_sender()
                    current_name = get_display_name(current_sender) if current_sender else "User"
                    cleaned_text = self._clean_text(user_text)
                    prompt_parts.append(f"{current_name}: {cleaned_text}")
                except Exception:
                    cleaned_text = self._clean_text(user_text)
                    prompt_parts.append(f"Запрос: {cleaned_text}")
            
            return "\n".join(prompt_parts).strip()
        
        def _clean_text(self, text):
            if not text:
                return text
            
            text = str(text)
            
            invisible_chars = [
                '\u200b', '\u200c', '\u200d', '\u200e', '\u200f',
                '\u202a', '\u202b', '\u202c', '\u202d', '\u202e',
                '\u2060', '\u2061', '\u2062', '\u2063', '\u2064',
                '\ufeff', '\u00a0', '\u2028', '\u2029', '\u3000',
                '\u3164', '\uffa0',
            ]
            
            for char in invisible_chars:
                text = text.replace(char, ' ')
            
            text = text.replace('󠆜', '')
            
            text = ' '.join(text.split())
            
            return text.strip()
        
        def _format_response(self, text):
            if not text:
                return text
            
            text = str(text)
            
            text = html.escape(text)
            
            text = text.replace('&quot;', '"').replace('&#34;', '"')
            text = text.replace('&#39;', "'").replace('&#x27;', "'")
            text = text.replace('&amp;', '&')
            text = text.replace('&lt;', '<')
            text = text.replace('&gt;', '>')
            text = text.replace('&nbsp;', ' ')
            
            return text
        
        async def _call_gemini_api(self, prompt, chat_id=None, gauto=False):
            api_keys = self.config["api_keys"]
            if not api_keys:
                raise ValueError("No API keys configured")
            
            messages = []
            if chat_id is not None:
                history = self._get_conversation_history(chat_id, gauto)
                for msg in history:
                    role = "user" if msg['role'] == 'user' else "model"
                    messages.append({"role": role, "parts": [msg['content']]})
            
            system_prompt = self.config["system_prompt"]
            if system_prompt and not gauto:
                messages.insert(0, {"role": "user", "parts": [f"System: {system_prompt}\n\n"]})
            
            try:
                user_timezone = pytz.timezone(self.config["timezone"])
            except pytz.UnknownTimeZoneError:
                user_timezone = pytz.utc
            
            now = datetime.now(user_timezone)
            time_str = now.strftime("%Y-%m-%d %H:%M:%S %Z")
            time_note = f"[System note: Current time is {time_str}]"
            messages.append({"role": "user", "parts": [f"{time_note}\n\n{prompt}"]})
            
            for i, api_key in enumerate(api_keys):
                try:
                    genai.configure(api_key=api_key)
                    
                    model_kwargs = {
                        "model_name": self.config["model"]
                    }
                    
                    try:
                        from google.generativeai.types import HarmCategory, HarmBlockThreshold
                        safety_settings = {
                            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
                        }
                        model_kwargs["safety_settings"] = safety_settings
                    except ImportError:
                        pass
                    
                    model = genai.GenerativeModel(**model_kwargs)
                    
                    response = await asyncio.wait_for(
                        model.generate_content_async(
                            messages,
                            generation_config=genai.types.GenerationConfig(
                                temperature=float(self.config["temperature"])
                            )
                        ),
                        timeout=120
                    )
                    
                    self.current_api_key_index = i
                    
                    if response.text:
                        return response.text
                    else:
                        raise ValueError("Empty response from Gemini")
                
                except Exception as e:
                    if i == len(api_keys) - 1:
                        raise e
                    continue
            
            return None
        
        async def _should_send_as_file(self, response_text):
            max_length = self.config.get("max_response_length", 1500)
            return len(response_text) > max_length
        
        async def _send_as_file(self, event, prompt, response):
            file_content = f"💬 Вопрос: {prompt}\n\n✨ Ответ Gemini:\n{response}"
            
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"gemini_response_{timestamp}.txt"
            
            file = io.BytesIO(file_content.encode('utf-8'))
            file.name = filename
            
            try:
                await event.delete()
            except Exception:
                pass
            
            try:
                await client.send_file(
                    event.chat_id,
                    file,
                    caption=f"🔮 <i>Ответ Gemini слишком длинный</i>\n<blockquote>🔬 <b>размер:</b> <code>{len(response)} символов</code></blockquote>",
                    parse_mode='html'
                )
            except Exception as e:
                await kernel.handle_error(e, source="gemini_send_file", event=event)
        
        async def _send_response_with_buttons(self, event, prompt, response_text, msg_id=None):
            try:
                cleaned_prompt = self._clean_text(prompt)
                formatted_prompt = self._format_response(cleaned_prompt)
                response = self._format_response(response_text)
                
                if self.config.get("use_expandable", True) and (len(formatted_prompt) > 200 or formatted_prompt.count('\n') > 3):
                    prompt_html = f"<blockquote expandable>{formatted_prompt}</blockquote>"
                else:
                    prompt_html = f"<blockquote>{formatted_prompt}</blockquote>"
                
                if self.config.get("use_expandable", True) and (len(response) > 200 or response.count('\n') > 3):
                    response_html = f"<blockquote expandable>{response}</blockquote>"
                else:
                    response_html = f"<blockquote>{response}</blockquote>"
                
                base_text = f"💬 <i>Вопрос:</i>\n{prompt_html}\n\n✨ <i>Gemini:</i>\n{response_html}"
                
                buttons = [
                    [Button.inline("🔄 Регенерировать", b"gemini_regenerate"),
                     Button.inline("🧹 Очистить", b"gemini_clear")]
                ]
                
                if msg_id:
                    try:
                        await event.edit(base_text, parse_mode='html', buttons=buttons)
                    except Exception:
                        await event.respond(base_text, parse_mode='html', buttons=buttons)
                else:
                    try:
                        await event.delete()
                    except Exception:
                        pass
                    await event.respond(base_text, parse_mode='html', buttons=buttons)
                
            except Exception as e:
                await kernel.handle_error(e, source="_send_response_with_buttons", event=event)
        
        async def gg_command(self, event):
            try:
                if not GOOGLE_AVAILABLE:
                    await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                    return
                
                if not self.config["api_keys"]:
                    await event.edit("🔮 <i>API ключи не настроены</i>", parse_mode='html')
                    return
                
                try:
                    msg = await event.edit("⌛️ <i>Обработка...</i>", parse_mode='html')
                except Exception:
                    msg = None
                
                args = self._get_args(event)
                prompt = await self._prepare_prompt(event, custom_text=args)
                
                if not prompt:
                    await event.edit("⚠️ <i>Нужен текст или ответ на медиа/файл</i>", parse_mode='html')
                    return
                
                self.last_user_by_chat[event.chat_id] = event.sender_id
                
                response_text = await self._call_gemini_api(prompt, event.chat_id)
                
                if not response_text:
                    await event.edit("❌ <i>Не удалось получить ответ от Gemini</i>", parse_mode='html')
                    return
                
                self._update_conversation_history(event.chat_id, prompt, response_text)
                await self.save_data("conversations")
                
                if await self._should_send_as_file(response_text):
                    await self._send_as_file(event, prompt, response_text)
                    return
                
                await self._send_response_with_buttons(event, prompt, response_text)
            
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gg_command", event=event)
        
        async def gclear_command(self, event):
            try:
                args = self._get_args(event)
                
                if args == "auto":
                    if str(event.chat_id) in self.gauto_conversations:
                        self._clear_conversation_history(event.chat_id, gauto=True)
                        await self.save_data("gauto")
                        await event.edit("🧹 <i>Память gauto очищена</i>", parse_mode='html')
                    else:
                        await event.edit("ℹ️ <i>В этом чате нет истории gauto</i>", parse_mode='html')
                else:
                    if str(event.chat_id) in self.conversations:
                        self._clear_conversation_history(event.chat_id, gauto=False)
                        await self.save_data("conversations")
                        await event.edit("🧹 <i>Память диалога очищена</i>", parse_mode='html')
                    else:
                        await event.edit("ℹ️ <i>В этом чате нет истории</i>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gclear_command", event=event)
        
        async def gauto_command(self, event):
            try:
                args = self._get_args(event).lower()
                
                if args == "on":
                    self.impersonation_chats.add(event.chat_id)
                    await self.save_data("impersonation")
                    chance = int(float(self.config["impersonation_reply_chance"]) * 100)
                    await event.edit(f"🎭 <i>Режим авто-ответа включен</i>\n<blockquote>🎲 <b>вероятность:</b> <code>{chance}%</code></blockquote>", parse_mode='html')
                elif args == "off":
                    self.impersonation_chats.discard(event.chat_id)
                    await self.save_data("impersonation")
                    await event.edit("🎭 <i>Режим авто-ответа выключен</i>", parse_mode='html')
                else:
                    await event.edit("ℹ️ <i>Использование:</i> <code>.gauto on/off</code>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gauto_command", event=event)
        
        async def gmodel_command(self, event):
            try:
                args = self._get_args(event)
                
                if args:
                    self.config["model"] = args
                    await self.save_config()
                    await event.edit(f"✅ <i>Модель изменена на:</i> <code>{args}</code>", parse_mode='html')
                else:
                    await event.edit(f"📋 <i>Текущая модель:</i> <code>{self.config['model']}</code>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gmodel_command", event=event)
        
        async def gprompt_command(self, event):
            try:
                args = self._get_args(event)
                
                if args == "-c":
                    self.config["system_prompt"] = ""
                    await self.save_config()
                    await event.edit("🗑 <i>Системный промпт очищен</i>", parse_mode='html')
                    return
                
                if args:
                    self.config["system_prompt"] = args
                    await self.save_config()
                    await event.edit(f"✅ <i>Системный промпт обновлен</i>\n<blockquote>🔬 <b>длина:</b> <code>{len(args)} символов</code></blockquote>", parse_mode='html')
                else:
                    system_prompt = self.config["system_prompt"]
                    if system_prompt:
                        await event.edit(f"📝 <i>Системный промпт:</i>\n<code>{html.escape(system_prompt[:4000])}</code>", parse_mode='html')
                    else:
                        await event.edit("ℹ️ <i>Использование:</i> <code>.gprompt текст</code>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gprompt_command", event=event)
        
        async def gres_command(self, event):
            try:
                args = self._get_args(event)
                
                if args == "auto":
                    self.gauto_conversations.clear()
                    await self.save_data("gauto")
                    await event.edit("🧹 <i>Вся память gauto очищена</i>", parse_mode='html')
                else:
                    chat_key = str(event.chat_id)
                    if chat_key in self.conversations and len(self.conversations[chat_key]) >= 2:
                        self.conversations[chat_key] = self.conversations[chat_key][:-2]
                        await self.save_data("conversations")
                        await event.edit("🔄 <i>Последний ответ удален</i>\n<blockquote>🧬 <b>используйте</b> <code>.gg</code> <b>для нового запроса</b></blockquote>", parse_mode='html')
                    else:
                        await event.edit("ℹ️ <i>Нет истории для перегенерации</i>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gres_command", event=event)
        
        async def gconfig_command(self, event):
            try:
                args = self._get_args(event)
                
                if not args:
                    await event.edit("ℹ️ <i>Использование:</i> <code>.gconfig переменная значение</code>", parse_mode='html')
                    return
                
                parts = args.split(maxsplit=2)
                
                if len(parts) >= 2:
                    key = parts[0]
                    value = parts[1] if len(parts) == 2 else parts[1] + " " + parts[2]
                    
                    if key not in self.config:
                        await event.edit(f"❌ <i>Настройка не найдена:</i> <code>{key}</code>", parse_mode='html')
                        return
                    
                    try:
                        if key == "api_keys":
                            new_keys = [k.strip() for k in value.split(",") if k.strip()]
                            self.config[key] = new_keys
                        elif key == "temperature":
                            new_val = float(value)
                            if not 0.0 <= new_val <= 2.0:
                                raise ValueError("Temperature must be between 0.0 and 2.0")
                            self.config[key] = new_val
                        elif key == "max_history_length":
                            new_val = int(value)
                            if new_val < 0:
                                raise ValueError("Max history length must be >= 0")
                            self.config[key] = new_val
                        elif key == "impersonation_reply_chance":
                            new_val = float(value)
                            if not 0.0 <= new_val <= 1.0:
                                raise ValueError("Reply chance must be between 0.0 and 1.0")
                            self.config[key] = new_val
                        elif key == "gauto_in_pm":
                            if value.lower() in ["true", "1", "yes", "on"]:
                                self.config[key] = True
                            elif value.lower() in ["false", "0", "no", "off"]:
                                self.config[key] = False
                            else:
                                raise ValueError("Must be true/false")
                        elif key == "use_expandable":
                            if value.lower() in ["true", "1", "yes", "on"]:
                                self.config[key] = True
                            elif value.lower() in ["false", "0", "no", "off"]:
                                self.config[key] = False
                            else:
                                raise ValueError("Must be true/false")
                        elif key == "max_response_length":
                            new_val = int(value)
                            if new_val < 100:
                                raise ValueError("Max response length must be >= 100")
                            self.config[key] = new_val
                        elif key == "use_inline":
                            if value.lower() in ["true", "1", "yes", "on"]:
                                self.config[key] = True
                            elif value.lower() in ["false", "0", "no", "off"]:
                                self.config[key] = False
                            else:
                                raise ValueError("Must be true/false")
                        elif key == "show_buttons":
                            if value.lower() in ["true", "1", "yes", "on"]:
                                self.config[key] = True
                            elif value.lower() in ["false", "0", "no", "off"]:
                                self.config[key] = False
                            else:
                                raise ValueError("Must be true/false")
                        elif key == "inline_bot_username":
                            self.config[key] = value.strip()
                        else:
                            self.config[key] = value
                        
                        await self.save_config()
                        await event.edit(f"✅ <i>Настройка обновлена</i>\n<blockquote>🔧 <b>{key}</b> = <code>{self.config[key]}</code></blockquote>", parse_mode='html')
                    
                    except Exception as e:
                        await event.edit(f"❌ <i>Некорректное значение для</i> <code>{key}</code>\n<blockquote>🚫 <b>ошибка:</b> <code>{str(e)}</code></blockquote>", parse_mode='html')
                else:
                    await event.edit("ℹ️ <i>Использование:</i> <code>.gconfig переменная значение</code>", parse_mode='html')
            except Exception as e:
                await event.edit("🌩️ <b>Ошибка, смотри логи</b>", parse_mode='html')
                await kernel.handle_error(e, source="gconfig_command", event=event)
        
        async def gcfg_command(self, event):
            try:
                await event.delete()
                
                config_text = f"""🔮 <i>Настройки Gemini</i>

<blockquote>📋 <b>модель:</b> <code>{self.config['model']}</code>
🌡 <b>температура:</b> <code>{self.config['temperature']}</code>
📚 <b>история:</b> <code>{self.config['max_history_length']} сообщений</code>
🔘 <b>кнопки:</b> <code>{'включены' if self.config.get('show_buttons', True) else 'выключены'}</code></blockquote>

🧬 <i>Используйте</i> <code>.gconfig переменная значение</code>"""
                
                await event.respond(config_text, parse_mode='html')
            except Exception as e:
                await kernel.handle_error(e, source="gcfg_command", event=event)
        
        async def ghelp_command(self, event):
            try:
                await event.delete()
                
                help_text = """🔮 <i>Модуль Gemini - Справка</i>

<blockquote>💬 <b>.gg [текст]</b> - запрос к Gemini
🧹 <b>.gclear [auto]</b> - очистка памяти
🎭 <b>.gauto on/off</b> - авто-ответ
📝 <b>.gmodel [модель]</b> - смена модели
📝 <b>.gprompt [текст]</b> - системный промпт
🔄 <b>.gres [auto]</b> - перегенерация/очистка
🔧 <b>.gconfig [переменная] [значение]</b> - настройка
⚙️ <b>.gcfg</b> - настройки
📖 <b>.ghelp</b> - эта справка</blockquote>"""
                
                await event.respond(help_text, parse_mode='html')
            except Exception as e:
                await kernel.handle_error(e, source="ghelp_command", event=event)
        
        async def callback_handler(self, event):
            try:
                data = event.data.decode()
                chat_id = event.chat_id
                user_id = event.sender_id
                
                last_user = self.last_user_by_chat.get(chat_id)
                
                if user_id != last_user:
                    try:
                        participant = await event.client.get_permissions(chat_id, user_id)
                        if not participant.is_admin:
                            await event.answer("Вы не можете нажимать эти кнопки.", alert=True)
                            return
                    except Exception:
                        await event.answer("Вы не можете нажимать эти кнопки.", alert=True)
                        return
                
                if data == "gemini_regenerate":
                    await event.answer("🔄 Регенерирую...")
                    
                    history = self._get_conversation_history(chat_id)
                    if len(history) >= 2:
                        self.conversations[str(chat_id)] = history[:-2]
                        
                        chat_key = str(chat_id)
                        if chat_key in self.conversations:
                            messages = self.conversations[chat_key]
                            if messages:
                                last_user_msg = messages[-1]['content'] if messages[-1]['role'] == 'user' else messages[-2]['content']
                                
                                response_text = await self._call_gemini_api(last_user_msg, chat_id)
                                if response_text:
                                    self._update_conversation_history(chat_id, last_user_msg, response_text)
                                    await self.save_data("conversations")
                                    
                                    await self._send_response_with_buttons(event, last_user_msg, response_text, msg_id=event.message_id)
                                else:
                                    await event.answer("❌ Не удалось регенерировать", alert=True)
                            else:
                                await event.answer("❌ Нет истории", alert=True)
                        else:
                            await event.answer("❌ Нет истории", alert=True)
                    else:
                        await event.answer("❌ Нет истории для регенерации", alert=True)
                
                elif data == "gemini_clear":
                    await event.answer("🧹 Очищаю историю...")
                    
                    self._clear_conversation_history(chat_id)
                    await self.save_data("conversations")
                    
                    try:
                        await event.edit("🧹 <i>История диалога очищена</i>", buttons=None, parse_mode='html')
                    except Exception:
                        pass
                
            except Exception as e:
                await event.answer(f"❌ Ошибка", alert=True)
                await kernel.handle_error(e, source="gemini_callback", event=event)
    
    gemini = GeminiModule()
    
    @kernel.register.command('gg')
    # <вопрос> спросить gemini
    async def gg_handler(event):
        await gemini.gg_command(event)
    
    @kernel.register.command('gclear')
    # очистить историю
    async def gclear_handler(event):
        await gemini.gclear_command(event)
    
    @kernel.register.command('gauto')
    # авто ответчик
    async def gauto_handler(event):
        await gemini.gauto_command(event)
    
    @kernel.register.command('gmodel')
    # <model> поменять модель gemini
    async def gmodel_handler(event):
        await gemini.gmodel_command(event)
    
    @kernel.register.command('gprompt')
    # поставить промпт
    async def gprompt_handler(event):
        await gemini.gprompt_command(event)
    
    @kernel.register.command('gres')
    # спросить ещё раз
    async def gres_handler(event):
        await gemini.gres_command(event)
    
    @kernel.register.command('gconfig')
    # значения: api_keys, temperature, max_history_length, use_inline, show_buttons ...
    async def gconfig_handler(event):
        await gemini.gconfig_command(event)
    
    @kernel.register.command('gcfg')
    # что включено сейчас
    async def gcfg_handler(event):
        await gemini.gcfg_command(event)
    
    @kernel.register.command('ghelp')
    # help gemini
    async def ghelp_handler(event):
        await gemini.ghelp_command(event)
    
    kernel.register_callback_handler('gemini_', gemini.callback_handler)
    
    asyncio.create_task(gemini.initialize())
