from fastapi import FastAPI, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import Optional
from typing import List

import bcrypt
import s3
import models
import schemas
import crud
import os
from database import engine, get_db

# 1. Автоматически создаем таблицы в PostgreSQL при старте бэкенда.
# SQLAlchemy проверит базу: если таблицы уже есть, он их не тронет.
models.Base.metadata.create_all(bind=engine)

# 2. Инициализируем приложение FastAPI
app = FastAPI(
    title="Music Streaming Service API",
    description="Бэкенд для музыкального стримингового сервиса на Flet",
    version="1.0.0"
)


#====== CRUD для пользователей ================================================
# 1. Сделать чтение профиля конкретного юзера по ID
@app.get("/api/users/{user_id}", response_model=schemas.UserOut, summary="Получить пользователя по ID")
def read_user(user_id: int, db: Session = Depends(get_db)):
    db_user = crud.get_user(db, user_id=user_id) # Убедись, что get_user есть в crud.py
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    return db_user

# 2. Получить список всех пользователей (полезно для поиска друзей во Flet)
@app.get("/api/users/", response_model=List[schemas.UserOut], summary="Получить список всех пользователей")
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

# 3. Обновление профиля
@app.put("/api/users/{user_id}", response_model=schemas.UserOut, summary="Обновить данные пользователя и аватар")
def update_user_profile(
    user_id: int,
    username: str = Form(...),          # Теперь это поле формы, а не JSON
    email: str = Form(...),             # Тоже поле формы
    password: Optional[str] = Form(None), # Необязательное поле формы
    avatar_file: Optional[UploadFile] = File(None), # Кнопка выбора файла!
    db: Session = Depends(get_db)
):
    # 1. Ищем пользователя в базе
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    
    # 2. Логика работы с аватаркой в MinIO
    avatar_url = db_user.avatar_url  # По умолчанию оставляем старый URL
    if avatar_file and avatar_file.filename:
        if not avatar_file.content_type.startswith("image/"):
            raise HTTPException(status_code=400, detail="Файл должен быть изображением")
            
        file_extension = os.path.splitext(avatar_file.filename)[1]
        object_name = f"avatars/user_{user_id}/avatar{file_extension}"
        
        avatar_url = s3.upload_file_to_s3(
            file_obj=avatar_file.file,
            object_name=object_name,
            content_type=avatar_file.content_type
        )

    # 3. Обновляем поля в базе данных
    db_user.username = username
    db_user.email = email
    if password:  
        db_user.hashed_password = password  # В будущем добавим сюда хэширование
    db_user.avatar_url = avatar_url

    db.commit()
    db.refresh(db_user)
    return db_user

# 4. Удаление аккаунта (благодаря CASCADE в models.py, удалятся и его связи, где это настроено)
@app.delete("/api/users/{user_id}", summary="Удалить пользователя и его файлы")
def delete_user_account(user_id: int, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.id == user_id).first()
    if db_user is None:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
        
    # 1. Сохраняем ссылку на аватар перед удалением пользователя
    user_avatar_url = db_user.avatar_url
    
    # 2. Удаляем пользователя из PostgreSQL
    db.delete(db_user)
    db.commit()
    
    # 3. Если у пользователя был аватар, удаляем его из MinIO
    if user_avatar_url:
        s3.delete_file_from_s3(user_avatar_url)
        
    return {"detail": "Пользователь и его аватар успешно удалены"}

