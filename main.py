from typing import Annotated
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select, join, and_, or_, not_
from db import init_db, get_session
from models2 import Ships,Ports,Users,Records,Favorite,Reports,SearchRecordsInfo
from datetime import datetime, timedelta

#app = FastAPI()

init_db()
SessionDep = Annotated[Session, Depends(get_session)]

#Что я хочу сделать?

#Кусок апишки для авторизации, где будет выдаваться токен и проверяться текущий токен
#Заранее все методы сразу делать под роли, в зависимости от авторизации 


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

@router_users.post("/", response_model=Users)
def create_user(user: Users, db: Session = Depends(get_session)):
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

@router_users.get("/", response_model=List[Users])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_session)):
    users = db.exec(select(Users).offset(skip).limit(limit)).all()
    return users

@router_users.get("/{user_number}", response_model=Users)
def read_user(user_number: int, db: Session = Depends(get_session)):
    user = db.get(Users, user_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router_users.patch("/{user_number}", response_model=Users)
def update_user(user_number: int, user: Users, db: Session = Depends(get_session)):
    db_user = db.get(Users, user_number)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    user_data = user.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(db_user, key, value)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router_users.delete("/{user_number}")
def delete_user(user_number: int, db: Session = Depends(get_session)):
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

@router_favorites.get("/user/{user_number}", response_model=List[Records])
def read_user_favorites(user_number: int, db: Session = Depends(get_session)):
    user = db.get(Users, user_number)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    data = []
    for link in user.records_links:
        data.append(db.get(Records, link.record))
    return data

@router_favorites.delete("/")
def delete_favorite(user: int, record: int, db: Session = Depends(get_session)):
    favorite = db.exec(select(Favorite).where(Favorite.user == user).where(Favorite.record == record)).first()
    if not favorite:
        raise HTTPException(status_code=404, detail="Favorite not found")
    db.delete(favorite)
    db.commit()
    return {"ok": True}

# Основное приложение FastAPI
from fastapi import FastAPI

app = FastAPI()
app.include_router(router_ports)
app.include_router(router_ships)
app.include_router(router_users)
app.include_router(router_records)
app.include_router(router_reports)
app.include_router(router_favorites)