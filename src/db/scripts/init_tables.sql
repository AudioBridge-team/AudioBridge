CREATE TABLE if not exists roles (
	user_id INTEGER PRIMARY KEY,
	permissions INTEGER[] NOT NULL,
	version_name TEXT DEFAULT 'v1.0.0' NOT NULL
);

CREATE TABLE if not exists audio_requests (
	user_id INTEGER PRIMARY KEY,
	audio_id TEXT UNIQUE,
	audio_url TEXT NOT NULL,
	audio_name TEXT,
	audio_author TEXT,
	audio_segment TEXT,
	date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
