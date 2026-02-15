import requests
import json
import time
import pika
from bs4 import BeautifulSoup
from config import Config
from datetime import datetime

class Scraper:
    def __init__(self, config:Config):
        self.config = config
        self.connection = None
        self.channel = None