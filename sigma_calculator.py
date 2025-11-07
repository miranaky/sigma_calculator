"""
Stock Volatility Tracker
주식의 일일 변동률을 추적하고 1, 2, 3 sigma 값을 계산합니다.
"""

import argparse
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, Optional
from database import StockDatabase


class StockVolatilityTracker:
    """주식 변동성을 추적하고 시그마 값을 계산하는 클래스"""

    def __init__(self, ticker: str, period_days: int = 365, use_cache: bool = True):
        """
        Args:
            ticker: 주식 티커 (예: 'AAPL', '005930.KS')
            period_days: 분석 기간 (기본값: 365일)
            use_cache: 캐시 사용 여부 (기본값: True)
        """
        self.ticker = ticker.upper()
        self.period_days = period_days
        self.use_cache = use_cache
        self.data: Optional[pd.DataFrame] = None
        self.daily_returns: Optional[pd.Series] = None
        self.mean: Optional[float] = None
        self.std: Optional[float] = None
        self.db = StockDatabase() if use_cache else None

    def fetch_data(self, force_refresh: bool = False) -> bool:
        """
        주식 데이터를 다운로드하거나 캐시에서 불러옵니다.

        Args:
            force_refresh: True이면 캐시를 무시하고 새로 다운로드

        Returns:
            성공 여부
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.period_days)

            # 캐시 확인
            if self.use_cache and not force_refresh and self.db:
                if self.db.has_recent_data(self.ticker, days=1):
                    print(f"💾 {self.ticker} 캐시에서 데이터를 불러오는 중...")
                    self.data = self.db.load_stock_data(self.ticker, start_date, end_date)

                    if self.data is not None and not self.data.empty:
                        print(f"✅ 캐시에서 {len(self.data)}일의 데이터를 불러왔습니다.")
                        return True
                    else:
                        print(f"⚠️  캐시가 오래되었거나 불완전합니다. 새로 다운로드합니다.")

            # API에서 다운로드
            print(f"📊 {self.ticker} 데이터를 다운로드하는 중...")
            ticker_obj = yf.Ticker(self.ticker)
            self.data = ticker_obj.history(start=start_date, end=end_date, auto_adjust=True)

            if self.data is None or self.data.empty:
                print(f"❌ {self.ticker}에 대한 데이터를 찾을 수 없습니다.")
                print(f"   티커 심볼을 확인해주세요.")
                return False

            print(f"✅ {len(self.data)}일의 데이터를 다운로드했습니다.")

            # 캐시에 저장
            if self.use_cache and self.db:
                self.db.save_stock_data(self.ticker, self.data)
                print(f"💾 데이터를 캐시에 저장했습니다.")

            return True

        except Exception as e:
            print(f"❌ 데이터 다운로드 중 오류 발생: {e}")
            print(f"   인터넷 연결을 확인하거나 티커 심볼을 확인해주세요.")
            return False

    def calculate_daily_returns(self) -> bool:
        """일일 변동률(%)을 계산합니다."""
        if self.data is None or self.data.empty:
            print("❌ 데이터가 없습니다. fetch_data()를 먼저 실행하세요.")
            return False

        try:
            # 일일 변동률 계산: (오늘 종가 - 어제 종가) / 어제 종가 * 100
            self.daily_returns = self.data['Close'].pct_change() * 100

            # NaN 값 제거 (첫 번째 데이터는 전날이 없으므로 NaN)
            self.daily_returns = self.daily_returns.dropna()

            print(f"✅ {len(self.daily_returns)}개의 일일 변동률을 계산했습니다.")
            return True

        except Exception as e:
            print(f"❌ 변동률 계산 중 오류 발생: {e}")
            return False

    def calculate_sigma(self) -> bool:
        """표준편차(sigma)를 계산합니다."""
        if self.daily_returns is None or len(self.daily_returns) == 0:
            print("❌ 변동률 데이터가 없습니다. calculate_daily_returns()를 먼저 실행하세요.")
            return False

        try:
            self.mean = self.daily_returns.mean()
            self.std = self.daily_returns.std()

            print(f"✅ 통계 계산 완료")
            print(f"   평균 변동률: {self.mean:.4f}%")
            print(f"   표준편차(1σ): {self.std:.4f}%")
            return True

        except Exception as e:
            print(f"❌ 표준편차 계산 중 오류 발생: {e}")
            return False

    def get_sigma_levels(self) -> Dict[str, float]:
        """1, 2, 3 시그마 레벨을 반환합니다."""
        if self.mean is None or self.std is None:
            raise ValueError("시그마가 계산되지 않았습니다. calculate_sigma()를 먼저 실행하세요.")

        return {
            'mean': self.mean,
            'std': self.std,
            '1_sigma_up': self.mean + self.std,
            '1_sigma_down': self.mean - self.std,
            '2_sigma_up': self.mean + 2 * self.std,
            '2_sigma_down': self.mean - 2 * self.std,
            '3_sigma_up': self.mean + 3 * self.std,
            '3_sigma_down': self.mean - 3 * self.std,
        }

    def print_report(self):
        """변동성 분석 리포트를 출력합니다."""
        if self.mean is None or self.std is None:
            print("❌ 분석이 완료되지 않았습니다.")
            return

        sigma_levels = self.get_sigma_levels()

        # 마지막 종가 가져오기
        last_price = self.data['Close'].iloc[-1]

        print("\n" + "="*60)
        print(f"📈 {self.ticker} 주식 변동성 분석 리포트")
        print("="*60)
        print(f"\n📅 분석 기간: 최근 {self.period_days}일")
        print(f"📊 분석 데이터: {len(self.daily_returns)}일의 일일 변동률")

        print(f"\n📉 기본 통계:")
        print(f"   마지막 종가: ${last_price:.2f}")
        print(f"   평균 일일 변동률: {sigma_levels['mean']:+.4f}%")
        print(f"   표준편차 (1σ): {sigma_levels['std']:.4f}%")

        print(f"\n🎯 내일 예상 변동 범위:")

        # 1 시그마
        price_1sigma_up = last_price * (1 + sigma_levels['1_sigma_up'] / 100)
        price_1sigma_down = last_price * (1 + sigma_levels['1_sigma_down'] / 100)
        print(f"\n   1 시그마 (68.3% 확률):")
        print(f"      상승: +{sigma_levels['1_sigma_up']:.2f}% 이상 → ${price_1sigma_up:.2f}")
        print(f"      하락: {sigma_levels['1_sigma_down']:.2f}% 이하 → ${price_1sigma_down:.2f}")

        # 2 시그마
        price_2sigma_up = last_price * (1 + sigma_levels['2_sigma_up'] / 100)
        price_2sigma_down = last_price * (1 + sigma_levels['2_sigma_down'] / 100)
        print(f"\n   2 시그마 (95.4% 확률):")
        print(f"      상승: +{sigma_levels['2_sigma_up']:.2f}% 이상 → ${price_2sigma_up:.2f}")
        print(f"      하락: {sigma_levels['2_sigma_down']:.2f}% 이하 → ${price_2sigma_down:.2f}")

        # 3 시그마
        price_3sigma_up = last_price * (1 + sigma_levels['3_sigma_up'] / 100)
        price_3sigma_down = last_price * (1 + sigma_levels['3_sigma_down'] / 100)
        print(f"\n   3 시그마 (99.7% 확률):")
        print(f"      상승: +{sigma_levels['3_sigma_up']:.2f}% 이상 → ${price_3sigma_up:.2f}")
        print(f"      하락: {sigma_levels['3_sigma_down']:.2f}% 이하 → ${price_3sigma_down:.2f}")

        print("\n" + "="*60)
        print("\n💡 해석:")
        print("   - 1σ: 내일 변동률이 이 범위를 벗어날 확률 약 31.7%")
        print("   - 2σ: 내일 변동률이 이 범위를 벗어날 확률 약 4.6%")
        print("   - 3σ: 내일 변동률이 이 범위를 벗어날 확률 약 0.3%")
        print("="*60 + "\n")

    def analyze(self, force_refresh: bool = False) -> bool:
        """
        전체 분석 프로세스를 실행합니다.

        Args:
            force_refresh: True이면 캐시를 무시하고 새로 분석

        Returns:
            성공 여부
        """
        if not self.fetch_data(force_refresh=force_refresh):
            return False

        if not self.calculate_daily_returns():
            return False

        if not self.calculate_sigma():
            return False

        # 분석 결과를 캐시에 저장
        if self.use_cache and self.db and self.mean is not None and self.std is not None:
            last_price = self.data['Close'].iloc[-1]
            self.db.save_analysis(
                self.ticker,
                self.period_days,
                self.mean,
                self.std,
                last_price,
                len(self.daily_returns)
            )

        self.print_report()
        return True


def load_tickers_from_file(file_path: str = "tickers.txt") -> list:
    """
    파일에서 티커 목록을 읽어옵니다.

    Args:
        file_path: 티커 목록 파일 경로

    Returns:
        티커 리스트
    """
    import os

    if not os.path.exists(file_path):
        return []

    tickers = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                # 빈 줄이나 주석 무시
                if not line or line.startswith('#'):
                    continue
                tickers.append(line)
    except Exception as e:
        print(f"⚠️  티커 파일 읽기 오류: {e}")
        return []

    return tickers


def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description='주식 변동성 추적기 - 일일 변동률의 시그마 값을 계산합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python sigma_calculator.py                   # tickers.txt 파일의 모든 티커 분석
  python sigma_calculator.py AAPL              # 애플 주식 분석 (캐시 사용)
  python sigma_calculator.py 005930.KS         # 삼성전자 분석
  python sigma_calculator.py TSLA -d 180       # 테슬라 180일 분석
  python sigma_calculator.py AAPL --refresh    # 캐시 무시하고 새로 분석
  python sigma_calculator.py --file my.txt     # 커스텀 파일의 티커 분석
  python sigma_calculator.py --stats           # 캐시 통계 보기
        """
    )
    parser.add_argument(
        'ticker',
        nargs='?',
        help='주식 티커 심볼 (예: AAPL, TSLA, 005930.KS). 생략하면 tickers.txt 파일의 모든 티커를 분석합니다.'
    )
    parser.add_argument(
        '-d', '--days',
        type=int,
        default=365,
        help='분석 기간 (일 수, 기본값: 365)'
    )
    parser.add_argument(
        '--refresh',
        action='store_true',
        help='캐시를 무시하고 새로 데이터를 다운로드합니다.'
    )
    parser.add_argument(
        '--no-cache',
        action='store_true',
        help='캐시를 사용하지 않습니다.'
    )
    parser.add_argument(
        '--file',
        type=str,
        default='tickers.txt',
        help='티커 목록 파일 경로 (기본값: tickers.txt)'
    )
    parser.add_argument(
        '--stats',
        action='store_true',
        help='캐시 통계를 표시하고 종료합니다.'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📊 주식 변동성 추적기 (Stock Volatility Tracker)")
    print("=" * 60 + "\n")

    # 캐시 통계 표시
    if args.stats:
        db = StockDatabase()
        stats = db.get_database_stats()
        print("📊 캐시 통계:")
        print(f"   저장된 티커 수: {stats['ticker_count']}")
        print(f"   총 데이터 레코드: {stats['data_count']:,}")
        print(f"   캐시된 분석 결과: {stats['cache_count']}")
        print(f"   데이터베이스 크기: {stats['db_size_mb']:.2f} MB")
        return

    # 티커 결정
    tickers = []
    if args.ticker:
        # 명령줄에서 티커 지정
        tickers = [args.ticker.strip()]
    else:
        # 파일에서 티커 목록 읽기
        tickers = load_tickers_from_file(args.file)

        if not tickers:
            print(f"⚠️  '{args.file}' 파일을 찾을 수 없거나 티커가 없습니다.")
            print(f"   티커를 직접 입력하거나, {args.file} 파일에 티커를 추가하세요.\n")

            # 대화형 모드로 전환
            ticker = input("주식 티커를 입력하세요 (예: AAPL, TSLA, 005930.KS): ").strip()
            if not ticker:
                print("❌ 티커를 입력해주세요.")
                return
            tickers = [ticker]
        else:
            print(f"📋 {args.file}에서 {len(tickers)}개의 티커를 찾았습니다.")
            print(f"   티커 목록: {', '.join(tickers)}\n")

    # 분석 설정
    use_cache = not args.no_cache

    # 여러 티커 분석
    success_count = 0
    fail_count = 0

    for i, ticker in enumerate(tickers, 1):
        if len(tickers) > 1:
            print(f"\n{'='*60}")
            print(f"[{i}/{len(tickers)}] {ticker} 분석 중...")
            print(f"{'='*60}")

        try:
            tracker = StockVolatilityTracker(ticker, period_days=args.days, use_cache=use_cache)
            if tracker.analyze(force_refresh=args.refresh):
                success_count += 1
            else:
                fail_count += 1
        except Exception as e:
            print(f"❌ {ticker} 분석 중 오류 발생: {e}")
            fail_count += 1

        # 여러 티커일 때 구분선
        if len(tickers) > 1 and i < len(tickers):
            print("\n" + "─" * 60 + "\n")

    # 최종 요약
    if len(tickers) > 1:
        print("\n" + "=" * 60)
        print("📊 분석 완료 요약")
        print("=" * 60)
        print(f"   총 티커 수: {len(tickers)}")
        print(f"   성공: {success_count}")
        print(f"   실패: {fail_count}")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
