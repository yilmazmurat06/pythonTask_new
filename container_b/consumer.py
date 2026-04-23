import json
import time
from io import BytesIO

import pika
import requests
from minio import Minio

from config import Config
from database import Database


class Consumer:
	def __init__(self, config: Config):
		self.config = config
		self.db = Database(config)
		self.connection = None
		self.channel = None
		self.minio = Minio(
			endpoint=self.config.minio_endpoint,
			access_key=self.config.minio_access_key,
			secret_key=self.config.minio_secret_key,
			secure=self.config.minio_secure,
		)
		self.ensure_bucket()

	def ensure_bucket(self):
		if not self.minio.bucket_exists(self.config.minio_bucket):
			self.minio.make_bucket(self.config.minio_bucket)
			print("Created MinIO bucket:", self.config.minio_bucket)

	def connect_rabbitmq(self):
		credentials = pika.PlainCredentials(
			self.config.rabbitmq_user, self.config.rabbitmq_pass
		)
		parameters = pika.ConnectionParameters(
			host=self.config.rabbitmq_host,
			port=self.config.rabbitmq_port,
			credentials=credentials,
			heartbeat=60,
		)
		self.connection = pika.BlockingConnection(parameters)
		self.channel = self.connection.channel()
		self.channel.queue_declare(queue=self.config.queue_name, durable=True)
		self.channel.basic_qos(prefetch_count=1)

	def _upload_photo(self, entity_id: str, photo_url: str, is_primary: bool, person_id: int):
		try:
			response = requests.get(photo_url, timeout=30)
			if response.status_code != 200:
				print("Photo fetch non-200:", response.status_code, photo_url)
				return
			if not response.content:
				print("Photo fetch empty content:", photo_url)
				return

			content_type = response.headers.get("Content-Type", "image/jpeg")
			object_key = self.db.object_key_from_url(entity_id, photo_url)

			data_bytes = response.content
			data_stream = BytesIO(data_bytes)

			self.minio.put_object(
				bucket_name=self.config.minio_bucket,
				object_name=object_key,
				data=data_stream,
				length=len(data_bytes),
				content_type=content_type,
			)

			self.db.upsert_photo(
				person_id=person_id,
				source_url=photo_url,
				object_key=object_key,
				content_type=content_type,
				etag=None,
				size_bytes=len(data_bytes),
				is_primary=is_primary,
			)
		except Exception as exc:
			print("Photo upload failed:", photo_url, exc)

	def callback(self, ch, method, properties, body):
		try:
			data = json.loads(body)
			entity_id = data.get("entity_id")
			if not entity_id:
				ch.basic_ack(delivery_tag=method.delivery_tag)
				return

			success, is_update, person_id = self.db.upsert_notice(data)
			if not success:
				ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
				return

			for index, photo_url in enumerate(data.get("photo_urls", [])):
				self._upload_photo(
					entity_id=entity_id,
					photo_url=photo_url,
					is_primary=(index == 0),
					person_id=person_id,
				)

			print("Saved:", entity_id, "updated:", is_update)
			ch.basic_ack(delivery_tag=method.delivery_tag)

		except Exception as exc:
			print("Consumer callback error:", exc)
			ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

	def run(self):
		while True:
			try:
				self.connect_rabbitmq()
				self.channel.basic_consume(
					queue=self.config.queue_name,
					on_message_callback=self.callback,
				)
				print("Consumer listening queue:", self.config.queue_name)
				self.channel.start_consuming()
			except KeyboardInterrupt:
				break
			except Exception as exc:
				print("Consumer reconnecting after error:", exc)
				time.sleep(5)

		if self.connection and self.connection.is_open:
			self.connection.close()


if __name__ == "__main__":
	cfg = Config()
	Consumer(cfg).run()
