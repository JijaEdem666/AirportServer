import asyncpg
import random
import string

class CommonUtils:
    @staticmethod
    async def get_db_connection():
        return await asyncpg.connect(
            user="postgres",
            password="root",
            database="kurumoch",
            host="localhost"
        )

    @staticmethod
    async def generate_flight_number(airline_code: str) -> str:
        letters = string.ascii_uppercase
        return f"{airline_code}{random.randint(100, 999)}"