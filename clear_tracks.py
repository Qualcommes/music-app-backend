# clear_tracks.py
from sqlalchemy.orm import Session
from database import SessionLocal
import models

def clear_only_tracks():
    db: Session = SessionLocal()
    try:
        print("[БД] Запуск очистки таблицы треков...")
        
        # Считаем, сколько треков было в базе перед удалением
        tracks_count = db.query(models.Track).count()
        print(f"[БД] Найдено треков для удаления: {tracks_count}")
        
        if tracks_count > 0:
            # Выполняем быструю очистку таблицы на уровне SQL
            db.query(models.Track).delete(synchronize_session=False)
            db.commit()
            print("[БД] Таблица 'tracks' успешно и полностью очищена!")
        else:
            print("[БД] Таблица треков уже пуста. Ничего удалять не потребовалось.")

    except Exception as e:
        db.rollback()
        print(f"[Ошибка] Не удалось очистить таблицу треков: {e}")
    finally:
        db.close()
        print("[БД] Сессия соединения закрыта.")

if __name__ == "__main__":
    clear_only_tracks()