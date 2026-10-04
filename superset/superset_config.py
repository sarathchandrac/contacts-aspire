import os
from urllib.parse import quote_plus

import pymysql

# Superset's MySQL engine spec imports MySQLdb; let pymysql stand in for it
pymysql.install_as_MySQLdb()

SECRET_KEY = os.environ["SUPERSET_SECRET_KEY"]

# Superset metadata lives in the shared PostgreSQL container ("superset" database)
SQLALCHEMY_DATABASE_URI = "postgresql+psycopg2://{user}:{pw}@{host}:{port}/{db}".format(
    user=os.environ["POSTGRES_USER"],
    pw=quote_plus(os.environ["POSTGRES_PASSWORD"]),
    host=os.environ["POSTGRES_HOST"],
    port=os.environ["POSTGRES_PORT"],
    db=os.environ["POSTGRES_DATABASE"],
)
WTF_CSRF_ENABLED = True
