# Почему если расставить импорты в соответствии со стандартами, то
# скрипт уже не работает?
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'foodgram.settings')
django.setup()

import csv
import chardet
from recipes.models import Ingredient


# Автоматически проверяем кодировку полученных данных
def detect_encoding(file_path):
    with open(file_path, 'rb') as file:
        result = chardet.detect(file.read())
    return result['encoding']


# Импортируем данные из CSV файла в модель CustomUser:
# Функция на вход должна получать путь до файла
def import_data_for_user(user_file_path):
    # Вызываем и запоминаем кодировку полученных данных
    encoding = detect_encoding(user_file_path)
    with open(user_file_path, 'r', encoding=encoding) as csv_file:
        reader = csv.DictReader(csv_file)
        for row in reader:
            # Сопоставляем поля модели со столбцами CSV файла
            instance = Ingredient(
                name=row['name'],
                measurement_unit=row['measurement_unit'],
            )
            instance.save()


user_file_path = 'data/ingredients.csv'
import_data_for_user(user_file_path)
