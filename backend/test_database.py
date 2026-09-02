from database import get_connection

conn = get_connection()

tables = conn.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
""").fetchall()

print("Tables:")
for table in tables:
    print("-", table["name"])

conn.close()