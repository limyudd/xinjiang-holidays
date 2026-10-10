# 新疆节假日 · 中文 iPhone 日历

订阅地址（需启用 GitHub Pages）：

**https://limyudd.github.io/xinjiang-holidays/xinjiang.ics**

包含肉孜节（开斋节）、古尔邦节及新疆已正式公布的额外放假日期。未来 15 年伊斯兰历节日按民用表算历法推算，**预测值不等于当地正式日期**，可能有 1–2 天偏差。已经公布的日期采用自治区官方公告覆盖。

## 部署
1. Settings → Pages → Build and deployment → Source: **Deploy from a branch** → Branch: **main**，Folder: **/docs**。
2. Actions → **更新新疆节假日日历** → Run workflow，首次运行后生成 `docs/xinjiang.ics`。
3. iPhone → 日历 → 日历 → 添加日历 → 添加订阅日历 → 填入上面网址。

## 更新策略
GitHub Actions 每天运行并刷新滚动 15 年日历。 `official.json` 储存正式公告中确认的节日日期和假期区间，优先于推算。每天运行 `sync_official.py`，尝试从新疆自治区政府通知公告列表发现下一年度正式放假通知，并仅在成功识别肉孜节和古尔邦节的节日及假期起止日期时更新 `official.json`。如果网站结构变化、公告多份或提取不确定，会跳过并保留预测值，避免错误覆盖；这种情况需要人工核对。节日预测本身无需人工维护。

2026 官方依据：[自治区人民政府节假日通知](https://www.xinjiang.gov.cn/xinjiang/tzgg/202512/aaece21b6906443e8d50b981070764a8.shtml)。

项目无需 API Key，纯 Python 标准库。GitHub Pages 发布可能有缓存延迟。
