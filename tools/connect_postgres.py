import psycopg2
from psycopg2 import OperationalError

def create_connection():
    try:
        connection = psycopg2.connect(
            user="kornelko",
            password="skslovan",
            host="192.168.88.97",  # or your Synology NAS IP address
            port="5433",
            database="kornelko"
        )
        print("Connection to PostgreSQL DB successful")
        return connection
    except OperationalError as e:
        print(f"The error '{e}' occurred")
        return None

def check_connection(connection):
    try:
        cursor = connection.cursor()
        cursor.execute("SELECT 1")
        print("Connection is available")
    except OperationalError as e:
        print(f"The error '{e}' occurred")

if __name__ == "__main__":
    conn = create_connection()
    if conn:
        check_connection(conn)
        conn.close()