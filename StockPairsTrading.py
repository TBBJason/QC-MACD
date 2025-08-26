from AlgorithmImports import *
from datetime import timedelta

class USStockPairsTrading(QCAlgorithm):  # Renamed for accuracy
    def Initialize(self):
        self.SetStartDate(2024, 6, 1)
        self.SetEndDate(2025, 6, 1)
        self.SetCash(100000)
        self.SetWarmUp(30)  # Warm-up for 30 data points
        
        self.pairs = [("AAPL", "MSFT"), ("META", "GOOGL"), ("SPY", "QQQ")]  # US assets
        
        self.symbols = []
        for pair in self.pairs:
            for ticker in pair:
                # Add US equities (Market.USA)
                symbol = self.AddEquity(ticker, Resolution.HOUR, Market.USA).Symbol
                self.symbols.append(symbol)
        
        self.UniverseSettings.Resolution = Resolution.DAILY
        self.AddAlpha(PairsTradingAlphaModel(self.pairs))
        self.SetPortfolioConstruction(EqualWeightingPortfolioConstructionModel())
        # self.SetRiskManagement(MaximumDrawdownPercentPerSecurity(0.02))
        self.SetExecution(ImmediateExecutionModel())

class PairsTradingAlphaModel(AlphaModel):
    def __init__(self, pairs):
        self.pairs = pairs
        self.spreadMean = {pair: SimpleMovingAverage(30) for pair in pairs}
        self.stdDev = {pair: StandardDeviation(30) for pair in pairs}
        self.macd = {pair: MovingAverageConvergenceDivergence(12, 26, 9, MovingAverageType.Exponential)
                     for pair in pairs}
        self.period = timedelta(hours=4)

    def Update(self, algorithm, data):
        insights = []

        for pair in self.pairs:
            symbol1 = next(s for s in algorithm.Securities.Keys if s.Value == pair[0])
            symbol2 = next(s for s in algorithm.Securities.Keys if s.Value == pair[1])

            if not (data.ContainsKey(symbol1) and data.ContainsKey(symbol2)):
                continue

            spread = data[symbol2].Price - data[symbol1].Price

            # Update indicators
            self.spreadMean[pair].Update(algorithm.Time, spread)
            self.stdDev[pair].Update(algorithm.Time, spread)
            self.macd[pair].Update(algorithm.Time, spread)

            if not (self.spreadMean[pair].IsReady and self.stdDev[pair].IsReady and self.macd[pair].IsReady):
                continue

            mean = self.spreadMean[pair].Current.Value
            std_dev = self.stdDev[pair].Current.Value
            if std_dev == 0:
                continue

            z_score = (spread - mean) / std_dev
            macd_line = self.macd[pair].Current.Value
            signal_line = self.macd[pair].Signal.Current.Value

            # Trade logic
            if macd_line > signal_line: # and z_score < -2:
                insights.append(Insight.Price(symbol2, self.period, InsightDirection.Up))
                # insights.append(Insight.Price(symbol1, self.period, InsightDirection.Down))

            elif macd_line < signal_line: # and z_score > 2:
                # insights.append(Insight.Price(symbol2, self.period, InsightDirection.Down))
                insights.append(Insight.Price(symbol1, self.period, InsightDirection.Up))

        return insights
