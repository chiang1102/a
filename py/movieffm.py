# coding=utf-8
# !/usr/bin/python
import sys
import requests
import re
import json
from bs4 import BeautifulSoup

class Spider(object):
    def init(self, extend=""):
        pass

    def getHeaders(self):
        return {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
            "Referer": "https://www.movieffm.net/",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7"
        }

    def homeContent(self, filter):
        result = {}
        classes = []
        # 注意：這裡的 type_id 必須對應網站 url 路徑
        classes.append({"type_name": "電影", "type_id": "movies"})
        classes.append({"type_name": "連續劇", "type_id": "tv-shows"})
        classes.append({"type_name": "動漫", "type_id": "anime"})
        classes.append({"type_name": "綜藝", "type_id": "variety"})
        
        result["class"] = classes
        result["filters"] = {} 
        return result

    def homeVideoContent(self):
        return {}

    # 統一解析列表項目的輔助函數
    def parse_items(self, soup):
        videos = []
        # 定義多種可能的 CSS 選擇器，逐一嘗試
        selectors = [
            'ul.products li.product',  # 結構 A
            'article.item',            # 結構 B (常見)
            '.items .item',            # 結構 C
            '.result-item',            # 結構 D
            '.TPost',                  # 結構 E (Toroplay)
            'div.poster'               # 結構 F
        ]
        
        items = []
        for sel in selectors:
            items = soup.select(sel)
            if items:
                # print(f"Matched selector: {sel}") # 調試用
                break
        
        for item in items:
            try:
                # 1. 解析標題
                title_tag = item.select_one('.entry-title a') or \
                            item.select_one('.title a') or \
                            item.select_one('h3 a') or \
                            item.select_one('a.woocommerce-LoopProduct-link')
                
                if not title_tag: continue
                name = title_tag.text.strip()
                link = title_tag['href']
                
                # 2. 解析圖片 (處理懶加載 data-src)
                img_tag = item.select_one('img')
                pic = ""
                if img_tag:
                    # 優先讀取懶加載屬性，防止取到空圖或 loading 圖
                    pic = img_tag.get('data-src') or \
                          img_tag.get('data-original') or \
                          img_tag.get('src')
                    
                    if pic and "http" not in pic:
                        pic = "https:" + pic

                # 3. 解析備註 (狀態/年份)
                remark = ""
                remark_tag = item.select_one('.quality') or \
                             item.select_one('.features') or \
                             item.select_one('.onsale') or \
                             item.select_one('.note')
                if remark_tag:
                    remark = remark_tag.text.strip()

                videos.append({
                    "vod_id": link,
                    "vod_name": name,
                    "vod_pic": pic,
                    "vod_remarks": remark
                })
            except Exception as e:
                continue
                
        return videos

    def categoryContent(self, tid, pg, filter, extend):
        result = {}
        # 修正 URL 拼接邏輯，確保符合 WordPress 分頁結構
        if pg == "1":
            url = 'https://www.movieffm.net/category/{}/'.format(tid)
        else:
            url = 'https://www.movieffm.net/category/{}/page/{}/'.format(tid, pg)
        
        try:
            r = requests.get(url, headers=self.getHeaders(), timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            videos = self.parse_items(soup)

            result['list'] = videos
            result['page'] = pg
            result['pagecount'] = 999
            result['limit'] = len(videos)
            result['total'] = 9999
            
        except Exception as e:
            pass # 這裡可以 print(e) 進行調試
        
        return result

    def detailContent(self, ids):
        url = ids[0]
        result = {}
        
        try:
            r = requests.get(url, headers=self.getHeaders(), timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            vod = {}
            # 詳情標題
            title_tag = soup.select_one('h1.entry-title') or soup.select_one('.product_title')
            title = title_tag.text.strip() if title_tag else "未知"
            
            # 劇情簡介
            desc_tag = soup.select_one('.entry-content') or \
                       soup.select_one('.woocommerce-product-details__short-description') or \
                       soup.select_one('#desc')
            desc = desc_tag.text.strip() if desc_tag else ""
            
            vod["vod_id"] = url
            vod["vod_name"] = title
            vod["vod_content"] = desc
            vod["vod_pic"] = "" 
            
            # 解析播放線路
            source_urls = []
            
            # 策略A: 抓取標準播放列表 (dooplay/toroplay)
            eps = soup.select('.episodios li a') or \
                  soup.select('#player-options ul li') or \
                  soup.select('.dooplay_player_option')
            
            if eps:
                for index, ep in enumerate(eps):
                    ep_name = ep.text.strip()
                    if not ep_name: ep_name = f"線路{index+1}"
                    # 有些是 javascript 點擊，這裡簡單處理，將當前頁面作為播放源
                    # 如果有 href 且不是 #，則使用 href
                    ep_url = ep.get('href')
                    if not ep_url or ep_url == "#":
                         ep_url = url 
                    
                    # 避免重複添加相同的 URL
                    source_urls.append(f"{ep_name}${ep_url}")
            else:
                # 策略B: 沒找到列表，可能直接是一個播放器或 iframe
                source_urls.append(f"立即播放${url}")

            vod["vod_play_from"] = "MovieFFM"
            vod["vod_play_url"] = "#".join(source_urls)

            result["list"] = [vod]
            
        except Exception as e:
            pass
            
        return result

    def searchContent(self, key, quick):
        result = {}
        url = 'https://www.movieffm.net/?s={}'.format(key)
        
        try:
            r = requests.get(url, headers=self.getHeaders(), timeout=10)
            r.encoding = 'utf-8'
            soup = BeautifulSoup(r.text, 'html.parser')
            
            videos = self.parse_items(soup)
            result['list'] = videos
            
        except Exception as e:
            pass
            
        return result

    def playerContent(self, flag, id, vipFlags):
        result = {}
        # 開啟嗅探模式
        result["parse"] = 1 
        result["playUrl"] = "" 
        result["url"] = id 
        result["header"] = self.getHeaders()
        return result

    def localProxy(self, param):
        return [200, "video/MP2T", action, ""]
