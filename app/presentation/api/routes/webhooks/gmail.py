import json

from fastapi import APIRouter, Depends, HTTPException
from google.genai.errors import ClientError
from googleapiclient.errors import HttpError

from app.application.dtos.gmail.gmail_webhook_dto import GmailWebhookDTO
from app.application.use_cases.process_gmail_event import ProcessGmailEventUseCase
from app.presentation.api.dependencies.use_cases import (
    get_process_gmail_event_use_case,
)

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/gmail")
async def gmail_webhook(
    payload: GmailWebhookDTO,
    use_case: ProcessGmailEventUseCase = Depends(
        get_process_gmail_event_use_case,
    ),
):
    try:
        result = await use_case.execute(payload.model_dump())
    except ClientError as error:
        raise _gemini_http_error(error) from error
    except HttpError as error:
        raise _gmail_http_error(error) from error

    return {"status": "received", **result}


@router.post("/gmail/process")
async def process_gmail_inbox(
    use_case: ProcessGmailEventUseCase = Depends(
        get_process_gmail_event_use_case,
    ),
):
    try:
        result = await use_case.execute()
    except ClientError as error:
        raise _gemini_http_error(error) from error
    except HttpError as error:
        raise _gmail_http_error(error) from error

    return {"status": "processed", **result}


@router.post("/gmail/process-new")
async def process_new_gmail_messages(
    use_case: ProcessGmailEventUseCase = Depends(
        get_process_gmail_event_use_case,
    ),
):
    try:
        result = await use_case.process_new_messages()
    except ClientError as error:
        raise _gemini_http_error(error) from error
    except HttpError as error:
        raise _gmail_http_error(error) from error

    return {"status": "processed", **result}


@router.post("/gmail/process-inbox")
async def process_all_gmail_inbox(
    archive: bool = False,
    max_messages: int | None = None,
    max_new_classifications: int | None = None,
    use_case: ProcessGmailEventUseCase = Depends(
        get_process_gmail_event_use_case,
    ),
):
    try:
        result = await use_case.process_all_inbox_messages(
            archive=archive,
            max_messages=max_messages,
            max_new_classifications=max_new_classifications,
        )
    except ClientError as error:
        raise _gemini_http_error(error) from error
    except HttpError as error:
        raise _gmail_http_error(error) from error

    return {"status": "processed", **result}


@router.post("/gmail/watch")
async def watch_gmail_inbox(
    use_case: ProcessGmailEventUseCase = Depends(
        get_process_gmail_event_use_case,
    ),
):
    try:
        result = await use_case.watch_mailbox()
    except HttpError as error:
        raise _gmail_http_error(error) from error

    return {"status": "watching", **result}


def _gemini_http_error(error: ClientError) -> HTTPException:
    error_text = str(error)

    if "API key not valid" in error_text:
        return HTTPException(
            status_code=502,
            detail=(
                "Gemini rechazo la API key. Revisa GEMINI_API_KEY o API_KEY "
                "en .env y confirma que pertenezca a Google AI Studio/Gemini."
            ),
        )

    if "no longer available" in error_text or "NOT_FOUND" in error_text:
        return HTTPException(
            status_code=502,
            detail=(
                "El modelo configurado en GEMINI_MODEL no esta disponible "
                "para esta API key. Usa gemini-flash-latest u otro modelo habilitado."
            ),
        )

    return HTTPException(
        status_code=502,
        detail="Gemini no pudo clasificar el correo.",
    )


def _gmail_http_error(error: HttpError) -> HTTPException:
    error_message = _extract_google_error_message(error)
    error_text = f"{error} {error_message}"

    if "gmail-api-push@system.gserviceaccount.com" in error_text:
        return HTTPException(
            status_code=502,
            detail=(
                "Gmail no puede publicar en el topic Pub/Sub. Dale rol "
                "Pub/Sub Publisher a gmail-api-push@system.gserviceaccount.com."
            ),
        )

    if "startHistoryId" in error_text or "HistoryId" in error_text:
        return HTTPException(
            status_code=409,
            detail=(
                "El historyId guardado ya no es valido. Ejecuta de nuevo "
                "POST /webhooks/gmail/watch para reiniciar la escucha."
            ),
        )

    return HTTPException(
        status_code=502,
        detail=f"Gmail API no pudo completar la operacion: {error_message}",
    )


def _extract_google_error_message(error: HttpError) -> str:
    try:
        content = json.loads(error.content.decode("utf-8"))
    except (AttributeError, UnicodeDecodeError, json.JSONDecodeError):
        return str(error)

    return content.get("error", {}).get("message", str(error))
