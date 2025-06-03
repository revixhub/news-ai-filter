#!/usr/bin/env python3
"""
Setup script для Marketing Digest Bot
Автоматизирует первоначальную настройку проекта
"""

import os
import sys
import shutil
from pathlib import Path

def check_python_version():
    """Проверка версии Python"""
    if sys.version_info < (3, 10):
        print("❌ Требуется Python 3.10 или выше")
        print(f"   Текущая версия: {sys.version_info.major}.{sys.version_info.minor}")
        sys.exit(1)
    print(f"✅ Python {sys.version_info.major}.{sys.version_info.minor} - OK")

def create_directories():
    """Создание необходимых папок"""
    directories = ['data', 'logs', 'data/digests']
    
    for directory in directories:
        path = Path(directory)
        path.mkdir(exist_ok=True)
        print(f"✅ Создана папка: {directory}")

def setup_env_file():
    """Настройка файла окружения"""
    env_example = Path("env.example")
    env_file = Path(".env")
    
    if not env_file.exists():
        if env_example.exists():
            shutil.copy2(env_example, env_file)
            print("✅ Создан файл .env из env.example")
            print("⚠️  Не забудьте заполнить API ключи в .env файле!")
        else:
            print("❌ Файл env.example не найден")
    else:
        print("✅ Файл .env уже существует")

def check_requirements():
    """Проверка установки зависимостей"""
    requirements_file = Path("requirements.txt")
    
    if not requirements_file.exists():
        print("❌ Файл requirements.txt не найден")
        return
    
    print("📦 Для установки зависимостей выполните:")
    print("   pip install -r requirements.txt")

def show_next_steps():
    """Показать следующие шаги"""
    print("\n" + "="*50)
    print("🎉 Настройка завершена!")
    print("="*50)
    print("\n📝 Следующие шаги:")
    print("1. Отредактируйте .env файл:")
    print("   - Добавьте TELEGRAM_BOT_TOKEN")
    print("   - Добавьте ваш USER_ID в ALLOWED_USER_IDS")
    print("   - Добавьте OPENAI_API_KEY или ANTHROPIC_API_KEY")
    print("   - Добавьте Telegram API данные для сбора каналов")
    print("\n2. Установите зависимости:")
    print("   pip install -r requirements.txt")
    print("\n3. Запустите бота:")
    print("   python main.py")
    print("\n📚 Документация: README.md")
    print("🆘 Помощь: /help в боте")

def main():
    """Главная функция настройки"""
    print("🚀 Настройка Marketing Digest Bot")
    print("="*40)
    
    try:
        check_python_version()
        create_directories()
        setup_env_file()
        check_requirements()
        show_next_steps()
        
    except KeyboardInterrupt:
        print("\n❌ Настройка прервана пользователем")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Ошибка при настройке: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 