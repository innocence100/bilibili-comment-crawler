import re
import requests
import json

import hashlib
import urllib
import time
import random
import gzip
import os


class JSON_WRITER():
    def __init__(self,f):
        self.f = open(f,'w',encoding='utf-8')
    def writerow(self,data):
        assert isinstance(data,(dict,list))
        json.dump(data,self.f,ensure_ascii=False)
        self.f.write("\n")
    def __enter__(self):
        return self
    def __exit__(self,*args,**kwargs):
        self.f.close()

# 获取B站的Header
def get_Header():
    with open('bili_cookie.txt','r',encoding="utf8") as f:
            cookie=f.read()
    header={
            "Cookie":cookie,
            "User-Agent":'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Safari/537.36 Edg/134.0.0.0'
    }
    return header

# 通过bv号，获取视频的oid
def get_information(bv):
    print(f"https://www.bilibili.com/video/{bv}/?p=14&spm_id_from=pageDriver&vd_source=cd6ee6b033cd2da64359bad72619ca8a")
    resp = requests.get(f"https://www.bilibili.com/video/{bv}/?p=14&spm_id_from=pageDriver&vd_source=cd6ee6b033cd2da64359bad72619ca8a",headers=get_Header())
    # 提取视频oid
    obj = re.compile(f'"aid":(?P<id>.*?),"bvid":"{bv}"')
    oid = obj.search(resp.text).group('id')

    # 提取视频的标题
    obj = re.compile(r'<title data-vue-meta="true">(?P<title>.*?)</title>')
    try:
        title = obj.search(resp.text).group('title')
    except:
        title = "未识别"

    return oid,title

# MD5加密
def md5(code):
    MD5 = hashlib.md5()
    MD5.update(code.encode('utf-8'))
    w_rid = MD5.hexdigest()
    return w_rid

# 下载图片
def download_imgs(reply,dir_name='.'):
    pics = reply.get("content", {}).get("pictures", [])
    if pics:
        for pic in pics:
            url = pic["img_src"]
            filename = url.split("/")[-1]
            print(f"下载 {reply['rpid']} 的图片 {filename}")
            try:
                response = requests.get(url,headers=get_Header())
                assert response
                open(os.path.join(dir_name,filename),"wb").write(response.content)
            except:
                print(f"{url} error")
                open(os.path.join(dir_name,filename+".failed"),"w").write(url)
    time.sleep(0.5)

# 轮页爬取
def start(bv, oid, pageID, count, csv_writer, is_second):
    # 参数
    mode = 2   # 为2时爬取的是最新评论，为3时爬取的是热门评论
    plat = 1
    type = 1  
    web_location = 1315875

    # 获取当下时间戳
    wts = int(time.time())
    
    # 如果不是第一页
    if pageID != '':
        pagination_str = '{"offset":"%s"}' % pageID
        code = f"mode={mode}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&type={type}&web_location={web_location}&wts={wts}" + 'ea1db124af3c7062474693fa704f4ff8'
        w_rid = md5(code)
        url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&web_location=1315875&w_rid={w_rid}&wts={wts}"
    
    # 如果是第一页
    else:
        pagination_str = '{"offset":""}'
        code = f"mode={mode}&oid={oid}&pagination_str={urllib.parse.quote(pagination_str)}&plat={plat}&seek_rpid=&type={type}&web_location={web_location}&wts={wts}" + 'ea1db124af3c7062474693fa704f4ff8'
        w_rid = md5(code)
        url = f"https://api.bilibili.com/x/v2/reply/wbi/main?oid={oid}&type={type}&mode={mode}&pagination_str={urllib.parse.quote(pagination_str, safe=':')}&plat=1&seek_rpid=&web_location=1315875&w_rid={w_rid}&wts={wts}"
    

    comment = requests.get(url=url, headers=get_Header()).content.decode('utf-8')
    comment = json.loads(comment)

    for reply in comment['data']['replies']:
        # 评论数量+1
        count += 1
        
        # 评论ID
        rpid = reply["rpid"]
        
        if count % 1000 ==0:
            time.sleep(20)

        # 相关回复数
        try:
            rereply = reply["reply_control"]["sub_reply_entry_text"]
            rereply = int(re.findall(r'\d+', rereply)[0])
        except:
            rereply = 0

        # 写入JSON文件
        json_writer.writerow(reply)

        # 二级评论(如果开启了二级评论爬取，且该评论回复数不为0，则爬取该评论的二级评论)
        if is_second and rereply !=0:
            for page in range(1,rereply//10+2):
                second_url=f"https://api.bilibili.com/x/v2/reply/reply?oid={oid}&type=1&root={rpid}&ps=10&pn={page}&web_location=333.788"
                second_comment=requests.get(url=second_url,headers=get_Header()).content.decode('utf-8')
                second_comment=json.loads(second_comment)
                for second in second_comment['data']['replies']:
                    # 评论数量+1
                    count += 1
                    # 相关回复数
                    try:
                        rereply = second["reply_control"]["sub_reply_entry_text"]
                        rereply = re.findall(r'\d+', rereply)[0]
                    except:
                        rereply = 0

                    # 写入JSON文件
                    json_writer.writerow(second)
            


    # 下一页的pageID
    try:
        next_pageID = comment['data']['cursor']['pagination_reply']['next_offset']
    except:
        next_pageID = 0

    # 判断是否是最后一页了
    if next_pageID == 0:
        print(f"评论爬取完成！总共爬取{count}条。")
        return bv, oid, next_pageID, count, csv_writer,is_second
    # 如果不是最后一页，则停0.5s（避免反爬机制）
    else:
        time.sleep(random.randint(500,1000)/1000)
        print(f"当前爬取{count}条。")
        return bv, oid, next_pageID, count, csv_writer,is_second

if __name__ == "__main__":

    import sys

    url = sys.argv[1]

    # 获取视频bv
    bv = re.search("/BV[^/?]*",url).group()[1:]
    print(bv)

    # 获取视频oid和标题
    oid,title = get_information(bv)
    # 评论起始页（默认为空）
    next_pageID = ''
    # 初始化评论数量
    count = 0


    # 是否开启二级评论爬取，默认开启
    is_second = True

    # 创建文件夹
    dir_name = f'{bv}_{int(time.time())}'
    assert not os.path.exists(dir_name)
    os.mkdir(dir_name)

    # 创建CSV文件并写入表头
    with JSON_WRITER(f'{dir_name}/{bv}_评论.jsonl') as json_writer:

        # 开始爬取
        while next_pageID != 0:
            bv, oid, next_pageID, count, csv_writer,is_second=start(bv, oid, next_pageID, count, json_writer,is_second)

    with open(f'{dir_name}/{bv}_评论.jsonl',encoding="utf8") as f:
        for line in f:
            j = json.loads(line)
            download_imgs(j,dir_name=dir_name)
