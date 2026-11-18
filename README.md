# geosite-ai-mirror

定時鏡像 v2fly [domain-list-community](https://github.com/v2fly/domain-list-community) 嘅
`category-ai-!cn`，**另外剔除 `xai` 與 `google-deepmind` 兩組域名**，編譯成精簡
`geosite-ai.dat`，俾 OpenWrt xray 用 `ext:geosite-ai.dat:category-ai-!cn` 做 AI 分流。

## Pipeline
- GitHub Actions（每週一 04:23 HKT，手動 dispatch 都得）：
  1. 拉 dlc 官方 release 最新 `dlc.dat.xz`
  2. `build_dat.py` 抽取 `category-ai-!cn`，減去 `xai` + `google-deepmind` 兩個 category 嘅 code（byte-level 保留 domain sub-message，語義唔會變）
  3. Sanity gate（kept ≥100、excluded ≥50、chatgpt.com 必須喺入面、grok/x.ai/gemini 必須唔喺入面）
  4. 有變動先 commit `docs/`
- `docs/` 亦係 GitHub Pages 根目录。

## 產物
| 檔 | 說明 |
|---|---|
| `docs/geosite-ai.dat` | 精簡 geodat（category: `CATEGORY-AI-!CN`） |
| `docs/geosite-ai.dat.sha256` | checksum |
| `docs/geosite-ai.dat.list` | 保留域名清單（auditable） |
| `docs/geosite-ai.dat.removed` | 被剔除清單 |

## -router 抓取（jsDelivr）
```
https://cdn.jsdelivr.net/gh/stevendolike/geosite-ai-mirror@main/docs/geosite-ai.dat
```
Router crontab（每週一 04:23 HKT）行 `/root/geosite-ai-update.sh`：fetch → size/sha 檢查 →
`xray run -test` → 通過先替換 + restart，失敗自動 rollback 備份（`/root/geosite-ai.dat.bak-auto`）。

## 手動重建
```
curl -fsSL <dlc.dat.xz release url> -o dlc.dat.xz && xz -d dlc.dat.xz
python3 build_dat.py dlc.dat docs/geosite-ai.dat --exclude "xai,google-deepmind"
```
