# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

## [1.2.7] - 25-08-2022

### Added
- Сохранение логов в файл

### Changed
- Модель ведения проекта на *github*
- Структура файлов и папок на сервере
- Скрипты авто-деплоя и установки бота на стороне сервера

### Removed
- Возможность запуска в *debug* режиме
- Переключение между версиями
- Таблица в базе данных для ролей
- В `.env` удалено хранение id разработчиков
- Команды для разработчиков (`commands/dev.py`)
- Класс `PermissionsType`

## [1.2.6] - 23-08-2022

### Added
- Поддержка PostgresSQL
- Полноценная версия переключения между версиями (`prod.` и `dev.`) для разработчиков
- Описание к каждой функции
- Кеширование ролей для работы системы переключений версий

### Changed
- Структура хранения файлов на сервере
- Распределение пользовательских команд

### Fixed
- Скрипт авто-деплоя для debug версии

## [1.2.5] - 20-08-2022
### Added
- Обработка аргументов
- Начальная версия системы переключения между версиями (`prod.` и `dev.`) для разработчиков
- Обработка последнего неотвеченного сообщения в случае обновления или краша бота
- Скрипт авто-деплоя для debug версии

### Changed
- Оптимизация кода файла audioBridge.py
- Распределение `enum` объектов из файла `config.py`

### Fixed
- мелкие недочёты предыдущих версий

## [1.2.4] - 17-08-2022
### Added
- Авто-деплой релиза через tag

### Fixed
- Формат введения `.env` для поддержки `Docker`

## [1.2.3] - 13-08-2022
### Added
- Обработка плейлиста
- Получение **полной** информации о музыке (автор, название песни)
- *Гибкое* ограничение на количество обработчиков запросов: появилась возможность указать кол-во обработчиков, выделяемых на одного пользователя
- Появление пользовательских команд для работы с процессом загрузки

### Changed
- "Защита от пользователя"
- Обработка очереди запросов стала *справедливой*
- Оптимизация кода

### Fixed
- Ошибка `Vk Api Longpoll`

## [1.1.7] - 14-07-2022
### Added
- Очистка сообщений для пользователя с процессом выполнения запроса

### Removed
- Лишние обработчики событий от `Vk Api Longpoll`

## [1.1.2] - 18-05-2022
### Added
- Возможность создавать аудиофрагменты
- "Защита от пользователя"
- Ограничение на количество обработчиков **общей** очереди запросов
- Logger

### Changed
- Описания ошибок для ясности пользователя

### Fixed
- Скачивание одной песни вместо целого плейлиста при получении ссылки на него
- Обработка непредвиденных ошибок от `youtube-dl`

## [1.0.0] - 15-04-2022
- Initial release

<!-- Links -->
[keep a changelog]: https://keepachangelog.com/en/1.0.0/
[semantic versioning]: https://semver.org/spec/v2.0.0.html

<!-- Versions -->
[unreleased]: https://github.com/shonqwezon-team/AudioBridge/compare/prod...dev
[1.2.7]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.2.6...v1.2.7
[1.2.6]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.2.5...v1.2.6
[1.2.5]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.2.4...v1.2.5
[1.2.4]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.1.7...v1.2.3
[1.1.7]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.1.2...v1.1.7
[1.1.2]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.0.0...v1.1.2
[1.0.0]: https://github.com/shonqwezon-team/AudioBridge/releases/tag/v1.0.0
