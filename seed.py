from database import SessionLocal
import crud
import schemas

def seed_data():
    db = SessionLocal()
    try:
        # --- НОВЫЙ БЛОК: Автоматически создаем Стефана, если база пуста ---
        # Проверяем, есть ли пользователь с email Стефана
        user = crud.get_user_by_email(db, email="qualcommes168@gmail.com")
        if not user:
            print("База пуста. Создаем пользователя Stefan...")
            user_in = schemas.UserCreate(
                username="Stefan",
                email="qualcommes168@gmail.com",
                password="123"
            )
            user = crud.create_user(db, user_in)
        # -----------------------------------------------------------------
        
        # 1. Проверяем, есть ли уже Led Zeppelin в базе
        artist = crud.get_artist_by_name(db, name="Led Zeppelin")
        if not artist:
            print("Создаем артиста: Led Zeppelin...")
            artist_in = schemas.ArtistCreate(
                name="Led Zeppelin", 
                bio="Британская рок-группа, образовавшаяся в 1968 году..."
            )
            artist = crud.create_artist(db, artist_in)
        
        # 2. Создаем альбом Led Zeppelin III от имени Стефана (owner_id=1)
        print("Создаем альбом: Led Zeppelin III...")
        album_in = schemas.AlbumCreate(title="Led Zeppelin III", artist_id=artist.id)
        album = crud.create_album(db, album_in, owner_id=1)

        # 3. Оригинальный треклист альбома
        tracklist = [
            "Immigrant Song",
            "Friends",
            "Celebration Day",
            "Since I've Been Loving You",
            "Out on the Tiles",
            "Gallows Pole",
            "Tangerine",
            "That's the Way",
            "Bron-Y-Aur Stomp",
            "Hats Off to (Roy) Harper"
        ]

        print("Загружаем треки...")
        for title in tracklist:
            # ИСПРАВЛЕНО: Теперь мы передаем title=title внутрь схемы!
            track_in = schemas.TrackCreate(
                title=title,
                artist_id=artist.id,
                album_id=album.id
            )
            # В качестве file_url временно пишем заглушку
            fake_url = f"/static/music/led_zeppelin/{title.lower().replace(' ', '_')}.mp3"
            crud.create_track(db, track_in, owner_id=1, file_url=fake_url)

        print("Успех! Led Zeppelin III полностью загружен в базу данных.")

    except Exception as e:
        print(f"Произошла ошибка при наполнении базы: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_data()