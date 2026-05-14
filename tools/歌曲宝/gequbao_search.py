"""
gequbao.com 歌曲搜索与下载工具
使用方法:
    python gequbao_search.py "歌曲名"                    # 搜索歌曲
    python gequbao_search.py "周杰伦" --download          # 搜索并交互选择下载
    python gequbao_search.py "晴天" -d -o ./music         # 下载到指定目录
    python gequbao_search.py "周杰伦" -d --all            # 下载全部搜索结果
    python gequbao_search.py "稻香" --json                # JSON 格式输出
"""

import argparse
import base64
import json
import os
import re
import sys
import time
from urllib.parse import quote, urljoin

try:
    import requests
except ImportError:
    print("请先安装 requests: pip install requests")
    sys.exit(1)

try:
    from bs4 import BeautifulSoup
except ImportError:
    print("请先安装 beautifulsoup4: pip install beautifulsoup4")
    sys.exit(1)

BASE_URL = "https://www.gequbao.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

# 用于 API 请求的 headers
API_HEADERS = {
    "User-Agent": HEADERS["User-Agent"],
    "Accept": "application/json, text/javascript, */*; q=0.01",
    "Accept-Language": "zh-CN,zh;q=0.9",
    "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": BASE_URL,
}

session = requests.Session()
session.headers.update(HEADERS)


def search_songs(keyword: str) -> list[dict]:
    """搜索歌曲，返回结果列表"""
    search_url = f"{BASE_URL}/s/{quote(keyword)}"
    print(f"正在搜索: {keyword}")
    print(f"请求地址: {search_url}")

    try:
        resp = session.get(search_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"搜索请求失败: {e}")
        return []

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    songs = []
    seen_urls = set()

    # 查找所有指向 /music/ 的链接
    for a in soup.find_all("a", href=re.compile(r"^/music/\d+$")):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        # 跳过"播放&下载"等按钮文字
        if not text or any(kw in text for kw in ["播放", "下载", "Play", "Download"]):
            continue

        full_url = urljoin(BASE_URL, href)
        if full_url in seen_urls:
            continue
        seen_urls.add(full_url)

        # 解析歌名和歌手 (格式: "歌名-歌手" 或 "歌名-歌手&嘉宾")
        title = text
        artist = ""
        if "-" in text:
            parts = text.split("-", 1)
            title = parts[0].strip()
            artist = parts[1].strip()

        songs.append({
            "title": title,
            "artist": artist,
            "url": full_url,
            "music_id": href.split("/")[-1],
        })

    return songs


def get_play_url(music_url: str) -> dict | None:
    """访问歌曲详情页，提取 appData 并通过 API 获取播放地址"""
    try:
        resp = session.get(music_url, timeout=15)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  获取详情页失败: {e}")
        return None

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    # 从 window.appData 中提取数据
    app_data = None
    for script in soup.find_all("script"):
        text = script.string or ""
        if "window.appData" in text:
            match = re.search(r"window\.appData\s*=\s*JSON\.parse\('(.+?)'\)", text)
            if match:
                raw = match.group(1)
                try:
                    decoded = raw.encode("utf-8").decode("unicode_escape")
                    app_data = json.loads(decoded)
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    print(f"  解析 appData 失败: {e}")
            break

    if not app_data:
        print("  未找到 appData")
        return None

    result = {
        "music_id": app_data.get("mp3_id"),
        "title": app_data.get("mp3_title", ""),
        "artist": app_data.get("mp3_author", ""),
        "cover": app_data.get("mp3_cover", ""),
        "duration": app_data.get("mp3_duration", ""),
    }

    # 提取网盘链接
    extra_urls = []
    for extra in app_data.get("mp3_extra_urls", []):
        link = extra.get("share_link", "")
        try:
            decoded_link = base64.b64decode(link).decode("utf-8")
            extra_urls.append({
                "type": extra.get("type", ""),
                "url": decoded_link,
            })
        except Exception:
            pass
    result["extra_urls"] = extra_urls

    # 通过 API 获取在线播放地址
    play_id = app_data.get("play_id", "")
    if play_id:
        try:
            api_resp = session.post(
                f"{BASE_URL}/api/play-url",
                data={"id": play_id},
                headers=API_HEADERS,
                timeout=15,
            )
            api_data = api_resp.json()
            if api_data.get("code") == 1:
                result["audio_url"] = api_data["data"].get("url", "")
            else:
                print(f"  API 返回错误: {api_data.get('msg', '未知错误')}")
        except Exception as e:
            print(f"  获取播放地址失败: {e}")

    return result


def download_song(audio_url: str, filename: str, output_dir: str) -> bool:
    """下载音频文件"""
    os.makedirs(output_dir, exist_ok=True)

    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
    ext = os.path.splitext(audio_url.split("?")[0])[1] or ".mp3"
    filepath = os.path.join(output_dir, safe_name + ext)

    if os.path.exists(filepath):
        print(f"  文件已存在，跳过: {filepath}")
        return True

    print(f"  正在下载: {audio_url[:80]}...")

    # CDN 需要对应站点的 Referer
    dl_headers = dict(HEADERS)
    if "kuwo.cn" in audio_url:
        dl_headers["Referer"] = "https://www.kuwo.cn/"
    elif "kugou.com" in audio_url:
        dl_headers["Referer"] = "https://www.kugou.com/"
    elif "qq.com" in audio_url:
        dl_headers["Referer"] = "https://y.qq.com/"

    try:
        resp = session.get(audio_url, headers=dl_headers, timeout=120, stream=True)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"  下载失败: {e}")
        return False

    total = int(resp.headers.get("content-length", 0))
    downloaded = 0

    with open(filepath, "wb") as f:
        for chunk in resp.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total > 0:
                pct = downloaded / total * 100
                mb = downloaded / 1024 / 1024
                total_mb = total / 1024 / 1024
                print(f"\r  进度: {pct:.1f}% ({mb:.1f}/{total_mb:.1f} MB)", end="", flush=True)

    print(f"\n  下载完成: {filepath}")
    return True


