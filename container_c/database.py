from psycopg2 import connect
from psycopg2.extras import RealDictCursor


class Database:
	def __init__(self, config):
		self.config = config

	def get_connection(self):
		return connect(
			host=self.config.postgres_host,
			port=self.config.postgres_port,
			dbname=self.config.postgres_db,
			user=self.config.postgres_user,
			password=self.config.postgres_password,
		)

	def get_recent_updates(self, limit=50):
		with self.get_connection() as conn:
			with conn.cursor(cursor_factory=RealDictCursor) as cursor:
				cursor.execute(
					"""
					SELECT
						ie.entity_id,
						ie.is_update,
						ie.processed_at,
						wp.name,
						wp.forename
					FROM ingest_event ie
					JOIN wanted_person wp ON wp.id = ie.person_id
					ORDER BY ie.processed_at DESC
					LIMIT %s
					""",
					(limit,),
				)
				return [dict(row) for row in cursor.fetchall()]

	def get_notice_count(self, filters):
		where_sql, params = self._build_where(filters)
		sql = f"""
			SELECT COUNT(*) AS total
			FROM wanted_person wp
			{where_sql}
		"""

		with self.get_connection() as conn:
			with conn.cursor(cursor_factory=RealDictCursor) as cursor:
				cursor.execute(sql, params)
				return int(cursor.fetchone()["total"])

	def get_notices(self, filters, page, page_size, sort_by, sort_order):
		where_sql, params = self._build_where(filters)

		sort_map = {
			"last_updated": "wp.last_updated",
			"first_seen": "wp.first_seen",
			"date_of_birth": "wp.date_of_birth",
			"update_count": "wp.update_count",
			"entity_id": "wp.entity_id",
			"name": "wp.name",
		}
		sort_column = sort_map.get(sort_by, "wp.last_updated")
		order = "ASC" if str(sort_order).lower() == "asc" else "DESC"

		limit = max(1, min(int(page_size), 100))
		offset = max(0, (int(page) - 1) * limit)

		sql = f"""
			SELECT
				wp.id,
				wp.entity_id,
				wp.name,
				wp.forename,
				wp.date_of_birth,
				wp.first_seen,
				wp.last_updated,
				wp.update_count,
				nat.nationalities,
				eye.eye_colors,
				COALESCE(cr.has_criminal_record, false) AS has_criminal_record,
				p.object_key AS primary_photo_key
			FROM wanted_person wp
			LEFT JOIN LATERAL (
				SELECT string_agg(n.iso_code, ', ' ORDER BY n.iso_code) AS nationalities
				FROM wanted_person_nationality wpn
				JOIN nationality n ON n.id = wpn.nationality_id
				WHERE wpn.person_id = wp.id
			) nat ON true
			LEFT JOIN LATERAL (
				SELECT string_agg(ec.code, ', ' ORDER BY ec.code) AS eye_colors
				FROM wanted_person_eye_color wpe
				JOIN eye_color ec ON ec.id = wpe.eye_color_id
				WHERE wpe.person_id = wp.id
			) eye ON true
			LEFT JOIN LATERAL (
				SELECT true AS has_criminal_record
				FROM criminal_record c
				WHERE c.person_id = wp.id
				LIMIT 1
			) cr ON true
			LEFT JOIN LATERAL (
				SELECT object_key
				FROM person_photo pp
				WHERE pp.person_id = wp.id
				ORDER BY pp.is_primary DESC, pp.id ASC
				LIMIT 1
			) p ON true
			{where_sql}
			ORDER BY {sort_column} {order}
			LIMIT %s OFFSET %s
		"""

		final_params = params + [limit, offset]

		with self.get_connection() as conn:
			with conn.cursor(cursor_factory=RealDictCursor) as cursor:
				cursor.execute(sql, final_params)
				return [dict(row) for row in cursor.fetchall()]

	def get_primary_photo(self, entity_id):
		with self.get_connection() as conn:
			with conn.cursor(cursor_factory=RealDictCursor) as cursor:
				cursor.execute(
					"""
					SELECT pp.object_key, pp.content_type
					FROM wanted_person wp
					JOIN person_photo pp ON pp.person_id = wp.id
					WHERE wp.entity_id = %s
					ORDER BY pp.is_primary DESC, pp.id ASC
					LIMIT 1
					""",
					(entity_id,),
				)
				row = cursor.fetchone()
				return dict(row) if row else None

	def _build_where(self, filters):
		where = []
		params = []

		search = (filters.get("search") or "").strip()
		if search:
			where.append("(wp.entity_id ILIKE %s OR wp.name ILIKE %s OR wp.forename ILIKE %s)")
			val = f"%{search}%"
			params.extend([val, val, val])

		nationality = (filters.get("nationality") or "").strip()
		if nationality:
			where.append(
				"""
				EXISTS (
					SELECT 1
					FROM wanted_person_nationality wpn
					JOIN nationality n ON n.id = wpn.nationality_id
					WHERE wpn.person_id = wp.id
					  AND n.iso_code ILIKE %s
				)
				"""
			)
			params.append(f"%{nationality}%")

		eye_color = (filters.get("eye_color") or "").strip()
		if eye_color:
			where.append(
				"""
				EXISTS (
					SELECT 1
					FROM wanted_person_eye_color wpe
					JOIN eye_color ec ON ec.id = wpe.eye_color_id
					WHERE wpe.person_id = wp.id
					  AND (ec.code ILIKE %s OR ec.label ILIKE %s)
				)
				"""
			)
			val = f"%{eye_color}%"
			params.extend([val, val])

		has_cr = filters.get("has_criminal_record")
		if has_cr == "true":
			where.append("EXISTS (SELECT 1 FROM criminal_record c WHERE c.person_id = wp.id)")
		elif has_cr == "false":
			where.append("NOT EXISTS (SELECT 1 FROM criminal_record c WHERE c.person_id = wp.id)")

		dob_from = (filters.get("dob_from") or "").strip()
		if dob_from:
			where.append("wp.date_of_birth >= %s")
			params.append(dob_from)

		dob_to = (filters.get("dob_to") or "").strip()
		if dob_to:
			where.append("wp.date_of_birth <= %s")
			params.append(dob_to)

		if where:
			return "WHERE " + " AND ".join(where), params
		return "", params
