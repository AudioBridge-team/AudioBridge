CREATE OR REPLACE FUNCTION user_insert_trigger_func() RETURNS trigger AS $$
BEGIN
    INSERT INTO user_settings VALUES(NEW.user_id);
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER user_insert_trigger
    AFTER INSERT ON users
    FOR EACH ROW
    EXECUTE FUNCTION user_insert_trigger_func();


CREATE OR REPLACE FUNCTION update_lastMsgDate_trigger_func() RETURNS trigger AS $$
BEGIN
    UPDATE users SET last_msg_date = NEW.msg_date WHERE user_id = NEW.author_id;
RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER update_lastMsgDate_trigger
    AFTER INSERT ON vk_messages
    FOR EACH ROW
    EXECUTE FUNCTION update_lastMsgDate_trigger_func();


CREATE OR REPLACE FUNCTION check_user_token_func() RETURNS trigger AS $$
BEGIN
    IF EXISTS (SELECT 1 FROM users WHERE (user_id = NEW.user_id) and (token IS NOT NULL)) THEN
        RETURN NEW;
    ELSE
        RAISE EXCEPTION 'User % does not have token in users table', NEW.user_id;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE TRIGGER check_user_token_trigger
    BEFORE UPDATE OF is_agent ON user_settings
    FOR EACH ROW
    EXECUTE FUNCTION check_user_token_func();
