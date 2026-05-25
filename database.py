from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# 1. URL для подключения к PostgreSQL.
# Формат: postgresql://логин:пароль@хост:порт/имя_базы_данных
DATABASE_URL = "postgresql://postgres:Re_noft168$@localhost:5432/music_db"

# 2. Создаем движок (Engine). 
# Это ядро связи с БД, которое управляет пулом соединений.
engine = create_engine(DATABASE_URL)

# 3. Создаем фабрику сессий.
# Каждая сессия — это как отдельное диалоговое окно или транзакция с базой данных.
# autocommit=False гарантирует, что изменения не сохранятся, пока мы явно не вызовем db.commit()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Создаем базовый класс для будущих моделей (таблиц).
# От него мы будем наследовать классы в models.py
Base = declarative_base()

# 5. Функция-зависимость (Dependency) для FastAPI.
# Она открывает сессию базы данных перед обработкой запроса от Flet-фронтенда
# и гарантированно закрывает её (через try...finally) после того, как ответ отправлен.
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()