from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import asyncpg
from datetime import datetime, time

from models.models import ClientCreate, UserResponse, LoginRequest, CityCreate, CityResponse, CityUpdate,\
    AirplaneResponse, AirplaneCreate, AirplaneUpdate, AirlineResponse, AirlineCreate, AirlineUpdate, FlightCreate, \
    FlightUpdate, BookingRequest, UserUpdate
from typing import List, Optional
from utils.commonUtils import CommonUtils

class ServiceHost():
    def __init__(self):
        self.PORT = 8000
        self.HOST = "localhost"
        self.app = FastAPI()

        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @self.app.get("/")
        async def root():
            return {"message": "Aviation Server is running!"}

        @self.app.put("/user/update/")
        async def update_user(user_data: UserUpdate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка существования пользователя
                    current_user = await conn.fetchrow(
                        "SELECT * FROM client WHERE id_client = $1",
                        user_data.id
                    )
                    if not current_user:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Пользователь не найден"
                        )

                    # Проверка уникальности нового email
                    if user_data.email != current_user['login']:
                        email_exists = await conn.fetchval(
                            "SELECT 1 FROM client WHERE login = $1 AND id_client != $2",
                            user_data.email, user_data.id
                        )
                        if email_exists:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail="Этот email уже занят"
                            )

                    if not user_data.password:
                        user_data.password = current_user['password']

                    # Хеширование пароля при необходимости
                    '''
                    password_hash = current_user['password']
                    if user_data.password:
                        password_hash = pwd_context.hash(user_data.password)
                        '''
                    # Обновление данных
                    await conn.execute(
                        """
                        UPDATE client SET
                            login = $1,
                            password = $2,
                            first_name = $3,
                            second_name = $4,
                            third_name = $5,
                            passport_seria = $6,
                            passport_number = $7,
                            phone = $8
                        WHERE id_client = $9
                        """,
                        user_data.email,
                        user_data.password,
                        user_data.firstname,
                        user_data.lastname,
                        user_data.patronymic,
                        user_data.passSeries,
                        user_data.passNumber,
                        user_data.phone,
                        user_data.id
                    )

                    return {"message": "Данные успешно обновлены"}

            except asyncpg.exceptions.UniqueViolationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ошибка уникальности данных"
                )
            finally:
                await conn.close()

        # 1. Получение истории бронирований
        @self.app.get("/bookings/{client_id}", response_model=List[dict])
        async def get_client_bookings(client_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                query = """
                SELECT 
                    f.id_flight as flight_id,
                    f.flight_number,
                    f.departure_date,
                    f.departure_time,
                    f.arrival_time,
                    c.id_city as city_id,
                    c.city_name,
                    c.distance,
                    a.id_airline,
                    a.airline_name,
                    p.id_airplane,
                    p.airplane_name,
                    p.model,
                    p.flight_distance,
                    t.id_ticket,
                    t.seat_number,
                    t.price,
                    cht.status as ticket_status,
                    cht.first_name as p_first_name,
                    cht.second_name as p_second_name,
                    cht.third_name as p_third_name,
                    cht.passport_seria as p_passport_seria,
                    cht.passport_number as p_passport_number,
                    cl.id_client,
                    cl.first_name as c_first_name,
                    cl.second_name as c_second_name,
                    cl.third_name as c_third_name,
                    cl.login,
                    cl.phone,
                    cl.passport_seria as c_passport_seria,
                    cl.passport_number as c_passport_number
                FROM client_has_ticket cht
                JOIN ticket t ON cht.ticket_id_ticket = t.id_ticket
                JOIN flight f ON t.flight_id_flight = f.id_flight
                JOIN city c ON f.arrival_city = c.id_city
                JOIN airline a ON f.airline_id_airline = a.id_airline
                JOIN airplane p ON f.airplane_id_airplane = p.id_airplane
                JOIN client cl ON cht.client_id_client = cl.id_client
                WHERE cht.client_id_client = $1
                """

                records = await conn.fetch(query, client_id)

                # Группировка по рейсам
                bookings = []
                if len(records) != 0:
                    flag_id = records[0]['flight_id']
                    flight = {}
                    tickets = []
                    for record in records:
                        flight_id = record['flight_id']
                        if flag_id != flight_id:
                            bookings.append({
                                "user": {
                                    "id": record['id_client'],
                                    "firstname": record['c_first_name'],
                                    "lastname": record['c_second_name'],
                                    "patronymic": record['c_third_name'],
                                    "email": record['login'],
                                    "phone": record['phone'],
                                    "passSeries": record['c_passport_seria'],
                                    "passNumber": record['c_passport_number']
                                },
                                "flight": flight,
                                "tickets": tickets
                            })
                            tickets = []
                            flag_id = flight_id
                        # Получаем информацию о кабине
                        cabin = await get_cabin_details(conn, record['id_airplane'])

                        flight = {
                            "id": flight_id,
                            "number": record['flight_number'],
                            "departureDate": {
                                "day": record['departure_date'].day,
                                "month": record['departure_date'].month,
                                "year": record['departure_date'].year
                            },
                            "flightTiming": {
                                "departureHour": int(str(record['departure_time']).split(':')[0]),
                                "departureMinutes": int(str(record['departure_time']).split(':')[1]),
                                "arrivalHour": int(str(record['arrival_time']).split(':')[0]),
                                "arrivalMinutes": int(str(record['arrival_time']).split(':')[1])
                            },
                            "city": {
                                "id": record['city_id'],
                                "name": record['city_name'],
                                "distance": record['distance']
                            },
                            "airline": {
                                "id": record['id_airline'],
                                "name": record['airline_name']
                            },
                            "plane": {
                                "id": record['id_airplane'],
                                "name": record['airplane_name'],
                                "model": record['model'],
                                "flightDistance": record['flight_distance'],
                                "cabin": cabin
                            }
                        }
                        tickets.append(
                            {
                                "id": record['id_ticket'],
                                "seat": record['seat_number'],
                                "price": record['price'],
                                "isCancelled": record['ticket_status'],
                                "passenger": {
                                    "lastname": record['p_second_name'],
                                    "firstname": record['p_first_name'],
                                    "patronymic": record['p_third_name'],
                                    "passSeries": record['p_passport_seria'],
                                    "passNumber": record['p_passport_number']
                                }
                            }
                        )
                    bookings.append({
                        "user": {
                            "id": records[-1]['id_client'],
                            "firstname": records[-1]['c_first_name'],
                            "lastname": records[-1]['c_second_name'],
                            "patronymic": records[-1]['c_third_name'],
                            "email": records[-1]['login'],
                            "phone": records[-1]['phone'],
                            "passSeries": records[-1]['c_passport_seria'],
                            "passNumber": records[-1]['c_passport_number']
                        },
                        "flight": flight,
                        "tickets": tickets
                    })

                return bookings

            finally:
                await conn.close()

        async def get_cabin_details(conn, plane_id: int):
            zones = await conn.fetch("""
            SELECT z.passes, z.rows, z.seats_per_row, zt.type_name
            FROM cabin c
            JOIN zone z ON c.zone1 = z.id_zone 
                         OR c.zone2 = z.id_zone 
                         OR c.zone3 = z.id_zone
            JOIN zone_type zt ON z.zone_type_id = zt.id_zone_type
            WHERE c.airplane_id_airplane = $1
            """, plane_id)

            return {
                "zones": [
                    {
                        "passes": z['passes'],
                        "rows": z['rows'],
                        "seatsPerRow": z['seats_per_row'],
                        "type": z['type_name']
                    } for z in zones
                ]
            }

        # 2. Отмена бронирования
        @self.app.post("/cancelTicket/{ticket_id}")
        async def cancel_booking(ticket_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверяем существование билета
                    exists = await conn.fetchval(
                        "SELECT 1 FROM client_has_ticket WHERE ticket_id_ticket = $1",
                        ticket_id
                    )
                    if not exists:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Бронь не найдена"
                        )

                    # Обновляем статус
                    await conn.execute(
                        "UPDATE client_has_ticket SET status = true WHERE ticket_id_ticket = $1",
                        ticket_id
                    )

                    return {"message": "Бронь успешно отменена"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка отмены брони: {str(e)}"
                )
            finally:
                await conn.close()

        # 1. Получение занятых мест
        @self.app.get("/flights/{flight_id}/taken-seats/", response_model=List[str])
        async def get_taken_seats(flight_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                seats = await conn.fetch(
                    "SELECT seat_number FROM ticket WHERE flight_id_flight = $1",
                    flight_id
                )
                return [s['seat_number'] for s in seats]
            finally:
                await conn.close()

        # 2. Создание бронирования
        @self.app.post("/bookings/", status_code=status.HTTP_201_CREATED)
        async def create_booking(booking_data: BookingRequest):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка занятости мест
                    taken_seats = await get_taken_seats(booking_data.flight['id'])
                    for ticket in booking_data.tickets:
                        if ticket.seat in taken_seats:
                            raise HTTPException(
                                status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f"Место {ticket.seat} уже занято"
                            )

                    # Создание билетов
                    ticket_ids = []
                    for ticket in booking_data.tickets:
                        ticket_id = await conn.fetchval(
                            """
                            INSERT INTO ticket (
                                flight_id_flight,
                                price,
                                seat_number
                            ) VALUES ($1, $2, $3)
                            RETURNING id_ticket
                            """,
                            booking_data.flight['id'],
                            ticket.price,
                            ticket.seat
                        )
                        ticket_ids.append(ticket_id)

                        # Связь с пользователем
                        await conn.execute(
                            """
                            INSERT INTO client_has_ticket (
                                client_id_client,
                                ticket_id_ticket,
                                first_name,
                                second_name,
                                third_name,
                                passport_seria,
                                passport_number,
                                status
                            ) VALUES ($1, $2, $3, $4, $5, $6, $7, false)
                            """,
                            booking_data.user['id'],
                            ticket_id,
                            ticket.passenger.firstname,
                            ticket.passenger.lastname,
                            ticket.passenger.patronymic,
                            ticket.passenger.passSeries,
                            ticket.passenger.passNumber
                        )

                    return {"message": "Бронирование успешно создано", "ticket_ids": ticket_ids}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Ошибка создания бронирования: {str(e)}"
                )
            finally:
                await conn.close()

        # 1. Создание рейса
        @self.app.post("/flights/", status_code=status.HTTP_200_OK)
        async def create_flight(flight_data: FlightCreate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Генерация номера рейса
                    airline_code = (await conn.fetchval(
                        "SELECT airline_name FROM airline WHERE id_airline = $1",
                        flight_data.airline['id']
                    ))[:2].upper()

                    flight_number = await CommonUtils.generate_flight_number(airline_code)

                    # Преобразование времени в объекты time
                    departure_time = time(
                        flight_data.flightTiming.departureHour,
                        flight_data.flightTiming.departureMinutes
                    )

                    arrival_time = time(
                        flight_data.flightTiming.arrivalHour,
                        flight_data.flightTiming.arrivalMinutes
                    )

                    # Вставка рейса
                    flight_id = await conn.fetchval(
                        """
                        INSERT INTO flight (
                            flight_number,
                            departure_date,
                            departure_time,
                            arrival_time,
                            airline_id_airline,
                            airplane_id_airplane,
                            arrival_city
                        ) VALUES ($1, $2, $3, $4, $5, $6, $7)
                        RETURNING id_flight
                        """,
                        flight_number,
                        datetime(
                            flight_data.departureDate.year,
                            flight_data.departureDate.month,
                            flight_data.departureDate.day
                        ),
                        departure_time,
                        arrival_time,
                        flight_data.airline['id'],
                        flight_data.plane['id'],
                        flight_data.city['id']
                    )
                    return {"message": "Рейс успешно создан", "id": flight_id}

            except Exception as e:
                print(e)
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не удалось создать рейс"
                )
            finally:
                await conn.close()

        # 2. Обновление рейса
        @self.app.put("/flights/")
        async def update_flight(flight_data: FlightUpdate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка наличия билетов
                    has_tickets = await conn.fetchval(
                        "SELECT 1 FROM ticket WHERE flight_id_flight = $1",
                        flight_data.id
                    )
                    if has_tickets:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя редактировать рейс с купленными билетами"
                        )

                    # Преобразование времени в объекты time
                    departure_time = time(
                        flight_data.flightTiming.departureHour,
                        flight_data.flightTiming.departureMinutes
                    )

                    arrival_time = time(
                        flight_data.flightTiming.arrivalHour,
                        flight_data.flightTiming.arrivalMinutes
                    )

                    # Обновление данных
                    await conn.execute(
                        """
                        UPDATE flight SET
                            departure_date = $1,
                            departure_time = $2,
                            arrival_time = $3,
                            airline_id_airline = $4,
                            airplane_id_airplane = $5,
                            arrival_city = $6
                        WHERE id_flight = $7
                        """,
                        datetime(
                            flight_data.departureDate.year,
                            flight_data.departureDate.month,
                            flight_data.departureDate.day
                        ),
                        departure_time,
                        arrival_time,
                        flight_data.airline['id'],
                        flight_data.plane['id'],
                        flight_data.city['id'],
                        flight_data.id
                    )
                    return {"message": "Рейс успешно обновлен"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            finally:
                await conn.close()

        # 3. Удаление рейса
        @self.app.delete("/flights/{flight_id}")
        async def delete_flight(flight_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка билетов
                    has_tickets = await conn.fetchval(
                        "SELECT 1 FROM ticket WHERE flight_id_flight = $1",
                        flight_id
                    )
                    if has_tickets:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить рейс с купленными билетами"
                        )

                    await conn.execute(
                        "DELETE FROM flight WHERE id_flight = $1",
                        flight_id
                    )
                    return {"message": "Рейс успешно удален"}

            finally:
                await conn.close()

        # 4. Получение всех рейсов
        @self.app.get("/flights/", response_model=List[dict])
        async def get_all_flights():
            conn = await CommonUtils.get_db_connection()
            try:
                flights = []
                records = await conn.fetch("SELECT * FROM flight")

                for record in records:
                    # Получение связанных данных
                    city = await conn.fetchrow(
                        "SELECT * FROM city WHERE id_city = $1",
                        record['arrival_city']
                    )

                    airline = await conn.fetchrow(
                        "SELECT * FROM airline WHERE id_airline = $1",
                        record['airline_id_airline']
                    )

                    plane = await conn.fetchrow(
                        "SELECT * FROM airplane WHERE id_airplane = $1",
                        record['airplane_id_airplane']
                    )

                    cabin = await conn.fetchrow(
                        """
                        SELECT 
                        airplane_id_airplane,
                        zone_number,
                        zone1,
                        zone2,
                        zone3
                    FROM cabin 
                    WHERE airplane_id_airplane = $1
                        """,
                        plane['id_airplane']
                    )

                    zones = []
                    for i in range(1, 4):
                        zone_id = cabin[f'zone{i}']
                        if zone_id:
                            zone = await conn.fetchrow(
                                """
                                SELECT z.*, zt.type_name 
                                FROM zone z
                                JOIN zone_type zt ON z.zone_type_id = zt.id_zone_type
                                WHERE z.id_zone = $1
                                """,
                                zone_id
                            )
                            zones.append({
                                "passes": zone['passes'],
                                "rows": zone['rows'],
                                "seatsPerRow": zone['seats_per_row'],
                                "type": zone['type_name']
                            })

                    flights.append({
                        "id": record['id_flight'],
                        "number": record['flight_number'],
                        "departureDate": {
                            "day": record['departure_date'].day,
                            "month": record['departure_date'].month,
                            "year": record['departure_date'].year
                        },
                        "flightTiming": {
                            "departureHour": int(str(record['departure_time']).split(':')[0]),
                            "departureMinutes": int(str(record['departure_time']).split(':')[1]),
                            "arrivalHour": int(str(record['arrival_time']).split(':')[0]),
                            "arrivalMinutes": int(str(record['arrival_time']).split(':')[1])
                        },
                        "city": {
                            "id": city['id_city'],
                            "name": city['city_name'],
                            "distance": city['distance']
                        },
                        "airline": {
                            "id": airline['id_airline'],
                            "name": airline['airline_name']
                        },
                        "plane": {
                            "id": plane['id_airplane'],
                            "name": plane['airplane_name'],
                            "model": plane['model'],
                            "flightDistance": plane['flight_distance'],
                            "cabin": {"zones": zones}
                        }
                    })

                return flights

            finally:
                await conn.close()

        # 5. Получение самолетов авиакомпании
        @self.app.get("/airlines/{airline_id}/planes/", response_model=List[dict])
        async def get_airline_planes(airline_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                planes = await conn.fetch(
                    "SELECT * FROM airplane WHERE airline_id_airline = $1",
                    airline_id
                )
                dicks = []
                for plane in planes:
                    cabin = await conn.fetchrow(
                        """
                        SELECT 
                        airplane_id_airplane,
                        zone_number,
                        zone1,
                        zone2,
                        zone3
                    FROM cabin 
                    WHERE airplane_id_airplane = $1
                        """,
                        plane['id_airplane']
                    )

                    zones = []
                    for i in range(1, 4):
                        zone_id = cabin[f'zone{i}']
                        if zone_id:
                            zone = await conn.fetchrow(
                                """
                                SELECT z.*, zt.type_name 
                                FROM zone z
                                JOIN zone_type zt ON z.zone_type_id = zt.id_zone_type
                                WHERE z.id_zone = $1
                                """,
                                zone_id
                            )
                            zones.append({
                                "passes": zone['passes'],
                                "rows": zone['rows'],
                                "seatsPerRow": zone['seats_per_row'],
                                "type": zone['type_name']
                            })
                    dick = {
                        "id": plane['id_airplane'],
                        "name": plane['airplane_name'],
                        "model": plane['model'],
                        "flightDistance": plane['flight_distance'],
                        "cabin": {
                            "zones": zones
                        }
                    }
                    dicks.append(dick)
                return dicks

            finally:
                await conn.close()

        # 1. Создание авиакомпании
        @self.app.post("/airlines/", status_code=status.HTTP_200_OK)
        async def create_airline(data: AirlineCreate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка существующей авиакомпании
                    exists = await conn.fetchval(
                        "SELECT 1 FROM airline WHERE airline_name = $1",
                        data.airline.name
                    )
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Авиакомпания с таким названием уже существует"
                        )

                    # Создание авиакомпании
                    airline_id = await conn.fetchval(
                        "INSERT INTO airline (airline_name) VALUES ($1) RETURNING id_airline",
                        data.airline.name
                    )

                    # Привязка самолетов
                    for plane in data.planes:
                        await conn.execute(
                            "UPDATE airplane SET airline_id_airline = $1 WHERE id_airplane = $2",
                            airline_id,
                            plane.id
                        )

                    return {"message": "Авиакомпания успешно создана", "id": airline_id}

            except asyncpg.exceptions.ForeignKeyViolationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Один из самолетов не найден"
                )
            finally:
                await conn.close()

        # 2. Обновление авиакомпании
        @self.app.put("/airlines/")
        async def update_airline(data: AirlineUpdate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка существования авиакомпании
                    current = await conn.fetchrow(
                        "SELECT * FROM airline WHERE id_airline = $1",
                        data.airline.id
                    )
                    if not current:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Авиакомпания не найдена"
                        )

                    # Обновление названия
                    await conn.execute(
                        "UPDATE airline SET airline_name = $1 WHERE id_airline = $2",
                        data.airline.name,
                        data.airline.id
                    )

                    # Удаление старых привязок
                    await conn.execute(
                        "UPDATE airplane SET airline_id_airline = NULL WHERE airline_id_airline = $1",
                        data.airline.id
                    )

                    # Добавление новых привязок
                    for plane in data.planes:
                        await conn.execute(
                            "UPDATE airplane SET airline_id_airline = $1 WHERE id_airplane = $2",
                            data.airline.id,
                            plane.id
                        )

                    return {"message": "Авиакомпания успешно обновлена"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не удалось обновить авиакомпанию"
                )
            finally:
                await conn.close()

        # 3. Удаление авиакомпании
        @self.app.delete("/airlines/{airline_id}")
        async def delete_airline(airline_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка использования в рейсах
                    used = await conn.fetchval(
                        "SELECT 1 FROM flight WHERE airline_id_airline = $1",
                        airline_id
                    )
                    if used:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Нельзя удалить авиакомпанию, так как она используется в рейсах"
                        )

                    # Удаление привязок самолетов
                    await conn.execute(
                        "UPDATE airplane SET airline_id_airline = NULL WHERE airline_id_airline = $1",
                        airline_id
                    )

                    # Удаление авиакомпании
                    await conn.execute(
                        "DELETE FROM airline WHERE id_airline = $1",
                        airline_id
                    )

                    return {"message": "Авиакомпания успешно удалена"}

            finally:
                await conn.close()

        # 4. Получение всех авиакомпаний
        @self.app.get("/airlines/", response_model=List[AirlineResponse])
        async def get_all_airlines():
            conn = await CommonUtils.get_db_connection()
            try:
                airlines = []
                airline_records = await conn.fetch("SELECT * FROM airline")

                for airline in airline_records:
                    # Получение самолетов авиакомпании
                    fetch_planes = await conn.fetch(
                        """
                        SELECT 
                            id_airplane as id,
                            airplane_name as name,
                            model,
                            flight_distance
                        FROM airplane 
                        WHERE airline_id_airline = $1
                        """,
                        airline['id_airline']
                    )

                    planes = []

                    for plane in fetch_planes:
                        cabin = await conn.fetchrow(
                            """
                            SELECT 
                            airplane_id_airplane,
                            zone_number,
                            zone1,
                            zone2,
                            zone3
                        FROM cabin 
                        WHERE airplane_id_airplane = $1
                            """,
                            plane['id']
                        )

                        zones = []
                        for i in range(1, 4):
                            zone_id = cabin[f'zone{i}']
                            if zone_id:
                                zone = await conn.fetchrow(
                                    """
                                    SELECT z.*, zt.type_name 
                                    FROM zone z
                                    JOIN zone_type zt ON z.zone_type_id = zt.id_zone_type
                                    WHERE z.id_zone = $1
                                    """,
                                    zone_id
                                )
                                zones.append({
                                    "passes": zone['passes'],
                                    "rows": zone['rows'],
                                    "seatsPerRow": zone['seats_per_row'],
                                    "type": zone['type_name']
                                })

                        planes.append({
                            "id": plane["id"],
                            "name": plane["name"],
                            "model": plane["model"],
                            "flightDistance": plane["flight_distance"],
                            "cabin": {"zones": zones}
                        })

                    airlines.append({
                        "airline": {
                            "id": airline['id_airline'],
                            "name": airline['airline_name']
                        },
                        "planes": planes
                    })

                if not airlines:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нет доступных авиакомпаний"
                    )

                return airlines

            finally:
                await conn.close()

        # 1. Сохранение нового самолета
        @self.app.post("/airplanes/", status_code=status.HTTP_200_OK)
        async def create_airplane(airplane: AirplaneCreate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка существующего самолета
                    exists = await conn.fetchval(
                        "SELECT 1 FROM airplane WHERE airplane_name = $1 AND model = $2",
                        airplane.name, airplane.model
                    )
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Такой самолёт уже существует"
                        )

                    # Вставка самолета
                    airplane_id = await conn.fetchval(
                        """
                        INSERT INTO airplane 
                            (airplane_name, model, flight_distance)
                        VALUES ($1, $2, $3)
                        RETURNING id_airplane
                        """,
                        airplane.name, airplane.model, airplane.flightDistance
                    )

                    # Вставка зон
                    zone_ids = []
                    for zone in airplane.cabin.zones:
                        # Получение типа зоны
                        zone_type_id = await conn.fetchval(
                            "SELECT id_zone_type FROM zone_type WHERE type_name = $1",
                            zone.type
                        )

                        # Создание зоны
                        zone_id = await conn.fetchval(
                            """
                            INSERT INTO zone 
                                (passes, rows, seats_per_row, zone_type_id)
                            VALUES ($1, $2, $3, $4)
                            RETURNING id_zone
                            """,
                            zone.passes, zone.rows, zone.seatsPerRow, zone_type_id
                        )
                        zone_ids.append(zone_id)

                    # Заполнение None для отсутствующих зон
                    zone_ids += [None] * (3 - len(zone_ids))

                    # Связь зон с самолетом
                    await conn.execute(
                        """
                        INSERT INTO cabin 
                            (airplane_id_airplane, zone_number, zone1, zone2, zone3)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        airplane_id,
                        len(airplane.cabin.zones),
                        *zone_ids[:3]
                    )

                    return {"message": "Самолёт успешно добавлен", "id": airplane_id}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            finally:
                await conn.close()

        # 2. Обновление самолета
        @self.app.put("/airplanes/")
        async def update_airplane(airplane: AirplaneUpdate):
            conn = await CommonUtils.get_db_connection()
            try:
                async with conn.transaction():
                    # Проверка существования самолета
                    current = await conn.fetchrow(
                        "SELECT * FROM airplane WHERE id_airplane = $1",
                        airplane.id
                    )
                    if not current:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Самолёт не найден"
                        )

                    # Обновление данных самолета
                    await conn.execute(
                        """
                        UPDATE airplane SET
                            airplane_name = $1,
                            model = $2,
                            flight_distance = $3
                        WHERE id_airplane = $4
                        """,
                        airplane.name, airplane.model,
                        airplane.flightDistance, airplane.id
                    )

                    # Обновление зон (удаление старых и создание новых)
                    await conn.execute(
                        "DELETE FROM cabin WHERE airplane_id_airplane = $1",
                        airplane.id
                    )

                    # Вставка зон
                    zone_ids = []
                    for zone in airplane.cabin.zones:
                        # Получение типа зоны
                        zone_type_id = await conn.fetchval(
                            "SELECT id_zone_type FROM zone_type WHERE type_name = $1",
                            zone.type
                        )

                        # Создание зоны
                        zone_id = await conn.fetchval(
                            """
                            INSERT INTO zone 
                                (passes, rows, seats_per_row, zone_type_id)
                            VALUES ($1, $2, $3, $4)
                            RETURNING id_zone
                            """,
                            zone.passes, zone.rows, zone.seatsPerRow, zone_type_id
                        )
                        zone_ids.append(zone_id)

                    # Заполнение None для отсутствующих зон
                    zone_ids += [None] * (3 - len(zone_ids))

                    # Связь зон с самолетом
                    await conn.execute(
                        """
                        INSERT INTO cabin 
                            (airplane_id_airplane, zone_number, zone1, zone2, zone3)
                        VALUES ($1, $2, $3, $4, $5)
                        """,
                        airplane.id,
                        len(airplane.cabin.zones),
                        *zone_ids[:3]
                    )

                    return {"message": "Самолёт успешно обновлён"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ошибка обновления: " + str(e)
                )
            finally:
                await conn.close()

        # 3. Удаление самолета
        @self.app.delete("/airplanes/{airplane_id}")
        async def delete_airplane(airplane_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                # Проверка использования в рейсах
                used = await conn.fetchval(
                    "SELECT 1 FROM flight WHERE airplane_id_airplane = $1",
                    airplane_id
                )
                if used:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нельзя удалить самолёт, так как он используется в рейсах"
                    )

                # Удаление самолета
                await conn.execute(
                    "DELETE FROM airplane WHERE id_airplane = $1",
                    airplane_id
                )
                return {"message": "Самолёт успешно удалён"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=str(e)
                )
            finally:
                await conn.close()

        # 4. Получение всех самолетов
        @self.app.get("/airplanes/", response_model=List[AirplaneResponse])
        async def get_all_airplanes():
            conn = await CommonUtils.get_db_connection()
            try:
                airplanes = []
                records = await conn.fetch("SELECT * FROM airplane")

                for record in records:
                    # Получение информации о кабине
                    cabin = await conn.fetchrow(
                        """
                        SELECT zone1, zone2, zone3 
                        FROM cabin 
                        WHERE airplane_id_airplane = $1
                        """,
                        record['id_airplane']
                    )

                    zones = []
                    for i in range(1, 4):
                        zone_id = cabin[f'zone{i}']
                        if zone_id:
                            zone = await conn.fetchrow(
                                """
                                SELECT z.*, zt.type_name 
                                FROM zone z
                                JOIN zone_type zt ON z.zone_type_id = zt.id_zone_type
                                WHERE z.id_zone = $1
                                """,
                                zone_id
                            )
                            zones.append({
                                "passes": zone['passes'],
                                "rows": zone['rows'],
                                "seatsPerRow": zone['seats_per_row'],
                                "type": zone['type_name']
                            })

                    airplanes.append({
                        "id": record['id_airplane'],
                        "name": record['airplane_name'],
                        "model": record['model'],
                        "flightDistance": record['flight_distance'],
                        "cabin": {"zones": zones}
                    })

                if not airplanes:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нет доступных самолётов"
                    )

                return airplanes

            finally:
                await conn.close()

        # 1. Сохранение нового города
        @self.app.post("/cities/", status_code=status.HTTP_200_OK)
        async def create_city(city: CityCreate):
            conn = await CommonUtils.get_db_connection()
            try:
                # Проверка существующего города
                exists = await conn.fetchval(
                    "SELECT 1 FROM city WHERE city_name = $1",
                    city.name
                )
                if exists:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Город с таким названием уже существует"
                    )

                # Вставка нового города
                city_id = await conn.fetchval(
                    "INSERT INTO city (city_name, distance) VALUES ($1, $2) RETURNING id_city",
                    city.name, city.distance
                )
                return {"message": "Город успешно добавлен", "id": city_id}

            except asyncpg.exceptions.UniqueViolationError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Город с таким названием уже существует"
                )
            finally:
                await conn.close()

        # 2. Обновление города
        @self.app.put("/cities/")
        async def update_city(city: CityUpdate):
            conn = await CommonUtils.get_db_connection()
            try:
                # Проверка существования города
                current = await conn.fetchrow(
                    "SELECT * FROM city WHERE id_city = $1",
                    city.id
                )
                if not current:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Город не найден"
                    )

                # Проверка уникальности нового имени
                if current['city_name'] != city.name:
                    exists = await conn.fetchval(
                        "SELECT 1 FROM city WHERE city_name = $1 AND id_city != $2",
                        city.name, city.id
                    )
                    if exists:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Город с таким названием уже существует"
                        )

                # Обновление данных
                await conn.execute(
                    "UPDATE city SET city_name = $1, distance = $2 WHERE id_city = $3",
                    city.name, city.distance, city.id
                )
                return {"message": "Город успешно обновлён"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Не удалось обновить город"
                )
            finally:
                await conn.close()

        # 3. Удаление города
        @self.app.delete("/cities/{city_id}")
        async def delete_city(city_id: int):
            conn = await CommonUtils.get_db_connection()
            try:
                # Проверка использования города в рейсах
                used = await conn.fetchval(
                    "SELECT 1 FROM flight WHERE arrival_city = $1",
                    city_id
                )
                if used:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нельзя удалить город, так как он используется в рейсах"
                    )

                # Удаление города
                await conn.execute(
                    "DELETE FROM city WHERE id_city = $1",
                    city_id
                )
                return {"message": "Город успешно удалён"}

            except Exception as e:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Ошибка при удалении города"
                )
            finally:
                await conn.close()

        # 4. Получение всех городов
        @self.app.get("/cities/", response_model=List[CityResponse])
        async def get_all_cities():
            conn = await CommonUtils.get_db_connection()
            try:
                cities = await conn.fetch(
                    "SELECT id_city as id, city_name as name, distance FROM city"
                )
                if not cities:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Нет доступных городов"
                    )
                return [dict(city) for city in cities]

            finally:
                await conn.close()

        # Авторизация
        @self.app.post("/login/", response_model=UserResponse)
        async def login(login_data: LoginRequest):
            conn = await CommonUtils.get_db_connection()
            try:
                user = await conn.fetchrow(
                    """
                    SELECT 
                        id_client,
                        first_name,
                        second_name,
                        third_name,
                        phone,
                        passport_seria,
                        passport_number,
                        EXISTS(SELECT 1 FROM admin WHERE login = $1) as is_admin
                    FROM client 
                    WHERE login = $1 AND password = $2
                    """,
                    login_data.email,
                    login_data.password
                )

                if not user:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Неверный логин или пароль"
                    )

                response = {
                    "user_id": user["id_client"],
                    "is_admin": user["is_admin"]
                }

                response.update({
                    "firstname": user['first_name'],
                    "lastname": user['second_name'],
                    "patronymic": user['third_name'],
                    "phone": user["phone"],
                    "passSeries": user['passport_seria'],
                    "passNumber": user['passport_number']
                })

                return response

            finally:
                await conn.close()

        @self.app.post("/register/")
        async def create_client(client: ClientCreate):
            conn = await CommonUtils.get_db_connection()
            try:
                # Проверка уникальности логина
                exists = await conn.fetchval(
                    "SELECT 1 FROM client WHERE login = $1",
                    client.login
                )
                if exists:
                    raise HTTPException(status_code=400, detail="Login already exists")

                # Вставка нового пользователя
                query = """
                    INSERT INTO client (
                        first_name, 
                        second_name, 
                        third_name,
                        login,
                        password,
                        phone,
                        passport_seria,
                        passport_number
                    )
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                    RETURNING id_client
                """
                result = await conn.execute(
                    query,
                    client.firstname,
                    client.lastname,
                    client.patronymic,
                    client.login,
                    client.password,
                    client.phone,
                    client.passSeries,
                    client.passNumber
                )
                print(result)
                return {"message": "User created", "user_id": result}

            except asyncpg.exceptions.UniqueViolationError:
                raise HTTPException(status_code=400, detail="Login already exists")
            finally:
                await conn.close()



    def start(self):
        print("Server started at port " + str(self.PORT))
        uvicorn.run(
            self.app,
            host="localhost",
            port=8000
        )