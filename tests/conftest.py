import os

os.environ["SECRET_KEY"] = ("test_key" + "*"*32)
os.environ["POSTGRES_DSN"] = "postgresql+asyncpg://user:password@localhost:5432/my_fastapi_test"
