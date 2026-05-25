from pydantic import BaseModel, EmailStr
from typing import Optional

# Базовые поля пользователя, которые используются почти везде
class UserBase(BaseModel):
    username: str
    email: EmailStr

# Схема, которую пришлет Flet при регистрации. Тут обязателен пароль!
class UserCreate(UserBase):
    password: str

# Схема, которую бэкенд вернет фронтенду. Пароль возвращать НЕЛЬЗЯ!
class UserOut(UserBase):
    id: int
    avatar_url: Optional[str] = None

    # Этот подкласс нужен, чтобы Pydantic умел читать данные из моделей SQLAlchemy
    class Config:
        from_attributes = True
#========================== Новое ====================================================================================
# --- Схемы для Исполнителей (Artists) ---
class ArtistBase(BaseModel):
    name: str
    bio: Optional[str] = None

class ArtistCreate(ArtistBase):
    pass

class ArtistOut(ArtistBase):
    id: int
    image_url: Optional[str] = None

    class Config:
        from_attributes = True

# --- Схемы для Альбомов (Albums) ---
class AlbumBase(BaseModel):
    title: str

class AlbumCreate(AlbumBase):
    artist_id: Optional[int] = None
    # owner_id передадим напрямую в CRUD из сессии авторизованного юзера

class AlbumOut(AlbumBase):
    id: int
    cover_url: Optional[str] = None
    owner_id: int
    artist_id: Optional[int] = None
    artist_name: Optional[str] = None  # <-- Добавили, чтобы фронтенд сразу видел автора

    class Config:
        from_attributes = True

# --- Схемы для Треков (Tracks) ---
class TrackBase(BaseModel):
    title: str

class TrackCreate(TrackBase):
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    visibility: Optional[str] = "public"

class TrackOut(TrackBase):
    id: int
    file_url: str                      # <-- Обязательно отдаем URL файла в MinIO для плеера
    visibility: str
    owner_id: int
    album_id: Optional[int] = None
    artist_id: Optional[int] = None

    class Config:
        from_attributes = True

# --- Обновление существующих треков ---
class TrackUpdate(BaseModel):
    title: Optional[str] = None
    artist_id: Optional[int] = None
    album_id: Optional[int] = None
    file_url: Optional[str] = None      # Ссылка на файл в MinIO, если файл перезаписали
    visibility: Optional[str] = None    # "public", "private" или "friends"

    class Config:
        from_attributes = True