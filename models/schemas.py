from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum

class Genre(str, Enum):
    BALLAD = "발라드"
    DANCE = "댄스"
    HIPHOP = "랩/힙합"
    IDOL = "아이돌"
    RB_SOUL = "R&B/Soul"
    INDIE = "인디음악"
    ROCK_METAL = "록/메탈"
    TROT = "성인가요/트로트"
    FOLK_BLUES = "포크/블루스"
    ELECTRONICA = "일렉트로니카"
    CLASSIC = "클래식"
    JAZZ = "재즈"
    JPOP = "J-POP"
    POP = "POP"
    KIDS = "키즈"
    CCM = "CCM"
    GUGAK = "국악"

class ConcertMood(str, Enum):
    EMOTIONAL = "Emotional"
    ENERGETIC = "Energetic"
    DREAMY = "Dreamy"
    GRAND = "Grand"
    CALM = "Calm"
    FUN = "Fun"
    INTENSE = "Intense"

class ConcertStyle(str, Enum):
    LIVE_BAND = "Live Band"
    ACOUSTIC = "Acoustic"
    ORCHESTRA = "Orchestra"
    SOLO = "Solo Performance"
    DANCE = "Dance Performance"
    THEATRICAL = "Theatrical Concert"

class ConcertType(str, Enum):
    FESTIVAL = "Festival"
    CONCERT = "Concert"
    MUSIC_SHOW = "Music Show"
    FAN_MEETING = "Fan Meeting"
    TALK_CONCERT = "Talk Concert"

class Casting(BaseModel):
    name: str = Field(description="출연진 이름")

class PerformanceRound(BaseModel):
    round: int = Field(description="공연 회차")
    datetime: str = Field(description="공연 날짜 및 시간 (YYYY-MM-DDTHH:MM:SS)")

class Concert(BaseModel):
    concert_name: str = Field(description="공연명")
    concert_poster: Optional[str] = Field(description="공연 포스터 이미지 URL")
    genre: Genre = Field(description="장르 선택")
    concert_mood: ConcertMood = Field(description="공연 분위기 선택")
    concert_style: ConcertStyle = Field(description="공연 스타일 선택")
    concert_type: ConcertType = Field(description="공연 종류 선택")
    casting: List[Casting] = Field(description="캐스팅 정보")
    performance_rounds: List[PerformanceRound] = Field(description="공연 회차 정보")
    venue: Optional[str] = Field(description="공연 장소")
    running_time: Optional[int] = Field(description="러닝 타임 (분 단위)")
    price: Optional[Dict[str, Optional[int]]] = Field(description="공연의 좌석 등급(예: 'VIP', 'R')을 키(key)로, 해당 등급의 가격을 정수 값(value)으로 갖는 딕셔너리",default={"type": None})
    age_limit: Optional[str] = Field(description="관람 연령")
    booking_limit: Optional[str] = Field(description="예매 가능 매수")
    selling_platform: str = Field(default="INTERPARK", description="예매처")
    ticket_status: bool = Field(description="현재 예매 가능 여부")
    ticket_open_dates: Optional[Dict[str,Optional[datetime]]] = Field(description="티켓 예매 유형을 키로, 해당 예매의 오픈 일시를 값으로 갖는 딕셔너리",default={"type": None})
    booking_link: Optional[str] = Field(description="예매 링크")
