# 網站維護（給 Claude）

- 頁面來源：Claude artifact「大阪京都 六日行」的 kansai_trip.html；`build_site.py` 加上 `window.TIX_STATIC=1` 變成 index.html。
- 票券明文正本（vault.json + 原始檔）**不放這個 repo**，存在使用者電腦 `旅遊\20261024大阪玩\票券原檔\`。
- 重建：`TIX_PW=<密碼> python3 -I tools/build_site.py <kansai_trip.html> <票券原檔/vault.json> <repo 根目錄>`；salt 沿用 manifest，換 salt 會讓手機記住的 Face ID 失效。
- 部署：push 到 main，GitHub Pages（main / root）。
