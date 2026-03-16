FROM python:3.11-slim

WORKDIR /program

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD [ "python", "-u", "scraper.py" ]

# önce requirements kopyalamamızın sebebi Docker layer cache mekanizmasının 
# kaynak kodu değişikliği sonrası dependency'leri yeniden yüklememesi için
# build süresi kısalır yani