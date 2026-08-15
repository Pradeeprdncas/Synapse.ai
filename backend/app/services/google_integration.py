import base64
import hashlib
import json
import os
import secrets
from datetime import datetime, timedelta
from email.message import EmailMessage
from urllib.parse import urlencode
from pathlib import Path

import requests
from dotenv import load_dotenv
from cryptography.fernet import Fernet, InvalidToken
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models.atlas_agent import GoogleConnection, NotificationDelivery, NotificationPreference, OAuthState
from app.services.assignment_context import attachment_details, render_assignment_email

load_dotenv(Path(__file__).resolve().parents[3] / ".env")

AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_URL = "https://oauth2.googleapis.com/token"
SCOPES = ["openid", "email", "https://www.googleapis.com/auth/gmail.send", "https://www.googleapis.com/auth/documents.readonly"]


def config():
    values = {
        "client_id": os.getenv("GOOGLE_CLIENT_ID") or os.getenv("GMAIL_CLIENT_ID"),
        "client_secret": os.getenv("GOOGLE_CLIENT_SECRET") or os.getenv("GMAIL_CLIENT_SECRET"),
        "redirect_uri": os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/google/oauth/callback"),
        "success_url": os.getenv("GOOGLE_FRONTEND_SUCCESS_URL", "http://localhost:8080/settings?google=connected"),
    }
    if not values["client_id"] or not values["client_secret"]:
        raise HTTPException(503, "Google OAuth is not configured")
    return values


def cipher():
    key = os.getenv("GOOGLE_TOKEN_ENCRYPTION_KEY")
    if not key:
        raise HTTPException(503, "GOOGLE_TOKEN_ENCRYPTION_KEY is required for encrypted token storage")
    try: return Fernet(key.encode())
    except ValueError: raise HTTPException(503, "GOOGLE_TOKEN_ENCRYPTION_KEY must be a valid Fernet key")


def encrypt(value: str | None):
    return cipher().encrypt(value.encode()).decode() if value else None


def decrypt(value: str | None):
    if not value: return None
    try: return cipher().decrypt(value.encode()).decode()
    except InvalidToken: raise HTTPException(503, "Stored Google token cannot be decrypted")


def create_authorization(db: Session, user_id: int):
    cfg = config(); state = secrets.token_urlsafe(32); state_hash = hashlib.sha256(state.encode()).hexdigest()
    db.add(OAuthState(state_hash=state_hash, user_id=user_id, expires_at=datetime.utcnow() + timedelta(minutes=10))); db.commit()
    params = {"client_id": cfg["client_id"], "redirect_uri": cfg["redirect_uri"], "response_type": "code",
        "scope": " ".join(SCOPES), "access_type": "offline", "prompt": "consent", "state": state,
        "include_granted_scopes": "true"}
    return f"{AUTH_URL}?{urlencode(params)}"


def consume_state(db: Session, state: str):
    digest = hashlib.sha256(state.encode()).hexdigest()
    row = db.query(OAuthState).filter_by(state_hash=digest).first()
    if not row or row.consumed_at or row.expires_at < datetime.utcnow(): raise HTTPException(400, "Invalid or expired OAuth state")
    row.consumed_at = datetime.utcnow(); db.commit(); return row.user_id


def exchange_code(db: Session, state: str, code: str):
    cfg = config(); user_id = consume_state(db, state)
    response = requests.post(TOKEN_URL, data={"client_id": cfg["client_id"], "client_secret": cfg["client_secret"],
        "code": code, "grant_type": "authorization_code", "redirect_uri": cfg["redirect_uri"]}, timeout=20)
    if not response.ok: raise HTTPException(400, "Google token exchange failed")
    token = response.json(); access = token.get("access_token")
    if not access: raise HTTPException(400, "Google callback did not return an access token")
    profile_response = requests.get("https://openidconnect.googleapis.com/v1/userinfo", headers={"Authorization": f"Bearer {access}"}, timeout=20)
    email = profile_response.json().get("email") if profile_response.ok else None
    row = db.query(GoogleConnection).filter_by(user_id=user_id).first() or GoogleConnection(user_id=user_id)
    row.email = email; row.scopes_json = json.dumps((token.get("scope") or "").split())
    row.encrypted_access_token = encrypt(access)
    if token.get("refresh_token"): row.encrypted_refresh_token = encrypt(token["refresh_token"])
    row.token_expires_at = datetime.utcnow() + timedelta(seconds=int(token.get("expires_in", 3600))); row.updated_at = datetime.utcnow()
    db.add(row); db.commit(); return row


