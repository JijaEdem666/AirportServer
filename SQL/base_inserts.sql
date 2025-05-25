-- 1. Заполнение типов зон
INSERT INTO zone_type (type_name) 
VALUES 
    ('Эконом класс'),
    ('Бизнес класс'),
    ('Первый класс');

-- 2. Заполнение зон для каждого типа
-- Эконом класс (3 зоны с разной конфигурацией)
INSERT INTO zone (passes, rows, seats_per_row, zone_type_id)
VALUES
    (150, 30, 5, 1),  -- Зона 1: 30 рядов по 5 мест
    (120, 20, 6, 1),  -- Зона 2: 20 рядов по 6 мест
    (200, 40, 5, 1);  -- Зона 3: 40 рядов по 5 мест

-- Бизнес класс (2 зоны)
INSERT INTO zone (passes, rows, seats_per_row, zone_type_id)
VALUES
    (50, 10, 5, 2),   -- Зона 4: 10 рядов по 5 мест
    (30, 5, 6, 2);    -- Зона 5: 5 рядов по 6 мест

-- Первый класс (1 зона)
INSERT INTO zone (passes, rows, seats_per_row, zone_type_id)
VALUES
    (20, 4, 5, 3);    -- Зона 6: 4 ряда по 5 мест

-- 3. Авиакомпании
INSERT INTO airline (airline_name)
VALUES
    ('Аэрофлот'),
    ('S7 Airlines'),
    ('Ural Airlines');

-- 4. Самолеты
INSERT INTO airplane (airplane_name, model, flight_distance, airline_id_airline)
VALUES
    ('Боинг 737', 'Boeing 737-800', 5000, 1),
    ('Аэробус A320', 'Airbus A320neo', 6000, 2),
    ('Сухой Суперджет', 'SSJ-100', 3000, 3);

-- 5. Распределение зон в салонах самолетов
-- Для Боинга 737: все три класса
INSERT INTO cabin (airplane_id_airplane, zone_number, zone1, zone2, zone3)
VALUES
    (1, 3, 1, 4, 6);  -- zone1=эконом, zone2=бизнес, zone3=первый

-- Для Аэробуса A320: эконом и бизнес
INSERT INTO cabin (airplane_id_airplane, zone_number, zone1, zone2)
VALUES
    (2, 2, 2, 5);

-- Для Суперджета: только эконом
INSERT INTO cabin (airplane_id_airplane, zone_number, zone1)
VALUES
    (3, 1, 3);

-- 6. Города
INSERT INTO city (city_name, distance)
VALUES
    ('Москва', 0),     -- Город отправления
    ('Санкт-Петербург', 650),
    ('Сочи', 1350),
    ('Новосибирск', 2800);

-- 7. Рейсы
INSERT INTO flight (
    flight_number, 
    departure_date, 
    departure_time, 
    arrival_time, 
    airline_id_airline, 
    airplane_id_airplane, 
    arrival_city
) VALUES
    ('SU 123', '2024-03-20', '08:00', '10:30', 1, 1, 2),
    ('S7 456', '2024-03-21', '12:15', '15:45', 2, 2, 3),
    ('UR 789', '2024-03-22', '18:00', '21:00', 3, 3, 4);

-- 8. Клиенты
INSERT INTO client (
    first_name, 
    second_name, 
    third_name, 
    login, 
    password, 
    phone, 
    passport_seria, 
    passport_number
) VALUES
    ('Иван', 'Иванов', 'Иванович', 'ivanov', 'qwerty123', '+79161234567', '1234', '567890'),
    ('Мария', 'Петрова', NULL, 'petrova', 'pass321', '+79059876543', '4321', '098765');

-- 9. Билеты
INSERT INTO ticket (flight_id_flight, price, seat_number)
VALUES
    (1, 5000, '15A'),  -- Эконом
    (1, 15000, '2B'),  -- Бизнес
    (2, 7000, '10C'),  -- Эконом
    (3, 3000, '5D');   -- Эконом


-- 10. Связь клиентов и билетов (с дополнительными полями)
INSERT INTO client_has_ticket (
    client_id_client,
    ticket_id_ticket,
    first_name,
    second_name,
    third_name,
    passport_seria,
    passport_number,
    status
)
SELECT 
    c.id_client,
    t.id_ticket,
    c.first_name,
    c.second_name,
    c.third_name,
    c.passport_seria,
    c.passport_number,
    CASE 
        WHEN t.id_ticket IN (1, 4) THEN true  -- Активные билеты
        ELSE false                             -- Неактивные
    END
FROM 
    client c
CROSS JOIN ticket t
WHERE 
    (c.id_client = 1 AND t.id_ticket IN (1, 2)) OR
    (c.id_client = 2 AND t.id_ticket IN (3, 4));