
from typing import Any, Generic, List, Type, TypeVar
from fastapi import HTTPException
from sqlalchemy import func, asc, desc
from sqlmodel import SQLModel, Session, select

from app.models.pagination import PaginationBase
from app.services.pg_error_handler import pg_error_handler


ModelTypePublic = TypeVar("ModelType", bound=SQLModel)
CreateSchemaType = TypeVar("CreateSchemaType")
UpdateSchemaType = TypeVar("UpdateSchemaType")

class BaseService(Generic[ModelTypePublic, CreateSchemaType, UpdateSchemaType]):
    """
    Generic base service class for CRUD operations on SQLModel models.  
    """
    def __init__(self, model: Type[ModelTypePublic], db_session: Session):
        self.model = model
        self.db_session = db_session

    def get(self, id: int) -> ModelTypePublic | None:
        obj: ModelTypePublic | None = self.db_session.get(self.model, id) 
        if obj is None:
            raise HTTPException(status_code=404, detail="Not Found")
        return obj

    def list(self, page: int = 0, per_page: int = 10, order_by: str | None = None) -> PaginationBase:
        """
        Retrieve a paginated list of objects.
        
        Args:
            page: Page number (0-indexed)
            per_page: Number of items per page, defaults to 10
            order_by: Optional ordering string in format "column" or "column:asc" or "column:desc"
        
        Returns:
            PaginationBase containing the paginated results and metadata
        """
        # Calculate offset
        offset = page * per_page
        
        # Get total count
        total: int = self.db_session.exec(select(func.count(self.model.id))).one()
        
        # Build query
        query = select(self.model)
        
        # Apply ordering if provided
        if order_by:
            # Parse order_by string (format: "column" or "column:asc" or "column:desc")
            order_parts = order_by.split(":")
            column_name = order_parts[0]
            direction = order_parts[1].lower() if len(order_parts) > 1 else "asc"
            
            # Get the column from model
            if hasattr(self.model, column_name):
                column = getattr(self.model, column_name)
                query = query.order_by(asc(column) if direction == "asc" else desc(column))
        
        # Get paginated results
        data: List[ModelTypePublic] = self.db_session.exec(
            query.offset(offset).limit(per_page)
        ).all()
        
        return PaginationBase(page=page, per_page=per_page, total=total, data=data)

    def search(self, *search_args) -> List[ModelTypePublic]:
        objs: List[ModelTypePublic] = self.db_session.exec(select(self.model).where(*search_args)).all()
        return objs

    def search_first(self, *search_args) -> ModelTypePublic | None:
        obj: ModelTypePublic | None = self.db_session.exec(select(self.model).where(*search_args)).first()
        return obj

    @pg_error_handler
    def create(self, obj: CreateSchemaType) -> ModelTypePublic:
        db_obj: ModelTypePublic = self.model(**obj.model_dump())
        self.db_session.add(db_obj)
        self.db_session.commit()
        return db_obj

    @pg_error_handler
    def update(self, id: Any, obj: UpdateSchemaType) -> ModelTypePublic | None:
        db_obj = self.get(id)
        for column, value in obj.model_dump(exclude_unset=True).items():
            setattr(db_obj, column, value) 
        self.db_session.commit()
        return db_obj

    def delete(self, id: Any) -> None:
        obj = self.get(id)
        self.db_session.delete(obj)
        self.db_session.commit()
