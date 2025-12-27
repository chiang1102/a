import base64
import ctypes
import os
import random
import struct
import time
import uuid
import requests
from construct import Struct, Int16ub, Int32ub, Bytes, this
from fastapi import FastAPI
from fastapi.responses import RedirectResponse, JSONResponse
import uvicorn
int16_str_struct = Struct(
    "length" / Int16ub,
    "value" / Bytes(this.length)
)
signature_uid_struct = Struct(
    "signature" / int16_str_struct,
    "uid" / int16_str_struct
)
int32_str_struct =Struct(
    "length" / Int32ub,
    "value" / Bytes(this.length)
)

ckey_struct = Struct(
    "header" / Bytes(12),
    "Platform" / Bytes(4),
    "signature" / Bytes(4),
    "Timestamp" / Bytes(4),
    "Sdtfrom" / int16_str_struct,
    "randFlag" / int16_str_struct,
    "appVer" / int16_str_struct,
    "vid" / int16_str_struct,
    "guid" / int16_str_struct,
    "part1" / Int32ub,
    "isDlna" / Int32ub,
    "uid" / int16_str_struct,
    "bundleID" / int16_str_struct,
    "uuid4" / int16_str_struct,
    "bundleID1"/ int16_str_struct,
    "ckeyVersion" / int16_str_struct,
    "packageName" / int16_str_struct,
    "platform_str" / int16_str_struct,
    "ex_json_bus"/ int16_str_struct,
    "ex_json_vs" / int16_str_struct,
    "ck_guard_time" / int16_str_struct
)
ckey42_struct =Struct(
    "length" / Int16ub,
    "value" / Bytes(this.length)
)
DELTA = 0x9e3779b9
ROUNDS = 16
LOG_ROUNDS = 4
SALT_LEN = 2
ZERO_LEN = 7
TEA_CKEY =bytes.fromhex('59b2f7cf725ef43c34fdd7c123411ed3')
XOR_KEY = [0x84, 0x2E, 0xED, 0x08, 0xF0, 0x66, 0xE6, 0xEA, 0x48, 0xB4, 0xCA, 0xA9, 0x91, 0xED, 0x6F, 0xF3];
STANDARD_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/='
CUSTOM_ALPHABET = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789_-='
class Size_t(object):
    value = 0

    def __init__(self, value):
        self.value = value
def encrypt(key: bytes, sIn: bytes, iLength: int, buffer: bytearray) -> None:
    outlen: Size_t = Size_t(oi_symmetry_encrypt2_len(iLength))

    oi_symmetry_encrypt2(sIn, iLength, key, buffer, outlen)

    while len(buffer) > outlen.value:
        buffer.pop()
def decrypt(key: bytes, sIn: bytes, iLength: int, buffer: bytearray) -> bool:
    outlen: Size_t = Size_t(iLength)

    if not oi_symmetry_decrypt2(sIn, iLength, key, buffer, outlen):
        return False

    while len(buffer) > outlen.value:
        buffer.pop()
    return True
# pOutBuffer、pInBuffer均为8byte, pKey为16byte
def TeaEncryptECB(pInBuf: bytes, pKey: bytes, pOutBuf: bytearray) -> None:
    k = list()
    pOutBuf.clear()
    # plain-text is TCP/IP-endian
    # GetBlockBigEndian(in, y, z)
    y, z = struct.unpack("!II", pInBuf[:8])

    # TCP/IP network byte order (which is big-endian)

    for i in struct.unpack("!IIII", pKey):
        # now key is TCP/IP-endian
        k.append(i)

    sum = 0
    for i in range(ROUNDS):
        sum += DELTA
        sum = ctypes.c_uint32(sum).value
        y += ((z << 4) + k[0]) ^ (z + sum) ^ ((z >> 5) + k[1])
        y = ctypes.c_uint32(y).value
        z += ((y << 4) + k[2]) ^ (y + sum) ^ ((y >> 5) + k[3])
        z = ctypes.c_uint32(z).value

    for i in struct.pack("!II", y, z):
        pOutBuf.append(i)

    # now encrypted buf is TCP/IP-endian
