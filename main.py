from typing import Annotated
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Security
from sqlmodel import Session, select, join, and_, or_, not_, Sequence
from db import init_db, get_session
from models2 import Ships,Ports,Users,Records,Favorite,Reports,SearchRecordsInfo, ReportBlockInfo, Token, TokenData, UserCreate, UserUpdate, User_Roles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
import statistics
from jose import JWTError, jwt
from passlib.context import CryptContext
import os
from dotenv import load_dotenv

from fastapi import FastAPI, APIRouter, Response, Request
from starlette.background import BackgroundTask
from fastapi.routing import APIRoute
from starlette.types import Message
from typing import Dict, Any
#app = FastAPI()

init_db()
SessionDep = Annotated[Session, Depends(get_session)]
# Основное приложение FastAPI
from fastapi import FastAPI

app = FastAPI()

# Конфигурация для хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Конфигурация для JWT
SECRET_KEY = os.environ.get("SECRET_KEY")  # Замените на реальный секретный ключ
ALGORITHM = os.environ.get("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.environ.get("ACCESS_TOKEN_EXPIRE_MINUTES"))

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="users/token")
# Вспомогательные функции
def verify_password(plain_password: str, hashed_password: str):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str):
    return pwd_context.hash(password)

def authenticate_user(db: Session, username: str, password: str):
    user = db.exec(select(Users).where(Users.login == username)).first()
    if not user:
        return False
    if not verify_password(password, user.hashed_pwd):
        return False
    return user

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_session)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = TokenData(username=username)
    except JWTError as e:
        print(f"JWT Error: {e}")  # Логируем ошибку
        raise credentials_exception
    
    # Добавим логирование для отладки
    print(f"Looking for user with login: {token_data.username}")
    
    user = db.exec(select(Users).where(Users.login == token_data.username)).first()
    if user is None:
        print("User not found in database")
        raise credentials_exception
    return user

async def get_current_active_user(current_user: Users = Depends(get_current_user)):
    # Здесь можно добавить проверку на активность пользователя, если нужно
    return current_user

# Роутер для портов
router_ports = APIRouter(prefix="/ports", tags=["ports"])

@router_ports.get("/", response_model=List[Ports])
def read_ports(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    ports = db.exec(select(Ports).offset(skip).limit(limit)).all()
    return ports

@router_ports.get("/{port_number}", response_model=Ports)
def read_port(port_number: int, db: Session = Depends(get_session)):
    port = db.get(Ports, port_number)
    if not port:
        raise HTTPException(status_code=404, detail="Port not found")
    return port


# Роутер для кораблей
router_ships = APIRouter(prefix="/ships", tags=["ships"])

@router_ships.get("/", response_model=List[Ships])
def read_ships(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    ships = db.exec(select(Ships).offset(skip).limit(limit)).all()
    return ships

@router_ships.get("/{ship_number}", response_model=Ships)
def read_ship(ship_number: int, db: Session = Depends(get_session)):
    ship = db.get(Ships, ship_number)
    if not ship:
        raise HTTPException(status_code=404, detail="Ship not found")
    return ship


# Роутер для пользователей
router_users = APIRouter(prefix="/users", tags=["users"])

@router_users.post("/token", response_model=Token)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_session)
):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.login}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

