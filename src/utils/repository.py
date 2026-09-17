from abc import ABC, abstractmethod


class AbstractReposytory(ABC):
    @abstractmethod
    async def add_one(self):
        pass

    @abstractmethod
    async def find_all(self):
        pass

class SQLAlchemyReposytory(AbstractReposytory):
    async def add_one(self):
        pass # Добавить логки

    async def find_all(self):
        pass # Добавить логки