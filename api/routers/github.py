"""GET /github/labels, POST /github/issues – GitHub-Integration fuer die WebApp."""

import time
from typing import Annotated

import httpx
import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user
from api.schemas.github import IssueCreate, IssueOut, IssueUpdate, LabelOut
from config.settings import settings

logger = structlog.get_logger(__name__)

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)

# In-memory Label-Cache (selten aendernd, 1h TTL)
_label_cache: list[dict] | None = None
_label_cache_ts: float = 0
_CACHE_TTL = 3600  # 1 Stunde

# In-memory Issue-Cache (haeufiger aendernd, 5min TTL)
_issue_cache: list[dict] | None = None
_issue_cache_ts: float = 0
_ISSUE_CACHE_TTL = 300  # 5 Minuten

_GITHUB_API = "https://api.github.com"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _require_token() -> None:
    if not settings.GITHUB_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="GitHub nicht konfiguriert – GITHUB_TOKEN fehlt in .env",
        )


@router.get("/labels", response_model=list[LabelOut])
async def list_labels(
    user_key: Annotated[str, Depends(get_current_user)],
) -> list[LabelOut]:
    """Labels des konfigurierten Repos zurueckgeben (cached)."""
    _require_token()

    global _label_cache, _label_cache_ts
    now = time.monotonic()

    if _label_cache is not None and (now - _label_cache_ts) < _CACHE_TTL:
        return [LabelOut(**lb) for lb in _label_cache]

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/labels"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(url, params={"per_page": 100}, headers=_headers())

    if resp.status_code != 200:
        logger.warning("github_labels_error", status=resp.status_code, body=resp.text[:200])
        raise HTTPException(status_code=502, detail="GitHub-Labels konnten nicht geladen werden")

    raw = resp.json()
    _label_cache = [{"name": lb["name"], "color": lb["color"], "description": lb.get("description")} for lb in raw]
    _label_cache_ts = now

    return [LabelOut(**lb) for lb in _label_cache]


@router.get("/issues", response_model=list[IssueOut])
async def list_issues(
    user_key: Annotated[str, Depends(get_current_user)],
) -> list[IssueOut]:
    """Offene Issues des konfigurierten Repos zurueckgeben (cached)."""
    _require_token()

    global _issue_cache, _issue_cache_ts
    now = time.monotonic()

    if _issue_cache is not None and (now - _issue_cache_ts) < _ISSUE_CACHE_TTL:
        return [IssueOut(**iss) for iss in _issue_cache]

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues"
    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.get(
            url,
            params={"state": "open", "per_page": 30, "sort": "created", "direction": "desc"},
            headers=_headers(),
        )

    if resp.status_code != 200:
        logger.warning("github_issues_error", status=resp.status_code, body=resp.text[:200])
        raise HTTPException(status_code=502, detail="GitHub-Issues konnten nicht geladen werden")

    raw = resp.json()
    # GitHub /issues endpoint includes PRs – filter them out
    _issue_cache = [
        {
            "number": iss["number"],
            "title": iss["title"],
            "html_url": iss["html_url"],
            "labels": [lb["name"] for lb in iss.get("labels", [])],
            "created_at": iss["created_at"],
        }
        for iss in raw
        if "pull_request" not in iss
    ]
    _issue_cache_ts = now

    return [IssueOut(**iss) for iss in _issue_cache]


@router.post("/issues", response_model=IssueOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_issue(
    request: Request,
    body: IssueCreate,
    user_key: Annotated[str, Depends(get_current_user)],
) -> IssueOut:
    """Neues GitHub-Issue im konfigurierten Repo erstellen."""
    _require_token()

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues"
    payload = {"title": body.title, "body": body.body}
    if body.labels:
        payload["labels"] = body.labels

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.post(url, json=payload, headers=_headers())

    if resp.status_code not in (201, 200):
        logger.error("github_create_issue_error", status=resp.status_code, body=resp.text[:300])
        detail = "Issue konnte nicht erstellt werden"
        if resp.status_code == 401:
            detail = "GitHub-Token ungueltig oder abgelaufen"
        elif resp.status_code == 403:
            detail = "GitHub-Token hat keine Berechtigung fuer dieses Repo"
        elif resp.status_code == 404:
            detail = f"Repo '{settings.GITHUB_REPO}' nicht gefunden"
        elif resp.status_code == 422:
            detail = "Ungueltige Daten – pruefen Sie Titel und Labels"
        raise HTTPException(status_code=502, detail=detail)

    # Invalidate issue list cache so the new issue appears immediately
    global _issue_cache
    _issue_cache = None

    data = resp.json()
    logger.info(
        "github_issue_created",
        number=data["number"],
        title=data["title"],
        user=user_key,
    )

    return IssueOut(
        number=data["number"],
        title=data["title"],
        html_url=data["html_url"],
        labels=[lb["name"] for lb in data.get("labels", [])],
        created_at=data["created_at"],
    )


@router.patch("/issues/{issue_number}", response_model=IssueOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_issue(
    request: Request,
    issue_number: int,
    body: IssueUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
) -> IssueOut:
    """Bestehendes GitHub-Issue aktualisieren (Titel, Body, State, Labels)."""
    _require_token()

    url = f"{_GITHUB_API}/repos/{settings.GITHUB_REPO}/issues/{issue_number}"
    payload = body.model_dump(exclude_none=True)
    if not payload:
        raise HTTPException(status_code=422, detail="Keine Aenderungen angegeben.")

    async with httpx.AsyncClient(timeout=15) as client:
        resp = await client.patch(url, json=payload, headers=_headers())

    if resp.status_code not in (200,):
        logger.error("github_update_issue_error", status=resp.status_code, body=resp.text[:300])
        detail = "Issue konnte nicht aktualisiert werden"
        if resp.status_code == 404:
            detail = f"Issue #{issue_number} nicht gefunden"
        elif resp.status_code == 422:
            detail = "Ungueltige Daten"
        raise HTTPException(status_code=502, detail=detail)

    # Invalidate issue cache
    global _issue_cache
    _issue_cache = None

    data = resp.json()
    logger.info(
        "github_issue_updated",
        number=data["number"],
        state=data.get("state"),
        user=user_key,
    )

    return IssueOut(
        number=data["number"],
        title=data["title"],
        html_url=data["html_url"],
        labels=[lb["name"] for lb in data.get("labels", [])],
        created_at=data["created_at"],
    )
