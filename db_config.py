DB_CONFIG = {
    'host': os.environ.get('MYSQLHOST', 'localhost'),
    'user': os.environ.get('MYSQLUSER', 'root'),
    'password': os.environ.get('MYSQLPASSWORD', 'root'),
    'database': os.environ.get('MYSQLDATABASE', 'mill'),
    'port': int(os.environ.get('MYSQLPORT', 3306))
}