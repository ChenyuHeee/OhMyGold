
### ⚠️ 重要注意事项：免费版的限制

在开发时，**务必注意**免费 Key 的硬性限制，否则程序会报错：

*   **频率限制**：每分钟最多 **5 次**请求。
*   **总量限制**：每天最多 **25 次**请求（以前是 500 次，现在收紧了）。

**针对您的项目，我有以下开发建议来规避这个限制：**

1.  **缓存数据（Caching）**：
    不要让您的 Agent 每次思考都去调 API。
    *   写一个 `fetch_news.py` 脚本，每天早上 8:00 运行一次，把新闻存成 `news_today.json`。
    *   让您的 AI Agent 读取这个本地 JSON 文件，而不是直接调 API。

2.  **只抓“情绪”接口**：
    把每天那宝贵的 25 次额度，全部用在核心接口 `NEWS_SENTIMENT` 上。

    **测试代码 (Python)：**
    您可以立刻用这行代码测试您的 Key 是否生效（替换 `YOUR_API_KEY`）：

    ```python
    import requests

    url = "https://www.alphavantage.co/query"
    params = {
        "function": "NEWS_SENTIMENT",
        "tickers": "XAUUSD", # 专门针对黄金/美元
        "limit": "5",        # 只取最新的5条
        "apikey": "YOUR_API_KEY"
    }

    response = requests.get(url, params=params)
    data = response.json()

    # 打印第一条新闻的情绪得分
    if "feed" in data:
        print(f"标题: {data['feed'][0]['title']}")
        print(f"情绪分: {data['feed'][0]['overall_sentiment_score']}")
    else:
        print("API请求受限或出错:", data)
    ```
