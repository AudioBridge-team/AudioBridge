CREATE TABLE if not exists audio_requests (
	user_id INTEGER PRIMARY KEY,
	audio_id TEXT UNIQUE,
	audio_url TEXT NOT NULL,
	audio_name TEXT,
	audio_author TEXT,
	audio_segment TEXT,
	date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
