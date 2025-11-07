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


class StockVolatilityTracker:
    """주식 변동성을 추적하고 시그마 값을 계산하는 클래스"""

    def __init__(self, ticker: str, period_days: int = 365):
        """
        Args:
            ticker: 주식 티커 (예: 'AAPL', '005930.KS')
            period_days: 분석 기간 (기본값: 365일)
        """
        self.ticker = ticker.upper()
        self.period_days = period_days
        self.data: Optional[pd.DataFrame] = None
        self.daily_returns: Optional[pd.Series] = None
        self.mean: Optional[float] = None
        self.std: Optional[float] = None

    def fetch_data(self) -> bool:
        """주식 데이터를 다운로드합니다."""
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=self.period_days)

            print(f"📊 {self.ticker} 데이터를 다운로드하는 중...")

            # yfinance Ticker 객체 사용 (session은 자동 처리)
            ticker_obj = yf.Ticker(self.ticker)
            self.data = ticker_obj.history(start=start_date, end=end_date, auto_adjust=True)

            if self.data is None or self.data.empty:
                print(f"❌ {self.ticker}에 대한 데이터를 찾을 수 없습니다.")
                print(f"   티커 심볼을 확인해주세요.")
                return False

            print(f"✅ {len(self.data)}일의 데이터를 다운로드했습니다.")
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

        print("\n" + "="*60)
        print(f"📈 {self.ticker} 주식 변동성 분석 리포트")
        print("="*60)
        print(f"\n📅 분석 기간: 최근 {self.period_days}일")
        print(f"📊 분석 데이터: {len(self.daily_returns)}일의 일일 변동률")

        print(f"\n📉 기본 통계:")
        print(f"   평균 일일 변동률: {sigma_levels['mean']:+.4f}%")
        print(f"   표준편차 (1σ): {sigma_levels['std']:.4f}%")

        print(f"\n🎯 내일 예상 변동 범위:")
        print(f"\n   1 시그마 (68.3% 확률):")
        print(f"      상승: +{sigma_levels['1_sigma_up']:.2f}% 이상")
        print(f"      하락: {sigma_levels['1_sigma_down']:.2f}% 이하")

        print(f"\n   2 시그마 (95.4% 확률):")
        print(f"      상승: +{sigma_levels['2_sigma_up']:.2f}% 이상")
        print(f"      하락: {sigma_levels['2_sigma_down']:.2f}% 이하")

        print(f"\n   3 시그마 (99.7% 확률):")
        print(f"      상승: +{sigma_levels['3_sigma_up']:.2f}% 이상")
        print(f"      하락: {sigma_levels['3_sigma_down']:.2f}% 이하")

        print("\n" + "="*60)
        print("\n💡 해석:")
        print("   - 1σ: 내일 변동률이 이 범위를 벗어날 확률 약 31.7%")
        print("   - 2σ: 내일 변동률이 이 범위를 벗어날 확률 약 4.6%")
        print("   - 3σ: 내일 변동률이 이 범위를 벗어날 확률 약 0.3%")
        print("="*60 + "\n")

    def analyze(self) -> bool:
        """전체 분석 프로세스를 실행합니다."""
        if not self.fetch_data():
            return False

        if not self.calculate_daily_returns():
            return False

        if not self.calculate_sigma():
            return False

        self.print_report()
        return True


def main():
    """메인 함수"""
    # 명령줄 인자 파싱
    parser = argparse.ArgumentParser(
        description='주식 변동성 추적기 - 일일 변동률의 시그마 값을 계산합니다.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
사용 예시:
  python sigma_calculator.py AAPL          # 애플 주식 분석
  python sigma_calculator.py 005930.KS     # 삼성전자 분석
  python sigma_calculator.py TSLA -d 180   # 테슬라 180일 분석
  python sigma_calculator.py               # 대화형 모드
        """
    )
    parser.add_argument(
        'ticker',
        nargs='?',
        help='주식 티커 심볼 (예: AAPL, TSLA, 005930.KS). 생략하면 대화형 모드로 실행됩니다.'
    )
    parser.add_argument(
        '-d', '--days',
        type=int,
        default=365,
        help='분석 기간 (일 수, 기본값: 365)'
    )

    args = parser.parse_args()

    print("=" * 60)
    print("📊 주식 변동성 추적기 (Stock Volatility Tracker)")
    print("=" * 60 + "\n")

    # 티커 결정
    if args.ticker:
        ticker = args.ticker.strip()
    else:
        # 대화형 모드
        ticker = input("주식 티커를 입력하세요 (예: AAPL, TSLA, 005930.KS): ").strip()

    if not ticker:
        print("❌ 티커를 입력해주세요.")
        return

    # 분석 실행
    tracker = StockVolatilityTracker(ticker, period_days=args.days)
    tracker.analyze()


if __name__ == "__main__":
    main()