# pOutBuffer、pInBuffer均为8byte, pKey为16byte
def TeaDecryptECB(pInBuf: bytes, pKey: bytes, pOutBuf: bytearray) -> None:
    k = list()
    pOutBuf.clear()
    # now encrypted buf is TCP/IP-endian
    # TCP/IP network byte order (which is big-endian).
    y, z = struct.unpack("!II", pInBuf[:8])

    for i in struct.unpack("!IIII", pKey):
        # key is TCP/IP-endian;
        k.append(i)

    sum = ctypes.c_uint32(DELTA << LOG_ROUNDS).value
    for i in range(ROUNDS):
        z -= ((y << 4) + k[2]) ^ (y + sum) ^ ((y >> 5) + k[3])
        z = ctypes.c_uint32(z).value
        y -= ((z << 4) + k[0]) ^ (z + sum) ^ ((z >> 5) + k[1])
        y = ctypes.c_uint32(y).value
        sum -= DELTA

    for i in struct.pack("!II", y, z):
        pOutBuf.append(i)
    # now plain-text is TCP/IP-endian;
# pKey为16byte
# 输入:nInBufLen为需加密的明文部分(Body)长度
# 输出:返回为加密后的长度(是8byte的倍数)
# TEA加密算法,CBC模式
# 密文格式:PadLen(1byte)+Padding(var,0-7byte)+Salt(2byte)+Body(var byte)+Zero(7byte)
def oi_symmetry_encrypt2_len(nInBufLen: int) -> int:
    # nPadSaltBodyZeroLen  # PadLen(1byte)+Salt+Body+Zero的长度
    # 根据Body长度计算PadLen,最小必需长度必需为8byte的整数倍
    nPadSaltBodyZeroLen = nInBufLen  # /*Body长度*/
    nPadSaltBodyZeroLen += 1 + SALT_LEN + ZERO_LEN  # PadLen(1byte)+Salt(2byte)+Zero(7byte)
    nPadlen = nPadSaltBodyZeroLen % 8
    if nPadlen:  # len=nSaltBodyZeroLen%8
        # 模8余0需补0,余1补7,余2补6,...,余7补1
        nPadlen = 8 - nPadlen
    return nPadSaltBodyZeroLen + nPadlen
# pKey为16byte
# 输入:pInBuf为需加密的明文部分(Body),nInBufLen为pInBuf长度
# 输出:pOutBuf为密文格式,pOutBufLen为pOutBuf的长度是8byte的倍数
# TEA加密算法,CBC模式
# 密文格式:PadLen(1byte)+Padding(var,0-7byte)+Salt(2byte)+Body(var byte)+Zero(7byte)
def oi_symmetry_encrypt2(pInBuf: bytes, nInBufLen: int, pKey: bytes, pOutBuf: bytearray, pOutBufLen: Size_t) -> None:
    # /*PadLen(1byte)+Salt+Body+Zero的长度*/
    # 根据Body长度计算PadLen,最小必需长度必需为8byte的整数倍
    nPadSaltBodyZeroLen = nInBufLen  # Body长度
    nPadSaltBodyZeroLen = nPadSaltBodyZeroLen + 1 + SALT_LEN + ZERO_LEN  # PadLen(1byte)+Salt(2byte)+Zero(7byte)
    nPadlen = nPadSaltBodyZeroLen % 8
    if nPadlen:  # len=nSaltBodyZeroLen%8
        # 模8余0需补0,余1补7,余2补6,...,余7补1
        nPadlen = 8 - nPadlen

    # srand( (unsigned)time( NULL ) ); 初始化随机数
    # 加密第一块数据(8byte),取前面10byte
    src_buf = bytearray([0] * 8)
    src_buf[0] = (random.randint(0, 255) & 0xf8) | nPadlen  # 最低三位存PadLen,清零
    src_i = 1  # src_i指向src_buf下一个位置

    while nPadlen:
        src_buf[src_i] = random.randint(0, 255)  # Padding
        src_i += 1
        nPadlen -= 1

    # come here, src_i must <= 8

    iv_plain = bytearray()
    for i in range(8):
        iv_plain.append(0)

    iv_crypt = bytearray(iv_plain)  # make zero iv

    pOutBufLen.value = 0  # init OutBufLen

    i = 1
    while i <= SALT_LEN:  # Salt(2byte)
        if src_i < 8:
            src_buf[src_i] = random.randint(0, 255)
            src_i += 1
            i += 1  # i inc in here
        if src_i == 8:
            # src_i==8

            for j in range(8):  # 加密前异或前8个byte的密文(iv_crypt指向的)
                src_buf[j] ^= iv_crypt[j]

            # pOutBuffer、pInBuffer均为8byte, pKey为16byte
            # 加密
            temp_pOutBuf = bytearray()
            TeaEncryptECB(src_buf, pKey, temp_pOutBuf)

            for j in range(8):  # 加密后异或前8个byte的明文(iv_plain指向的)
                temp_pOutBuf[j] ^= iv_plain[j]

            # 保存当前的iv_plain
            for j in range(8):
                iv_plain[j] = src_buf[j]

            # 更新iv_crypt
            src_i = 0
            iv_crypt = bytearray(temp_pOutBuf)
            pOutBufLen.value += 8
            pOutBuf += temp_pOutBuf

    # src_i指向src_buf下一个位置
    pInBufIndex = 0
    while nInBufLen:
        if src_i < 8:
            src_buf[src_i] = pInBuf[pInBufIndex]
            pInBufIndex += 1
            src_i += 1
            nInBufLen -= 1
        if src_i == 8:
            # src_i==8
            for j in range(8):  # 加密前异或前8个byte的密文(iv_crypt指向的)
                src_buf[j] ^= iv_crypt[j]
            # pOutBuffer、pInBuffer均为8byte, pKey为16byte
            temp_pOutBuf = bytearray()
            TeaEncryptECB(src_buf, pKey, temp_pOutBuf)

            for j in range(8):  # 加密后异或前8个byte的明文(iv_plain指向的)
                temp_pOutBuf[j] ^= iv_plain[j]

            # 保存当前的iv_plain
            for j in range(8):
                iv_plain[j] = src_buf[j]

            src_i = 0
            iv_crypt = bytearray(temp_pOutBuf)
            pOutBufLen.value += 8
            pOutBuf += temp_pOutBuf

    # src_i指向src_buf下一个位置
    i = 1
    while i <= ZERO_LEN:
        if src_i < 8:
            src_buf[src_i] = 0
            src_i += 1
            i += 1  # i inc in here
        if src_i == 8:
            # src_i==8

            for j in range(8):  # 加密前异或前8个byte的密文(iv_crypt指向的)
                src_buf[j] ^= iv_crypt[j]

            # pOutBuffer、pInBuffer均为8byte, pKey为16byte
            temp_pOutBuf = bytearray()
            TeaEncryptECB(src_buf, pKey, temp_pOutBuf)

            for j in range(8):  # 加密后异或前8个byte的明文(iv_plain指向的)
                temp_pOutBuf[j] ^= iv_plain[j]

            # 保存当前的iv_plain
            for j in range(8):
                iv_plain[j] = src_buf[j]

            src_i = 0
            iv_crypt = temp_pOutBuf
            pOutBufLen.value += 8
            pOutBuf += temp_pOutBuf
