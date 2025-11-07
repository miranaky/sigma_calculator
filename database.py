"""
SQLite 데이터베이스 관리 모듈
주식 데이터와 분석 결과를 캐싱합니다.
"""

import sqlite3
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os


class StockDatabase:
    """주식 데이터와 분석 결과를 SQLite에 저장/조회하는 클래스"""

    def __init__(self, db_path: str = "stock_data.db"):
        """
        Args:
            db_path: SQLite 데이터베이스 파일 경로
        """
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """데이터베이스 초기화 및 테이블 생성"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 주식 데이터 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS stock_data (
                ticker TEXT NOT NULL,
                date TEXT NOT NULL,
                close_price REAL NOT NULL,
                PRIMARY KEY (ticker, date)
            )
        """)

        # 분석 결과 캐시 테이블
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS analysis_cache (
                ticker TEXT NOT NULL,
                period_days INTEGER NOT NULL,
                last_update TEXT NOT NULL,
                mean REAL NOT NULL,
                std REAL NOT NULL,
                last_price REAL NOT NULL,
                data_days INTEGER NOT NULL,
                PRIMARY KEY (ticker, period_days)
            )
        """)

        # 인덱스 생성
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_data_ticker
            ON stock_data(ticker)
        """)

        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_stock_data_date
            ON stock_data(date)
        """)

        conn.commit()
        conn.close()

    def save_stock_data(self, ticker: str, data: pd.DataFrame):
        """
        주식 데이터를 데이터베이스에 저장합니다.

        Args:
            ticker: 주식 티커
            data: Close 컬럼이 있는 DataFrame (인덱스는 날짜)
        """
        conn = sqlite3.connect(self.db_path)

        # 기존 데이터 삭제 (업데이트)
        conn.execute("DELETE FROM stock_data WHERE ticker = ?", (ticker,))

        # 새 데이터 삽입
        records = []
        for date_idx, row in data.iterrows():
            date_str = date_idx.strftime('%Y-%m-%d')
            records.append((ticker, date_str, float(row['Close'])))

        conn.executemany(
            "INSERT OR REPLACE INTO stock_data (ticker, date, close_price) VALUES (?, ?, ?)",
            records
        )

        conn.commit()
        conn.close()

    def load_stock_data(self, ticker: str, start_date: datetime, end_date: datetime) -> Optional[pd.DataFrame]:
        """
        데이터베이스에서 주식 데이터를 불러옵니다.

        Args:
            ticker: 주식 티커
            start_date: 시작 날짜
            end_date: 종료 날짜

        Returns:
            DataFrame 또는 None (데이터가 없으면)
        """
        conn = sqlite3.connect(self.db_path)

        query = """
            SELECT date, close_price
            FROM stock_data
            WHERE ticker = ? AND date >= ? AND date <= ?
            ORDER BY date
        """

        df = pd.read_sql_query(
            query,
            conn,
            params=(ticker, start_date.strftime('%Y-%m-%d'), end_date.strftime('%Y-%m-%d')),
            parse_dates=['date'],
            index_col='date'
        )

        conn.close()

        if df.empty:
            return None

        df.rename(columns={'close_price': 'Close'}, inplace=True)
        return df

    def has_recent_data(self, ticker: str, days: int = 7) -> bool:
        """
        최근 N일 이내의 데이터가 있는지 확인합니다.

        Args:
            ticker: 주식 티커
            days: 최근 며칠 이내

        Returns:
            True if 최근 데이터 있음, False otherwise
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cutoff_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')

        cursor.execute("""
            SELECT COUNT(*) FROM stock_data
            WHERE ticker = ? AND date >= ?
        """, (ticker, cutoff_date))

        count = cursor.fetchone()[0]
        conn.close()

        return count > 0

    def save_analysis(self, ticker: str, period_days: int, mean: float, std: float,
                     last_price: float, data_days: int):
        """
        분석 결과를 캐시에 저장합니다.

        Args:
            ticker: 주식 티커
            period_days: 분석 기간
            mean: 평균 변동률
            std: 표준편차
            last_price: 마지막 종가
            data_days: 실제 데이터 일 수
        """
        conn = sqlite3.connect(self.db_path)

        now = datetime.now().isoformat()

        conn.execute("""
            INSERT OR REPLACE INTO analysis_cache
            (ticker, period_days, last_update, mean, std, last_price, data_days)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (ticker, period_days, now, mean, std, last_price, data_days))

        conn.commit()
        conn.close()

    def load_analysis(self, ticker: str, period_days: int, max_age_hours: int = 24) -> Optional[Tuple]:
        """
        캐시된 분석 결과를 불러옵니다.

        Args:
            ticker: 주식 티커
            period_days: 분석 기간
            max_age_hours: 최대 캐시 유효 시간 (시간)

        Returns:
            (mean, std, last_price, data_days) 튜플 또는 None
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT last_update, mean, std, last_price, data_days
            FROM analysis_cache
            WHERE ticker = ? AND period_days = ?
        """, (ticker, period_days))

        result = cursor.fetchone()
        conn.close()

        if not result:
            return None

        last_update_str, mean, std, last_price, data_days = result
        last_update = datetime.fromisoformat(last_update_str)

        # 캐시가 너무 오래되었는지 확인
        age = datetime.now() - last_update
        if age.total_seconds() > max_age_hours * 3600:
            return None

        return (mean, std, last_price, data_days)

    def get_database_stats(self) -> dict:
        """데이터베이스 통계 정보를 반환합니다."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # 저장된 티커 수
        cursor.execute("SELECT COUNT(DISTINCT ticker) FROM stock_data")
        ticker_count = cursor.fetchone()[0]

        # 총 데이터 레코드 수
        cursor.execute("SELECT COUNT(*) FROM stock_data")
        data_count = cursor.fetchone()[0]

        # 캐시된 분석 결과 수
        cursor.execute("SELECT COUNT(*) FROM analysis_cache")
        cache_count = cursor.fetchone()[0]

        # 데이터베이스 파일 크기
        db_size = os.path.getsize(self.db_path) if os.path.exists(self.db_path) else 0

        conn.close()

        return {
            'ticker_count': ticker_count,
            'data_count': data_count,
            'cache_count': cache_count,
            'db_size_mb': db_size / (1024 * 1024)
        }

    def clear_cache(self, ticker: Optional[str] = None):
        """
        캐시를 삭제합니다.

        Args:
            ticker: 특정 티커만 삭제 (None이면 전체 삭제)
        """
        conn = sqlite3.connect(self.db_path)

        if ticker:
            conn.execute("DELETE FROM stock_data WHERE ticker = ?", (ticker,))
            conn.execute("DELETE FROM analysis_cache WHERE ticker = ?", (ticker,))
        else:
            conn.execute("DELETE FROM stock_data")
            conn.execute("DELETE FROM analysis_cache")

        conn.commit()
        conn.close()
