FROM php:8.2-alpine

WORKDIR /app

# 這裡最關鍵：它會去抓我們剛剛建立的 index.php
COPY index.php .

# 安裝時區 (避免時間錯誤)
RUN apk add --no-cache tzdata

EXPOSE 80

CMD ["php", "-S", "0.0.0.0:80", "index.php"]
