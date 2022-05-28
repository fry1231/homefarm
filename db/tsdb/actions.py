from influxdb import InfluxDBClient
from config import CONFIG


client = InfluxDBClient(host=CONFIG.hostname,
                        port=CONFIG.tsdb_port,
                        username=CONFIG.tsdb_username,
                        password=CONFIG.tsdb_password)


