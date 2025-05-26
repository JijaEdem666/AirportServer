from pydantic import BaseModel, constr
from typing import Optional, List

class ClientCreate(BaseModel):
    firstname: str
    lastname: str
    patronymic: str
    login: str
    password: str
    phone: str
    passSeries: str
    passNumber: str

# Модель для запроса
class LoginRequest(BaseModel):
    email: str
    password: str

# Модель для успешного ответа
class UserResponse(BaseModel):
    user_id: int
    is_admin: bool
    firstname: str | None = None
    lastname: str | None = None
    patronymic: str | None = None
    phone: str | None = None
    passSeries: str | None = None
    passNumber: str | None = None

# Модель для ошибки
class ErrorResponse(BaseModel):
    error: str

#Модели для городов
class CityCreate(BaseModel):
    name: str
    distance: int

class CityUpdate(BaseModel):
    id: int
    name: str
    distance: int

class CityResponse(BaseModel):
    id: int
    name: str
    distance: int

#Модели для самолётов
class ZoneData(BaseModel):
    passes: int
    rows: int
    seatsPerRow: int
    type: str

class CabinData(BaseModel):
    zones: List[ZoneData]

class AirplaneCreate(BaseModel):
    name: str
    model: str
    flightDistance: int
    cabin: CabinData

class AirplaneUpdate(AirplaneCreate):
    id: int

class AirplaneResponse(BaseModel):
    id: int
    name: str
    model: str
    flightDistance: int
    cabin: CabinData

#Модели для авиакомпаний
class AirlineDataForCreate(BaseModel):
    name: str

class AirlineDataForUpdate(BaseModel):
    id: int
    name: str

class PlaneData(BaseModel):
    id: int

class AirlineCreate(BaseModel):
    airline: AirlineDataForCreate
    planes: List[PlaneData]

class AirlineUpdate(BaseModel):
    airline: AirlineDataForUpdate
    planes: List[PlaneData]

class PlaneDataResponse(PlaneData):
    name: str
    model: str
    flightDistance: int
    cabin: CabinData

class AirlineResponse(BaseModel):
    airline: AirlineDataForUpdate
    planes: List[PlaneDataResponse]

#Модели для рейсов
class DateModel(BaseModel):
    day: int
    month: int
    year: int

class TimeModel(BaseModel):
    departureHour: int
    departureMinutes: int
    arrivalHour: int
    arrivalMinutes: int

class FlightCreate(BaseModel):
    departureDate: DateModel
    flightTiming: TimeModel
    city: dict
    airline: dict
    plane: dict

class FlightUpdate(FlightCreate):
    id: int
    number: str

# Модели для бронирования
class Passenger(BaseModel):
    lastname: str
    firstname: str
    patronymic: str
    passSeries: str
    passNumber: str

class TicketRequest(BaseModel):
    seat: str
    price: int
    isCancelled: bool
    passenger: Passenger

class BookingRequest(BaseModel):
    user: dict
    flight: dict
    tickets: List[TicketRequest]

# Модель ответа для бронирования

# Модель для ЛК
class UserUpdate(BaseModel):
    id: int
    email: str
    password: Optional[str] = None
    lastname: str
    firstname: str
    patronymic: Optional[str] = None
    passSeries: str
    passNumber: str
    phone: str