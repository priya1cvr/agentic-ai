import sqlite3

DB_PATH = "database/chatbot.db"


def create_tables():

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS chat_history
        (
            username TEXT,
            question TEXT,
            answer TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()

    conn.close()


def save_chat(
        username,
        question,
        answer
):

    conn = sqlite3.connect(DB_PATH)

    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO chat_history
        (
            username,
            question,
            answer
        )
        VALUES
        (
            ?,
            ?,
            ?
        )
        """,
        (
            username,
            question,
            answer
        )
    )

    conn.commit()

    conn.close()
