#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import uuid
import base64
import hashlib
import requests
import json
from datetime import datetime
from Crypto.Cipher import AES
from flask import Flask, request, redirect, Response
from urllib.parse import urlparse, parse_qs
import os

app = Flask(__name__)

# ID到fsASSET_ID的映射
ID_TO_FS_ASSET_ID = {
    '1': '4gtv-4gtv003',
    '2': '4gtv-4gtv001',
    '3': '4gtv-4gtv002',
    '4': '4gtv-4gtv040',
    '6': '4gtv-4gtv041',
    '7': '4gtv-4gtv042',
    '8': 'litv-ftv17',
    '9': 'litv-ftv16',
    '11': '4gtv-4gtv018',
    '15': '4gtv-4gtv044',
    '16': '4gtv-4gtv004',
    '19': '4gtv-4gtv070',
    '21': '4gtv-4gtv046',
    '22': '4gtv-4gtv047',
    '23': 'litv-longturn18',
    '24': 'litv-ftv09',
    '25': '4gtv-4gtv049',
    '28': 'litv-longturn11',
    '30': '4gtv-4gtv009',
    '31': 'litv-ftv13',
    '33': '4gtv-4gtv074',
    '34': '4gtv-4gtv052',
    '36': 'litv-longturn14',
    '38': '4gtv-4gtv013',
    '39': '4gtv-4gtv017',
    '40': '4gtv-4gtv011',
    '42': '4gtv-4gtv055',
    '48': 'litv-longturn05',
    '50': 'litv-longturn07',
    '51': 'litv-longturn10',
    '52': 'litv-longturn09',
    '57': '4gtv-4gtv077',
    '58': '4gtv-4gtv101',
    '59': '4gtv-4gtv057',
    '60': 'litv-ftv15',
    '61': 'litv-ftv07',
    '69': '4gtv-4gtv014',
    '78': '4gtv-4gtv082',
    '79': '4gtv-4gtv083',
    '80': '4gtv-4gtv059',
    '82': '4gtv-4gtv061',
    '83': '4gtv-4gtv062',
    '84': '4gtv-4gtv063',
    '85': 'litv-ftv10',
    '86': 'litv-ftv03',
    '88': '4gtv-4gtv065',
    '93': '4gtv-4gtv035',
    '94': '4gtv-4gtv038',
    '106': 'litv-longturn20',
    '107': '4gtv-4gtv043',
    '113': '4gtv-4gtv006',
    '114': '4gtv-4gtv039',
    '116': '4gtv-4gtv058',
    '118': '4gtv-4gtv045',
    '119': '4gtv-4gtv054',
    '121': 'litv-longturn03',
    '123': '4gtv-4gtv064',
    '124': '4gtv-4gtv080',
    '139': '4gtv-live208',
    '160': '4gtv-live201',
    '168': '4gtv-live206',
    '169': '4gtv-live207',
    '170': '4gtv-4gtv084',
    '171': '4gtv-4gtv085',
    '172': '4gtv-4gtv034',
    '173': '4gtv-live047',
    '174': '4gtv-live046',
    '175': '4gtv-live121',
    '176': '4gtv-live157',
    '178': '4gtv-live122',
    '179': '4gtv-4gtv053',
    '180': '4gtv-live138',
    '181': '4gtv-live109',
    '182': '4gtv-live110',
    '183': '4gtv-4gtv073',
    '184': '4gtv-4gtv068',
    '185': '4gtv-live105',
    '186': '4gtv-live620',
    '188': '4gtv-live030',
    '189': '4gtv-4gtv079',
    '201': '4gtv-live021',
    '202': '4gtv-live022',
    '204': '4gtv-live024',
    '209': '4gtv-live007',
    '210': '4gtv-live008',
    '212': '4gtv-live023',
    '213': '4gtv-live025',
    '214': '4gtv-live026',
    '215': '4gtv-live027',
    '217': '4gtv-live029',
    '218': '4gtv-live031',
    '219': '4gtv-live032',
    '223': '4gtv-live050',
    '224': '4gtv-live060',
    '225': '4gtv-live069',
    '226': '4gtv-live071',
    '227': '4gtv-4gtv067',
    '229': '4gtv-live089',
    '230': '4gtv-live106',
    '231': '4gtv-live107',
    '235': '4gtv-live130',
    '236': '4gtv-live144',
    '237': '4gtv-live120',
    '244': '4gtv-live006',
    '245': '4gtv-live005',
    '246': '4gtv-live215',
    '249': '4gtv-live012',
    '250': 'litv-longturn17',
    '252': '4gtv-live112',
    '254': '4gtv-live403',
    '255': '4gtv-live401',
    '256': '4gtv-live452',
    '257': '4gtv-live413',
    '258': '4gtv-live474',
    '260': '4gtv-live409',
    '261': '4gtv-live417',
    '262': '4gtv-live408',
    '264': '4gtv-live405',
    '265': '4gtv-live404',
    '266': '4gtv-live407',
    '267': '4gtv-live406',
    '268': '4gtv-4gtv075',
    '269': '4gtv-live009',
    '270': '4gtv-live010',
    '273': '4gtv-live014',
    '274': '4gtv-live011',
    '275': '4gtv-live080',
    '276': '4gtv-live410',
    '277': '4gtv-live411',
    '278': '4gtv-live015',
    '279': '4gtv-live016',
    '280': 'litv-longturn15',
    '281': 'litv-longturn23',
    '282': '4gtv-live017',
    '283': '4gtv-live059',
    '284': '4gtv-live087',
    '285': '4gtv-live088',
    '286': '4gtv-live049',
    '287': '4gtv-live048',
    '288': '4gtv-4gtv016',
    '289': '4gtv-live301',
    '290': '4gtv-live302',
    '291': '4gtv-4gtv072',
    '292': '4gtv-4gtv152',
    '293': '4gtv-4gtv153',
}


