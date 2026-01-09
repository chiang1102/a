<?php
// =========================================================================
// IPTV Player V7.15 - 手動幫浦版 (解決 HTTP 500 Timeout 問題)
// =========================================================================
// 修正重點：
// 1. [Mode B] 放棄 stream_copy_to_stream，改用 while 迴圈手動讀寫 (fread/echo)。
// 2. [核心] 加入 flush() 強制刷新，防止 Nginx/Apache 因等待數據而報 500 錯誤。
// 3. [核心] 加入 X-Accel-Buffering: no，禁止伺服器緩衝直播流。
// =========================================================================

// 1. 基礎環境設定
set_time_limit(0);           // 腳本永不超時
ini_set('memory_limit', '512M');
ignore_user_abort(true);     // 允許背景執行(但我們會手動檢測斷線)

// 2. 徹底關閉 PHP 輸出緩衝
if (function_exists('apache_setenv')) {
    @apache_setenv('no-gzip', 1);
}
@ini_set('zlib.output_compression', 0);
@ini_set('implicit_flush', 1);
while (ob_get_level() > 0) {
    ob_end_clean();
}

ini_set('display_errors', 0);
error_reporting(E_ALL);

// =========================================================================
// 設定區
// =========================================================================
$VALID_TOKEN = '0971889022';
$DEFAULT_M3U = 'http://220.135.64.124:5050/?type=m3u';
$COOKIE_NAME = 'iptv_session_v7';
$COOKIE_SRC  = 'iptv_source_url_v7';

// =========================================================================
// A. 邏輯處理區
// =========================================================================
$is_logged_in = false;
$msg = "";
$currentSourceType = "預設訊號";
$m3uContent = "";

if (isset($_GET['logout'])) {
    setcookie($COOKIE_NAME, "", time() - 3600);
    $is_logged_in = false;
} elseif ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['pwd'])) {
    if ($_POST['pwd'] === $VALID_TOKEN) {
        setcookie($COOKIE_NAME, md5($VALID_TOKEN), time() + 86400 * 30);
        $is_logged_in = true;
    } else $msg = "Token 錯誤";
} elseif (isset($_COOKIE[$COOKIE_NAME]) && $_COOKIE[$COOKIE_NAME] === md5($VALID_TOKEN)) {
    $is_logged_in = true;
}

if ($is_logged_in) {
    if ($_SERVER['REQUEST_METHOD'] === 'POST' && isset($_POST['custom_url'])) {
        $url = trim($_POST['custom_url']);
        if (!empty($url)) {
            setcookie($COOKIE_SRC, $url, time() + 86400 * 30);
            $_COOKIE[$COOKIE_SRC] = $url;
        } else {
            setcookie($COOKIE_SRC, "", time() - 3600);
            unset($_COOKIE[$COOKIE_SRC]);
        }
    }

    if (isset($_FILES['m3u_file']) && $_FILES['m3u_file']['error'] === UPLOAD_ERR_OK) {
        $m3uContent = @file_get_contents($_FILES['m3u_file']['tmp_name']);
        $currentSourceType = "本機檔案";
    } elseif (isset($_COOKIE[$COOKIE_SRC]) && !empty($_COOKIE[$COOKIE_SRC])) {
        $opts = ["http"=>["header"=>"User-Agent: Mozilla/5.0\r\ntimeout: 10\r\n"]];
        $m3uContent = @file_get_contents($_COOKIE[$COOKIE_SRC], false, stream_context_create($opts));
        $currentSourceType = "自訂網址";
    } else {
        $opts = ["http"=>["header"=>"User-Agent: Mozilla/5.0\r\ntimeout: 10\r\n"]];
        $m3uContent = @file_get_contents($DEFAULT_M3U, false, stream_context_create($opts));
        $currentSourceType = "預設訊號";
    }
}