def process_song(song: dict, output_dir: str) -> bool:
    """处理单首歌曲：获取详情 + 下载"""
    print(f"\n--- {song['title']} ({song.get('artist', '')}) ---")
    print(f"  详情页: {song['url']}")

    detail = get_play_url(song["url"])
    if not detail:
        print("  获取详情失败")
        return False

    # 显示额外链接（网盘）
    if detail.get("extra_urls"):
        print("  网盘链接:")
        for eu in detail["extra_urls"]:
            print(f"    {eu['type']}: {eu['url']}")

    if not detail.get("audio_url"):
        print("  未获取到在线播放地址，可尝试上面的网盘链接手动下载")
        return False

    filename = f"{song['artist']} - {song['title']}" if song.get("artist") else song["title"]
    return download_song(detail["audio_url"], filename, output_dir)


def interactive_mode(output_dir: str):
    """交互模式：循环搜索和下载"""
    print("=" * 44)
    print("      歌曲搜索下载工具 (gequbao.com)")
    print("=" * 44)
    print(f"  下载目录: {os.path.abspath(output_dir)}")
    print("  输入 q 退出")
    print("=" * 44)

    while True:
        print()
        keyword = input("搜索: ").strip()
        if keyword.lower() in ("q", "quit", "exit"):
            print("再见!")
            break
        if not keyword:
            continue

        songs = search_songs(keyword)
        if not songs:
            print("没找到，换个关键词试试")
            continue

        print(f"\n找到 {len(songs)} 首:\n")
        for i, song in enumerate(songs[:20], 1):
            artist = f" - {song['artist']}" if song.get("artist") else ""
            print(f"  [{i:2d}] {song['title']}{artist}")

        if len(songs) > 20:
            print(f"  ... 共 {len(songs)} 首，只显示前 20 首")

        choice = input("\n下载哪首? 输入编号 (多个用逗号, 0=全部, 回车跳过): ").strip()
        if not choice:
            continue

        if choice == "0":
            indices = list(range(len(songs)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
            except ValueError:
                print("输入无效，跳过")
                continue

        for idx in indices:
            if 0 <= idx < len(songs):
                process_song(songs[idx], output_dir)
                time.sleep(0.5)
            else:
                print(f"编号 {idx + 1} 无效，跳过")


def main():
    parser = argparse.ArgumentParser(
        description="gequbao.com 歌曲搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               '  python gequbao_search.py "晴天"\n'
               '  python gequbao_search.py "周杰伦" -d\n'
               '  python gequbao_search.py "稻香" -d -o D:\\Music\n'
               '  python gequbao_search.py --interactive\n',
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词（歌名或歌手名）")
    parser.add_argument("--download", "-d", action="store_true", help="下载歌曲")
    default_output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")
    parser.add_argument("--output", "-o", default=default_output, help="下载目录 (默认: 脚本同目录下 music 文件夹)")
    parser.add_argument("--all", "-a", action="store_true", help="下载所有搜索结果")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出搜索结果")
    parser.add_argument("--limit", "-l", type=int, default=0, help="限制搜索结果数量 (0=不限)")
    parser.add_argument("--interactive", "-i", action="store_true", help="进入交互模式")
    args = parser.parse_args()

    if args.interactive:
        interactive_mode(args.output)
        return

    if not args.keyword:
        # 没给关键词也没开交互模式，默认进入交互模式
        interactive_mode(args.output)
        return

    songs = search_songs(args.keyword)

    if not songs:
        print("\n未找到任何结果。")
        print("提示: 尝试使用更简短的关键词，或去掉特殊字符。")
        sys.exit(1)

    if args.limit > 0:
        songs = songs[:args.limit]

    if args.json:
        print(json.dumps(songs, ensure_ascii=False, indent=2))
        return

    print(f"\n找到 {len(songs)} 首歌曲:\n")
    for i, song in enumerate(songs, 1):
        artist = f" - {song['artist']}" if song.get("artist") else ""
        print(f"  [{i:2d}] {song['title']}{artist}")

    if not args.download:
        print(f"\n提示: 添加 --download 参数来下载歌曲")
        return

    # 确定要下载的索引
    if args.all:
        indices = list(range(len(songs)))
    else:
        choice = input("\n输入要下载的编号 (多个用逗号分隔, 0=全部): ").strip()
        if choice == "0":
            indices = list(range(len(songs)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
            except ValueError:
                print("输入无效")
                sys.exit(1)

    success = 0
    for idx in indices:
        if idx < 0 or idx >= len(songs):
            print(f"\n编号 {idx + 1} 无效，跳过")
            continue
        if process_song(songs[idx], args.output):
            success += 1
        time.sleep(0.5)

    print(f"\n完成! 成功下载 {success}/{len(indices)} 首歌曲")


if __name__ == "__main__":
    main()