def generate_uuid():
    """生成UUID"""
    return str(uuid.uuid4()).upper()


def generate_4gtv_auth():
    """生成4GTV认证令牌"""
    head_key = "PyPJU25iI2IQCMWq7kblwh9sGCypqsxMp4sKjJo95SK43h08ff+j1nbWliTySSB+N67BnXrYv9DfwK+ue5wWkg=="
    KEY = b"ilyB29ZdruuQjC45JhBBR7o2Z8WJ26Vg"
    IV = b"JUMxvVMmszqUTeKn"
    
    try:
        decode = base64.b64decode(head_key)
        format_date = datetime.utcnow().strftime("%Y%m%d")
        
        cipher = AES.new(KEY, AES.MODE_CBC, IV)
        decrypted_raw = cipher.decrypt(decode)
        
        # 手动移除PKCS7填充
        padding_length = decrypted_raw[-1]
        decrypted = decrypted_raw[:-padding_length]
        
        to_hash = format_date + decrypted.decode('utf-8')
        sha512_binary = hashlib.sha512(to_hash.encode()).digest()
        final_result = base64.b64encode(sha512_binary).decode()
        
        print(f"Debug - Date: {format_date}")
        print(f"Debug - 4GTV_AUTH: {final_result[:50]}...")
        
        return final_result
    except Exception as e:
        print(f"Error in generate_4gtv_auth: {e}")
        raise


def get_play_url(url, return_type):
    """获取播放URL"""
    headers = {
        'User-Agent': 'okhttp/3.12.11'
    }
    
    try:
        response = requests.get(url, headers=headers, verify=False)
        if not response.text:
            return None
        
        parsed_url = urlparse(url)
        resp_text = response.text.strip()
        lines = resp_text.split('\n')
        latest_line = lines[-1].strip()
        url_path = os.path.dirname(parsed_url.path)
        new_url = f"{parsed_url.scheme}://{parsed_url.netloc}{url_path}/{latest_line}"
        
        if return_type == 'url':
            return new_url
        
        if '.ts' in latest_line:
            return resp_text
        else:
            return get_play_url(new_url, return_type)
    except Exception as e:
        print(f"Error in get_play_url: {e}")
        return None


