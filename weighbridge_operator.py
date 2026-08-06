from werkzeug.security import generate_password_hash
import mysql.connector

# Database config
conn = mysql.connector.connect(
    host='localhost',
    user='root',
    password='root',
    database='mill'
)

cursor = conn.cursor()

# Hash password
plain_password = 'wb123'
hashed_password = generate_password_hash(plain_password)

# Insert user
cursor.execute("""
    INSERT INTO users (username, password_hash, password, role)
    VALUES (%s, %s, %s, %s)
""", ('wb', hashed_password, plain_password, 'OPERATOR'))

conn.commit()

print("✅ Weighbridge operator created!")
print("Username: wb")
print("Password: wb123")
print("Role: OPERATOR")

cursor.close()
conn.close()