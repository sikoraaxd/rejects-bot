from fastapi import APIRouter
import json

from app.schemas.analysis import ChatRequest, ChatResponse
from app.services.llm import get_agent

router = APIRouter()


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
    result = agent.invoke({"input": message})
    print(result)
    answer = result.get("output", str(result))
    answer = answer.split('</think>')[1].strip() if 'think' in answer else answer
    return ChatResponse(answer=answer)
