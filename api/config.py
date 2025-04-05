from datetime import datetime
import pytz
from sqlalchemy import create_engine


def get_connection():
    # server = 'localhost:5432' # localhost
    server = '109.106.255.215:5432' # server
    database = 'webberkah'
    username = 'berkah'
    password = 'berkah'
    return create_engine(f'postgresql+psycopg2://{username}:{password}@{server}/{database}')

def get_timezone():
    wita = pytz.timezone("Asia/Makassar")
    now = datetime.now(wita)

    tanggal_now = now.date()
    jam_now = now.time()

    return tanggal_now, jam_now

