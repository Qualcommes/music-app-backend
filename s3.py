# s3.py
import boto3
import json  # ДОБАВЛЕНО: импорт для работы с политиками доступа
from botocore.exceptions import NoCredentialsError
import os

# Конфигурация подключения к локальному MinIO
MINIO_ENDPOINT = "http://localhost:9000"  # API порт MinIO
ACCESS_KEY = "minioadmin"
SECRET_KEY = "minioadmin"
BUCKET_NAME = "music-service"

# Инициализируем S3 клиент
s3_client = boto3.client(
    "s3",
    endpoint_url=MINIO_ENDPOINT,
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY
)

def set_bucket_public_readonly(bucket_name: str):
    """Принудительно делает бакет публичным на чтение через JSON-политику"""
    public_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {"AWS": ["*"]},
                "Action": ["s3:GetObject"],
                "Resource": [f"arn:aws:s3:::{bucket_name}/*"]
            }
        ]
    }
    
    try:
        policy_string = json.dumps(public_policy)
        s3_client.put_bucket_policy(Bucket=bucket_name, Policy=policy_string)
        print(f"Политика Public Read-Only для бакета '{bucket_name}' успешно применена!")
    except Exception as e:
        print(f"Не удалось установить политику бакета: {e}")

def upload_file_to_s3(file_obj, object_name: str, content_type: str) -> str:
    """
    Загружает файл в MinIO и возвращает прямую ссылку на него.
    """
    try:
        # ИСПРАВЛЕНО: Перед каждой загрузкой проверяем и обновляем права бакета
        set_bucket_public_readonly(BUCKET_NAME)
        
        s3_client.upload_fileobj(
            file_obj,
            BUCKET_NAME,
            object_name,
            ExtraArgs={
                "ContentType": content_type,
                "ACL": "public-read"  # ИСПРАВЛЕНО: Явно открываем доступ на чтение для этого файла
            }
        )
        
        # ИСПРАВЛЕНО: Для стабильности Windows-браузера возвращаем 127.0.0.1 вместо localhost
        file_url = f"http://127.0.0.1:9000/{BUCKET_NAME}/{object_name}"
        return file_url
        
    except Exception as e:
        print(f"Ошибка загрузки в MinIO: {e}")
        raise e
    
def delete_file_from_s3(file_url: str):
    """
    Удаляет файл из MinIO по его полной ссылке (URL).
    """
    if not file_url:
        return
        
    try:
        # Извлекаем путь к файлу из ссылки. 
        # Например, из "http://127.0.0.1:9000/music-service/avatars/user_1/avatar.jpg"
        # нам нужно получить "avatars/user_1/avatar.jpg"
        search_string = f"/{BUCKET_NAME}/"
        if search_string in file_url:
            object_name = file_url.split(search_string)[1]
            
            s3_client.delete_object(Bucket=BUCKET_NAME, Key=object_name)
            print(f"Файл '{object_name}' успешно удален из MinIO!")
    except Exception as e:
        print(f"Не удалось удалить файл из MinIO: {e}")