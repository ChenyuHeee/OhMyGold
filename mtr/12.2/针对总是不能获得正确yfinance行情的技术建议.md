在查看了你的代码（特别是 `src/ohmygold/services/market_data.py`）之后，我发现有几个常见原因会导致你“无法获取正确的行情”或者获取到看起来像是“假数据”的行情。

这里是排查和修复的步骤：

### 1. 检查是否误触了“模拟数据”模式
你的代码中有一个**静默回退（Silent Fallback）**机制，这最容易导致误解。

在 `market_data.py` 的第 187-189 行：
```python
        except DataProviderError as exc:
            if mode == "hybrid":
                logger.error("Market data provider failed, falling back to mock data: %s", exc)
                return _mock_price_history(symbol, days)
```
如果你的 `.env` 配置中设置了 `DATA_MODE=hybrid`（这通常是默认值），一旦 `yfinance` 下载失败（比如网络超时、被 Yahoo 限流），系统会自动切换到 `_mock_price_history` 生成随机数据。

**解决方法**：
在 `.env` 文件中强制设置：
```ini
DATA_MODE=live
```
这样如果获取失败，程序会直接报错而不是给你假数据，你可以看到具体的错误信息（例如是网络问题还是代码问题）。

### 2. 检查 `yfinance` 的代码（Ticker）
在 `src/ohmygold/tools/data_tools.py` 中，默认的 Symbol 是 `XAUUSD`：
```python
def get_gold_market_snapshot(symbol: str = "XAUUSD", days: int = 30) -> Dict[str, Any]:
```
Yahoo Finance (`yfinance`) 对黄金的代码定义比较特殊：
*   **`GC=F`**: 黄金期货（最常用）
*   **`XAUUSD=X`**: 现货黄金
*   纯 `XAUUSD` 在 Yahoo Finance 上可能无法识别，或者数据不全。

**解决方法**：
尝试在运行命令时明确指定 Yahoo 能识别的代码：
```bash
python -m ohmygold.main --symbol "GC=F" --days 14
# 或者
python -m ohmygold.main --symbol "XAUUSD=X" --days 14
```

### 3. 清除本地缓存
你的代码使用了 `requests_cache` 来缓存数据（第 60 行 `market_data_cache`），并且默认有效期可能较长。如果你之前获取过一次错误数据或旧数据，代码可能会一直读取缓存。

**解决方法**：
删除临时目录下的缓存文件。代码中定义的缓存路径通常在系统的临时文件夹下（`tmp/ohmygold/market_data_cache.sqlite`）。
或者在 `.env` 中临时禁用缓存（如果你有这个配置项），或者手动删除缓存文件。

### 4. 依赖库 `yfinance` 的版本问题
`yfinance` 是一个非官方库，Yahoo 经常更改 API 导致它失效。
**解决方法**：
尝试更新 `yfinance` 到最新版：
```bash
pip install --upgrade yfinance
```

### 总结调试建议
建议你先做这个操作来定位问题：
1.  修改 `.env` 设置 `DATA_MODE=live`。
2.  使用 `python -m ohmygold.main --symbol "GC=F"` 运行。
3.  观察控制台是否有报错信息。如果是网络报错，考虑是否需要配置代理。