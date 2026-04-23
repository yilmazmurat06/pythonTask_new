from typing import Optional, Tuple
import hashlib

import psycopg2


class Database:
    def __init__(self, config):
        self.config = config

    def get_connection(self):
        return psycopg2.connect(
            host=self.config.postgres_host,
            port=self.config.postgres_port,
            dbname=self.config.postgres_db,
            user=self.config.postgres_user,
            password=self.config.postgres_password,
        )

    def _get_or_create_nationality(self, cursor, iso_code: str) -> int:
        cursor.execute(
            """
            INSERT INTO nationality (iso_code, name)
            VALUES (%s, %s)
            ON CONFLICT (iso_code) DO UPDATE SET name = EXCLUDED.name
            RETURNING id
            """,
            (iso_code, iso_code),
        )
        return cursor.fetchone()[0]

    def _get_or_create_eye_color(self, cursor, code: str) -> int:
        cursor.execute(
            """
            INSERT INTO eye_color (code, label)
            VALUES (%s, %s)
            ON CONFLICT (code) DO UPDATE SET label = EXCLUDED.label
            RETURNING id
            """,
            (code, code),
        )
        return cursor.fetchone()[0]

    def upsert_notice(self, data: dict) -> Tuple[bool, bool, int]:
        entity_id = data.get("entity_id")
        if not entity_id:
            return False, False, -1

        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "SELECT id, update_count FROM wanted_person WHERE entity_id = %s",
                    (entity_id,),
                )
                existing = cursor.fetchone()

                if existing:
                    person_id = existing[0]
                    next_count = (existing[1] or 1) + 1
                    cursor.execute(
                        """
                        UPDATE wanted_person
                        SET name = %s,
                            forename = %s,
                            date_of_birth = %s,
                            sex_id = %s,
                            last_updated = now(),
                            update_count = %s
                        WHERE id = %s
                        """,
                        (
                            data.get("name"),
                            data.get("forename"),
                            data.get("birth_date"),
                            data.get("sex_id"),
                            next_count,
                            person_id,
                        ),
                    )
                    is_update = True
                else:
                    cursor.execute(
                        """
                        INSERT INTO wanted_person (
                            entity_id, name, forename, date_of_birth, sex_id, first_seen, last_updated, update_count
                        ) VALUES (%s, %s, %s, %s, %s, now(), now(), 1)
                        RETURNING id
                        """,
                        (
                            entity_id,
                            data.get("name"),
                            data.get("forename"),
                            data.get("birth_date"),
                            data.get("sex_id"),
                        ),
                    )
                    person_id = cursor.fetchone()[0]
                    is_update = False

                cursor.execute("DELETE FROM wanted_person_nationality WHERE person_id = %s", (person_id,))
                for iso in data.get("nationalities", []):
                    if not iso:
                        continue
                    nat_id = self._get_or_create_nationality(cursor, str(iso).upper())
                    cursor.execute(
                        """
                        INSERT INTO wanted_person_nationality (person_id, nationality_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (person_id, nat_id),
                    )

                cursor.execute("DELETE FROM wanted_person_eye_color WHERE person_id = %s", (person_id,))
                for color in data.get("eyes_colors", []):
                    if not color:
                        continue
                    color_id = self._get_or_create_eye_color(cursor, str(color).upper())
                    cursor.execute(
                        """
                        INSERT INTO wanted_person_eye_color (person_id, eye_color_id)
                        VALUES (%s, %s)
                        ON CONFLICT DO NOTHING
                        """,
                        (person_id, color_id),
                    )

                cursor.execute("DELETE FROM criminal_record WHERE person_id = %s", (person_id,))
                for record in data.get("criminal_records", []):
                    if isinstance(record, dict):
                        record_type = record.get("charge") or record.get("type") or "unknown"
                        description = record.get("description") or record.get("issuing_country_id")
                        country_code = record.get("issuing_country_id")
                    else:
                        record_type = "text"
                        description = str(record)
                        country_code = None

                    cursor.execute(
                        """
                        INSERT INTO criminal_record (
                            person_id, record_type, description, country_code, created_at
                        ) VALUES (%s, %s, %s, %s, now())
                        """,
                        (person_id, record_type, description, country_code),
                    )

                cursor.execute(
                    """
                    INSERT INTO ingest_event (person_id, entity_id, is_update, processed_at)
                    VALUES (%s, %s, %s, now())
                    """,
                    (person_id, entity_id, is_update),
                )

            conn.commit()
        return True, is_update, person_id

    def upsert_photo(
        self,
        person_id: int,
        source_url: str,
        object_key: str,
        content_type: Optional[str],
        etag: Optional[str],
        size_bytes: Optional[int],
        is_primary: bool,
    ):
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO person_photo (
                        person_id, source_url, object_key, content_type, etag, size_bytes, is_primary, created_at
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, now())
                    ON CONFLICT (object_key) DO UPDATE SET
                        person_id = EXCLUDED.person_id,
                        source_url = EXCLUDED.source_url,
                        content_type = EXCLUDED.content_type,
                        etag = EXCLUDED.etag,
                        size_bytes = EXCLUDED.size_bytes,
                        is_primary = EXCLUDED.is_primary
                    """,
                    (person_id, source_url, object_key, content_type, etag, size_bytes, is_primary),
                )
            conn.commit()

    @staticmethod
    def object_key_from_url(entity_id: str, url: str) -> str:
        digest = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]
        return f"{entity_id}/{digest}.jpg"
    