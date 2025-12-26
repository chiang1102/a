# coding=utf-8
# !/usr/bin/python
import sys
import requests
import re
import json
from bs4 import BeautifulSoup

class Spider(object):
    # 初始化
    def init(self, extend=""):
        pass

    # 定義請求頭，避免被擋
    def getHeaders(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Referer": "https://www.movieffm.net/"
        }

    # 1. 首頁分類配置
    def homeContent(self, filter):
        result = {}
        # 手動定義分類，這樣比爬取快且穩定
        # 注意：這裡的 type_id 要對應網站 URL 的路徑，例如 /category/movies/ -> type_id="movies"
        classes = []
        classes.append({"type_name": "電影", "type_id": "movies"})
        classes.append({"type_name": "連續劇", "type_id": "tv-shows"})
        classes.append({"type_name": "動漫", "type_id": "anime"})
        classes.append({"type_name": "綜藝", "type_id": "variety"})
        
        result["class"] = classes
        # 如果網站有篩選器可在此定義，這裡暫時留空
        result["filters"] = {} 
        return result

    # 首頁推薦視頻 (可選，這裡留空)
    def homeVideoContent(self):
        return {}

    # 2. 分類列表資源
    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 構建 URL: https://www.movieffm.net/category/{tid}/page/{pg}/
        url = 'https://www.movieffm.net/category/{}/page/{}/'.format(tid, pg)
        
        try:
            r = requests.get(url, headers=self.getHeaders())
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            videos = []
            # 【關鍵】這裡需要根據實際網頁結構調整 CSS 選擇器
            # 假設列表項在 class="item" 或 article 標籤中
            # 下面是常見的結構猜測，如果讀取不到，請檢查網頁源碼
            items = soup.select('article.item') # 或 soup.select('.movie-item')
            
            if not items:
                # 嘗試另一種常見結構
                items = soup.select('.result-item')

            for item in items:
                # 獲取標題
                title_tag = item.select_one('.title a') or item.select_one('h3 a')
                name = title_tag.text.strip() if title_tag else "未知標題"
                
                # 獲取圖片
                img_tag = item.select_one('img')
                pic = img_tag['src'] if img_tag else ""
                if "http" not in pic and pic: # 處理相對路徑
                    pic = "https:" + pic
                
                # 獲取詳情頁 ID (即 URL)
                link = title_tag['href']
                vid = link  # 直接把完整鏈接當作 ID

                # 獲取狀態 (如: HD, 更新至xx集)
                remark_tag = item.select_one('.quality') or item.select_one('.features')
                remark = remark_tag.text.strip() if remark_tag else ""

                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })

            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 9999 # 假設有很多頁
            result['limit'] = len(videos)
            result['total'] = 9999
            
        except Exception as e:
            print(f"Error in categoryContent: {e}")
        
        return result

    # 3. 詳情頁內容
    def detailContent(self, ids):
        # ids 是一個列表，通常只有一個元素
        url = ids[0]
        result = {}
        
        try:
            r = requests.get(url, headers=self.getHeaders())
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            vod = {}
            # 獲取基本信息
            title = soup.select_one('h1.entry-title').text.strip() if soup.select_one('h1.entry-title') else "未知"
            desc = soup.select_one('.entry-content').text.strip() if soup.select_one('.entry-content') else ""
            
            # 演員/導演等信息 (根據實際結構提取)
            # actors = ...
            
            vod["vod_id"] = url
            vod["vod_name"] = title
            vod["vod_pic"] = "" # 詳情頁圖片可選
            vod["type_name"] = ""
            vod["vod_year"] = ""
            vod["vod_area"] = ""
            vod["vod_remarks"] = ""
            vod["vod_actor"] = ""
            vod["vod_director"] = ""
            vod["vod_content"] = desc
            
            # 【關鍵】解析播放線路
            # 尋找播放列表區域
            play_url_list = []
            # 假設結構：多個線路 tab，對應多個列表
            # 這裡簡化處理：抓取所有可見的播放鏈接
            
            # 格式：名稱$鏈接#名稱$鏈接
            # 假設網站使用 dooplay 或類似主題，播放源通常在 javascript 或特定的 div 中
            # 簡單範例：抓取含有 iframe 或 跳轉鏈接的按鈕
            
            # 假設只有一個播放列表，名為 "預設線路"
            source_name = "MovieFFM線路"
            source_urls = []
            
            # 查找播放連結 (這部分最需要根據網站實際情況修改)
            # 很多網站將播放連結加密在 JS 變量中，或直接放在 a 標籤
            # 這裡假設它有一個播放列表區塊
            episodes = soup.select('.episodios li a') # 連續劇常見結構
            if not episodes:
                 episodes = soup.select('.player_nav li a') # 另一種結構

            if episodes:
                for ep in episodes:
                    ep_name = ep.text.strip()
                    ep_url = ep['href']
                    source_urls.append(f"{ep_name}${ep_url}")
            else:
                # 如果是電影，可能直接就是當前頁面播放，或者有一個 'Play' 按鈕
                # 為了簡單，我們把當前頁面作為播放頁傳給 playerContent 處理
                source_urls.append(f"立即播放${url}")

            vod["vod_play_from"] = source_name
            vod["vod_play_url"] = "#".join(source_urls)

            result["list"] = [vod]
            
        except Exception as e:
            print(f"Error in detailContent: {e}")
            
        return result

    # 4. 搜索功能
    def searchContent(self, key, quick):
        result = {}
        # 搜索 URL: https://www.movieffm.net/?s={key}
        url = 'https://www.movieffm.net/?s={}'.format(key)
        
        try:
            r = requests.get(url, headers=self.getHeaders())
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            videos = []
            # 搜索結果的結構通常和分類列表相似
            items = soup.select('.result-item') # 假設搜索結果 class
            if not items:
                items = soup.select('article.item')

            for item in items:
                title_tag = item.select_one('.title a') or item.select_one('h3 a')
                name = title_tag.text.strip() if title_tag else "未知"
                
                img_tag = item.select_one('img')
                pic = img_tag['src'] if img_tag else ""
                
                link = title_tag['href']
                vid = link
                
                videos.append({
                    "vod_id": vid,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": ""
                })
                
            result['list'] = videos
            
        except Exception as e:
            print(f"Error in searchContent: {e}")
            
        return result

    # 5. 播放器解析
    def playerContent(self, flag, id, vipFlags):
        result = {}
        # id 是從 detailContent 傳過來的鏈接
        url = id
        
        # 這裡有兩種情況：
        # 1. 如果 id 本身就是 mp4/m3u8 連結 -> 直接播放
        # 2. 如果 id 是網頁連結 -> 需要再次請求該網頁，提取 iframe src 或真實地址
        
        # 簡單策略：使用 webview (嗅探) 模式
        # 這會告訴 TVBox 打開一個隱藏瀏覽器加載該頁面，並自動嗅探媒體文件
        result["parse"] = 1 # 1=嗅探, 0=直接播放
        result["playUrl"] = "" 
        result["url"] = url 
        result["header"] = self.getHeaders()
        
        return result

    # 本地測試入口
    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]