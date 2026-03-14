import requests
import json
import time
import pika
from config import Config
from datetime import datetime

# Verileri çekmek (scraping) ve RabbitMQ'ya göndermek için
class Scraper:
    def __init__(self, config:Config):
        self.config = config
        self.connection = None
        self.channel = None

    # RabbitMQ'ya bağlanmak için
    def connect_rabbitmq(self):
        # kimlik doğrulama bilgileri - RabbitMQ'ya bağlanmak için gereken kullanıcı adı ve şifre
        credentials = pika.PlainCredentials(self.config.rabbitmq_user, 
                                            self.config.rabbitmq_pass)
        
        # RabbitMq bağlantı parameretreleri - sunucu adresi, portu ve credentials bilgileri
        parameters = pika.ConnectionParameters(host=self.config.rabbitmq_host, 
                                               port=self.config.rabbitmq_port, 
                                               credentials=credentials)
        
        # tcp bağlantısı 
        self.connection = pika.BlockingConnection(parameters)
        # kanal oluşturma - sunucu ile iletişim 
        self.channel = self.connection.channel()

        self.channel.queue_declare(queue=self.config.queue_name, durable=True)
        print("RabbitMQ baglantisi kuruldu: ", self.config.rabbitmq_host)


    def fetch_interpol_data(self):
        try:
            url = "https://ws-public.interpol.int/notices/v1/red"
            response = requests.get(url)
            
            if response.status_code == 200:
                data = response.json()
                
                data_list = []
                for item in data.get('notices', []):
                    notice = {
                        'id': item.get('entity_id'),
                        'name': item.get('name'),
                        'forename': item.get('forename'),
                        'birth_date': item.get('date_of_birth'),
                        'nationality': item.get('nationalities', []),
                    }

                    data_list.append(notice)
        
        except Exception as e:
            print("Error fetching data from Interpol API: ", e)
            return []

        return data_list
    
    # çekilen verileri kuyruğa göndermek için
    def send_to_rabbitmq_queue(self, data):
        try:
            message = {
                'timestamp': datetime.now(),
                'entity_id': data.get('id'),
                'name': data.get('name'),
                'forename': data.get('forename'),
                'birth_date': data.get('date_of_birth'),
                'nationality': data.get('nationalities', [])
            }

            self.channel.basic_publish(
                exchange = '',
                routing_key = self.config.queue_name,
                body = json.dumps(message),
                properties = pika.BasicProperties(delivery_mode = 2) # kuyruğa gönderilen verinin kalıcı
                                                                     # olmasını sağlamak için mode = 2     
            )

            print("Message sent to queue: ", message['entity_id'])

        except Exception as e:
            print("Queue sending failed: ", e)

    # asıl çalışma
    def run(self):
        print("_____Initializing Scraper Service_____ ")

        while True:
            try:
                self.connect_rabbitmq()
                break

            except Exception as e:
                print("RabbitMQ Connection Failed: ", e)

        while True:
            try:
                print(datetime.now(), "\t Fetching Datas...")
                notices = self.fetch_interpol_data()

                for notice in notices:
                    self.send_to_rabbitmq_queue(notice)

                print(datetime.now(), "\tCompleted. All notices are fetched")

            except KeyboardInterrupt:
                print("Ctrl+C signal detected. Stopped")
                break

            except Exception as e:
                print("ERROR: ", e)

        if self.connection:
            self.connection.close()

if __name__ == "__main__":
    config = Config()
    scraper = Scraper()
    scraper.run()