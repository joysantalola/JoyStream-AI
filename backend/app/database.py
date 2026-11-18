
import os

from sqlalchemy import (
    create_engine,
    MetaData,
    Table,
    Column,
    String,
    Integer,
    DateTime,
    Text,
    func,
    BigInteger, 
    Index, 
    Identity
)
from sqlalchemy.engine import URL


# Configuración de la conexión
database_url = URL.create(
    drivername="postgresql+psycopg",
    username="joystream",
    password=os.environ["POSTGRES_PASSWORD"],
    host="db",
    port=5432,
    database="joystream",
)

engine = create_engine(database_url, pool_pre_ping=True)

metadata = MetaData()


# Tabla de vídeos
videos_table = Table(
    "videos",
    metadata,
    Column("id", String, primary_key=True),
    Column("title", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("duration", String),
    Column("view_count", Integer),
    Column("url", Text),
    Column(
        "synced_at",
        DateTime(timezone=True),
        server_default=func.now()
    ),
)


# Tabla de clips
clips_table = Table(
    "clips",
    metadata,
    Column("id", String, primary_key=True),
    Column("title", Text, nullable=False),
    Column("created_at", DateTime(timezone=True)),
    Column("duration", String),
    Column("view_count", Integer),
    Column("game_id", String),
    Column("url", Text),
    Column(
        "synced_at",
        DateTime(timezone=True),
        server_default=func.now()
    ),
)


# Tabla de historial de visualizaciones
view_history_table = Table(
    "view_history",
    metadata,

    Column(
        "id",
        BigInteger,
        Identity(),
        primary_key=True
    ),

    Column(
        "content_type",
        String(10),
        nullable=False
    ),

    Column(
        "content_id",
        String,
        nullable=False
    ),

    Column(
        "view_count",
        BigInteger,
        nullable=False
    ),

    Column(
        "captured_at",
        DateTime(timezone=True),
        nullable=False
    ),

    Index(
        "idx_history_content_date",
        "content_type",
        "content_id",
        "captured_at"
    )
)


# Historial de espectadores en directo
stream_samples_table = Table(
    "stream_samples",
    metadata,

    Column(
        "id",
        BigInteger,
        Identity(),
        primary_key=True
    ),

    Column("stream_id", String, nullable=False),
    Column("viewer_count", Integer, nullable=False),
    Column("game_id", String),
    Column("game_name", String),
    Column("title", Text),

    Column(
        "started_at",
        DateTime(timezone=True),
        nullable=False
    ),

    Column(
        "captured_at",
        DateTime(timezone=True),
        nullable=False
    ),

    Index(
        "idx_stream_samples_session",
        "stream_id",
        "captured_at"
    )
)


def create_tables():
    """Crea las tablas si todavía no existen."""
    metadata.create_all(engine)