@app.route('/')
def index():
    """主路由处理函数"""
    # 获取ID参数，默认为"1"
    channel_id = request.args.get('id', '1')
    
    # 从映射中获取fsASSET_ID
    if channel_id not in ID_TO_FS_ASSET_ID:
        return "Invalid channel ID", 400
    
    fs_asset_id = ID_TO_FS_ASSET_ID[channel_id]
    
    # 生成认证信息
    auth_val = generate_4gtv_auth()
    fs_enc_key = generate_uuid()
    
    # 构建请求
    url = 'https://api2.4gtv.tv/App/GetChannelUrl2'
    
    payload = {
        "fnCHANNEL_ID": channel_id,
        "fsDEVICE_TYPE": "mobile",
        "clsAPP_IDENTITY_VALIDATE_ARUS": {
            "fsVALUE": "",
            "fsENC_KEY": fs_enc_key
        },
        "fsASSET_ID": fs_asset_id
    }
    
    headers = {
        "4GTV_AUTH": auth_val,
        "fsDEVICE": "iOS",
        "fsVALUE": "",
        "fsVERSION": "3.2.1",
        "fsENC_KEY": fs_enc_key,
        "User-Agent": "%E5%9B%9B%E5%AD%A3%E7%B7%9A%E4%B8%8A/1 CFNetwork/1568.200.51 Darwin/24.1.0",
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Host": "api2.4gtv.tv",
        "Connection": "keep-alive"
    }
    
    print(f"\n=== 请求信息 ===")
    print(f"频道ID: {channel_id}")
    print(f"资源ID: {fs_asset_id}")
    print(f"UUID: {fs_enc_key}")
    print(f"Payload: {json.dumps(payload, ensure_ascii=False)}")
    
    # 发送请求
    try:
        response = requests.post(url, json=payload, headers=headers, verify=False)
        
        # 调试信息
        print(f"Response Status Code: {response.status_code}")
        print(f"Response Headers: {response.headers}")
        print(f"Response Text: {response.text[:500]}")  # 打印前500个字符
        
        # 检查响应状态
        if response.status_code != 200:
            return f"API返回错误状态码: {response.status_code}, 内容: {response.text}", 500
        
        # 检查响应内容是否为空
        if not response.text:
            return "API返回空响应", 500
        
        # 尝试解析JSON
        try:
            data = response.json()
        except json.JSONDecodeError as e:
            return f"JSON解析错误: {str(e)}, 响应内容: {response.text}", 500
        
        urls = data.get('Data', {}).get('flstURLs', [])
        
        # 过滤URL
        final_url = ""
        for url_item in urls:
            if 'cds.cdn.hinet.net' not in url_item:
                final_url = url_item
        
        # 处理URL
        if final_url.startswith('https://4gtvfree-mozai.4gtv.tv'):
            final_url = final_url.replace('/index.m3u8?', '/1080.m3u8?')
            return redirect(final_url)
        else:
            final_url = get_play_url(final_url, 'url')
            if not final_url:
                return "Failed to get play URL", 500
                
            m3u8_content = get_play_url(final_url, 'ts')
            if not m3u8_content:
                return "Failed to get M3U8 content", 500
            
            # 解析URL获取频道信息
            pre_array = final_url.split('?')[0].split('/')
            mid_array = pre_array[-1].split('-')
            channel = f"{mid_array[0]}-{mid_array[1]}"
            
            lines = []
            prex = f"https://litvpc-hichannel.cdn.hinet.net/live/pool/{channel}/litv-pc/"
            
            for line in m3u8_content.split('\n'):
                if line.startswith('#EXT') or line.strip() == '':
                    lines.append(line)
                else:
                    ts_file_array = line.split('?')[0].split('/')
                    ts_file = ts_file_array[-1]
                    ts_file = ts_file.replace('video=2000000', 'video=6000000')
                    ts_file = ts_file.replace('video=2936000', 'video=5936000')
                    ts_file = ts_file.replace('video=3000000', 'video=6000000')
                    ts_file = ts_file.replace('avc1_2000000=3', 'avc1_6000000=1')
                    ts_file = ts_file.replace('avc1_2000000=6', 'avc1_6000000=1')
                    ts_file = ts_file.replace('avc1_2936000=4', 'avc1_6000000=5')
                    ts_file = ts_file.replace('avc1_3000000=3', 'avc1_6000000=1')
                    ts_url = prex + ts_file
                    lines.append(ts_url)
            
            m3u8_content = '\n'.join(lines)
            return Response(m3u8_content, mimetype='application/vnd.apple.mpegurl')
            
    except Exception as e:
        return f"Error: {str(e)}", 500


if __name__ == '__main__':
    # 禁用SSL警告
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    
    # 运行Flask应用
    app.run(host='0.0.0.0', port=5000, debug=True)

