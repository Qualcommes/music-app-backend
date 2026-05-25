from sqlalchemy.orm import Session
from sqlalchemy import or_
import models
import schemas
# Импортируем нашу функцию хэширования
from security import hash_password

#=================== CRUD для пользователей ==========================================
# 1. Поиск пользователя по email (нужен для проверки уникальности при регистрации)
def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

# 1.1 поиск пользоваетеля по id
def get_user(db: Session, user_id: int):
    """Найти одного конкретного пользователя по его ID"""
    return db.query(models.User).filter(models.User.id == user_id).first()

# 2. Поиск пользователя по ID
def get_user_by_id(db: Session, user_id: int):
    return db.query(models.User).filter(models.User.id == user_id).first()

# 3. Создание нового пользователя
def create_user(db: Session, user: schemas.UserCreate):
    # Хэшируем пароль перед сохранением в БД
    hashed_pwd = hash_password(user.password)
    
    # Создаем объект модели SQLAlchemy
    db_user = models.User(
        username=user.username,
        email=user.email,
        hashed_password=hashed_pwd
    )
    
    db.add(db_user)          # Добавляем в транзакцию
    db.commit()          # Сохраняем изменения в PostgreSQL
    db.refresh(db_user)      # Подгружаем сгенерированный базой ID обратно в объект
    
    return db_user

# 4. Получение всех пользователей 
def get_users(db: Session, skip: int = 0, limit: int = 100):
    """Получить список всех пользователей с пагинацией"""
    return db.query(models.User).offset(skip).limit(limit).all()

# 5. Обновление пользователя 
def update_user(db: Session, user_id: int, user_update: schemas.UserCreate):
    """Обновить данные пользователя (например, имя или email)"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db_user.username = user_update.username
        db_user.email = user_update.email
        # Если меняется пароль — хэшируем его (пока пишем напрямую)
        db_user.hashed_password = user_update.password  
        db.commit()
        db.refresh(db_user)
    return db_user

# 6. Удаление пользователя 
def delete_user(db: Session, user_id: int):
    """Удалить пользователя из базы данных"""
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user:
        db.delete(db_user)
        db.commit()
        return True
    return False
#========================== Новое ====================================================================================
# --- CRUD для Артистов ---
def create_artist(db: Session, artist: schemas.ArtistCreate):
    db_artist = models.Artist(name=artist.name, bio=artist.bio)
    db.add(db_artist)
    db.commit()
    db.refresh(db_artist)
    return db_artist

def get_artist_by_name(db: Session, name: str):
    return db.query(models.Artist).filter(models.Artist.name == name).first()

# --- CRUD для Альбомов ---
def create_album(db: Session, album: schemas.AlbumCreate, owner_id: int):
    db_album = models.Album(
        title=album.title,
        artist_id=album.artist_id,
        owner_id=owner_id
    )
    db.add(db_album)
    db.commit()
    db.refresh(db_album)
    return db_album

# --- Получение доступных альбомов для конкретного пользователя ---
def get_available_albums(db: Session, user_id: int):
    """
    Возвращает альбомы, которые имеет право видеть пользователь:
    1. Все публичные альбомы (visibility == 'public')
    2. Собственные приватные/дружеские альбомы пользователя (owner_id == user_id)
    """
    query = db.query(models.Album).filter(
        or_(
            models.Album.visibility == models.VisibilityEnum.PUBLIC,
            models.Album.owner_id == user_id
        )
    )
    
    albums = query.all()
    
    # Динамически добавляем artist_name в объекты модели, 
    # чтобы Pydantic в схеме AlbumOut смог его прочитать через from_attributes
    for album in albums:
        if album.artist:
            album.artist_name = album.artist.name
        else:
            album.artist_name = "Неизвестный исполнитель"
            
    return albums

# --- Получение всех треков конкретного альбома ---
def get_tracks_by_album(db: Session, album_id: int):
    """
    Возвращает список всех треков, привязанных к указанному альбому
    """
    return db.query(models.Track).filter(models.Track.album_id == album_id).all()

# --- CRUD для Треков ---
def create_track(db: Session, track: schemas.TrackCreate, owner_id: int, file_url: str):
    db_track = models.Track(
        title=track.title,
        artist_id=track.artist_id,
        album_id=track.album_id,
        owner_id=owner_id,
        file_url=file_url  # Сюда временно пишем фейковый путь
    )
    db.add(db_track)
    db.commit()
    db.refresh(db_track)
    return db_track

def update_track(db: Session, track_id: int, track_in: schemas.TrackUpdate):
    """
    Обновляет существующий трек по его ID.
    Принимает только измененные поля.
    """
    # 1. Находим трек в базе данных
    db_track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if not db_track:
        return None

    # 2. Превращаем Pydantic-модель в словарь, исключая те поля, которые не были переданы
    update_data = track_in.model_dump(exclude_unset=True) # Для Pydantic v2 используется model_dump вместо dict

    # 3. Накатываем изменения на модель SQLAlchemy
    for key, value in update_data.items():
        setattr(db_track, key, value)

    # 4. Сохраняем в PostgreSQL
    db.commit()
    db.refresh(db_track)
    return db_track

def delete_track(db: Session, track_id: int):
    """
    Находит трек по ID, удаляет его из базы данных 
    
    и возвращает объект трека (чтобы узнать url файла для S3).
    """
    db_track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if db_track:
        db.delete(db_track)
        db.commit()
        return db_track
    return None