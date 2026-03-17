from flask import Flask, render_template, jsonify
import pika
import json
import threading
from config import Config
from database import Database
from datetime import datetime
import time

app = Flask(__name__)
config = Config()
db = Database(config.db_path)

updates = []
MAX_UPDATES = 50

class QueueConsumer:
    def __init__(self, config: Config, db: Database):
        self.config = config
        self.db = db
        self.connection = None
        self.channel = None

    # rabbitmq bağlantıyı başlat
    def connect(self):
        credentials = pika.PlainCredentials(
            self.config.rabbitmq_user,
            self.config.rabbitmq_pass
        )

        parameters = pika.ConnectionParameters(
            host = self.config.rabbitmq_host,
            port = self.config.rabbitmq_port,
            credentials = credentials
        )

        self.connection = pika.BlockingConnection(parameters)
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue = self.config.queue_name, durable=True)
        print("Listening the queue...")

    # queue'dan mesaj geldiğinde çalışacak
    def callback(self, ch, method, properties, body):
        try:
            data = json.loads(body)     # JSON -> Dict

            print("Fetched from queue: ", data.get('entity_id'))
            success, isUpdated = self.db.insert_or_update(data)

            if success:
                update_info = {
                    'id': data.get('entity_id'),
                    'entity_id': data.get('entity_id'),
                    'name': data.get('name'),
                    'forename': data.get('forename'),
                    'birth_date': data.get('birth_date'),
                    'nationality': data.get('nationality', []),
                    'timestamp': datetime.now().isoformat(),
                    'is_update': isUpdated,
                    'alert': isUpdated  # güncelleme ise alarm
                }
                
                updates.insert(0, update_info)  # başa ekle
                if(len(updates) > MAX_UPDATES):
                    updates.pop() # sondan pop et

                if(isUpdated):
                    print("UPDATED DATA")
                else:
                    print("NEW DATA")
                print("Saved to Database: ", isUpdated)

                ch.basic_ack(delivery_tag=method.delivery_tag)  # mesaj alındı, kuyruktan sil                

        except Exception as e:
            print("ERROR: ", e)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)  # mesaj alınmadı, kuyruğa geri koy                

    # queue dinlemeye başlar
    def start_consuming(self):
        if self.channel is None:
            raise Exception("Channel is not initialized. Call connect() first.")
        
        self.channel.basic_qos(prefetch_count=1)   # aynı anda sadece 1 tane veriyi işleyecek, biri bitmeden öbürüne geçme
        
        self.channel.basic_consume(
            queue = self.config.queue_name,
            on_message_callback = self.callback     # mesaj gelince çalışacak fonksiyon
        )

        self.channel.start_consuming()
        print("Started Listening the queue")

# ana sayfa
@app.route('/')
def index():
    return render_template('index.html')

# kayıtları json olarak return et
@app.route('/api/notices')
def get_notices():
    notices = db.get_all_notices()
    return jsonify(notices)

# updated verileri döner
@app.route('/api/updates')
def get_updates():
    return jsonify(updates)

# queue listener için ayrı thread aç
def start_queue_consumer():
    consumer = QueueConsumer(config, db)

    while True:
        try:
            consumer.connect()
            consumer.start_consuming()

        except Exception as e:
            print("Queue Failed: ", e , "    Reconnecting...")
            time.sleep(5)

if __name__ == '__main__':
    thread = threading.Thread(target=start_queue_consumer, daemon=True)
    thread.start()

    print("Initializing web server: http://0.0.0.0:", config.web_port)
    app.run(host='0.0.0.0', port = config.web_port)