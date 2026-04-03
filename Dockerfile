# 使用 ubuntu:24.04 作為基礎映像檔
FROM ubuntu:24.04

# 更新套件庫並安裝程式所需的 OpenSSL 與憑證
RUN apt-get update && apt-get install -y \
    ca-certificates \
    libssl3 \
    && rm -rf /var/lib/apt/lists/*

# 設定容器內的工作目錄
WORKDIR /app

# 將本機的 tms_rust 複製到容器內
COPY tms_rust /app/tms_rust

# 賦予執行權限
RUN chmod +x /app/tms_rust

# 設定啟動指令
CMD ["./tms_rust"]