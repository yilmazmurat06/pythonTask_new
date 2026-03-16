import json
import time
import pika
from curl_cffi import requests
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
        data_list = []

        try:
            url = "https://ws-public.interpol.int/notices/v1/red"

            # bot olarak algilanmamak icin User-Agent ve JSON istegi
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.interpol.int/"
            }
            params = {
                "resultPerPage": 20
            }

            # curl_cffi 
            response = requests.get(
                url, 
                headers=headers, 
                params=params, 
                impersonate="chrome116", 
                timeout=30
            )

            if response.status_code == 403:
                # Bazi ortamlarda 403 alinabiliyor; ikinci bir deneme yap
                alt_headers = dict(headers)
                alt_headers["Referer"] = "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices"
                response = requests.get(url, headers=alt_headers, params=params, timeout=20)

            if response.status_code == 200:
                try:
                    data = response.json()
                    print("RAW KEYS:", data.keys())
                    print("RAW DATA:", str(data)[:300])
                except ValueError:
                    print("API Response is not JSON")
                    return []

                notices = data.get('_embedded', {}).get('notices', [])
                print(f"Fetched {len(notices)} notices")

                if notices is None:
                    notices = []

            elif response.status_code == 403:
                print("API 403 Forbidden Gercek tarayici taklidi basarisiz.")
                notices = []
            else:
                print("API Request Failed! Status Code: ", response.status_code)
                notices = []

            for item in notices:
                notice = {
                    'id': item.get('entity_id'),
                    'name': item.get('name'),
                    'forename': item.get('forename'),
                    'birth_date': item.get('date_of_birth'),
                    'nationality': item.get('nationalities', []),
                }

                data_list.append(notice)

            print("Fetched notices count: ", len(data_list))

        except Exception as e:
            print("Error fetching data from Interpol API: ", e)
            return []

        return data_list
    
    # çekilen verileri kuyruğa göndermek için
    def send_to_rabbitmq_queue(self, data):
        try:
            message = {
                'timestamp': datetime.now().isoformat(),
                'entity_id': data.get('id'),
                'name': data.get('name'),
                'forename': data.get('forename'),
                'birth_date': data.get('birth_date'),
                'nationality': data.get('nationality', [])
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
                time.sleep(5)

        while True:
            try:
                print(datetime.now(), "\t Fetching Datas...")
                notices = self.fetch_interpol_data()

                for notice in notices:
                    self.send_to_rabbitmq_queue(notice)

                print(datetime.now(), "\tCompleted. All notices are fetched")
                time.sleep(self.config.scrape_interval)

            except KeyboardInterrupt:
                print("Ctrl+C signal detected. Stopped")
                break

            except Exception as e:
                print("ERROR: ", e)

        if self.connection:
            self.connection.close()

if __name__ == '__main__':
    config = Config()
    scraper = Scraper(config)
    scraper.run()