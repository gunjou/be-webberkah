from sqlalchemy import create_engine


def get_connection():
    server = 'localhost:5432'
    database = 'webberkah'
    username = 'berkah'
    password = 'berkah'
    return create_engine(f'postgresql+psycopg2://{username}:{password}@{server}/{database}')
