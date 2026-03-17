import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional

# veritabanını yönetimi sınıfı

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()

    # database bağlantısı için
    def get_connection(self):
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        return connection
    
    # veritabanında tablo oluşturma
    def init_database(self):
        connection = self.get_connection()
        cursor = connection.cursor()

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS interpol_notices (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                entity_id TEXT UNIQUE NOT NULL,
                name TEXT,
                forename TEXT,
                date_of_birth TEXT,
                nationalities TEXT,
                first_seen TIMESTAMP,
                last_updated TIMESTAMP,
                update_count INTEGER DEFAULT 1
            )
        ''')

        connection.commit() # değişiklikleri kaydet
        connection.close()  # kapat

        print("Database is ready.")

    # veriyi ekler veya günceller
    def insert_or_update(self, data: Dict):
        connection = self.get_connection()
        cursor = connection.cursor()

        try:
            entity_id = data.get('entity_id')

            # ? sql injection yapılmasını engeller
            cursor.execute('SELECT id, update_count FROM interpol_notices WHERE entity_id = ?', {entity_id: entity_id})
            existing = cursor.fetchone()

            if existing:
                cursor.execute('''
                    UPDATE interpol_notices
                    SET name = ?, forename = ?, date_of_birth = ?,
                        nationalities = ?, last_updated = ?, update_count = ?
                    WHERE entity_id = ?
                ''', (
                    data.get('name'),
                    data.get('forename'),
                    data.get('birth_date'),
                    json.dumps(data.get('nationality', [])),
                    datetime.now().isoformat(),
                    existing['update_count'] + 1,
                    entity_id
                ))

                connection.commit()
                connection.close()
                return True, True
        
            else:
                cursor.execute('''
                    INSERT INTO interpol_notices
                    (entity_id, name, forename, date_of_birth, nationalities, first_seen, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    entity_id,
                    data.get('name'),
                    data.get('forename'),
                    data.get('birth_date'),
                    json.dumps(data.get('nationality', [])),
                    datetime.now().isoformat(),
                    datetime.now().isoformat()
                ))

                connection.commit()
                return True, False

        except Exception as e:
            print("Database Error: ", e)
            connection.close()
            return False, False
        
        finally:
            connection.close()
        

    def get_all_notices(self):
        connnection = self.get_connection()
        cursor = connnection.cursor()

        cursor.execute(''' SELECT * FROM interpol_notices ORDER BY last_updated DESC LIMIT 100''')

        rows = cursor.fetchall()
        connnection.close()

        return [dict(row) for row in rows]  # AI söyledi burayı anlamadım?
    