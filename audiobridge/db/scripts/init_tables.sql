CREATE TABLE if not exists users (
    user_id int PRIMARY KEY,
    role smallint NOT NULL DEFAULT 0,
    first_msg_date timestamp(0) NOT NULL DEFAULT current_timestamp,
    last_msg_date timestamp(0) NOT NULL DEFAULT current_timestamp
);

CREATE TABLE if not exists user_settings (
    user_id int PRIMARY KEY references users(user_id),
    is_promoting boolean NOT NULL DEFAULT true
);


CREATE TABLE if not exists vk_messages (
    msg_id int PRIMARY KEY,
    msg_type smallint NOT NULL DEFAULT 0,
    author_id int NOT NULL references users(user_id),
    msg_body text NOT NULL,
    msg_date timestamp(0) NOT NULL DEFAULT current_timestamp
);

CREATE TABLE if not exists convert_requests (
    task_id serial PRIMARY KEY,
    msg_request_id int NOT NULL references vk_messages(msg_id),
    download_url text NOT NULL,
    audio_id int UNIQUE references vk_audio(audio_id),
    status_str text,
    process_time real(2),
    request_date timestamp(0) NOT NULL DEFAULT current_timestamp
);

CREATE TABLE if not exists vk_audio (
    audio_id int PRIMARY KEY,
    custom_title text,
    custom_author text,
    is_segmented boolean NOT NULL DEFAULT false,
    audio_duration real(2) NOT NULL
);
