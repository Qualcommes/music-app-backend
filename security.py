import bcrypt

def hash_password(password: str) -> str:
    """Генерирует безопасный хэш из сырого пароля."""
    # Превращаем строку пароля в байты
    pwd_bytes = password.encode('utf-8')
    # Генерируем случайную соль
    salt = bcrypt.gensalt()
    # Хэшируем и переводим обратно в строку для хранения в БД
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Проверяет, соответствует ли введенный пароль хэшу из базы данных."""
    pwd_bytes = plain_password.encode('utf-8')
    hashed_bytes = hashed_password.encode('utf-8')
    # Функция сама сравнивает пароль с солью, зашитой в хэш
    return bcrypt.checkpw(pwd_bytes, hashed_bytes)