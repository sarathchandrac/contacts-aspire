FROM apache/superset:latest
USER root
RUN uv pip install --python /app/.venv/bin/python psycopg2-binary pymysql
COPY superset_config.py /app/pythonpath/superset_config.py
COPY bootstrap.sh /app/bootstrap.sh
RUN chmod +x /app/bootstrap.sh
USER superset
EXPOSE 8088
CMD ["/app/bootstrap.sh"]
