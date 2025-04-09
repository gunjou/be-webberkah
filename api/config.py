import os
import pytz
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine


load_dotenv()

def get_connection():
    # server = 'localhost:5432' # localhost
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    dbname = os.getenv("DB_NAME")
    username = os.getenv("DB_USER")
    password = os.getenv("DB_PASS")

    return create_engine(f'postgresql+psycopg2://{username}:{password}@{host}:{port}/{dbname}')

def get_timezone():
    wita = pytz.timezone("Asia/Makassar")
    now = datetime.now(wita)

    tanggal_now = now.date()
    jam_now = now.time()

    return tanggal_now, jam_now

def get_datetime_now():
    wita = pytz.timezone("Asia/Makassar")
    now = datetime.now(wita)
    formatted_time = now.strftime("%Y-%m-%d %H:%M:%S.") + f"{int(now.microsecond / 1000):03d}"

    return formatted_time
