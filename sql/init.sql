CREATE TABLE IF NOT EXISTS wanted_person (
	id BIGSERIAL PRIMARY KEY,
	entity_id TEXT UNIQUE NOT NULL,
	name TEXT,
	forename TEXT,
	date_of_birth DATE,
	sex_id TEXT,
	first_seen TIMESTAMPTZ NOT NULL DEFAULT now(),
	last_updated TIMESTAMPTZ NOT NULL DEFAULT now(),
	update_count INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS eye_color (
	id SMALLSERIAL PRIMARY KEY,
	code TEXT UNIQUE NOT NULL,
	label TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS nationality (
	id SMALLSERIAL PRIMARY KEY,
	iso_code TEXT UNIQUE NOT NULL,
	name TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wanted_person_eye_color (
	person_id BIGINT NOT NULL REFERENCES wanted_person(id) ON DELETE CASCADE,
	eye_color_id SMALLINT NOT NULL REFERENCES eye_color(id) ON DELETE CASCADE,
	PRIMARY KEY (person_id, eye_color_id)
);

CREATE TABLE IF NOT EXISTS wanted_person_nationality (
	person_id BIGINT NOT NULL REFERENCES wanted_person(id) ON DELETE CASCADE,
	nationality_id SMALLINT NOT NULL REFERENCES nationality(id) ON DELETE CASCADE,
	PRIMARY KEY (person_id, nationality_id)
);

CREATE TABLE IF NOT EXISTS criminal_record (
	id BIGSERIAL PRIMARY KEY,
	person_id BIGINT NOT NULL REFERENCES wanted_person(id) ON DELETE CASCADE,
	record_type TEXT,
	description TEXT,
	country_code TEXT,
	created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS person_photo (
	id BIGSERIAL PRIMARY KEY,
	person_id BIGINT NOT NULL REFERENCES wanted_person(id) ON DELETE CASCADE,
	source_url TEXT NOT NULL,
	object_key TEXT UNIQUE NOT NULL,
	content_type TEXT,
	etag TEXT,
	size_bytes BIGINT,
	is_primary BOOLEAN NOT NULL DEFAULT false,
	created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ingest_event (
	id BIGSERIAL PRIMARY KEY,
	person_id BIGINT NOT NULL REFERENCES wanted_person(id) ON DELETE CASCADE,
	entity_id TEXT NOT NULL,
	is_update BOOLEAN NOT NULL DEFAULT false,
	processed_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_wanted_person_entity_id ON wanted_person(entity_id);
CREATE INDEX IF NOT EXISTS idx_wanted_person_last_updated ON wanted_person(last_updated DESC);
CREATE INDEX IF NOT EXISTS idx_wanted_person_dob ON wanted_person(date_of_birth);

CREATE INDEX IF NOT EXISTS idx_wpn_person_id ON wanted_person_nationality(person_id);
CREATE INDEX IF NOT EXISTS idx_wpn_nationality_id ON wanted_person_nationality(nationality_id);

CREATE INDEX IF NOT EXISTS idx_wpec_person_id ON wanted_person_eye_color(person_id);
CREATE INDEX IF NOT EXISTS idx_wpec_eye_color_id ON wanted_person_eye_color(eye_color_id);

CREATE INDEX IF NOT EXISTS idx_criminal_record_person_id ON criminal_record(person_id);
CREATE INDEX IF NOT EXISTS idx_person_photo_person_id ON person_photo(person_id);
CREATE INDEX IF NOT EXISTS idx_ingest_event_processed_at ON ingest_event(processed_at DESC);
