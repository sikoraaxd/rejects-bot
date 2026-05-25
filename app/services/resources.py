import json
import re
from dataclasses import dataclass
from functools import lru_cache
from html import unescape
from io import BytesIO, StringIO
from pathlib import Path
from typing import Iterable
from urllib.parse import urlparse

import pandas as pd
import requests
from fastapi import UploadFile

from app.services.sheets import SheetsClient


MAX_RESOURCE_BYTES = 500 * 1024 * 1024
MAX_RESOURCE_CHARS = 4_000_000
URL_RE = re.compile(r"https?://[^\s<>()\"']+", re.IGNORECASE)


@dataclass
class ResourceText:
    title: str
    text: str
    source_type: str


def extract_urls(text: str) -> list[str]:
    urls = []
    for match in URL_RE.findall(text or ""):
        url = match.rstrip(".,;:!?)]}")
        if url not in urls:
            urls.append(url)
    return urls


def format_resource_context(resources: Iterable[ResourceText]) -> str:
    parts = []
    for resource in resources:
        text = _limit_text(resource.text)
        if text:
            parts.append(
                f"Источник: {resource.title}\n"
                f"Тип: {resource.source_type}\n"
                f"Содержимое:\n{text}"
            )
    return "\n\n---\n\n".join(parts)


async def extract_uploaded_files(files: list[UploadFile]) -> list[ResourceText]:
    resources = []
    for file in files:
        content = await file.read(MAX_RESOURCE_BYTES + 1)
        if len(content) > MAX_RESOURCE_BYTES:
            resources.append(
                ResourceText(
                    title=file.filename or "uploaded-file",
                    text="Файл слишком большой для обработки.",
                    source_type="file",
                )
            )
            continue

        resources.append(
            ResourceText(
                title=file.filename or "uploaded-file",
                text=extract_file_text(file.filename or "", content, file.content_type or ""),
                source_type="file",
            )
        )
    return resources


def extract_url_resources(message: str) -> list[ResourceText]:
    return [fetch_url_text(url) for url in extract_urls(message)]


def extract_file_text(filename: str, content: bytes, content_type: str = "") -> str:
    suffix = Path(filename).suffix.lower()
    content_type = content_type.lower()

    try:
        if suffix in {".xlsx", ".xls"}:
            return _extract_excel(content)
        if suffix == ".csv" or "csv" in content_type:
            return _extract_csv(content)
        if suffix == ".json" or "json" in content_type:
            return _extract_json(content)
        if _looks_like_text(content_type, suffix):
            return _decode_text(content)
    except Exception as error:
        return f"Не удалось извлечь текст из файла: {error}"

    return (
        "Формат файла пока не поддерживается для извлечения текста. "
        "Поддерживаются txt, md, csv, json, xlsx и xls."
    )


@lru_cache
def get_sheets_client() -> SheetsClient:
    return SheetsClient()


def fetch_url_text(url: str) -> ResourceText:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        return ResourceText(title=url, text="Неподдерживаемая схема ссылки.", source_type="url")

    try:
        if _is_google_sheet_url(parsed):
            text = get_sheets_client().extract_excel_data(url)
            return ResourceText(title=url, text=text, source_type="google-sheet")

        response = requests.get(
            url,
            timeout=15,
            headers={"User-Agent": "rejects-analyzer/0.1"},
            stream=True,
        )
        response.raise_for_status()

        content = bytearray()
        for chunk in response.iter_content(chunk_size=64 * 1024):
            content.extend(chunk)
            if len(content) > MAX_RESOURCE_BYTES:
                break

        content_type = response.headers.get("content-type", "").lower()
        title = _url_title(url, response.url)
        if "text/html" in content_type:
            text = _html_to_text(_decode_text(bytes(content)))
        elif "json" in content_type:
            text = _extract_json(bytes(content))
        elif "csv" in content_type:
            text = _extract_csv(bytes(content))
        elif _looks_like_text(content_type, Path(parsed.path).suffix.lower()):
            text = _decode_text(bytes(content))
        else:
            text = (
                "Ссылка доступна, но тип контента не поддерживается для извлечения: "
                f"{content_type or 'unknown'}."
            )

        return ResourceText(title=title, text=text, source_type="url")
    except Exception as error:
        return ResourceText(title=url, text=f"Не удалось загрузить ссылку: {error}", source_type="url")


def _extract_excel(content: bytes) -> str:
    sheets = pd.read_excel(BytesIO(content), sheet_name=None, engine="openpyxl")
    parts = []
    for sheet_name, frame in sheets.items():
        if frame.empty:
            continue
        frame = frame.fillna("").head(200)
        parts.append(f"Лист: {sheet_name}\n{frame.to_csv(index=False)}")
    return "\n\n".join(parts)


def _extract_csv(content: bytes) -> str:
    text = _decode_text(content)
    try:
        frame = pd.read_csv(StringIO(text)).fillna("").head(500)
        return frame.to_csv(index=False)
    except Exception:
        return text


def _extract_json(content: bytes) -> str:
    data = json.loads(_decode_text(content))
    return json.dumps(data, ensure_ascii=False, indent=2)


def _decode_text(content: bytes) -> str:
    for encoding in ("utf-8", "utf-8-sig", "cp1251", "latin-1"):
        try:
            return _limit_text(content.decode(encoding))
        except UnicodeDecodeError:
            continue
    return _limit_text(content.decode("utf-8", errors="replace"))


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style).*?>.*?</\1>", " ", html)
    html = re.sub(r"(?s)<[^>]+>", " ", html)
    html = unescape(html)
    html = re.sub(r"\s+", " ", html)
    return _limit_text(html.strip())


def _is_google_sheet_url(parsed_url) -> bool:
    return parsed_url.netloc in {"docs.google.com", "drive.google.com"} and (
        "/spreadsheets/" in parsed_url.path
        or "/file/" in parsed_url.path
    )


def _looks_like_text(content_type: str, suffix: str) -> bool:
    text_suffixes = {
        ".txt",
        ".md",
        ".log",
        ".py",
        ".js",
        ".ts",
        ".html",
        ".css",
        ".xml",
        ".yaml",
        ".yml",
    }
    return content_type.startswith("text/") or suffix in text_suffixes


def _limit_text(text: str) -> str:
    text = text.strip()
    if len(text) <= MAX_RESOURCE_CHARS:
        return text
    return text[:MAX_RESOURCE_CHARS] + "\n\n[Текст обрезан из-за ограничения размера.]"


def _url_title(original_url: str, final_url: str) -> str:
    if original_url == final_url:
        return original_url
    return f"{original_url} -> {final_url}"