// =========================================================================
// B. PHP Proxy 核心 (V7.15 手動幫浦版)
// =========================================================================
if (isset($_GET['proxy_url'])) {
    $targetUrl = $_GET['proxy_url'];
    
    // 判斷是否為複雜模式 (YSP/M3U8)
    $isComplexMode = (strpos($targetUrl, 'ysp') !== false) || (strpos($targetUrl, '.m3u8') !== false);

    if ($isComplexMode) {
        // [模式 A: 列表修復 (cURL)] - 保持不變，因為這部分沒問題
        $ch = curl_init();
        curl_setopt($ch, CURLOPT_URL, $targetUrl);
        curl_setopt($ch, CURLOPT_FOLLOWLOCATION, true);
        curl_setopt($ch, CURLOPT_MAXREDIRS, 5);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, false);
        curl_setopt($ch, CURLOPT_SSL_VERIFYHOST, false);
        curl_setopt($ch, CURLOPT_ENCODING, ''); 
        curl_setopt($ch, CURLOPT_HTTPHEADER, [
            "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Connection: keep-alive"
        ]);
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        
        $content = curl_exec($ch);
        $effectiveUrl = curl_getinfo($ch, CURLINFO_EFFECTIVE_URL);
        curl_close($ch);
        
        if ($content && strpos($content, '#EXTM3U') === 0) {
            header("Access-Control-Allow-Origin: *");
            header("Content-Type: application/vnd.apple.mpegurl");

            $cleanUrl = strtok($effectiveUrl, '?'); 
            $baseUrl = substr($cleanUrl, 0, strrpos($cleanUrl, '/') + 1);
            $protocol = (isset($_SERVER['HTTPS']) && $_SERVER['HTTPS'] === 'on') ? "https" : "http";
            $currentScript = $protocol . "://" . $_SERVER['HTTP_HOST'] . $_SERVER['PHP_SELF'];
            $isYSP = (strpos($targetUrl, 'ysp') !== false);

            $lines = explode("\n", $content);
            foreach ($lines as $line) {
                $line = trim($line);
                if (empty($line)) continue;
                if (strpos($line, '#') !== 0) {
                    if (strpos($line, 'http') !== 0) $line = $baseUrl . $line;
                    if ($isYSP) $line = $currentScript . '?proxy_url=' . urlencode($line);
                }
                echo $line . "\n";
            }
        } else {
            echo $content;
        }
    } else {
        // [模式 B: 手動幫浦串流 (Manual Pump)]
        // 這是解決 500 錯誤的關鍵
        
        $opts = [
            "http" => [
                "method" => "GET",
                "header" => "User-Agent: VLC/3.0.16 LibVLC/3.0.16\r\n" .
                            "Accept: */*\r\n" . 
                            "Connection: close\r\n", 
                "follow_location" => 1,
                "timeout" => 10 // 連線超時，非讀取超時
            ],
            "ssl" => ["verify_peer"=>false, "verify_peer_name"=>false]
        ];
        
        $context = stream_context_create($opts);
        $src = @fopen($targetUrl, 'rb', false, $context);
        
        if ($src) {
            // 發送標頭
            header("Access-Control-Allow-Origin: *");
            header("Content-Type: video/mp2t");
            header("X-Accel-Buffering: no"); // [關鍵] 告訴 Nginx 不要緩衝
            
            // [V7.15 核心] 手動讀取迴圈
            // 每次讀 8KB 就立刻吐出去，不讓 PHP 休息，避免 Server 以為 PHP 掛了
            while (!feof($src)) {
                $chunk = fread($src, 8192); // 讀取 8KB
                
                if ($chunk === false || strlen($chunk) === 0) {
                    break;
                }
                
                echo $chunk;
                flush(); // [關鍵] 強制輸出到瀏覽器
                
                // 如果瀏覽器斷線了，PHP 也停止，節省資源
                if (connection_aborted()) {
                    break;
                }
            }
            fclose($src);
        } else {
            http_response_code(404);
            echo "Stream Unreachable";
        }
    }
    exit;
}