# pKey为16byte
# 输入: pInBuf为密文格式, nInBufLen为pInBuf的长度是8byte的倍数;
# *pOutBufLen为接收缓冲区的长度
# 特别注意 * pOutBufLen应预置接收缓冲区的长度!
# 输出: pOutBuf为明文(Body), pOutBufLen为pOutBuf的长度, 至少应预留nInBufLen - 10;
# 返回值: 如果格式正确返回true;
# TEA解密算法, CBC模式
# 密文格式: PadLen(1byte)+Padding(var, 0 - 7byte)+Salt(2byte)+Body(varbyte)+Zero(7byte)
def oi_symmetry_decrypt2(pInBuf: bytes, nInBufLen: int, pKey: bytes, pOutBuf: bytearray, pOutBufLen: Size_t) -> bool:
    dest_buf = bytearray()
    zero_buf = bytearray()

    # const char * pInBufBoundary;
    nBufPos = 0

    if (nInBufLen % 8) or (nInBufLen < 16):
        return False

    TeaDecryptECB(pInBuf, pKey, dest_buf)

    nPadLen = dest_buf[0] & 0x7  # 只要最低三位

    # 密文格式: PadLen(1byte)+Padding(var, 0-7byte)+Salt(2byte)+Body(var byte)+Zero(7byte)
    i = nInBufLen - 1  # PadLen(1byte)
    i = i - nPadLen - SALT_LEN - ZERO_LEN  # 明文长度

    if (pOutBufLen.value < i) or (i < 0):
        return False

    pOutBufLen.value = i

    # pInBufBoundary = pInBuf + nInBufLen; 输入缓冲区的边界，下面不能pInBuf >= pInBufBoundary

    for i in range(8):
        zero_buf.append(0)

    iv_pre_crypt = bytearray(zero_buf)
    iv_cur_crypt = bytearray(pInBuf)  # init iv

    pInBuf = pInBuf[8:]
    nBufPos += 8
    dest_i = 1  # dest_i指向dest_buf下一个位置

    # 把Padding滤掉
    dest_i += nPadLen

    # dest_i must <= 8

    # 把Salt滤掉
    i = 1
    while i <= SALT_LEN:
        if dest_i < 8:
            dest_i += 1
            i += 1
        elif dest_i == 8:
            # 解开一个新的加密块
            # 改变前一个加密块的指针
            iv_pre_crypt = bytearray(iv_cur_crypt)
            iv_cur_crypt = bytearray(pInBuf)

            # 异或前一块明文(在dest_buf[]中)
            for j in range(8):
                if nBufPos + j >= nInBufLen:
                    return False
                dest_buf[j] ^= pInBuf[j]

            # dest_i == 8
            TeaDecryptECB(bytes(dest_buf), pKey, dest_buf)

            # 在取出的时候才异或前一块密文(iv_pre_crypt)

            pInBuf = pInBuf[8:]
            nBufPos += 8
            dest_i = 0  # dest_i指向dest_buf下一个位置

    # 还原明文
    nPlainLen = pOutBufLen.value
    while nPlainLen:
        if dest_i < 8:
            pOutBuf.append(dest_buf[dest_i] ^ iv_pre_crypt[dest_i])
            dest_i += 1
            nPlainLen -= 1
        elif dest_i == 8:
            # dest_i == 8
            # 改变前一个加密块的指针
            iv_pre_crypt = bytearray(iv_cur_crypt)
            iv_cur_crypt = bytearray(pInBuf)

            # 解开一个新的加密块
            # 异或前一块明文(在dest_buf[]中)
            for j in range(8):
                if nBufPos + j >= nInBufLen:
                    return False
                dest_buf[j] ^= pInBuf[j]
            TeaDecryptECB(bytes(dest_buf), pKey, dest_buf)
            # 在取出的时候才异或前一块密文(iv_pre_crypt)
            pInBuf = pInBuf[8:]
            nBufPos += 8
            dest_i = 0  # dest_i指向dest_buf下一个位置

    # 校验Zero
    i = 1
    while i <= ZERO_LEN:
        if dest_i < 8:
            if dest_buf[dest_i] ^ iv_pre_crypt[dest_i]:
                return False
            dest_i += 1
            i += 1
        elif dest_i == 8:
            # 改变前一个加密块的指针
            iv_pre_crypt = bytearray(iv_cur_crypt)
            iv_cur_crypt = bytearray(pInBuf)

            # 解开一个新的加密块
            # 异或前一块明文(在dest_buf[]中)
            for j in range(8):
                if nBufPos + j >= nInBufLen:
                    return False
                dest_buf[j] ^= pInBuf[j]

            TeaDecryptECB(bytes(dest_buf), pKey, dest_buf)

            # 在取出的时候才异或前一块密文(iv_pre_crypt)
            pInBuf += 8
            nBufPos += 8
            dest_i = 0  # dest_i指向dest_buf下一个位置
    return True
