from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from to_do_list_fast_api.database import get_db
from to_do_list_fast_api.dependencies import get_current_user
from to_do_list_fast_api.models import Todo, User
from to_do_list_fast_api.schemas import (
    PriorityEnum,
    TodoCreate,
    TodoResponse,
    TodoUpdate,
)

router = APIRouter(prefix="/todos", tags=["Todos"])


@router.get(
    "",
    response_model=list[TodoResponse],
    summary="Get all todos for the current user with optional filtering",
)
def get_todos(
    completed: bool | None = Query(
        default=None, description="Filter by completion status"
    ),
    priority: PriorityEnum | None = Query(
        default=None, description="Filter by priority level"
    ),
    search: str | None = Query(
        default=None, description="Search term for title or description"
    ),
    skip: int = Query(default=0, ge=0, description="Pagination offset"),
    limit: int = Query(default=20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Todo).filter(Todo.user_id == current_user.id)

    if completed is not None:
        query = query.filter(Todo.is_completed == completed)

    if priority is not None:
        query = query.filter(Todo.priority == priority.value)

    if search:
        search_filter = f"%{search}%"
        query = query.filter(
            (Todo.title.ilike(search_filter)) | (Todo.description.ilike(search_filter))
        )

    todos = query.order_by(Todo.created_at.desc()).offset(skip).limit(limit).all()
    return todos


@router.post(
    "",
    response_model=TodoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new todo for the current user",
)
def create_todo(
    todo_in: TodoCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    new_todo = Todo(
        user_id=current_user.id,
        title=todo_in.title,
        description=todo_in.description,
        is_completed=todo_in.is_completed,
        priority=todo_in.priority.value,
        due_date=todo_in.due_date,
    )
    db.add(new_todo)
    db.commit()
    db.refresh(new_todo)
    return new_todo


@router.get(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Get details of a specific todo",
)
def get_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todo)
        .filter(Todo.id == todo_id, Todo.user_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {todo_id} not found",
        )
    return todo


@router.put(
    "/{todo_id}",
    response_model=TodoResponse,
    summary="Update a todo",
)
def update_todo(
    todo_id: int,
    todo_in: TodoUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todo)
        .filter(Todo.id == todo_id, Todo.user_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {todo_id} not found",
        )

    update_data = todo_in.model_dump(exclude_unset=True)
    if "priority" in update_data and update_data["priority"] is not None:
        update_data["priority"] = update_data["priority"].value

    for field, value in update_data.items():
        setattr(todo, field, value)

    db.commit()
    db.refresh(todo)
    return todo


@router.patch(
    "/{todo_id}/toggle",
    response_model=TodoResponse,
    summary="Toggle completion status of a todo",
)
def toggle_todo_status(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todo)
        .filter(Todo.id == todo_id, Todo.user_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {todo_id} not found",
        )

    todo.is_completed = not todo.is_completed
    db.commit()
    db.refresh(todo)
    return todo


@router.delete(
    "/{todo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a todo",
)
def delete_todo(
    todo_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    todo = (
        db.query(Todo)
        .filter(Todo.id == todo_id, Todo.user_id == current_user.id)
        .first()
    )
    if not todo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Todo with ID {todo_id} not found",
        )

    db.delete(todo)
    db.commit()
    return None
