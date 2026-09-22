from abc import ABC, abstractmethod
from typing import TypeVar, Generic
from sqlmodel import SQLModel, select

class AbstractReposytory(ABC):
    @abstractmethod
    async def add_one(self):
        pass

    @abstractmethod
    async def find_all(self):
        pass

    @abstractmethod
    async def get_one(self):
        pass

    @abstractmethod
    async def delete(self):
        pass

ModelType = TypeVar("ModelType", bound=SQLModel)

class SQLAlchemyReposytory(AbstractReposytory):
    async def add_one(self):
        pass # Добавить логки

    async def find_all(self):
        pass # Добавить логки