# 5. Эндпоинт регистрации пользователя
@app.post(
    "/api/auth/register", 
    response_model=schemas.UserOut, 
    status_code=status.HTTP_201_CREATED,
    summary="Регистрация нового пользователя"
)
def register_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Регистрирует нового пользователя в системе:
    - Проверяет, занят ли email.
    - Хэширует пароль.
    - Создает запись в БД.
    - Возвращает данные пользователя без пароля.
    """
    # Проверяем, существует ли уже пользователь с таким email
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Пользователь с таким email уже зарегистрирован"
        )
    
    # Если всё ок — создаем и возвращаем созданного пользователя
    return crud.create_user(db=db, user=user)
#===================================================================================
# Тестовый эндпоинт для проверки работоспособности
@app.get("/", summary="Проверка статуса сервера")
def read_root():
    return {"status": "working", "message": "Welcome to Music API"}

#===================== CRUD для треков ==============================================================================
@app.post("/api/tracks/upload", response_model=schemas.TrackOut, summary="Загрузить аудиофайл трека")
def upload_track(
    title: str = Form(...),                  # FastAPI умеет принимать текст...
    artist_id: Optional[int] = Form(None),  # ИСПРАВЛЕНО: явно указали Optional и дефолт None
    album_id: Optional[int] = Form(None),   # ИСПРАВЛЕНО: явно указали Optional и дефолт None
    owner_id: int = Form(...),               # ...вместе с файлами только через Form данные
    audio_file: UploadFile = File(...)      # А это сам файл
):
    
    # ЗАЩИТА ОТ НУЛЕЙ ИЗ SWAGGER: 
    # Если Swagger прислал 0, принудительно превращаем в None (Null для БД)
    if artist_id == 0:
        artist_id = None
    if album_id == 0:
        album_id = None

    # 1. Формируем уникальное имя файла в хранилище, чтобы избежать коллизий
    # Например: tracks/owner_1/my_song.mp3
    file_extension = os.path.splitext(audio_file.filename)[1]
    object_name = f"tracks/owner_{owner_id}/{title.lower().replace(' ', '_')}{file_extension}"
    
    # 2. Загружаем файл в MinIO через наш модуль s3
    # audio_file.file — это файловый объект python, который ожидает boto3
    real_file_url = s3.upload_file_to_s3(
        file_obj=audio_file.file,
        object_name=object_name,
        content_type=audio_file.content_type
    )
    
    # 3. Сохраняем информацию в PostgreSQL базу данных
    track_in = schemas.TrackCreate(
        title=title,
        artist_id=artist_id,
        album_id=album_id
    )
    
    db_track = crud.create_track(
        db=next(get_db()), # Берем сессию БД напрямую для теста
        track=track_in,
        owner_id=owner_id,
        file_url=real_file_url
    )
    
    return db_track

#================== CRUD для альбомов ============================================================
# 1. загрузка обложки альбома 
@app.post("/api/albums/upload-cover", summary="Загрузить обложку альбома")
def upload_album_cover(
    album_id: int = Form(...),
    cover_file: UploadFile = File(...)
):
    # 1. Проверяем, что нам прислали именно картинку
    if not cover_file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400, 
            detail="Файл должен быть изображением (jpeg, png, webp и т.д.)"
        )
    
    # 2. Формируем путь внутри бакета MinIO: covers/album_ID/имя_файла
    file_extension = os.path.splitext(cover_file.filename)[1]
    object_name = f"covers/album_{album_id}/cover{file_extension}"
    
    # 3. Загружаем файл в MinIO, используя наш готовый s3.py
    real_cover_url = s3.upload_file_to_s3(
        file_obj=cover_file.file,
        object_name=object_name,
        content_type=cover_file.content_type
    )
    
    # 4. Обновляем поле cover_url у альбома в базе данных
    db = next(get_db())
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    
    if not db_album:
        raise HTTPException(status_code=404, detail="Альбом не найден в базе данных")
    
    db_album.cover_url = real_cover_url
    db.commit()
    db.refresh(db_album)
    
    return {
        "message": "Обложка успешно загружена",
        "album_id": db_album.id,
        "album_title": db_album.title,
        "cover_url": db_album.cover_url
    }

#=============== Авторизация пользователя =======================================================
@app.post("/api/auth/login", summary="Авторизация пользователя по хэшированному паролю")
def login_user(
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    # 1. Ищем пользователя в PostgreSQL по email
    user = db.query(models.User).filter(models.User.email == email).first()
    
    # 2. Если пользователь не найден
    if not user:
        raise HTTPException(status_code=400, detail="Неверный email или пароль")
    
    # 3. Сверяем хэши. 
    # Библиотека bcrypt работает исключительно с байтами (bytes), 
    # поэтому строки нужно закодировать через .encode('utf-8')
    password_bytes = password.encode('utf-8')
    stored_hash_bytes = user.hashed_password.encode('utf-8')
    
    # Функция checkpw сама поймет, как расшифровать хэш и сравнить со строкой
    if not bcrypt.checkpw(password_bytes, stored_hash_bytes):
        raise HTTPException(status_code=400, detail="Неверный email или пароль")
    
    # 4. Если проверка прошла успешно
    return {
        "message": "Успешный вход", 
        "user_id": user.id, 
        "username": user.username
    }

#=============== ЭНДПОИНТЫ АЛЬБОМОВ И ТРЕКОВ ==========================================

@app.get(
    "/api/albums/", 
    response_model=List[schemas.AlbumOut], 
    summary="Получить список доступных пользователю альбомов"
)
def read_available_albums(user_id: int, db: Session = Depends(get_db)):
    """
    Возвращает список альбомов, доступных пользователю с переданным user_id
    """
    albums = crud.get_available_albums(db, user_id=user_id)
    return albums


@app.get(
    "/api/albums/{album_id}/tracks", 
    response_model=List[schemas.TrackOut], 
    summary="Получить все треки из альбома"
)
def read_album_tracks(album_id: int, db: Session = Depends(get_db)):
    """
    Возвращает список всех треков, которые принадлежат альбому с ID = album_id
    """
    # Проверим, существует ли сам альбом
    db_album = db.query(models.Album).filter(models.Album.id == album_id).first()
    if not db_album:
        raise HTTPException(status_code=404, detail="Альбом не найден")
        
    tracks = crud.get_tracks_by_album(db, album_id=album_id)
    return tracks

@app.patch(
    "/api/tracks/{track_id}", 
    response_model=schemas.TrackOut, 
    summary="Частично обновить данные существующего трека"
)
def modify_track(
    track_id: int, 
    track_in: schemas.TrackUpdate, 
    db: Session = Depends(get_db) # Используем правильный Depends вместо next(get_db())
):
    """
    Эндпоинт для изменения параметров трека (название, альбом, артист, видимость, ссылка).
    Передавать можно только те поля, которые требуют изменения.
    """
    # Валидация альбома (если его передали и он не равен None)
    if track_in.album_id is not None:
        db_album = db.query(models.Album).filter(models.Album.id == track_in.album_id).first()
        if not db_album:
            raise HTTPException(
                status_code=404, 
                detail=f"Альбом с ID {track_in.album_id} не найден. Перепривязка невозможна."
            )

    # Валидация артиста (если его передали и он не равен None)
    if track_in.artist_id is not None:
        db_artist = db.query(models.Artist).filter(models.Artist.id == track_in.artist_id).first()
        if not db_artist:
            raise HTTPException(
                status_code=404, 
                detail=f"Артист с ID {track_in.artist_id} не найден."
            )

    # Вызов CRUD функции
    updated_track = crud.update_track(db=db, track_id=track_id, track_in=track_in)
    
    if not updated_track:
        raise HTTPException(
            status_code=404, 
            detail=f"Трек с ID {track_id} не найден в базе данных."
        )

    return updated_track

# Пример изменения трека в фронтенде:
'''
# Пример вызова из Flet при сохранении редактирования:
payload = {
    "title": "Новое название трека",
    "album_id": 3  # Привязываем к другому альбому
}
response = requests.patch(f"http://127.0.0.1:8000/api/tracks/{track_id}", json=payload)
'''

# Добавь в main.py в раздел CRUD для треков

@app.delete("/api/tracks/{track_id}", summary="Удалить трек по его ID")
def delete_existing_track(track_id: int, db: Session = Depends(get_db)):
    """
    Эндпоинт полностью удаляет трек из базы данных PostgreSQL
    и автоматически стирает связанный аудиофайл из бакета MinIO.
    """
    # 1. Сначала ищем трек, чтобы проверить его существование
    db_track = db.query(models.Track).filter(models.Track.id == track_id).first()
    if not db_track:
        raise HTTPException(
            status_code=404, 
            detail=f"Трек с ID {track_id} не найден в базе данных"
        )
        
    # Сохраняем URL файла перед удалением записи из БД
    file_to_delete = db_track.file_url

    # 2. Удаляем запись из PostgreSQL
    crud.delete_track(db=db, track_id=track_id)

    # 3. Удаляем физический файл из MinIO S3
    # (Если путь содержит реальную ссылку, а не заглушку вроде "http://fake...")
    if file_to_delete and "fake" not in file_to_delete:
        try:
            s3.delete_file_from_s3(file_to_delete)
        except Exception as e:
            print(f"Запись в БД удалена, но файл из S3 не удалось стереть: {e}")

    return {
        "status": "success", 
        "message": f"Трек с ID {track_id} и его файл успешно удалены."
    }