# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog],
and this project adheres to [Semantic Versioning].

## [Unreleased]

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
[unreleased]: https://github.com/shonqwezon-team/AudioBridge/compare/main...develop
[1.2.4]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.2.3...v1.2.4
[1.2.3]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.1.7...v1.2.3
[1.1.7]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.1.2...v1.1.7
[1.1.2]: https://github.com/shonqwezon-team/AudioBridge/compare/v1.0.0...v1.1.2
[1.0.0]: https://github.com/shonqwezon-team/AudioBridge/releases/tag/v1.0.0
