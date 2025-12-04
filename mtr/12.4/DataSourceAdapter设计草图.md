# DataSourceAdapter 设计草图

## 1. 角色定位
- 统一封装历史（REST/批量）、实时（WebSocket/Streaming）与回测（离线文件）三类数据通道
- 替换现有 `MarketDataAdapter` 单接口体系，向行情、宏观、衍生品等数据扩展
- 对上：`services/market_data.py`、工具函数、Agent 调用
- 对下：不同供应商 SDK（IBKR、Polygon、FRED、本地 CSV/WebSocket）

## 2. 核心接口
```python
class DataSourceAdapter(ABC):
    name: str
    provider_type: Literal["live", "delayed", "historical", "mock"]

    # 批量历史
    def fetch_ohlcv(self, symbol: str, start: datetime, end: datetime, *, timeframe: str = "1d") -> pd.DataFrame:
        """返回指定周期内的 OHLCV。"""

    # 即时快照
    def snapshot(self, symbol: str) -> QuoteSnapshot:
        """返回最新价格、盘口、成交量等。"""

    # 实时流
    def stream_quotes(
        self,
        symbol: str,
        *,
        on_tick: Callable[[QuoteTick], None],
        on_disconnect: Optional[Callable[[Exception | None], None]] = None,
    ) -> StreamingHandle:
        """订阅实时行情，返回可关闭的句柄。"""

    # 回测钩子
    def iter_backtest_bars(
        self,
        symbol: str,
        *,
        start: datetime,
        end: datetime,
        timeframe: str = "1d",
    ) -> Iterator[Bar]:
        """以生成器方式输出历史Bar，便于策略回放。"""

    # 缓存与重试
    def configure_cache(self, cache: CacheConfig) -> None:
        """注入统一缓存策略（requests-cache / 本地SQLite）。"""

    def configure_retry(self, retry: RetryConfig) -> None:
        """设置重试与退避策略。"""
```

### 支持特性探测
```python
class Capability(NamedTuple):
    streaming: bool
    level2: bool
    historical: bool
    economic_calendar: bool
```

## 3. 关键数据结构
```python
@dataclass
class QuoteSnapshot:
    bid: float | None
    ask: float | None
    last: float | None
    volume: float | None
    timestamp: datetime
    provider: str

@dataclass
class QuoteTick:
    price: float
    size: float
    side: Literal["bid", "ask", "trade"]
    timestamp: datetime
```

`StreamingHandle` 提供 `close()`、`is_active`，供协程/线程安全关闭

## 4. 缓存策略
- 历史数据：默认启用 `requests-cache`，缓存键包含 `provider`、`symbol`、`timeframe`
- 实时数据：可选内存 ring buffer（近期 N 条，用于快照合成）
- 提供统一的 `CacheConfig(expire: timedelta, backend: str, namespace: str)` 数据类

## 5. 回测切换
- `DataSourceRouter` 管理多个 `DataSourceAdapter`
  ```python
  router = DataSourceRouter(live=PolygonAdapter(...), backtest=ParquetAdapter(...))
  router.set_mode("live")  # or "backtest"
  ```
- `services/market_data.fetch_price_history` 将改为调用 `router.fetch_ohlcv`
- 回测模式下提供 `on_bar_advance` 钩子，供策略引擎驱动

## 6. 渐进式落地步骤
1. 在 `services/data_providers/base.py` 引入 `DataSourceAdapter` 抽象，保持现有 `MarketDataAdapter` 兼容
2. 逐步改造已有适配器继承新基类（短期内 `snapshot/stream_quotes` 可抛 `NotImplementedError`）
3. 新增 `services/data_source_router.py` 管理模式切换、缓存策略注入
4. 重构 `market_data.fetch_price_history`、`tools/data_tools.py` 使用新接口，实现宏观/行情统一数据源
5. 引入首个 Streaming 供应商（如 Polygon WebSocket 或 IBKR TWS）进行端到端验证
