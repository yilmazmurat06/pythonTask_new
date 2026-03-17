import os

class Config:
    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'guest')
        self.scrape_interval = int(os.getenv('SCRAPE_INTERVAL', 300))
        self.queue_name = 'interpol_queue'

# env dosyasında ilgili bilgiler yoksa ikinci parametreleri kullan