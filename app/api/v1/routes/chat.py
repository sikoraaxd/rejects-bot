from fastapi import APIRouter
import json

from app.schemas.analysis import ChatRequest, ChatResponse
from app.services.llm import get_agent
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage


router = APIRouter()


def convert_chat_history(raw_history: list[dict]):
    messages = []

    for item in raw_history:
        role = item.get("role")
        content = item.get("content", "")

        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
        elif role == "system":
            messages.append(SystemMessage(content=content))
        else:
            raise ValueError(f"Unknown role: {role}")

    return messages


@router.post("", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    print(request)
    message = request.messages[-1]['content']
    if not message:
        return ChatResponse(answer="Не получил вопрос пользователя.")
    try:
        context = '\n'.join([f'{k}: {v}' for k, v in json.loads(request.context).items()])
    except Exception as e:
        print(e)
        context = ''
    agent = get_agent(context=context)
    print('message:',message)
    print('context:', context)
    result = agent.invoke({
        "input": message,
        "context": context,
        "chat_history": convert_chat_history(request.messages[:-1])
    })
    print(result)
    answer = result.get("output", str(result))
    answer = answer.split('</think>')[1].strip() if 'think' in answer else answer
    return ChatResponse(answer=answer)
