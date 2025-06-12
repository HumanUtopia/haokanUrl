import base64
from xmlrpc.client import boolean

import httpx
import re
import json
import logging
import argparse


def main():
    parser = argparse.ArgumentParser(description='Get Baidu Haokan video direct links.')
    parser.add_argument('url', nargs='?', type=str, default='https://haokan.baidu.com/v?vid=12009615128559063161',
                        help='The URL of the Baidu Haokan video (positional).')
    parser.add_argument('-u', '-url', '--url', dest='url_option', type=str,
                        help='The URL of the Baidu Haokan video (optional argument).')
    parser.add_argument('-c', '-cookie','--cookie', type=str, default='BDUSS=1145141919810;',
                        help='The BDUSS cookie.')
    parser.add_argument('-d', '--debug', action='store_true',
                        help='Enable debug mode.')
    args = parser.parse_args()

    url = args.url_option if args.url_option else args.url
    cookie_string = args.cookie
    debug = args.debug
    if debug:
        logging.basicConfig(level=logging.DEBUG)
        logging.debug("Debug mode enabled")
    else:
        logging.basicConfig(level=logging.ERROR)

    logging.info(f'Using URL: {url}')
    logging.info(f'Using cookie_string: {cookie_string}')

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36",
    }

    #垃圾百度不给Cookie不给返回视频信息
    cookies = None
    if cookie_string:
        cookies = dict(cookie.split("=", 1) for cookie in cookie_string.split("; ") if "=" in cookie)

    with httpx.Client(http2=True, headers=headers, cookies=cookies, timeout=10.0) as client:
        resp = client.get(url)
        html = resp.text

    if resp.status_code != 200:
        logging.error(f"status code not 200: {resp.status_code}, exiting")
        exit(1)

    match = re.search(r'"encrptedVideoMeta"\s*:\s*"([^"]+)"', html)

    if not match:
        logging.error(f"未找到 encrptedVideoMeta 可能是视频不存在。")
        exit(1)

    try:
        meta = match.group(1)
    except Exception as e:
        logging.error(f"Failed to extract meta from match: {e}")
        raise

    def xor_cipher(meta: str, t: str) -> str:
        result = ""
        for i in range(len(meta)):
            o = ord(meta[i])
            s = ord(t[i % len(t)])
            result += chr(o ^ s)
        return result

    try:
        meta = base64.b64decode(meta).decode()
        logging.info("Base64 decode success")
    except Exception as e:
        logging.error(f"Base64 decode failed: {e}")
        raise

    try:
        meta = xor_cipher(meta, "guanghui456")
        logging.info("XOR cipher success")
    except Exception as e:
        logging.error(f"XOR cipher failed: {e}")
        raise

    try:
        meta = json.loads(meta)
        logging.info("JSON loads success")
        #print(meta['clarityUrl'])
    except Exception as e:
        logging.error(f"JSON loads failed: {e}")
        raise
    clarity_list = meta['clarityUrl']
    new_urls = {}
    for clarity in clarity_list:
        url = clarity['url']
        video_hw = clarity.get('vodVideoHW', '')
        if video_hw and '$$' in video_hw:
            resolution = video_hw.split('$$')[0] + 'p'
        else:
            resolution = clarity.get('key', '')

        # 匹配路径，如果路径第二段是字母（hd/sc/sd/1080p），则用它，否则用分辨率
        m = re.search(r"https://[^/]+/([^/]+)/([^/]+)/([^/]+)/(\d+)/([^/]+)\.mp4", url)
        if m:
            fileid1 = m.group(1)
            dir2 = m.group(2) # 可能是hd/sc/1080p，也可能是360p/576p...
            h264 = m.group(3)
            seg_id = m.group(4)
            fileid2 = m.group(5)

            # 判断目录名
            # 如果 dir2 是数字开头（如'576p'），就用它，否则用 dir2（如hd/sc/1080p）
            if re.match(r'\d+p', dir2):
                dir_name = dir2
            else:
                # 第一种格式，目录名用hd/sc/1080p
                dir_name = dir2

            new_url = f"https://vd3.bdstatic.com/{fileid1}/{dir_name}/{h264}/{seg_id}/{fileid2}.mp4"
            new_urls[resolution] = new_url

    print(new_urls)
if __name__ == "__main__":
    main()