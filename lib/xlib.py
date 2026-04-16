# SPDX-License-Identifier: MIT
# Copyright (c) 2026 MCUB

"""
xlib - MCUB Utility Library

A comprehensive utility library providing common formatting, keyboard generation,
and text manipulation functions for MCUB modules.

Usage in class-style modules: (v1.2.7 version MCUB)
    self.xlib = await self.import_lib("https://raw.githubusercontent.com/hairpin01/repo-MCUB-fork/refs/heads/main/lib/xlib.py")
    text = self.xlib.format_size(1024)
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timedelta
from typing import Any, TYPE_CHECKING

if TYPE_CHECKING:
    from telethon import Button

__all__ = [
    "format_size",
    "format_num",
    "format_duration",
    "format_date",
    "format_delta",
    "format_percent",
    "format_list",
    "truncate",
    "plural",
    "num_word",
    "grid",
    "confirm",
    "pagination",
    "url_button",
    "callback_button",
    "bold",
    "italic",
    "code",
    "link",
    "button",
    "pre",
]

DEFAULT_LOCALE = "en"

Button = None


def _get_button() -> Any:
    global Button
    if Button is None:
        Button = __import__("telethon", fromlist=["Button"]).Button
    return Button


_SIZE_SUFFIXES = {
    "en": ["B", "KB", "MB", "GB", "TB", "PB"],
    "ru": ["Б", "КБ", "МБ", "ГБ", "ТБ", "ПБ"],
}

_MONTHS = {
    "en": [
        "Jan",
        "Feb",
        "Mar",
        "Apr",
        "May",
        "Jun",
        "Jul",
        "Aug",
        "Sep",
        "Oct",
        "Nov",
        "Dec",
    ],
    "ru": [
        "янв",
        "фев",
        "мар",
        "апр",
        "мая",
        "июн",
        "июл",
        "авг",
        "сен",
        "окт",
        "ноя",
        "дек",
    ],
}

_MONTHS_FULL = {
    "en": [
        "January",
        "February",
        "March",
        "April",
        "May",
        "June",
        "July",
        "August",
        "September",
        "October",
        "November",
        "December",
    ],
    "ru": [
        "января",
        "февраля",
        "марта",
        "апреля",
        "мая",
        "июня",
        "июля",
        "августа",
        "сентября",
        "октября",
        "ноября",
        "декабря",
    ],
}


def format_size(bytes_value: int, locale: str = DEFAULT_LOCALE) -> str:
    """
    Format bytes to human-readable size.

    Args:
        bytes_value: Number of bytes.
        locale: Locale for suffix ('en' or 'ru').

    Returns:
        Formatted string like "1.5 KB" or "1.5 МБ".

    Examples:
        1024 -> "1 KB"
        1536 -> "1.5 KB"
        1048576 -> "1 MB"
    """
    if bytes_value < 0:
        return "0 B"

    suffixes = _SIZE_SUFFIXES.get(locale, _SIZE_SUFFIXES["en"])
    size = float(bytes_value)
    idx = 0

    while size >= 1024 and idx < len(suffixes) - 1:
        size /= 1024
        idx += 1

    if idx == 0:
        return f"{int(size)} {suffixes[idx]}"
    return f"{size:.2f} {suffixes[idx]}"


def format_num(value: int | float, sep: str = " ") -> str:
    """
    Format number with thousands separator.

    Args:
        value: Number to format.
        sep: Separator character (default: space).

    Returns:
        Formatted string like "1 234 567".

    Examples:
        1234567 -> "1 234 567"
        1234567.89 -> "1 234 567.89"
    """
    if isinstance(value, int):
        return f"{value:,}".replace(",", sep)
    return f"{value:,}".replace(",", sep)


def format_duration(
    seconds: int | float,
    short: bool = False,
    locale: str = DEFAULT_LOCALE,
) -> str:
    """
    Format duration in seconds to human-readable string.

    Args:
        seconds: Duration in seconds.
        short: Use short format (h/m/s instead of hours/minutes/seconds).
        locale: Locale for labels.

    Returns:
        Formatted duration string.

    Examples:
        3661 -> "1h 1m 1s" or "1ч 1м 1с"
    """
    if seconds < 0:
        return "0s"

    if short:
        labels = {"en": ["d", "h", "m", "s"], "ru": ["д", "ч", "м", "с"]}
    else:
        labels = {
            "en": ["day", "hour", "minute", "second"],
            "ru": ["день", "час", "минута", "секунда"],
        }

    loc_labels = labels.get(locale, labels["en"])
    parts = []

    days = int(seconds // 86400)
    hours = int((seconds % 86400) // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)

    if days > 0:
        parts.append(f"{days}{loc_labels[0]}")
    if hours > 0:
        parts.append(f"{hours}{loc_labels[1]}")
    if minutes > 0:
        parts.append(f"{minutes}{loc_labels[2]}")
    if secs > 0 or not parts:
        parts.append(f"{secs}{loc_labels[3]}")

    return " ".join(parts)


def format_date(
    timestamp: int | float,
    fmt: str = "%d %b %Y",
    locale: str = DEFAULT_LOCALE,
) -> str:
    """
    Format timestamp to date string.

    Args:
        timestamp: Unix timestamp.
        fmt: Format string (strftime style). Use %b for short month, %B for full month.
        locale: Locale for month names.

    Returns:
        Formatted date string.

    Examples:
        format_date(1234567890) -> "14 Feb 2009"
        format_date(1234567890, "%d %B %Y") -> "14 February 2009"
        format_date(1234567890, "%d %b %Y", "ru") -> "14 фев 2009"
    """
    dt = datetime.fromtimestamp(timestamp)
    months_short = _MONTHS.get(locale, _MONTHS["en"])
    months_full = _MONTHS_FULL.get(locale, _MONTHS_FULL["en"])

    result = fmt
    result = re.sub(r"%b", months_short[dt.month - 1], result)
    result = re.sub(r"%B", months_full[dt.month - 1], result)

    return dt.strftime(result)


def format_delta(
    timestamp: int | float,
    locale: str = DEFAULT_LOCALE,
    short: bool = False,
) -> str:
    """
    Format time delta (relative time like "5 minutes ago").

    Args:
        timestamp: Unix timestamp.
        locale: Locale for labels.
        short: Use short format.

    Returns:
        Relative time string.

    Examples:
        format_delta(time.time() - 300) -> "5 minutes ago" or "5 мин назад"
    """
    now = time.time()
    diff = now - timestamp

    if diff < 0:
        if short:
            return "now"
        return "just now"

    if locale == "ru":
        if short:
            ago = "назад"
        else:
            ago = "назад"
        second = "секунда"
        seconds = "секунд"
        minute = "минута"
        minutes = "минут"
        hour = "час"
        hours = "часов"
        day = "день"
        days = "дней"
        month = "месяц"
        months = "месяцев"
        year = "год"
        years = "лет"
    else:
        if short:
            ago = "ago"
        else:
            ago = "ago"
        second = "second"
        seconds = "seconds"
        minute = "minute"
        minutes = "minutes"
        hour = "hour"
        hours = "hours"
        day = "day"
        days = "days"
        month = "month"
        months = "months"
        year = "year"
        years = "years"

    if diff < 60:
        n = int(diff)
        w = plural(n, second, seconds, seconds)
        return f"{n} {w} {ago}"

    if diff < 3600:
        n = int(diff / 60)
        w = plural(n, minute, minutes, minutes)
        return f"{n} {w} {ago}"

    if diff < 86400:
        n = int(diff / 3600)
        w = plural(n, hour, hours, hours)
        return f"{n} {w} {ago}"

    if diff < 2592000:
        n = int(diff / 86400)
        w = plural(n, day, days, days)
        return f"{n} {w} {ago}"

    if diff < 31536000:
        n = int(diff / 2592000)
        w = plural(n, month, months, months)
        return f"{n} {w} {ago}"

    n = int(diff / 31536000)
    w = plural(n, year, years, years)
    return f"{n} {w} {ago}"


def format_percent(value: int | float, total: int | float, decimals: int = 1) -> str:
    """
    Format percentage.

    Args:
        value: Part value.
        total: Total value.
        decimals: Number of decimal places.

    Returns:
        Formatted percentage string.

    Examples:
        format_percent(25, 100) -> "25.0%"
    """
    if total == 0:
        return "0%"
    pct = (value / total) * 100
    if decimals == 0:
        return f"{int(pct)}%"
    return f"{pct:.{decimals}f}%"


def format_list(
    items: list[str],
    sep: str = ", ",
    last: str = " and ",
) -> str:
    """
    Format list with separator and "and" before last item.

    Args:
        items: List of items.
        sep: Separator between items.
        last: Separator before last item.

    Returns:
        Formatted list string.

    Examples:
        ["a", "b", "c"] -> "a, b and c"
    """
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return f"{sep.join(items[:-1])}{last}{items[-1]}"


def truncate(text: str, max_len: int, suffix: str = "...") -> str:
    """
    Truncate text to maximum length.

    Args:
        text: Text to truncate.
        max_len: Maximum length.
        suffix: Suffix to append when truncated.

    Returns:
        Truncated string.

    Examples:
        truncate("hello world", 8) -> "hello..."
    """
    if len(text) <= max_len:
        return text
    return text[: max_len - len(suffix)] + suffix


def plural(n: int, one: str, few: str, many: str) -> str:
    """
    Pluralize word based on number (Russian style).

    Args:
        n: Number.
        one: Singular form ("яблоко").
        few: Few form ("яблока").
        many: Many form ("яблок").

    Returns:
        Correct word form.

    Examples:
        plural(1, "яблоко", "яблока", "яблок") -> "яблоко"
        plural(2, "яблоко", "яблока", "яблок") -> "яблока"
        plural(5, "яблоко", "яблока", "яблок") -> "яблок"
    """
    n = abs(n) % 100
    if 11 <= n <= 14:
        return many
    n = n % 10
    if n == 1:
        return one
    if 2 <= n <= 4:
        return few
    return many


def num_word(n: int, one: str, few: str, many: str) -> str:
    """
    Same as plural() - kept for backwards compatibility.
    """
    return plural(n, one, few, many)


def emoji_count(n: int, item: str = " item") -> str:
    """
    Format number with emoji suffix and plural.

    Args:
        n: Number.
        item: Item name.

    Returns:
        Formatted count string.

    Examples:
        emoji_count(5, "apple") -> "5 apples"
    """
    return f"{n}{item}"


def grid(
    buttons: list["Button"],
    cols: int = 2,
) -> list[list["Button"]]:
    """
    Arrange buttons in grid.

    Args:
        buttons: List of telethon Button objects.
        cols: Number of columns.

    Returns:
        2D list of buttons.

    Examples:
        grid([btn1, btn2, btn3, btn4], 2) -> [[btn1, btn2], [btn3, btn4]]
    """
    result = []
    for i in range(0, len(buttons), cols):
        result.append(buttons[i : i + cols])
    return result


def confirm(
    yes_text: str = "Yes",
    no_text: str = "No",
    yes_data: bytes = b"yes",
    no_data: bytes = b"no",
) -> list[list["Button"]]:
    """
    Create confirm keyboard (Yes/No buttons).

    Args:
        yes_text: Yes button text.
        no_text: No button text.
        yes_data: Yes callback data.
        no_data: No callback data.

    Returns:
        2D list of telethon Button objects.

    Examples:
        confirm() -> [[Button.inline("Yes", b"yes"), Button.inline("No", b"no")]]
    """
    B = _get_button()
    return [[B.inline(yes_text, yes_data), B.inline(no_text, no_data)]]


def pagination(
    current: int,
    total: int,
    prefix: str = "page",
) -> list[list["Button"]]:
    """
    Create pagination keyboard.

    Args:
        current: Current page number.
        total: Total pages.
        prefix: Callback data prefix.

    Returns:
        2D list of telethon Button objects.
    """
    buttons = []
    if total <= 1:
        return buttons

    B = _get_button()
    if current > 1:
        data = f"{prefix}:{current - 1}".encode()
        buttons.append(B.inline(f"{prefix}:{current - 1}", data))
    if current < total:
        data = f"{prefix}:{current + 1}".encode()
        buttons.append(B.inline(f"{prefix}:{current + 1}", data))

    return grid(buttons, 2)


def url_button(text: str, url: str, new_tab: bool = False) -> "Button":
    """
    Create URL button (telethon Button.url).

    Args:
        text: Button text.
        url: URL to open.
        new_tab: Open in new tab (for inline buttons).

    Returns:
        telethon Button object.

    Examples:
        url_button("Google", "https://google.com")
        url_button("Open", "https://example.com", new_tab=True)
    """
    B = _get_button()
    return B.url(text, url, new_tab=new_tab)


def callback_button(text: str, data: bytes) -> "Button":
    """
    Create callback button (telethon Button.inline).

    Args:
        text: Button text.
        data: Callback data (bytes).

    Returns:
        telethon Button object.

    Examples:
        callback_button("Click", b"action:click")
    """
    B = _get_button()
    return B.inline(text, data)


def bold(text: str) -> str:
    """
    Format text as bold.

    Args:
        text: Text to format.

    Returns:
        HTML bold string.

    Examples:
        bold("hello") -> "<b>hello</b>"
    """
    return f"<b>{text}</b>"


def italic(text: str) -> str:
    """
    Format text as italic.

    Args:
        text: Text to format.

    Returns:
        HTML italic string.

    Examples:
        italic("hello") -> "<i>hello</i>"
    """
    return f"<i>{text}</i>"


def code(text: str, lang: str | None = None) -> str:
    """
    Format text as code.

    Args:
        text: Text to format.
        lang: Optional language for syntax highlighting.

    Returns:
        HTML code string.

    Examples:
        code("print('hello')") -> "<code>print('hello')</code>"
        code("print('hello')", "python") -> "<code language=\"python\">print('hello')</code>"
    """
    if lang:
        return f'<code language="{lang}">{text}</code>'
    return f"<code>{text}</code>"


def link(url: str, text: str) -> str:
    """
    Create HTML link.

    Args:
        url: Link URL.
        text: Link text.

    Returns:
        HTML link string.

    Examples:
        link("https://google.com", "Google") -> '<a href="https://google.com">Google</a>'
    """
    return f'<a href="{url}">{text}</a>'


def button(text: str, data: bytes | None = None, url: str | None = None) -> "Button":
    """
    Create button (telethon Button).

    Args:
        text: Button text.
        data: Callback data (bytes) - if URL button not used.
        url: URL - if URL button.

    Returns:
        telethon Button object.

    Examples:
        button("Click", data=b"action:click") -> Button.inline
        button("Google", url="https://google.com") -> Button.url
    """
    if url:
        return url_button(text, url)
    return callback_button(text, data)


def pre(text: str) -> str:
    """
    Format text as preformatted (code block).

    Args:
        text: Text to format.

    Returns:
        HTML preformatted string.

    Examples:
        pre("code here") -> "<pre>code here</pre>"
    """
    return f"<pre>{text}</pre>"