def tc_tea_encrypt(keys: bytes, message: bytes) -> bytes:
    data = bytearray()
    encrypt(keys, message, len(message), data)
    return bytes(data)
def tc_tea_decrypt(keys: bytes, message: bytes) -> bytes:
    data = bytearray()
    if decrypt(keys, message, len(message), data):
        return bytes(data)
    else:
        raise Exception('解密失败')
def CalcSignature(decArray):
    signature = 0
    for byte in decArray:
        signature = (0x83 * signature + byte)
    return signature& 0x7FFFFFFF
def RandomHexStr(length):
    return ''.join(random.choice('0123456789ABCDEF') for _ in range(length))
def XOR_Array(byteArray):
    retArray = bytearray(byteArray)
    for i in range(len(retArray)):
        retArray[i] ^= XOR_KEY[i & 0xF]
    return retArray
def custom_encode(text):
    encoded_data = base64.b64encode(text)
    encoded_str = encoded_data.decode('utf-8')
    translated_str = encoded_str.translate(str.maketrans(STANDARD_ALPHABET, CUSTOM_ALPHABET))
    return translated_str
def custom_decode(text):
    text =text if len(text) % 4 == 0 else text + '=' * (4 - len(text) % 4)
    data = base64.b64decode(text.translate(str.maketrans(CUSTOM_ALPHABET, STANDARD_ALPHABET)))
    return data
def create_str_data(value):
    #如果是数字
    if value is None:
        value = ""
    if isinstance(value, int):
        value = str(value)
    return {"length": len(value), "value": value.encode('utf-8')}


