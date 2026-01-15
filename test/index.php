<?php
// === 設定區域 ===
error_reporting(0);
date_default_timezone_set('Asia/Shanghai');

// [健康檢查] 讓 Koyeb 知道程式活著
if (isset($_SERVER['REQUEST_URI']) && $_SERVER['REQUEST_URI'] === '/health') {
    http_response_code(200);
    die("OK");
}

$valid_token = getenv('APP_TOKEN') ?: "0971889022";
$user_token = $_GET['token'] ?? ''; 

if ($user_token !== $valid_token) {
    header('HTTP/1.1 403 Forbidden');
    die("Access Denied");
}

// Header 優化
header("Cache-Control: no-store, no-cache, must-revalidate, max-age=0");
header("Access-Control-Allow-Origin: *"); 

function rewrite_output($buffer) {
    global $valid_token;
    if (strpos($buffer, 'token=') === false) {
        $buffer = preg_replace('/(\.php\?id=[^&\s"\'<]+)/', '$1&token=' . $valid_token, $buffer);
    }
    return $buffer;
}

function check_cache($php_file, $st_info){
    if(!file_exists($php_file) || !file_exists($st_info)) return false;
    $data = json_decode(file_get_contents($st_info), true) ?? false;
    if($data === false || (time() - $data["update_time"] > 60) || empty($data["uuid"])) return false;
    return true;
}

function fetch_url($url, $uuid){
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

// 使用 /tmp 確保可寫
$php_file = "/tmp/cache_code.php";
$st_info = "/tmp/st_info.json";

// 簡單 UUID 生成
function get_uuid() {
    return vsprintf('%s%s-%s-%s-%s-%s%s%s', str_split(bin2hex(random_bytes(16)), 4));
}

if(check_cache($php_file, $st_info) === false){
    $existing = json_decode(@file_get_contents($st_info), true);
    $uuid = $existing['uuid'] ?? get_uuid();
    $php = fetch_url("https://litv.msbot.dpdns.org/litv.php", $uuid);
    if($php && strlen($php) > 100){
        file_put_contents($php_file, $php);
        file_put_contents($st_info, json_encode(["update_time" => time(), "uuid" => $uuid]));
    }
}

if(!file_exists($php_file)) { die("Error loading source."); }

ob_start('rewrite_output');
include($php_file);
ob_end_flush();
exit;
?>
