import uuid

from src.core.db.models import Item
from src.core.db.schemas import ItemCreate, ItemRead, ItemUpdate
from src.core.uow import AbstractUnitOfWork
from src.services.exceptions import (
    ItemAccessDenied,
    ItemNotFound,
    UserNotFound,
)


class ItemService:
    def __init__(self, uow: AbstractUnitOfWork) -> None:
        self.uow = uow

    async def create(self, user_id: uuid.UUID, data: ItemCreate) -> ItemRead:
        async with self.uow:
            if await self.uow.users.get_one(user_id) is None:
                raise UserNotFound(user_id)

            item = Item(
                title=data.title, description=data.description, owner_id=user_id
            )
            await self.uow.items.add_one(item)
            await self.uow.commit()
            return ItemRead.model_validate(item)

    async def get(self, item_id: uuid.UUID, user_id: uuid.UUID) -> ItemRead:
        async with self.uow:
            item = await self.uow.items.get_one(item_id)
            if item is None:
                raise ItemNotFound(item_id)
            if item.owner_id != user_id:
                raise ItemAccessDenied(item_id, user_id)

            return ItemRead.model_validate(item)

    async def get_all_users_item(self, user_id: uuid.UUID) -> list[ItemRead]:
        async with self.uow:
            items = await self.uow.items.get_all_users_item(user_id)
            if items is None:
                raise ItemNotFound("No any items!")

            return [ItemRead.model_validate(item) for item in items]

    async def update(
        self, item_id: uuid.UUID, user_id: uuid.UUID, data: ItemUpdate
    ) -> ItemRead:
        async with self.uow:
            item = await self.uow.items.get_one(item_id)
            if item is None:
                raise ItemNotFound(item_id)
            if item.owner_id != user_id:
                raise ItemAccessDenied(item_id, user_id)

            for field, value in data.model_dump(exclude_unset=True).items():
                setattr(item, field, value)
            await self.uow.commit()
            return ItemRead.model_validate(item)

    async def delete(self, item_id: uuid.UUID, user_id: uuid.UUID) -> None:
        async with self.uow:
            item = await self.uow.items.get_one(item_id)
            if item is None:
                raise ItemNotFound(item_id)
            if item.owner_id != user_id:
                raise ItemAccessDenied(item_id, user_id)

            await self.uow.items.delete(item_id)
            await self.uow.commit()