def ckey42(Platform, Timestamp, Sdtfrom = "fcgo",vid="600002264", guid=None, appVer="V8.22.1035.3031"):
    header = b'\x00\x00\x00\x42\x00\x00\x00\x04\x00\x00\x04\xd2'
    data = {
        "header": header,
        "Platform": int(Platform).to_bytes(4, 'big'),
        "signature": b'\x00\x00\x00\x00',
        "Timestamp": Timestamp.to_bytes(4, 'big'),
        "Sdtfrom": create_str_data(Sdtfrom),
        "randFlag": create_str_data(
            base64.b64encode(os.urandom(18)).decode()
        ),
        "appVer": create_str_data(appVer),
        "vid": create_str_data(vid),
        "guid": create_str_data(guid),
        "part1": 1,
        "isDlna": 1,
        "uid": create_str_data("2622783A"),
        "bundleID": create_str_data("nil"),
        "uuid4": create_str_data(str(uuid.uuid4())),
        "bundleID1": create_str_data("nil"),
        "ckeyVersion": create_str_data("v0.1.000"),
        "packageName": create_str_data("com.cctv.yangshipin.app.iphone"),
        "platform_str": create_str_data(str(Platform)),
        "ex_json_bus": create_str_data("ex_json_bus"),
        "ex_json_vs": create_str_data("ex_json_vs"),
        "ck_guard_time": create_str_data(RandomHexStr(66)),
    }
    Buffer = ckey_struct.build(data)
    BufferLenHex = hex(len(Buffer))[2:].zfill(4)
    BufferHead = [int(BufferLenHex[i:i+2], 16) for i in range(0, len(BufferLenHex), 2)]
    Buffer = BufferHead + list(Buffer)
    encrypt_data = tc_tea_encrypt(TEA_CKEY, bytes(Buffer))
    encrypt_data=bytearray(encrypt_data)
    CheckSum=CalcSignature(Buffer)
    CheckSumBytes = struct.pack('>I', CheckSum)
    encrypt_data.extend(CheckSumBytes)
    result = XOR_Array(encrypt_data)
    return "--01"+custom_encode(result).replace('=','')
app=FastAPI()
@app.get("/ysp")
def ysp(cnlid: str, livepid: str, defn: str = "auto"):
    try:
        url = "https://liveinfo.ysp.cctv.cn"
        params ={
            "atime":"120",
            "livepid":  livepid,
            "cnlid":  cnlid,
            "appVer": "V8.22.1035.3031",
            "app_version": "300090",
            "caplv": "1",
            "cmd": "2",
            "defn":  defn,
            "device": "iPhone",
            "encryptVer": "4.2",
            "getpreviewinfo": "0",
            "hevclv": "33",
            "lang": "zh-Hans_JP",
            "livequeue": "0",
            "logintype": "1",
            "nettype": "1",
            "newnettype": "1",
            "newplatform": "4330403",
            "platform": "4330403",
            "playbacktime": "0",
            "sdtfrom": "v3021",
            "spacode": "23",
            "spaudio": "1",
            "spdemuxer": "6",
            "spdrm": "2",
            "spdynamicrange": "7",
            "spflv": "1",
            "spflvaudio": "1",
            "sphdrfps": "60",
            "sphttps": "0",
            "spvcode": "MSgzMDoyMTYwLDYwOjIxNjB8MzA6MjE2MCw2MDoyMTYwKTsyKDMwOjIxNjAsNjA6MjE2MHwzMDoyMTYwLDYwOjIxNjAp",
            "spvideo": "4",
            "stream": "1",
            "system": "1",
            "sysver": "ios18.2.1",
            "uhd_flag": "4",
        }
        headers = {
            'User-Agent': "qqlive",
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip"
        }
        Platform = params['platform']
        Timestamp = int(time.time())
        appVer = params['appVer']
        Cnlid = params['cnlid']
        StaGuid = RandomHexStr(32)
        sdtfrom = 'dcgh'
        ckey=ckey42(Platform, Timestamp, sdtfrom, Cnlid, StaGuid, appVer)
        params.update({"cKey":ckey})
        data = requests.get(url,params=params,headers=headers).json()
        if defn=="auto":
            formats=data['formats']
            return  JSONResponse(content={"formats": formats})
        url=data['playurl']
        return RedirectResponse(url=url)
    except Exception as e:
        return {"error": str(e)}

if __name__ == '__main__':
    uvicorn.run(app, host="0.0.0.0", port=8080)

    
    
    

    