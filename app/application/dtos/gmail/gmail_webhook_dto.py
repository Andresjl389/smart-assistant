from pydantic import BaseModel


class PubSubMessageDTO(BaseModel):
    data: str
    messageId: str | None = None
    publishTime: str | None = None


class GmailWebhookDTO(BaseModel):
    message: PubSubMessageDTO
    subscription: str
