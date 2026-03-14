import os

class Config:
    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'guest')

        self.db_path = os.getenv('DB_PATH', '/app/data/interpol.db')
        self.queue_name = 'interpol_queue'
        self.web_port = 8000