# Модифицированные CRUD конечные точки
@router_users.post("/", response_model=Users)
def create_user(user: UserCreate, db: Session = Depends(get_session)):
    # Проверяем, существует ли пользователь с таким логином
    existing_user = db.exec(select(Users).where(Users.login == user.login)).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Login already registered")
    
    hashed_password = get_password_hash(user.password)
    db_user = Users(
        firstname=user.firstname,
        lastname=user.lastname,
        login=user.login,
        hashed_pwd=hashed_password,
        role=user.role
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router_users.get("/", response_model=List[Users])
def read_users(
    skip: int = 0,
    limit: int = 100,
    current_user: Users = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    users = db.exec(select(Users).offset(skip).limit(limit)).all()
    return users

@router_users.get("/authors", response_model=List[dict])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    users = db.exec(select(Users).offset(skip).limit(limit)).all()
    new_list = []
    for item in users:
        it = item.model_dump()
        new_item = {
            "number": it["number"],
            "name": f"{it['firstname']} {it['lastname']}"
        }
        new_list.append(new_item)
    return new_list

@router_users.get("/current/get", response_model=Users)
async def read_users_me(current_user: Users = Depends(get_current_active_user)):
    return current_user
@router_users.get("/{user_number}", response_model=Users)
def read_user(
    user_number: int,
    current_user: Users = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    user = db.get(Users, user_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router_users.patch("/{user_number}", response_model=Users)
def update_user(
    user_number: int,
    user: UserUpdate,
    current_user: Users = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    db_user = db.get(Users, user_number)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user_data = user.dict(exclude_unset=True)
    
    if "password" in user_data:
        hashed_password = get_password_hash(user_data["password"])
        user_data["hashed_pwd"] = hashed_password
        del user_data["password"]
    
    for key, value in user_data.items():
        setattr(db_user, key, value)
    
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router_users.delete("/{user_number}")
def delete_user(
    user_number: int,
    current_user: Users = Depends(get_current_active_user),
    db: Session = Depends(get_session)
):
    user = db.get(Users, user_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    db.delete(user)
    db.commit()
    return {"ok": True}



# Роутер для записей
router_records = APIRouter(prefix="/records", tags=["records"])

@router_records.post("/", response_model=Records)
def create_record(record: Records, db: Session = Depends(get_session)):
    db.add(record)
    db.commit()
    db.refresh(record)
    return record

@router_records.get("/", response_model=List[Records])
def read_records(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    records = db.exec(select(Records).offset(skip).limit(limit)).all()
    return records
    # stmt = (
    #     select(
    #         Records, Ships.name.label("ship_name"), Ports.name.label("port_name"))
    #     .select_from(
    #         join(Records, Ships, Records.ship == Ships.number).
    #         join(Ports, Records.port == Ports.number))
    #     .offset(skip).limit(limit))
    # results = db.exec(stmt).all()
    # formatted_records = []
    # for record, ship_name, port_name in results:
    #     record.ship = ship_name
    #     record.port = port_name
    #     formatted_records.append(record)
    # return formatted_records

@router_records.get("/{record_number}", response_model=Records)
def read_record(record_number: int, db: Session = Depends(get_session)):
    record = db.get(Records, record_number)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    return record

@router_records.post("/search", response_model=List[int])
def read_record(search_info: SearchRecordsInfo, db: Session = Depends(get_session)):
    query = select(Records.number)
    # Фильтрация по кораблю и порту
    if search_info.ship is not None:
        query = query.where(Records.ship == search_info.ship)
    if search_info.port is not None:
        query = query.where(Records.port == search_info.port)
    # Фильтрация по дате прибытия
    if search_info.arrive_date_info is not None:
        arrive_filters = []
        date_info = search_info.arrive_date_info
        if date_info.start_changed and date_info.start is not None:
            arrive_filters.append(Records.arrive_date >= date_info.start)
        if date_info.end_changed and date_info.end is not None:
            arrive_filters.append(Records.arrive_date <= date_info.end)
        if arrive_filters:
            query = query.where(and_(*arrive_filters))
    # Фильтрация по дате отплытия
    if search_info.sail_date_info is not None:
        sail_filters = []
        date_info = search_info.sail_date_info
        if date_info.start_changed and date_info.start is not None:
            sail_filters.append(Records.sail_date >= date_info.start)
        if date_info.end_changed and date_info.end is not None:
            sail_filters.append(Records.sail_date <= date_info.end)
        if sail_filters:
            query = query.where(and_(*sail_filters))
    # Фильтрация по архивным записям
    if search_info.archived is not None:
        current_date = datetime.now()
        if search_info.archived:
            # Только архивные записи
            query = query.where(
                and_(
                    Records.arrive_date.isnot(None),
                    Records.sail_date.isnot(None),
                    Records.arrive_date_real.isnot(None),
                    Records.sail_date_real.isnot(None),
                    Records.sail_date_real < (current_date - timedelta(days=7))
                )
            )
        else:
            # Только неархивные записи
            query = query.where(
                or_(
                    Records.arrive_date.is_(None),
                    Records.sail_date.is_(None),
                    Records.arrive_date_real.is_(None),
                    Records.sail_date_real.is_(None),
                    Records.sail_date_real >= (current_date - timedelta(days=7))
                )
            )
    
    # Выполняем запрос и возвращаем результаты
    records = db.exec(query).all()
    return records

@router_records.patch("/{record_number}", response_model=Records)
def update_record(record_number: int, record: Records, db: Session = Depends(get_session)):
    db_record = db.get(Records, record_number)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")
    record_data = record.dict(exclude_unset=True)
    for key, value in record_data.items():
        setattr(db_record, key, value)
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return db_record

@router_records.delete("/{record_number}")
def delete_record(record_number: int, db: Session = Depends(get_session)):
    record = db.get(Records, record_number)
    if not record:
        raise HTTPException(status_code=404, detail="Record not found")
    db.delete(record)
    db.commit()
    return {"ok": True}

@router_records.post("/status_change/{record_number}")
def change_ship_status(record_number: int, db: Session = Depends(get_session)):
    db_record = db.get(Records, record_number)
    if not db_record:
        raise HTTPException(status_code=404, detail="Record not found")
    if not db_record.arrive_date_real:
        setattr(db_record, 'arrive_date_real', datetime.now())
    elif not db_record.sail_date_real:
        setattr(db_record, 'sail_date_real', datetime.now())
    else:
        return {"Status cannot be changed because record is completed"}
    db.add(db_record)
    db.commit()
    db.refresh(db_record)
    return {"status changed":"succesfully","arrive_date_real":db_record.arrive_date_real,"sail_date_real":db_record.sail_date_real}

# Роутер для отчетов
router_reports = APIRouter(prefix="/reports", tags=["reports"])

@router_reports.post("/", response_model=Reports)
def create_report(report: Reports, db: Session = Depends(get_session)):
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@router_reports.post("/create_block", response_model=list)
def create_record_block(info: ReportBlockInfo, db: Session = Depends(get_session)):
    if info.dateTo.timestamp() != 0:
        statement = select(Records).where(
            and_(
                Records.arrive_date >= info.dateFrom,
                Records.arrive_date <= info.dateTo,
                Records.ship.in_(info.ships)
            )
        )
    else:
        statement = select(Records).where(
            and_(
                Records.arrive_date >= info.dateFrom,
                Records.ship.in_(info.ships)
            )
        )
    records = db.exec(statement).all()
    def format_timedelta(td: timedelta):
                """Форматирует timedelta в строку 'HHH:MM:SS'"""
                total_seconds = int(td.total_seconds())
                hours, remainder = divmod(total_seconds, 3600)
                minutes, seconds = divmod(remainder, 60)
                return f"{hours}:{minutes:02d}:{seconds:02d}"
    match info.name:
        case "records":
            return records
        case "points":
            def process_ship_data(data: Sequence[Records]):
                ships = {}
                for item in data:
                    ship_id = item.ship
                    if ship_id not in ships:
                        ships[ship_id] = {
                            'arrive_in_time': 0,
                            'arrive_late': 0,
                            'sail_in_time': 0,
                            'sail_late': 0
                        }
                    
                    # Обработка arrive дат (пропускаем, если arrive_date_real == None)
                    arrive_date = item.arrive_date
                    arrive_date_real = item.arrive_date_real
                    
                    if arrive_date_real is not None:
                        if arrive_date > arrive_date_real:
                            ships[ship_id]['arrive_in_time'] += 1
                        else:
                            ships[ship_id]['arrive_late'] += 1
                    
                    # Обработка sail дат (пропускаем, если sail_date_real == None)
                    sail_date = item.sail_date
                    sail_date_real = item.sail_date_real
                    
                    if sail_date_real is not None:
                        if sail_date > sail_date_real:
                            ships[ship_id]['sail_in_time'] += 1
                        else:
                            ships[ship_id]['sail_late'] += 1
                
                # Формируем итоговый список
                result = []
                for i, (ship_id, stats) in enumerate(ships.items(), start=1):
                    arrive_total = stats['arrive_in_time'] + stats['arrive_late']
                    sail_total = stats['sail_in_time'] + stats['sail_late']
                    
                    result.append({
                        'number': i,
                        'ship': ship_id,  # Можно заменить на название судна, если есть связь
                        'arrive': {
                            'inTime': stats['arrive_in_time'],
                            'late': stats['arrive_late'],
                            'total': arrive_total
                        },
                        'sail': {
                            'inTime': stats['sail_in_time'],
                            'late': stats['sail_late'],
                            'total': sail_total
                        }
                    })
                
                return result
            return process_ship_data(records)
        case "travel":
            def calculate_time_stats(deltas: List[timedelta]):
                """Вычисляет min, avg, max для списка timedelta и форматирует в строки"""
                if not deltas:
                    return {"min": "0:00:00", "avg": "0:00:00", "max": "0:00:00"}
                
                min_td = min(deltas)
                avg_seconds = statistics.mean([td.total_seconds() for td in deltas])
                avg_td = timedelta(seconds=avg_seconds)
                max_td = max(deltas)
                
                return {
                    "min": format_timedelta(min_td),
                    "avg": format_timedelta(avg_td),
                    "max": format_timedelta(max_td)
                }
            def process_ship_time_stats(data: Sequence[Records]):
                ships = {}
                
                for item in data:
                    ship_id = item.ship
                    if ship_id not in ships:
                        ships[ship_id] = {
                            'arrive_lag': [],
                            'arrive_lead': [],
                            'sail_lag': [],
                            'sail_lead': []
                        }
                    
                    # Обработка arrive
                    if item.arrive_date_real is not None:
                        delta = item.arrive_date_real - item.arrive_date
                        if delta >= timedelta(0):
                            ships[ship_id]['arrive_lag'].append(delta)
                        else:
                            ships[ship_id]['arrive_lead'].append(abs(delta))
                    
                    # Обработка sail
                    if item.sail_date_real is not None:
                        delta = item.sail_date_real - item.sail_date
                        if delta >= timedelta(0):
                            ships[ship_id]['sail_lag'].append(delta)
                        else:
                            ships[ship_id]['sail_lead'].append(abs(delta))
                
                # Формируем итоговый результат
                result = []
                for i, (ship_id, stats) in enumerate(ships.items(), start=1):
                    result.append({
                        "number": i,
                        "ship": ship_id,
                        "lag": {
                            "arrive": calculate_time_stats(stats['arrive_lag']),
                            "sail": calculate_time_stats(stats['sail_lag'])
                        },
                        "lead": {
                            "arrive": calculate_time_stats(stats['arrive_lead']),
                            "sail": calculate_time_stats(stats['sail_lead'])
                        }
                    })
                return result
            return process_ship_time_stats(records)
        case "port":
            def calculate_port_stats(data: Sequence[Records]):
                ships = {}
                
                for item in data:
                    ship_id = item.ship
                    if ship_id not in ships:
                        ships[ship_id] = {
                            'planned_times': [],
                            'real_times': []
                        }
                    
                    # Вычисляем плановое время в порту (sail_date - arrive_date)
                    planned_time = item.sail_date - item.arrive_date
                    ships[ship_id]['planned_times'].append(planned_time)
                    
                    # Вычисляем фактическое время в порту (sail_date_real - arrive_date_real)
                    if item.arrive_date_real is not None and item.sail_date_real is not None:
                        real_time = item.sail_date_real - item.arrive_date_real
                        ships[ship_id]['real_times'].append(real_time)
                
                # Формируем итоговый результат
                result = []
                for i, (ship_id, stats) in enumerate(ships.items(), start=1):
                    # Статистика для планового времени
                    planned_stats = {
                        "min": format_timedelta(min(stats['planned_times'])),
                        "avg": format_timedelta(timedelta(
                            seconds=statistics.mean(
                                [t.total_seconds() for t in stats['planned_times']]
                            )
                        )),
                        "max": format_timedelta(max(stats['planned_times']))
                    } if stats['planned_times'] else {
                        "min": "0:00:00",
                        "avg": "0:00:00",
                        "max": "0:00:00"
                    }
                    
                    # Статистика для фактического времени
                    real_stats = {
                        "min": format_timedelta(min(stats['real_times'])),
                        "avg": format_timedelta(timedelta(
                            seconds=statistics.mean(
                                [t.total_seconds() for t in stats['real_times']]
                            )
                        )),
                        "max": format_timedelta(max(stats['real_times']))
                    } if stats['real_times'] else {
                        "min": "0:00:00",
                        "avg": "0:00:00",
                        "max": "0:00:00"
                    }
                    
                    result.append({
                        "number": i,
                        "ship": ship_id,
                        "planned": planned_stats,
                        "real": real_stats
                    })
                return result
            return calculate_port_stats(records)
    return [{"error" : f"incorrct info.name, got `{info.name}`, expected: [records, points, travel, port]"}]

@router_reports.get("/", response_model=List[Reports])
def read_reports(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    reports = db.exec(select(Reports).offset(skip).limit(limit)).all()
    return reports

@router_reports.get("/{report_number}", response_model=Reports)
def read_report(report_number: int, db: Session = Depends(get_session)):
    report = db.get(Reports, report_number)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return report

@router_reports.patch("/{report_number}", response_model=Reports)
def update_report(report_number: int, report: Reports, db: Session = Depends(get_session)):
    db_report = db.get(Reports, report_number)
    if not db_report:
        raise HTTPException(status_code=404, detail="Report not found")
    report_data = report.dict(exclude_unset=True)
    for key, value in report_data.items():
        setattr(db_report, key, value)
    db.add(db_report)
    db.commit()
    db.refresh(db_report)
    return db_report

@router_reports.delete("/{report_number}")
def delete_report(report_number: int, db: Session = Depends(get_session)):
    report = db.get(Reports, report_number)
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    db.delete(report)
    db.commit()
    return {"ok": True}

# Роутер для избранного
router_favorites = APIRouter(prefix="/favorites", tags=["favorites"])

@router_favorites.post("/", response_model=Favorite)
def create_favorite(favorite: Favorite, db: Session = Depends(get_session)):
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite

@router_favorites.get("/", response_model=List[Favorite])
def read_favorites(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    favorites = db.exec(select(Favorite).offset(skip).limit(limit)).all()
    return favorites

@router_favorites.get("/user/{user_number}", response_model=List[int])
def read_user_favorites(user_number: int, db: Session = Depends(get_session)):
    user = db.get(Users, user_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = []
    for link in user.records_links:
        data.append(db.get(Records, link.record).number)
    return data

@router_favorites.delete("/")
def delete_favorite(user: int, record: int, db: Session = Depends(get_session)):
    favorite = db.exec(select(Favorite).where(Favorite.user == user).where(Favorite.record == record)).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(favorite)
    db.commit()
    return {"ok": True}

app.include_router(router_ports)
app.include_router(router_ships)
app.include_router(router_users)
app.include_router(router_records)
app.include_router(router_reports)
app.include_router(router_favorites)