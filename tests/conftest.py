import os

os.environ["SECRET_KEY"] = (
    "test_keyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyyy"
)
os.environ["POSTGRES_DSN"] = "postgresql+asyncpg://test:test@localhost:5432/test"
