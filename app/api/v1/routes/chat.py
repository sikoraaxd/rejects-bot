import json

from fastapi import APIRouter, File, Form, UploadFile
from app.schemas.analysis import ChatRequest, ChatResponse
from app.services.llm import get_agent
from app.services.resources import (
    extract_uploaded_files,
    extract_url_resources,
    format_resource_context,
)
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


router = APIRouter()


def convert_chat_history(raw_history: list[dict]):
    messages = []

    for item in raw_history:
        role = item.get("role")
        content = item.get("content", "")
        resource_context = item.get("resource_context", "")
        if resource_context:
            content = f"{content}\n\nКонтекст из вложений и ссылок:\n{resource_context}"

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        else:
            raise ValueError(f"Unknown role: {role}")

    return messages


async def build_chat_response(
    messages: list[dict],
    context_raw: str = "",
    files: list[UploadFile] | None = None,
) -> ChatResponse:
    if not messages:
        return ChatResponse(answer="Не получил вопрос пользователя.")

    message = messages[-1].get("content", "")
    if not message and not files:
        return ChatResponse(answer="Не получил вопрос пользователя.")

    resource_context = format_resource_context(
        [
            *extract_url_resources(message),
            *(await extract_uploaded_files(files or [])),
        ]
    )

    try:
        context = "\n".join([f"{k}: {v}" for k, v in json.loads(context_raw).items()])
    except Exception as e:
        print(e)
        context = ""

    if resource_context:
        context = f"{context}\n\nКонтекст из вложений и ссылок:\n{resource_context}".strip()

    agent = get_agent(context=context)
    agent_input = message or "Проанализируй прикрепленные файлы."
    if resource_context:
        agent_input = f"{agent_input}\n\nКонтекст из вложений и ссылок:\n{resource_context}"

    print("message:", agent_input)
    print("context:", context)
    result = agent.invoke(
        {
            "input": agent_input,
            "context": context,
            "chat_history": convert_chat_history(messages[:-1]),
        }
    )
    print(result)
    answer = result.get("output", str(result))
    answer = answer.split("</think>")[1].strip() if "think" in answer else answer
    return ChatResponse(answer=answer, resource_context=resource_context)


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    print(request)
    return await build_chat_response(messages=request.messages, context_raw=request.context)


@router.post("/multipart", response_model=ChatResponse)
async def chat_multipart(
    messages: str = Form(...),
    context: str = Form(default=""),
    files: list[UploadFile] = File(default=[]),
) -> ChatResponse:
    parsed_messages = json.loads(messages)
    return await build_chat_response(
        messages=parsed_messages,
        context_raw=context,
        files=files,
    )
