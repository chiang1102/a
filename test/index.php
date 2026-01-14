<?php
// === 設定區域 ===
error_reporting(0);
date_default_timezone_set('Asia/Shanghai');

// [Docker 優化] 優先從環境變數讀取 Token，若無則使用預設值
$valid_token = getenv('APP_TOKEN') ?: "0971889022";

// === 1. Token 驗證邏輯 ===
$user_token = $_GET['token'] ?? ''; 

if ($user_token !== $valid_token) {
    header('HTTP/1.1 403 Forbidden');
    die("存取被拒：Token 錯誤或遺失。");
}

// === Header 優化：防止瀏覽器/播放器快取導致的死循環 ===
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Cache-Control: post-check=0, pre-check=0", false);
header("Pragma: no-cache");
header("Access-Control-Allow-Origin: *"); 

// === 2. 定義輸出修改器 ===
function rewrite_output($buffer) {
    global $valid_token;

    // --- A. 處理 Header 轉址 ---
    $headers = headers_list();
    foreach ($headers as $header) {
        if (stripos($header, 'Location:') === 0) {
            $url = trim(substr($header, 9));
            if (strpos($url, 'token=') === false) {
                $separator = (strpos($url, '?') !== false) ? '&' : '?';
                $new_url = $url . $separator . 'token=' . $valid_token;
                header("Location: $new_url", true); 
            }
            return ""; 
        }
    }

    // --- B. 處理文字內容 (針對列表/M3U8) ---
    // 針對 .php?id=xxx 補上 token
    if (strpos($buffer, 'token=') === false) {
        $buffer = preg_replace('/(\.php\?id=[^&\s"\'<]+)/', '$1&token=' . $valid_token, $buffer);
    }

    return $buffer;
}

// === 函式定義 ===
function check_cache($php_file, $st_info){
    if(!file_exists($php_file) || !file_exists($st_info)) return false;
    
    $data = json_decode(file_get_contents($st_info), true) ?? false;
    
    // [效能優化] 緩存時間設為 60 秒，確保 Token 有效性
    if($data === false || (time() - $data["update_time"] > 60) || empty($data["uuid"])) {
        return false;
    }
    return true;
}

function creat_random_uuid(){
    try { $data = random_bytes(16); } catch (Exception $e) { $data = openssl_random_pseudo_bytes(16); }
    $data[6] = chr(ord($data[6]) & 0x0f | 0x40);
    $data[8] = chr(ord($data[8]) & 0x3f | 0x80);
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex($data), 4));
}

function fetch_url($url, $uuid){
    // [關鍵修復] 透傳播放器的 User-Agent，解決播放 5 秒後卡頓
    $current_ua = $_SERVER['HTTP_USER_AGENT'] ?? $uuid;
    
    $options = [
        "http" => [
            "method" => "GET",
            "header" => "User-Agent: " . $current_ua . "\r\n" . 
                        "X-Forwarded-For: " . ($_SERVER['REMOTE_ADDR'] ?? '127.0.0.1') . "\r\n" . 
                        "Connection: close\r\n",
            "timeout" => 5
        ]
    ];
    $context = stream_context_create($options);
    return @file_get_contents($url, false, $context);
}

// === 主程式邏輯 ===
// [Docker 優化] 使用 /tmp 目錄，解決唯讀容器權限問題
$php_file = "/tmp/cache_code.php";
$st_info = "/tmp/st_info.json";

// 檢查緩存
if(check_cache($php_file, $st_info) === false){
    $existing_data = json_decode(@file_get_contents($st_info), true);
    $uuid = $existing_data['uuid'] ?? creat_random_uuid();
    
    $php = fetch_url("https://litv.msbot.dpdns.org/litv.php", $uuid);
    
    if($php !== false && strlen($php) >= 100){
        file_put_contents($php_file, $php);
        file_put_contents($st_info, json_encode(["update_time" => time(), "uuid" => $uuid]));
    }
}

if(!file_exists($php_file) || filesize($php_file) < 100) {
    header('HTTP/1.1 502 Bad Gateway');
    die("源站抓取失敗，請檢查網路連線或稍後重試。");
}

// === 3. 啟動緩衝並執行 ===
ob_start('rewrite_output');
include($php_file);
ob_end_flush();
exit;
?>