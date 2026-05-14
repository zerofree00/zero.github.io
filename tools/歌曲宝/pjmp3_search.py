"""
pjmp3.com (泡椒音乐) 歌曲搜索工具
搜索歌曲后自动在浏览器打开歌曲页面，手动下载
"""

import argparse
import json
import os
import re
import sys
import webbrowser
from urllib.parse import quote

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

BASE_URL = "https://pjmp3.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
}

session = requests.Session()
session.headers.update(HEADERS)


def _request(url: str, retries: int = 2, **kwargs) -> requests.Response | None:
    kwargs.setdefault("timeout", 15)
    for attempt in range(retries + 1):
        try:
            resp = session.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < retries:
                import time
                time.sleep(1)
                continue
            print(f"  请求失败: {e}")
            return None


def search_songs(keyword: str) -> list[dict]:
    """搜索歌曲"""
    search_url = f"{BASE_URL}/search.php?keyword={quote(keyword)}"
    print(f"正在搜索: {keyword}")

    resp = _request(search_url)
    if not resp:
        return []

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    songs = []
    seen_ids = set()

    for a in soup.find_all("a", href=re.compile(r"song\.php\?id=\d+")):
        href = a.get("href", "")

        m = re.search(r"id=(\d+)", href)
        if not m:
            continue
        song_id = m.group(1)
        if song_id in seen_ids:
            continue
        seen_ids.add(song_id)

        # 从专门的元素中提取歌名和歌手
        title_elem = a.find("div", class_="search-result-list-item-left-song")
        artist_elem = a.find("div", class_="search-result-list-item-left-singer")

        title = title_elem.get_text(strip=True) if title_elem else ""
        artist = artist_elem.get_text(strip=True) if artist_elem else ""

        if not title:
            title = a.get_text(strip=True)

        songs.append({
            "title": title,
            "artist": artist,
            "song_id": song_id,
            "url": f"{BASE_URL}/song.php?id={song_id}",
        })

    return songs


def interactive_mode():
    """交互模式"""
    print("=" * 44)
    print("    pjmp3.com (泡椒音乐) 搜索工具")
    print("=" * 44)
    print("  搜索歌曲后自动打开浏览器，手动下载")
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

        print(f"\n找到 {len(songs)} 首歌曲:\n")
        for i, song in enumerate(songs[:20], 1):
            artist = f" - {song['artist']}" if song.get("artist") else ""
            print(f"  [{i:2d}] {song['title']}{artist}")

        if len(songs) > 20:
            print(f"  ... 共 {len(songs)} 首，只显示前 20 首")

        choice = input("\n打开哪首? 输入编号 (多个用逗号, 回车跳过): ").strip()
        if not choice:
            continue

        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
        except ValueError:
            print("输入无效，跳过")
            continue

        for idx in indices:
            if 0 <= idx < len(songs):
                song = songs[idx]
                print(f"\n  打开浏览器: {song['url']}")
                webbrowser.open(song["url"])
            else:
                print(f"编号 {idx + 1} 无效，跳过")


def main():
    parser = argparse.ArgumentParser(
        description="pjmp3.com (泡椒音乐) 歌曲搜索工具",
        epilog='示例:\n'
               '  python pjmp3_search.py "晴天"\n'
               '  python pjmp3_search.py --interactive\n',
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词（歌名或歌手名）")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出")
    parser.add_argument("--interactive", "-i", action="store_true", help="进入交互模式")
    args = parser.parse_args()

    if args.interactive or not args.keyword:
        interactive_mode()
        return

    songs = search_songs(args.keyword)
    if not songs:
        print("\n未找到任何结果。")
        sys.exit(1)

    if args.json:
        print(json.dumps(songs, ensure_ascii=False, indent=2))
        return

    print(f"\n找到 {len(songs)} 首歌曲:\n")
    for i, song in enumerate(songs, 1):
        artist = f" - {song['artist']}" if song.get("artist") else ""
        print(f"  [{i:2d}] {song['title']}{artist}")

    choice = input("\n打开哪首? 输入编号 (多个用逗号, 0=全部, 回车跳过): ").strip()
    if not choice:
        return

    if choice == "0":
        indices = list(range(len(songs)))
    else:
        try:
            indices = [int(x.strip()) - 1 for x in choice.split(",")]
        except ValueError:
            print("输入无效")
            sys.exit(1)

    for idx in indices:
        if 0 <= idx < len(songs):
            song = songs[idx]
            print(f"\n  打开浏览器: {song['url']}")
            webbrowser.open(song["url"])
        else:
            print(f"编号 {idx + 1} 无效，跳过")


if __name__ == "__main__":
    main()
