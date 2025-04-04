from sqlalchemy import create_engine


def get_connection():
    # server = 'localhost:5432' # localhost
    server = '109.106.255.215:5432' # server
    database = 'webberkah'
    username = 'berkah'
    password = 'berkah'
    return create_engine(f'postgresql+psycopg2://{username}:{password}@{server}/{database}')
