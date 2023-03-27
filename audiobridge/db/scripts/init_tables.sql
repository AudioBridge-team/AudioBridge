CREATE TABLE if not exists audio_requests (
    req_id INTEGER PRIMARY KEY,                 -- id запроса (сообщения в вк)
    audio_id INTEGER UNIQUE,                    -- id песни ВК, получаемый при загрузке песни
    status TEXT NOT NULL,                       -- статус обработки песни (будет писаться OK, либо наазвание ошибки)
    user_id INTEGER NOT NULL,                   -- id пользователя отправившего запрос
    url TEXT NOT NULL,                          -- url запроса
    new_title TEXT,                             -- поле для кастомного названия песни
    new_author TEXT,                            -- поле для кастомного имени автора
    is_segmented BOOLEAN NOT NULL,              -- флаг сегментирования песни
    audio_duration INTEGER NOT NULL,            -- длительность песни
    process_time INTEGER NOT NULL,              -- время обработки запроса
    date TIMESTAMP DEFAULT CURRENT_TIMESTAMP    -- дата запроса
);

CREATE TABLE if not exists users (
    user_id INTEGER PRIMARY KEY,                    -- id пользователя в вк
    role INTEGER NOT NULL,                          -- роль пользователя
    reg_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- дата регистрации пользователя, т.е. отправления первой команды /start
    last_req_date TIMESTAMP NOT NULL,               -- дата последнего сообщения
    req_count INTEGER NOT NULL,                     -- общее кол-во запросов (сообщений)
    is_promoting BOOLEAN NOT NULL                   -- включён ли режим продвижеия (название группы в авторстве песни)
);