def access_token(db: Session, user_id: int):
    row = db.query(GoogleConnection).filter_by(user_id=user_id).first()
    if not row: raise HTTPException(409, "Google account is not connected")
    if row.token_expires_at and row.token_expires_at > datetime.utcnow() + timedelta(minutes=2): return decrypt(row.encrypted_access_token)
    refresh = decrypt(row.encrypted_refresh_token)
    if not refresh: raise HTTPException(409, "Google connection requires reauthorization")
    cfg = config(); response = requests.post(TOKEN_URL, data={"client_id": cfg["client_id"], "client_secret": cfg["client_secret"], "refresh_token": refresh, "grant_type": "refresh_token"}, timeout=20)
    if not response.ok: raise HTTPException(502, "Google token refresh failed")
    token = response.json(); row.encrypted_access_token = encrypt(token["access_token"]); row.token_expires_at = datetime.utcnow() + timedelta(seconds=int(token.get("expires_in", 3600))); row.updated_at = datetime.utcnow(); db.commit()
    return token["access_token"]


def send_assignment_email(db: Session, sender_user_id: int, context: dict):
    recipient_user_id = context["assignee"]["id"]; project_id = context["project"]["id"]; task_id = context["task"]["id"]
    preference = db.query(NotificationPreference).filter_by(user_id=recipient_user_id).first()
    if preference and not preference.task_assignment_email: return {"status": "DISABLED"}
    key = f"assignment:{task_id}:{recipient_user_id}:initial"
    existing = db.query(NotificationDelivery).filter_by(idempotency_key=key).first()
    if existing and existing.status in ("SENT", "PENDING"): return {"status": existing.status, "deliveryId": existing.id, "duplicatePrevented": True}
    delivery = existing or NotificationDelivery(project_id=project_id, user_id=recipient_user_id, task_id=task_id, kind="TASK_ASSIGNMENT", idempotency_key=key)
    delivery.status = "PENDING"; delivery.safe_error = None; db.add(delivery); db.commit(); db.refresh(delivery)
    message = EmailMessage(); message["To"] = context["assignee"]["email"]; message["Subject"] = f"Atlas — New task assigned: {context['task']['title']}"
    plain, html = render_assignment_email(context); message.set_content(plain); message.add_alternative(html, subtype="html")
    attached = []
    for document in context["documents"]:
        details = attachment_details(document)
        if details:
            with open(details["path"], "rb") as source: message.add_attachment(source.read(), maintype=details["maintype"], subtype=details["subtype"], filename=details["filename"])
            attached.append(document["id"])
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        response = requests.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send", headers={"Authorization": f"Bearer {access_token(db, sender_user_id)}", "Content-Type": "application/json"}, json={"raw": encoded}, timeout=20)
        response.raise_for_status(); delivery.status = "SENT"; delivery.provider_message_id = response.json().get("id")
    except Exception as exc:
        delivery.status = "FAILED"; delivery.safe_error = type(exc).__name__; db.commit()
        return {"status": "FAILED", "deliveryId": delivery.id, "safeError": type(exc).__name__, "attachments": attached}
    db.commit(); return {"status": delivery.status, "deliveryId": delivery.id, "attachments": attached,
        "requirementsShared": len(context["requirements"]), "documentsShared": len(context["documents"])}


def send_gmail_message(db: Session, sender_user_id: int, message: EmailMessage):
    """Send an explicitly constructed transactional email through the connected user's Gmail account."""
    encoded = base64.urlsafe_b64encode(message.as_bytes()).decode()
    try:
        response = requests.post("https://gmail.googleapis.com/gmail/v1/users/me/messages/send",
            headers={"Authorization": f"Bearer {access_token(db, sender_user_id)}", "Content-Type": "application/json"},
            json={"raw": encoded}, timeout=20)
        response.raise_for_status()
        return {"status": "SENT", "providerMessageId": response.json().get("id")}
    except Exception as exc:
        return {"status": "FAILED", "safeError": type(exc).__name__}


def fetch_google_doc(db: Session, user_id: int, document_id: str):
    if not document_id or not all(ch.isalnum() or ch in "-_" for ch in document_id): raise HTTPException(400, "Invalid Google document ID")
    response = requests.get(f"https://docs.googleapis.com/v1/documents/{document_id}", headers={"Authorization": f"Bearer {access_token(db, user_id)}"}, timeout=20)
    if not response.ok: raise HTTPException(502, "Google Doc import failed")
    data = response.json(); parts = []
    for item in data.get("body", {}).get("content", []):
        for element in item.get("paragraph", {}).get("elements", []): parts.append(element.get("textRun", {}).get("content", ""))
    return data.get("title", "Google Doc"), "".join(parts)
