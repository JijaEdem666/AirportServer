SELECT sequencename 
FROM pg_sequences 
WHERE schemaname = 'public' AND sequencename LIKE '%id_client%';

ALTER SEQUENCE zone_type_id_zone_type_seq RESTART WITH 1;

ALTER SEQUENCE airline_id_airline_seq RESTART WITH 1;

ALTER SEQUENCE airplane_id_airplane_seq RESTART WITH 1;

ALTER SEQUENCE city_id_city_seq RESTART WITH 5;

ALTER SEQUENCE flight_id_flight_seq RESTART WITH 1;

ALTER SEQUENCE ticket_id_ticket_seq RESTART WITH 1;

ALTER SEQUENCE zone_id_zone_seq RESTART WITH 1;

ALTER SEQUENCE client_id_client_seq RESTART WITH 5;