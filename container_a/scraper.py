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
        # kimlik doğrulama bilgileri
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

    def extract_photo_urls(self, item: dict) -> list:
        urls = []
        links = item.get("_links", {}) or {}
        thumb = (links.get("thumbnail") or {}).get("href")
        image = (links.get("image") or {}).get("href")

        if thumb: 
            urls.append(thumb)
        if image and image not in urls:
            urls.append(image)

        return urls
    
    def normalize_notice(self, item:dict) -> dict:
        nationalities = item.get("nationalities") or []
        if isinstance(nationalities, str):
            nationalities = [nationalities]
        
        eyes_colors = item.get("eyes_colors") or []
        if isinstance(eyes_colors, str):
            eyes_colors = [eyes_colors]

        criminal_records = item.get("arrest_warrants") or []
        if isinstance(criminal_records, dict):
            criminal_records = [criminal_records]
        if not isinstance(criminal_records, list):
            criminal_records = []

        return {
        "entity_id": item.get("entity_id"),
        "name": item.get("name"),
        "forename": item.get("forename"),
        "birth_date": item.get("date_of_birth"),
        "nationalities": nationalities,
        "eyes_colors": eyes_colors,
        "sex_id": item.get("sex_id"),
        "criminal_records": criminal_records,
        "photo_urls": self.extract_photo_urls(item),
    }

    def fetch_interpol_data(self):
        data_list = []
        page = 1
        fetched_pages = 0

        try:
            while fetched_pages < self.config.max_pages:
                url = "https://ws-public.interpol.int/notices/v1/red"

                headers = {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Accept": "application/json",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Referer": "https://www.interpol.int/"
                }
                params = {
                    "resultPerPage": self.config.result_per_page,
                    "page": page
                }

                response = requests.get(
                    url,
                    headers=headers,
                    params=params,
                    impersonate="chrome116",
                    timeout=30
                )

                if response.status_code == 403:
                    alt_headers = dict(headers)
                    alt_headers["Referer"] = "https://www.interpol.int/en/How-we-work/Notices/Red-Notices/View-Red-Notices"
                    response = requests.get(url, headers=alt_headers, params=params, timeout=20)

                if response.status_code != 200:
                    print("API Request Failed! Status Code: ", response.status_code)
                    break

                try:
                    data = response.json()
                except ValueError:
                    print("API Response is not JSON")
                    break

                notices = data.get('_embedded', {}).get('notices', []) or []
                print(f"Fetched {len(notices)} notices on page {page}")

                if not notices:
                    break

                for item in notices:
                    normalized = self.normalize_notice(item)
                    if normalized.get("entity_id"):
                        data_list.append(normalized)

                fetched_pages += 1
                page += 1

                if not ((data.get("_links", {}) or {}).get("next")):
                    break

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
                'entity_id': data.get('entity_id'),
                'name': data.get('name'),
                'forename': data.get('forename'),
                'birth_date': data.get('birth_date'),
                'nationalities': data.get('nationalities', []),
                "eyes_colors": data.get("eyes_colors", []),
                "sex_id": data.get("sex_id"),
                "criminal_records": data.get("criminal_records", []),
                "photo_urls": data.get("photo_urls", []),
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
                
                if self.connection and self.connection.is_open:
                    self.connection.sleep(self.config.scrape_interval)
                else:
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