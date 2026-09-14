import pyodbc

def get_connection():

    connection = pyodbc.connect(
        "DRIVER={SQL Server};SERVER=127.0.0.1;DATABASE=BunCha;;UID=sa;PWD=HuyPhu@999;TrustServerCertificate=yes;MARS_Connection=yes;"
    )

    return connection