// =========================================================================
// C. M3U 解析
// =========================================================================
$groups = [];
if ($is_logged_in && !empty($m3uContent)) {
    $lines = explode("\n", $m3uContent);
    $tempChannels = [];
    $currentKey = '';

    foreach ($lines as $line) {
        $line = trim($line);
        if (empty($line)) continue;
        if (strpos($line, '#EXTINF:') === 0) {
            $nameParts = explode(',', $line);
            $name = trim(end($nameParts));
            preg_match('/tvg-logo="([^"]*)"/', $line, $logo);
            preg_match('/group-title="([^"]*)"/', $line, $grp);
            $group = $grp[1] ?? '未分類';
            $key = $group . '|' . $name; 
            if (!isset($tempChannels[$key])) {
                $tempChannels[$key] = ['name' => $name, 'logo' => $logo[1] ?? '', 'group' => $group, 'urls' => []];
            }
            $currentKey = $key;
        } elseif (strpos($line, '#') !== 0) {
            if ($currentKey && isset($tempChannels[$currentKey])) {
                $tempChannels[$currentKey]['urls'][] = $line;
            }
        }
    }
    foreach ($tempChannels as $ch) if (!empty($ch['urls'])) $groups[$ch['group']][] = $ch;
}
?>

<!DOCTYPE html>
<html lang="zh-TW">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="referrer" content="no-referrer">
    <title>IPTV Player V7.15</title>
    <script src="https://cdn.jsdelivr.net/npm/hls.js@latest"></script>
    <style>
        body { margin: 0; background: #0f0f0f; color: #e0e0e0; font-family: 'Segoe UI', sans-serif; height: 100vh; display: flex; overflow: hidden; }
        .login-overlay { position: fixed; top:0; left:0; width:100%; height:100%; background:#0f0f0f; z-index:999; display:flex; justify-content:center; align-items:center;}
        .login-box { background:#1e1e1e; padding:30px; border-radius:8px; width:300px; text-align:center; border:1px solid #333; }
        .login-box input { width:100%; padding:12px; margin:15px 0; background:#2a2a2a; border:1px solid #444; color:#fff; border-radius: 4px;}
        .login-box button { width:100%; padding:12px; background:#e50914; color:#fff; border:none; cursor:pointer; border-radius: 4px; font-weight: bold;}

        .sidebar { width: 350px; background: #1a1a1a; border-right: 1px solid #333; display: flex; flex-direction: column; }
        .controls { padding: 15px; border-bottom: 1px solid #333; background: #202020; }
        .settings-panel { display: none; background: #2a2a2a; padding: 10px; margin-bottom: 10px; border-radius: 4px; border: 1px solid #444; }
        .settings-panel.show { display: block; }
        .settings-panel input[type="text"] { width: 100%; padding: 6px; box-sizing: border-box; margin-bottom: 8px; background: #111; border: 1px solid #444; color: #fff; font-size: 12px; }
        .settings-panel button { width: 100%; padding: 6px; background: #444; color: #fff; border: none; cursor: pointer; font-size: 12px; }
        .settings-btn { width: 100%; padding: 8px; background: #333; color: #ccc; border: 1px solid #444; cursor: pointer; margin-bottom: 10px; font-size: 12px; }
        
        .manual-input { display: flex; gap:5px; margin-bottom: 10px; }
        .manual-input input { flex:1; padding:6px; background:#333; color:#fff; border:1px solid #555; border-radius: 3px; font-size: 13px;}
        .manual-input button { padding:6px 12px; background:#444; color:#fff; border:1px solid #555; cursor:pointer; border-radius: 3px;}
        .search-box input { width:100%; padding:8px; background:#333; color:#fff; border:1px solid #555; border-radius: 3px;}
        .list { flex: 1; overflow-y: auto; scrollbar-width: thin; scrollbar-color: #444 #1a1a1a; }
        .g-head { padding: 12px; background: #2a2a2a; cursor: pointer; border-bottom: 1px solid #3d3d3d; display: flex; justify-content: space-between; font-weight: 600; }
        .g-head::after { content: '▼'; font-size: 0.8em; }
        .g-head.collapsed::after { transform: rotate(-90deg); }
        .g-body.collapsed { display: none !important; }
        .item { padding: 10px; border-bottom: 1px solid #252525; }
        .item:hover { background: #333; }
        .item.active { background: #2d2d2d; border-left: 3px solid #e50914; }
        .i-main { display: flex; align-items: center; cursor: pointer; }
        .logo { width: 30px; height: 30px; margin-right: 12px; background: #000; object-fit: contain; border-radius: 2px;}
        .lines { margin-top: 6px; margin-left: 42px; display: flex; flex-wrap: wrap; gap: 6px; }
        .l-btn { font-size: 11px; padding: 2px 8px; background: #333; color: #bbb; border: 1px solid #444; cursor: pointer; border-radius: 2px; }
        .l-btn.active { background: #e50914; color: #fff; border-color: #e50914; }
        .main { flex: 1; background: #000; display: flex; justify-content: center; align-items: center; position: relative; }
        video { width: 100%; height: 100%; max-height: 100vh; }
        @media(max-width:768px){ body{flex-direction:column;} .sidebar{height:45vh;width:100%;} .main{height:55vh;} }
    </style>
</head>
<body>

<?php if (!$is_logged_in): ?>
    <div class="login-overlay">
        <div class="login-box">
            <h2 style="color:#e50914; margin-top:0;">IPTV V7.15</h2>
            <?php if($msg): ?><p style="color:#ff6b6b; font-size:14px;"><?php echo $msg; ?></p><?php endif; ?>
            <form method="post"><input type="password" name="pwd" placeholder="輸入 Token" required autofocus><button type="submit">進入播放器</button></form>
        </div>
    </div>
<?php else: ?>
    <div class="sidebar">
        <div class="controls">
            <button class="settings-btn" onclick="toggleSettings()">⚙️ 訊號源設定 (目前: <?php echo htmlspecialchars($currentSourceType); ?>)</button>
            <div id="settingsPanel" class="settings-panel">
                <h4>更改訊號源</h4>
                <form method="post" enctype="multipart/form-data">
                    <input type="text" name="custom_url" placeholder="輸入 http/https M3U 網址" value="<?php echo isset($_COOKIE[$COOKIE_SRC]) ? htmlspecialchars($_COOKIE[$COOKIE_SRC]) : ''; ?>">
                    <input type="file" name="m3u_file" accept=".m3u,.m3u8" style="margin-bottom:8px; width:100%; color:#ccc; font-size:12px;">
                    <button type="submit" style="background:#e50914; margin-top:5px;">套用設定</button>
                    <button type="button" onclick="clearSettings()" style="background:#444; margin-top:5px;">恢復預設值</button>
                </form>
            </div>
            <div class="manual-input">
                <input type="text" id="mUrl" placeholder="手動貼上播放連結...">
                <button onclick="playManual()">播放</button>
            </div>
            <div class="search-box">
                <input type="text" id="search" placeholder="搜尋頻道..." onkeyup="filterList()">
            </div>
            <a href="?logout=1" style="display:block;margin-top:8px;text-align:center;color:#666;font-size:12px;text-decoration:none;">安全登出</a>
        </div>
        <div class="list" id="list">
            <?php if(empty($groups)): ?>
                <div style="padding:20px; text-align:center; color:#666;">沒有載入任何頻道。</div>
            <?php else: ?>
                <?php foreach($groups as $gName => $gChs): ?>
                    <div class="g-head collapsed" onclick="toggleGrp(this)"><span><?php echo htmlspecialchars($gName); ?></span></div>
                    <div class="g-body collapsed">
                        <?php foreach($gChs as $ch): ?>
                            <div class="item" data-name="<?php echo htmlspecialchars($ch['name']); ?>">
                                <div class="i-main" onclick="play('<?php echo $ch['urls'][0]; ?>', this, 0)">
                                    <img src="<?php echo htmlspecialchars($ch['logo']?:''); ?>" class="logo" onerror="this.src='data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCIgZmlsbD0iIzMzMyI+PHBhdGggZD0iTTAgMGgyNHYyNEgwVjB6Ii8+PC9zdmc+'">
                                    <span class="ch-name"><?php echo htmlspecialchars($ch['name']); ?></span>
                                </div>
                                <?php if(count($ch['urls'])>1): ?>
                                    <div class="lines"><?php foreach($ch['urls'] as $i=>$u): ?><div class="l-btn" onclick="event.stopPropagation();play('<?php echo $u; ?>',this.closest('.item'),<?php echo $i; ?>)">線路 <?php echo $i+1; ?></div><?php endforeach; ?></div>
                                <?php endif; ?>
                            </div>
                        <?php endforeach; ?>
                    </div>
                <?php endforeach; ?>
            <?php endif; ?>
        </div>
    </div>
    <div class="main"><video id="vid" controls autoplay></video></div>
    <script>
        function toggleSettings() { document.getElementById('settingsPanel').classList.toggle('show'); }
        function clearSettings() { document.querySelector('input[name="custom_url"]').value = ""; document.forms[0].submit(); }
        var hls = null;
        var vid = document.getElementById('vid');
        function playManual() { var url = document.getElementById('mUrl').value; if(url) play(url.trim(), null, -1); }
        function play(url, el, idx) {
            if(el) {
                document.querySelectorAll('.item').forEach(e => e.classList.remove('active'));
                document.querySelectorAll('.l-btn').forEach(e => e.classList.remove('active'));
                el.classList.add('active');
                if(idx >= 0) el.querySelectorAll('.l-btn')[idx]?.classList.add('active');
            }
            var cur = window.location.pathname.split('/').pop() || "index.php";
            var useProxy = false;
            var hasPort = url.match(/:[0-9]{2,5}/);
            var isStandard = url.includes(':80/') || url.includes(':443/');
            var isNested = url.includes('/http/'); 
            if (url.includes('.php') || url.includes('mqlive') || url.includes('jamin') || url.includes('ysp') || url.includes('/udp/')) useProxy = true;
            if(location.protocol === 'https:' && url.startsWith('http:')) useProxy = true;
            if (hasPort && !isStandard && !isNested) useProxy = true;
            var final = useProxy ? (cur + "?proxy_url=" + encodeURIComponent(url)) : url;
            console.log("Play:", final);
            if(Hls.isSupported()) {
                if(hls) hls.destroy();
                hls = new Hls({ manifestLoadingTimeOut: 20000, manifestLoadingMaxRetry: 4, enableWorker: true });
                hls.loadSource(final);
                hls.attachMedia(vid);
                hls.on(Hls.Events.MANIFEST_PARSED, () => vid.play());
                hls.on(Hls.Events.ERROR, function (event, data) {
                    if (data.fatal) {
                        if(data.type === Hls.ErrorTypes.NETWORK_ERROR) hls.startLoad(); else hls.destroy();
                    }
                });
            } else if(vid.canPlayType('application/vnd.apple.mpegurl')) { vid.src = final; vid.play(); }
        }
        function toggleGrp(h) { h.classList.toggle('collapsed'); var b = h.nextElementSibling; if(b && b.classList.contains('g-body')) b.classList.toggle('collapsed'); }
        function filterList() {
            var v = document.getElementById('search').value.toUpperCase();
            var bodies = document.getElementsByClassName('g-body');
            for(var i=0; i<bodies.length; i++) {
                var body = bodies[i];
                var head = body.previousElementSibling;
                var items = body.getElementsByClassName('item');
                var hit = false;
                for(var j=0; j<items.length; j++) {
                    if(items[j].getAttribute('data-name').toUpperCase().indexOf(v) > -1) { items[j].style.display = ""; hit = true; } else items[j].style.display = "none";
                }
                head.style.display = hit ? "" : "none";
                if(hit && v !== "") { head.classList.remove('collapsed'); body.classList.remove('collapsed'); }
            }
        }
    </script>
<?php endif; ?>
</body>
</html>