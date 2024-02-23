import sqlite3


class DBConnection:

    def __init__(self, db_name="../../db_sqlite/my_database.db"):
        self.db_connection = sqlite3.connect(db_name, check_same_thread=False)
        self.db_cursor = self.db_connection.cursor()

    def select_query(self, query):
        self.db_cursor.execute(query)
        result = self.db_cursor.fetchall()
        return result

    def commit_query(self, query):
        self.db_cursor.execute(query)
        self.db_connection.commit()

    def close_connection(self):
        self.db_connection.close()
