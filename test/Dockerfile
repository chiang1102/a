# 1. 改用 Alpine 版本 (基底只有約 5MB，加上 PHP 約 80MB)
FROM php:8.2-alpine

# 2. 設定工作目錄
WORKDIR /app

# 3. 複製程式碼 (注意：這裡直接複製 index.php)
COPY index.php .

# 4. 安裝時區資料 (Alpine 預設沒有時區檔，為了您的 Asia/Shanghai 設定)
RUN apk add --no-cache tzdata

# 5. 暴露 Port 80
EXPOSE 80

# 6. 啟動命令：直接使用 PHP 內建的 Web Server (取代肥大的 Apache)
# 參數說明：-S 啟動伺服器, 0.0.0.0:80 監聽所有 IP 的 80 Port
CMD ["php", "-S", "0.0.0.0:80", "index.php"]