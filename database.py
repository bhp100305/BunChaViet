import pyodbc

def get_connection():

    connection = pyodbc.connect(
        "DRIVER={ODBC Driver 17 for SQL Server};"
        "SERVER=THAFIE\\SQLEXPRESS;"
        "DATABASE=BunCha;"
        "Trusted_Connection=yes;"
        "TrustServerCertificate=yes;"
    )

    return connection