"""GET/POST/PATCH/DELETE /tasks"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from api.dependencies import get_current_user, get_task_service
from api.schemas.task import TaskCreate, TaskOut, TaskUpdate
from config.settings import settings

router = APIRouter()
limiter = Limiter(key_func=get_remote_address)


@router.get("", response_model=list[TaskOut])
async def list_tasks(
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
    all: bool = False,
):
    if all:
        return await task_svc.get_all_tasks(user_key)
    return await task_svc.get_open_tasks(user_key)


@router.post("", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def create_task(
    request: Request,
    body: TaskCreate,
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
):
    return await task_svc.create_task(
        user_key=user_key,
        title=body.title,
        priority=body.priority,
        description=body.description,
        due_date=body.due_date,
        recurrence=body.recurrence,
    )


@router.patch("/{task_id}", response_model=TaskOut)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def update_task(
    request: Request,
    task_id: int,
    body: TaskUpdate,
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
):
    updates = body.model_dump(exclude_unset=True)
    if not updates:
        raise HTTPException(status_code=400, detail="Keine Änderungen angegeben.")

    # Handle status=done specially (preserves recurrence logic)
    if updates.get("status") == "done" and len(updates) == 1:
        result = await task_svc.complete_task(task_id, user_key)
        if not result:
            raise HTTPException(status_code=404, detail="Task nicht gefunden.")
        return result

    from src.services.database import Task, get_db

    with get_db()() as session:
        task = session.query(Task).filter_by(id=task_id, user_key=user_key).first()
        if not task:
            raise HTTPException(status_code=404, detail="Task nicht gefunden.")

        # If status=done is part of a multi-field update, apply other fields first
        if updates.get("status") == "done":
            for k, v in updates.items():
                if k != "status":
                    setattr(task, k, v)
            session.flush()
            result = await task_svc.complete_task(task_id, user_key)
            if not result:
                raise HTTPException(status_code=404, detail="Task nicht gefunden.")
            return result

        for k, v in updates.items():
            setattr(task, k, v)
        session.flush()
        session.refresh(task)
        return task


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit(settings.RATE_LIMIT_WRITE)
async def delete_task(
    request: Request,
    task_id: int,
    user_key: Annotated[str, Depends(get_current_user)],
    task_svc=Depends(get_task_service),
):
    ok = await task_svc.delete_task(task_id, user_key)
    if not ok:
        raise HTTPException(status_code=404, detail="Task nicht gefunden.")
