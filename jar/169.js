function main(item) {
    const __CACHE__ = {};
    // 基础参数获取
    let url = item["url"];
    let id = ku9.getQuery(url, "id") || '12';
    const jsonUrl = 'http://45.207.194.97/p3p169.php';

    // 缓存配置
    const CACHE_KEY = 'port_data_cache';
    const CACHE_EXPIRY = 3600 * 1000; // 1小时缓存

    // 尝试从内存缓存读取
    let portData = null;
    if (__CACHE__[CACHE_KEY] && Date.now() < __CACHE__[CACHE_KEY].expiry) {
        portData = __CACHE__[CACHE_KEY].data;
    }

    // 缓存未命中时重新请求
    if (!portData) {
        const headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
        };
        portData = ku9.get(jsonUrl, JSON.stringify(headers));

        // 写入内存缓存
        if (portData) {
            __CACHE__[CACHE_KEY] = {
                data: portData,
                expiry: Date.now() + CACHE_EXPIRY
            };
        }
    }

    // 端口提取逻辑
    const regex = /p3p:\/\/108\.181\.32\.169:(\d+)/;
    const match = portData.match(regex);
    const dk = match ? match[1] : '';

    // 构建最终URL
    const url2 = `p3p://108.181.32.169:${dk}/${id}`;

    return JSON.stringify({ url: url2 });
}