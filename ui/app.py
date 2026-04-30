import sys
from pathlib import Path
from typing import Any
import json

import requests
import streamlit as st


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.core.settings import settings

BACKEND_URL = settings.backend_url.rstrip("/")


def api_get(path: str) -> Any:
    response = requests.get(f"{BACKEND_URL}{path}", timeout=30)
    response.raise_for_status()
    return response.json()


def api_post(path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{BACKEND_URL}{path}", json=payload, timeout=90)
    response.raise_for_status()
    return response.json()


def get_case_options() -> dict[str, Any]:
    return api_get("/api/v1/cases/options?limit=2000")


def filter_cases(cases: list[dict[str, Any]], filters: dict[str, str]) -> list[dict[str, Any]]:
    return [
        case
        for case in cases
        if all(not value or str(case.get(field, "")) == value for field, value in filters.items())
    ]


def unique_values(cases: list[dict[str, Any]], field: str) -> list[str]:
    return sorted(
        {str(case[field]).strip() for case in cases if str(case[field]).strip()},
        key=str.casefold,
    )


def render_case_sidebar(
    cases: list[dict[str, Any]],
    filter_options: dict[str, list[str]],
) -> dict[str, Any] | None:
    st.sidebar.title("Фильтры")
    st.sidebar.caption(f"Кейсов: {len(cases)}")

    if st.sidebar.button("Обновить таблицу"):
        st.rerun()

    fields = [
        ("project_name", "Проект"),
        ("employee", "Сотрудник"),
        ("technology", "Технология"),
        ("grade", "Грейд"),
        ("source", "Источник"),
        ("date", "Дата"),
    ]
    selected_filters = {
        field: st.session_state.get(f"case_filter_{field}") or ""
        for field, _ in fields
    }

    for field, label in fields:
        key = f"case_filter_{field}"
        option_filters = {
            name: value
            for name, value in selected_filters.items()
            if name != field and value
        }
        available_cases = filter_cases(cases, option_filters)
        options = unique_values(available_cases, field)
        if not option_filters:
            options = filter_options.get(field) or options

        current_value = selected_filters[field]
        if current_value and current_value not in options:
            selected_filters[field] = ""
            st.session_state[key] = None

        selected = st.sidebar.selectbox(
            label,
            options=options,
            index=None,
            placeholder=f"Выберите {label.lower()}",
            key=key,
        )
        selected_filters[field] = selected or ""

    filters = {field: value for field, value in selected_filters.items() if value}
    matching_cases = filter_cases(cases, filters)
    st.sidebar.caption(f"Подходит кейсов: {len(matching_cases)}")

    return filters


def render_chat() -> None:
    st.set_page_config(page_title="Анализ отказов", page_icon="RA", layout="wide")
    st.title("Анализ отказов")

    try:
        case_options = get_case_options()
    except requests.RequestException as error:
        st.error("Не удалось загрузить кейсы")
        st.caption(str(error))
        return

    cases = case_options.get("items", [])
    filter_options = case_options.get("filters", {})
    selected_case = render_case_sidebar(cases, filter_options)

    history = st.session_state.setdefault("chat_history", [])
    for message in history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    prompt = st.chat_input("Спросите по кейсу или по аналитике всей таблицы")
    if not prompt:
        return

    history.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.write(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Анализирую"):
            try:
                response = api_post(
                    "/api/v1/chat",
                    {
                        "messages": history[-20:],
                        "context": json.dumps(selected_case, indent=2, ensure_ascii=False),
                    },
                )
                answer = response["answer"]
            except requests.RequestException as error:
                answer = f"Ошибка обращения к backend: {error}"
        st.write(answer)

    history.append({"role": "assistant", "content": answer})


if __name__ == "__main__":
    render_chat()
