import os

class Config:
    def __init__(self):
        self.rabbitmq_host = os.getenv('RABBITMQ_HOST', 'localhost')
        self.rabbitmq_port = int(os.getenv('RABBITMQ_PORT', 5672))
        self.rabbitmq_user = os.getenv('RABBITMQ_USER', 'guest')
        self.rabbitmq_pass = os.getenv('RABBITMQ_PASS', 'guest')
        self.queue_name = os.getenv('QUEUE_NAME', 'interpol_queue')
        self.scrape_interval = int(os.getenv('SCRAPE_INTERVAL', 300))
        self.result_per_page = int(os.getenv('RESULT_PER_PAGE', 160))
        self.max_pages = int(os.getenv('MAX_PAGES', 3))

        

# env dosyasında ilgili bilgiler yoksa ikinci parametreleri kullan