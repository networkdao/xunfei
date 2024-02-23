import json
import base64
import hashlib
import hmac
import requests
from datetime import datetime
from time import mktime
from urllib.parse import urlencode
from PyPDF2 import PdfReader
import time
import re
from email.utils import format_datetime
from datetime import datetime, timezone
from wsgiref.handlers import format_date_time

APPId = "yourid"
APISecret = "your secret"
APIKey = "your key"

# 术语资源唯一标识，请根据控制台定义的RES_ID替换具体值，如不需术语可以不用传递此参数
RES_ID = "its_en_cn_word"

class AssembleHeaderException(Exception):
    def __init__(self, msg):
        self.message = msg

class Url:
    def __init__(self, host, path, schema):
        self.host = host
        self.path = path
        self.schema = schema

# calculate sha256 and encode to base64
def sha256base64(data):
    sha256 = hashlib.sha256()
    sha256.update(data)
    digest = base64.b64encode(sha256.digest()).decode(encoding='utf-8')
    return digest

def parse_url(request_url):
    stidx = request_url.index("://")
    host = request_url[stidx + 3:]
    schema = request_url[:stidx + 3]
    edidx = host.index("/")
    if edidx <= 0:
        raise AssembleHeaderException("invalid request url:" + request_url)
    path = host[edidx:]
    host = host[:edidx]
    u = Url(host, path, schema)
    return u

# build websocket auth request url
def assemble_ws_auth_url(request_url, method="POST", api_key="", api_secret=""):
    u = parse_url(request_url)
    host = u.host
    path = u.path
    now = datetime.now()
    date = format_date_time(mktime(now.timetuple()))
    
    signature_origin = "host: {}\ndate: {}\n{} {} HTTP/1.1".format(host, date, method, path)
    signature_sha = hmac.new(api_secret.encode('utf-8'), signature_origin.encode('utf-8'),
                             digestmod=hashlib.sha256).digest()
    signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')
    authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
        api_key, "hmac-sha256", "host date request-line", signature_sha)
    authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
    values = {
        "host": host,
        "date": date,
        "authorization": authorization
    }
    return request_url + "?" + urlencode(values)

def translate_text(text):
    url = 'https://itrans.xf-yun.com/v1/its'

    body = {
        "header": {
            "app_id": APPId,
            "status": 3,
            "res_id": RES_ID
        },
        "parameter": {
            "its": {
                "from": "en",
                "to": "cn",
                "result": {}
            }
        },
        "payload": {
            "input_data": {
                "encoding": "utf8",
                "status": 3,
                "text": base64.b64encode(text.encode("utf-8")).decode('utf-8')
            }
        }
    }

    request_url = assemble_ws_auth_url(url, "POST", APIKey, APISecret)
    headers = {'content-type': "application/json", 'host': 'itrans.xf-yun.com', 'app_id': APPId}
    response = requests.post(request_url, data=json.dumps(body), headers=headers)
    tempResult = json.loads(response.content.decode())
    translated_text = json.loads(base64.b64decode(tempResult['payload']['result']['text']).decode())['trans_result']['dst']
    return translated_text


# 定义一个函数，将文本分割成指定大小的块
def split_text_into_chunks(text, chunk_size=4500):
    # 初始化一个空列表，用于存储文本块
    chunks = []
    # 初始化起始位置
    start = 0
    # 当起始位置小于文本长度时，继续循环
    while start < len(text):
        # 计算结束位置
        end = start + chunk_size
        # 如果结束位置大于或等于文本长度
        if end >= len(text):
            # 将剩余的文本添加到块列表中，并结束循环
            chunks.append(text[start:])
            break
        else:
            # 在 [start, end] 范围内向前查找英文句号 . 的位置
            last_period = text.rfind('.', start, end)
            # 如果找到了句号
            if last_period != -1:
                # 将句号及其之前的文本切割出来并添加到块列表中
                chunks.append(text[start:last_period + 1])
                # 更新起始位置为句号之后的位置
                start = last_period + 1
            else:
                # 如果在 [start, end] 范围内没有找到英文句号 .，则直接切割到 end 处
                chunks.append(text[start:end])
                # 更新起始位置为 end
                start = end
    # 返回包含所有文本块的列表
    return chunks

# 读取PDF文件
pdf_path = "your source pdf file path x.pdf"
output_text_file = "destionation file y.txt"

with open(pdf_path, "rb") as file:
    pdf_reader = PdfReader(file)
    total_text = ""
    for page in pdf_reader.pages:
        total_text += page.extract_text()

    translated_text = ""
    for chunk in split_text_into_chunks(total_text):
        translated_chunk = translate_text(chunk)
        translated_text += translated_chunk + "\n"

# 将翻译后的文本写入新文件
with open(output_text_file, "w", encoding="utf-8") as output_file:
    output_file.write(translated_text)

print("翻译完成，并已生成新文件:", output_text_file)
