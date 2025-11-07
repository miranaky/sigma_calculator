"""
샘플 데이터로 StockVolatilityTracker를 테스트합니다.
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sigma_calculator import StockVolatilityTracker


def create_sample_data(num_days=252):
    """
    가상의 주식 데이터를 생성합니다.
    평균 일일 변동률 0.1%, 표준편차 2%로 시뮬레이션
    """
    np.random.seed(42)
    dates = pd.date_range(end=datetime.now(), periods=num_days, freq='D')

    # 시작가 100, 일일 수익률 정규분포 (평균 0.1%, 표준편차 2%)
    daily_returns = np.random.normal(0.001, 0.02, num_days)
    prices = [100]

    for ret in daily_returns[1:]:
        prices.append(prices[-1] * (1 + ret))

    data = pd.DataFrame({
        'Close': prices
    }, index=dates)

    return data


def main():
    print("=" * 60)
    print("📊 주식 변동성 추적기 - 샘플 데이터 테스트")
    print("=" * 60 + "\n")

    # StockVolatilityTracker 인스턴스 생성
    tracker = StockVolatilityTracker('SAMPLE', period_days=365)

    # 샘플 데이터 주입
    print("📊 샘플 주식 데이터를 생성하는 중...")
    tracker.data = create_sample_data(252)
    print(f"✅ {len(tracker.data)}일의 데이터를 생성했습니다.")

    # 변동률 계산
    if not tracker.calculate_daily_returns():
        return

    # 시그마 계산
    if not tracker.calculate_sigma():
        return

    # 리포트 출력
    tracker.print_report()


if __name__ == "__main__":
    main()
