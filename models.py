import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, Table
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()

# Промежуточная таблица для друзей (многие-ко-многим)
friendship = Table(
    "friendship",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("friend_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
)

# Промежуточные таблицы для лайков
track_likes = Table(
    "track_likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("track_id", Integer, ForeignKey("tracks.id", ondelete="CASCADE"), primary_key=True)
)

# Промежуточная таблица для лайков исполнителей
artist_likes = Table(
    "artist_likes",
    Base.metadata,
    Column("user_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("artist_id", Integer, ForeignKey("artists.id", ondelete="CASCADE"), primary_key=True)
)

class VisibilityEnum(str, enum.Enum):
    PUBLIC = "public"
    FRIENDS = "friends"
    PRIVATE = "private"

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    avatar_url = Column(String, nullable=True)

    # Связи
    uploaded_tracks = relationship("Track", back_populates="owner")
    created_albums = relationship("Album", back_populates="owner")
    liked_artists = relationship("Artist", secondary=artist_likes, backref="liked_by")
    
    # Связь "друзья" (самоссылающаяся связь)
    friends = relationship(
        "User",
        secondary=friendship,
        primaryjoin=id == friendship.c.user_id,
        secondaryjoin=id == friendship.c.friend_id,
        backref="befriended_by"
    )

class Artist(Base):
    __tablename__ = "artists"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, nullable=False, index=True)
    bio = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    tracks = relationship("Track", back_populates="artist")
    albums = relationship("Album", back_populates="artist")

class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    file_url = Column(String, nullable=False)  # Путь к аудиофайлу
    visibility = Column(Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)
    
    # Делаем связи необязательными
    artist_id = Column(Integer, ForeignKey("artists.id"), nullable=True)
    album_id = Column(Integer, ForeignKey("albums.id"), nullable=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    owner = relationship("User", back_populates="uploaded_tracks")
    artist = relationship("Artist", back_populates="tracks")
    album = relationship("Album", back_populates="tracks")

class Album(Base):
    __tablename__ = "albums"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    cover_url = Column(String, nullable=True)
    visibility = Column(Enum(VisibilityEnum), default=VisibilityEnum.PUBLIC, nullable=False)

    owner_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    artist_id = Column(Integer, ForeignKey("artists.id", ondelete="SET NULL"), nullable=True)

    owner = relationship("User", back_populates="created_albums")
    artist = relationship("Artist", back_populates="albums")
    tracks = relationship("Track", back_populates="album")