#Сгенерировал с помощью библы sqlacodegen от себя только заменил ассоциативную таблицу Favorite, так как поменялся её стандарт генерации и добавил по строке в Users и Records
#Запрос:
#sqlacodegen --generator sqlmodels "postgresql://localhost/DB_NAME?user=postgres&password=PWD"

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, DateTime, Enum, ForeignKeyConstraint, Integer, JSON, PrimaryKeyConstraint, Sequence, SmallInteger, String, Table, Text, text
from sqlmodel import Field, Relationship, SQLModel

class Ports(SQLModel, table=True):
    __table_args__ = (
        PrimaryKeyConstraint('number', name='port_pkey'),
    )

    number: Optional[int] = Field(default=None, sa_column=Column('number', SmallInteger, Sequence('port_number_seq'), primary_key=True))
    name: str = Field(sa_column=Column('name', String))

    records: List['Records'] = Relationship(back_populates='ports')


class Ships(SQLModel, table=True):
    __table_args__ = (
        PrimaryKeyConstraint('number', name='ship_pkey'),
        {'comment': 'table for ids and names of ships'}
    )

    number: Optional[int] = Field(default=None, sa_column=Column('number', SmallInteger, Sequence('ship_number_seq'), primary_key=True))
    name: str = Field(sa_column=Column('name', String))

    records: List['Records'] = Relationship(back_populates='ships')

class Favorite(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(['user'], ['users.number'], name='user_number'),
        ForeignKeyConstraint(['record'], ['records.number'], name='record_number'),
        PrimaryKeyConstraint('user','record', name='favorite_pkey')
    )
    user: int = Field(sa_column=Column('user', SmallInteger))
    record: int = Field(sa_column=Column('record', Integer))

class Users(SQLModel, table=True):
    __table_args__ = (
        PrimaryKeyConstraint('number', name='users_pkey'),
    )

    number: Optional[int] = Field(default=None, sa_column=Column('number', SmallInteger, primary_key=True))
    firstname: str = Field(sa_column=Column('firstname', Text))
    lastname: str = Field(sa_column=Column('lastname', Text))
    login: str = Field(sa_column=Column('login', Text))
    hashed_pwd: str = Field(sa_column=Column('hashed_pwd', Text))
    role: str = Field(sa_column=Column('role', Enum('admin', 'department_worker', ' dispatcher', name='user_role'), server_default=text("'department_worker'::user_role")))

    reports: List['Reports'] = Relationship(back_populates='users')
    favorite: List['Records'] = Relationship(back_populates="users", link_model=Favorite)


class Records(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(['port'], ['ports.number'], name='port_number'),
        ForeignKeyConstraint(['ship'], ['ships.number'], name='ship_number'),
        PrimaryKeyConstraint('number', name='record_pkey')
    )

    number: Optional[int] = Field(default=None, sa_column=Column('number', Integer, Sequence('record_number_seq'), primary_key=True))
    ship: int = Field(sa_column=Column('ship', SmallInteger))
    port: int = Field(sa_column=Column('port', SmallInteger))
    arrive_date: datetime = Field(sa_column=Column('arrive_date', DateTime))
    sail_date: datetime = Field(sa_column=Column('sail_date', DateTime))
    created_at: datetime = Field(sa_column=Column('created_at', DateTime))
    arrive_date_real: Optional[datetime] = Field(default=None, sa_column=Column('arrive_date_real', DateTime))
    sail_date_real: Optional[datetime] = Field(default=None, sa_column=Column('sail_date_real', DateTime))
    comment: Optional[str] = Field(default=None, sa_column=Column('comment', Text))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column('updated_at', DateTime))

    ports: Optional['Ports'] = Relationship(back_populates='records')
    ships: Optional['Ships'] = Relationship(back_populates='records')
    favorite: List['Users'] = Relationship(back_populates="records", link_model=Favorite)


class Reports(SQLModel, table=True):
    __table_args__ = (
        ForeignKeyConstraint(['author'], ['users.number'], name='author_number'),
        PrimaryKeyConstraint('number', name='reports_pkey')
    )

    number: Optional[int] = Field(default=None, sa_column=Column('number', Integer, primary_key=True))
    author: int = Field(sa_column=Column('author', SmallInteger))
    created_at: datetime = Field(sa_column=Column('created_at', DateTime))
    content: dict = Field(sa_column=Column('content', JSON))
    updated_at: Optional[datetime] = Field(default=None, sa_column=Column('updated_at', DateTime))

    users: Optional['Users'] = Relationship(back_populates='reports')