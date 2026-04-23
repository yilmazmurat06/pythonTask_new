import os


class Config:
	def __init__(self):
		self.web_port = int(os.getenv("WEB_PORT", 8080))

		self.postgres_host = os.getenv("POSTGRES_HOST", "localhost")
		self.postgres_port = int(os.getenv("POSTGRES_PORT", 5432))
		self.postgres_db = os.getenv("POSTGRES_DB", "interpol")
		self.postgres_user = os.getenv("POSTGRES_USER", "postgres")
		self.postgres_password = os.getenv("POSTGRES_PASSWORD", "postgres")

		self.minio_endpoint = os.getenv("MINIO_ENDPOINT", "localhost:9000")
		self.minio_access_key = os.getenv("MINIO_ACCESS_KEY", "minioadmin")
		self.minio_secret_key = os.getenv("MINIO_SECRET_KEY", "minioadmin")
		self.minio_bucket = os.getenv("MINIO_BUCKET", "interpol-photos")
		self.minio_secure = os.getenv("MINIO_SECURE", "false").lower() == "true"
