from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field, HttpUrl

from api.agent_loop import run_chat

router = APIRouter()

DEFAULT_BASE_URL = "https://api.xkiro.com/v1"
DEFAULT_MODEL = "cohere/command-a"


class Message(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=20_000)


class ChatRequest(BaseModel):
    api_key: str = Field(min_length=8, max_length=256)
    base_url: str = Field(default=DEFAULT_BASE_URL, max_length=256)
    model: str = Field(default=DEFAULT_MODEL, max_length=128)
    messages: list[Message] = Field(min_length=1, max_length=40)


class ChatStep(BaseModel):
    tool: str
    args: dict
    result_summary: str


class ChatResponse(BaseModel):
    reply: str
    steps: list[ChatStep]


@router.post("/run", response_model=ChatResponse)
async def run_agent(request: Request, payload: ChatRequest, response: Response) -> ChatResponse:
    if not payload.api_key.startswith(("sk-", "mstrl_")):
        raise HTTPException(status_code=422, detail="Format API key tidak dikenali.")
    try:
        reply, steps = await run_chat(
            base_url=payload.base_url,
            api_key=payload.api_key,
            model=payload.model,
            messages=[item.model_dump() for item in payload.messages],
        )
    except Exception as error:
        raise HTTPException(status_code=502, detail=f"Gateway gagal: {type(error).__name__}") from error
    response.headers["Cache-Control"] = "no-store"
    return ChatResponse(reply=reply, steps=[ChatStep(**step) for step in steps])
