import base64
import logging
import os
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

load_dotenv()

logger = logging.getLogger(__name__)

_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

_CREDENTIALS_PATH = os.getenv("GMAIL_CREDENTIALS_PATH", "credentials.json")
_TOKEN_PATH = os.getenv("GMAIL_TOKEN_PATH", "token.json")
_EMAIL_BODY_MAX_CHARS = int(os.getenv("EMAIL_BODY_MAX_CHARS", "3000"))


def _authenticate() -> Credentials:
    creds = None
    token_file = Path(_TOKEN_PATH)

    if token_file.exists():
        creds = Credentials.from_authorized_user_file(str(token_file), _SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Abre o navegador interativamente na primeira execução
            flow = InstalledAppFlow.from_client_secrets_file(_CREDENTIALS_PATH, _SCOPES)
            creds = flow.run_local_server(port=0)
        token_file.write_text(creds.to_json(), encoding="utf-8")

    return creds


def _extract_plain_body(payload: dict) -> str:
    """Extrai texto plano do payload do Gmail (recursivo para multipart)."""
    mime_type = payload.get("mimeType", "")

    if mime_type.startswith("multipart"):
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                data = part.get("body", {}).get("data", "")
                if data:
                    return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
            result = _extract_plain_body(part)
            if result:
                return result
    else:
        data = payload.get("body", {}).get("data", "")
        if data:
            return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")

    return ""


def _parse_headers(headers: list[dict]) -> dict:
    result: dict[str, str] = {}
    for h in headers:
        name = h.get("name", "").lower()
        if name in ("date", "from", "subject"):
            result[name] = h.get("value", "")
    return result


def fetch_emails(since: datetime) -> list[dict]:
    """
    Busca e-mails da caixa de entrada recebidos desde `since`.

    Retorna lista de dicts com: message_id, date, from, subject, body.
    O campo `message_id` é o ID do Gmail — usado como chave em retry_counts.
    """
    creds = _authenticate()
    service = build("gmail", "v1", credentials=creds)

    since_ts = int(since.timestamp())
    query = f"in:inbox after:{since_ts}"
    logger.info("Consultando Gmail com query: %s", query)

    message_refs: list[dict] = []
    page_token = None
    while True:
        kwargs: dict = {"userId": "me", "q": query, "maxResults": 500}
        if page_token:
            kwargs["pageToken"] = page_token
        result = service.users().messages().list(**kwargs).execute()
        message_refs.extend(result.get("messages", []))
        page_token = result.get("nextPageToken")
        if not page_token:
            break

    logger.info("%d mensagens encontradas", len(message_refs))

    emails: list[dict] = []
    for ref in message_refs:
        try:
            msg = service.users().messages().get(
                userId="me", id=ref["id"], format="full"
            ).execute()

            headers = _parse_headers(msg.get("payload", {}).get("headers", []))
            body = _extract_plain_body(msg.get("payload", {}))

            emails.append({
                "message_id": ref["id"],
                "date": headers.get("date", ""),
                "from": headers.get("from", ""),
                "subject": headers.get("subject", ""),
                "body": body[:_EMAIL_BODY_MAX_CHARS],
            })
        except Exception as exc:
            logger.warning("Erro ao processar mensagem %s: %s", ref["id"], exc)

    return emails
