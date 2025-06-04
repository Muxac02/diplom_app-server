from typing import Optional
import enum
from sqlmodel import Field, SQLModel, Column, JSON, Relationship, Enum
from datetime import datetime, timedelta


class Ports(SQLModel, table=True):
    number: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Ships(SQLModel, table=True):
    number: Optional[int] = Field(default=None, primary_key=True)
    name: str

class Favorite(SQLModel, table=True):
    user: Optional[int] = Field(default=None, primary_key=True, foreign_key="users.number")
    record: Optional[int] = Field(default=None, primary_key=True, foreign_key="records.number")
    
    user_cont: "Users" = Relationship(back_populates="records_links", passive_deletes=True)
    record_cont: "Records" = Relationship(back_populates="users_links", passive_deletes=True)

class User_Roles(str, enum.Enum):
    admin = "admin"
    department_worker = "department_worker"
    dispatcher = "dispatcher"

class Users(SQLModel, table=True):
    number: Optional[int] = Field(default=None, primary_key=True)
    firstname: str
    lastname: str
    login: str
    hashed_pwd: str
    role: User_Roles = Field(default=User_Roles.department_worker, sa_column=(Enum(User_Roles)))
    
    records_links: list[Favorite] = Relationship(back_populates="user_cont", passive_deletes=True)
    

tm = datetime.now()
tm += timedelta(minutes=5)
tm -= timedelta(minutes=tm.minute % 10, seconds=tm.second, microseconds=tm.microsecond)

class DateInfo(SQLModel, table=False):
    end: datetime = Field(default=None)
    start: datetime = Field(default=None)
    start_changed: bool = Field(default=False)
    end_changed: bool = Field(default=False)

class SearchRecordsInfo(SQLModel, table=False):
    ship: Optional[int] = Field(default=None, foreign_key="ships.number")
    port: Optional[int] = Field(default=None, foreign_key="ports.number")
    arrive_date_info: DateInfo = Field(default=None)
    sail_date_info: DateInfo = Field(default=None)
    archived: bool = Field(default=False)

class Records(SQLModel, table=True):
    number: Optional[int] = Field(default=None, primary_key=True)
    ship: int = Field(default=None, foreign_key="ships.number")
    port: int = Field(default=None, foreign_key="ports.number")
    arrive_date: datetime = Field(default=tm)
    sail_date: datetime = Field(default=tm+timedelta(days=7))
    created_at: datetime = Field(default=datetime.now())
    arrive_date_real: Optional[datetime] = Field(default=None)
    sail_date_real: Optional[datetime] = Field(default=None)
    comment: Optional[str] = Field(default=None)
    updated_at: Optional[datetime] = Field(default=None)
    
    users_links: list[Favorite] = Relationship(back_populates="record_cont", passive_deletes=True)


class Reports(SQLModel, table=True):
    number: Optional[int] = Field(default=None, primary_key=True)
    author: int = Field(default=None, foreign_key="users.number")
    created_at: datetime
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))
    updated_at: Optional[datetime] = Field(default=None)

class ReportBlockInfo(SQLModel, table=False):
    name: str = Field(default=None)
    ships: list[int] = Field(default_factory=list)
    dateFrom: datetime = Field(default=None)
    dateTo: datetime = Field(default=None)
    
class ReportBlockContent(SQLModel, table=False):
    content: dict = Field(default_factory=dict, sa_column=Column(JSON))