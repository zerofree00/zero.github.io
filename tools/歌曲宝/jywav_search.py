"""
jywav.com 歌曲搜索与下载工具
使用方法:
    python jywav_search.py "歌曲名"                    # 搜索歌曲
    python jywav_search.py "周杰伦" --download          # 搜索并交互选择下载
    python jywav_search.py "晴天" -d -o ./music         # 下载到指定目录
    python jywav_search.py "周杰伦" -d --all            # 下载全部搜索结果
    python jywav_search.py "晴天" --json                # JSON 格式输出
"""

import argparse
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

BASE_URL = "https://www.jywav.com"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Referer": BASE_URL,
}

session = requests.Session()
session.headers.update(HEADERS)


def _request(url: str, method: str = "GET", retries: int = 2, **kwargs) -> requests.Response | None:
    """带重试的请求"""
    kwargs.setdefault("timeout", 15)
    for attempt in range(retries + 1):
        try:
            if method.upper() == "POST":
                resp = session.post(url, **kwargs)
            else:
                resp = session.get(url, **kwargs)
            resp.raise_for_status()
            return resp
        except requests.RequestException as e:
            if attempt < retries:
                time.sleep(1)
                continue
            print(f"  请求失败: {e}")
            return None


def search_songs(keyword: str, page: int = 0) -> list[dict]:
    """搜索歌曲，返回结果列表"""
    search_url = f"{BASE_URL}/search?page={page}&keyword={quote(keyword)}"
    print(f"正在搜索: {keyword}")

    resp = _request(search_url)
    if not resp:
        return []

    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")
    songs = []
    seen_ids = set()

    for a in soup.find_all("a", href=re.compile(r"/music/info\.html\?id=MUSIC_\d+")):
        href = a.get("href", "")
        text = a.get_text(strip=True)

        mid = re.search(r"id=(MUSIC_\d+)", href)
        if not mid:
            continue
        music_id = mid.group(1)
        if music_id in seen_ids:
            continue
        seen_ids.add(music_id)

        # 解析歌名和歌手 (格式: 歌手《歌名》或 歌手《歌名 (版本)》)
        title = text
        artist = ""
        m = re.match(r"(.+?)《(.+?)》", text)
        if m:
            artist = m.group(1).strip()
            title = m.group(2).strip()

        songs.append({
            "title": title,
            "artist": artist,
            "music_id": music_id,
            "url": f"{BASE_URL}/music/info.html?id={music_id}",
        })

    return songs


def get_song_detail(song_url: str) -> dict | None:
    """访问歌曲详情页，提取下载信息"""
    resp = _request(song_url)
    if not resp:
        print("  获取详情页失败")
        return None

    resp.encoding = "utf-8"

    # 从页面 JS 中提取 detail JSON
    match = re.search(r"detail\s*=\s*JSON\.parse\('(.+?)'\)", resp.text)
    if not match:
        print("  未找到歌曲详情数据")
        return None

    try:
        raw = match.group(1)
        # 先处理 JSON 中的 \/ 转义（unicode_escape 不支持）
        raw = raw.replace("\\/", "/")
        decoded = raw.encode("utf-8").decode("unicode_escape")
        data = json.loads(decoded)
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"  解析详情数据失败: {e}")
        return None

    result = {
        "music_id": data.get("music_id"),
        "title": data.get("music_name") or "",
        "artist": data.get("music_artist") or "",
        "album": data.get("music_album") or "",
        "cover": data.get("music_cover") or "",
        "mp3_url": data.get("mp3_url") or "",
        "flac_url": data.get("flac_url") or "",
        "music_mp3Url": data.get("music_mp3Url") or "",
        "music_flacUrl": data.get("music_flacUrl") or "",
    }

    return result


def download_file(url: str, filename: str, output_dir: str) -> bool:
    """下载文件"""
    os.makedirs(output_dir, exist_ok=True)

    safe_name = re.sub(r'[<>:"/\\|?*]', "_", filename)
    ext = os.path.splitext(url.split("?")[0])[1] or ".mp3"
    filepath = os.path.join(output_dir, safe_name + ext)

    if os.path.exists(filepath):
        print(f"  文件已存在，跳过: {filepath}")
        return True

    # CDN 需要对应站点的 Referer
    dl_headers = dict(HEADERS)
    if "kuwo.cn" in url:
        dl_headers["Referer"] = "https://www.kuwo.cn/"
    elif "kugou.com" in url:
        dl_headers["Referer"] = "https://www.kugou.com/"

    print(f"  正在下载: {url[:80]}...")
    resp = _request(url, headers=dl_headers, timeout=120, stream=True)
    if not resp:
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


def check_song_quality(song: dict) -> dict:
    """检查歌曲音质信息，返回 {flac: bool, mp3: bool, pan: bool}"""
    detail = get_song_detail(song["url"])
    if not detail:
        return {"flac": False, "mp3": False, "pan": False}

    def _valid(v):
        return v and v != "None" and v.startswith("http")

    flac = _valid(detail.get("music_flacUrl"))
    mp3 = _valid(detail.get("music_mp3Url"))
    pan = _valid(detail.get("mp3_url")) or _valid(detail.get("flac_url"))
    return {"flac": flac, "mp3": mp3, "pan": pan}


def quality_tag(q: dict) -> str:
    """根据音质信息返回标签"""
    if q.get("flac"):
        return "[FLAC]"
    if q.get("mp3"):
        return "[MP3]"
    if q.get("pan"):
        return "[网盘]"
    return "[?]"


def process_song(song: dict, output_dir: str, prefer_flac: bool = False) -> bool:
    """处理单首歌曲：获取详情 + 下载"""
    print(f"\n--- {song['title']} ({song.get('artist', '')}) ---")
    print(f"  详情页: {song['url']}")

    detail = get_song_detail(song["url"])
    if not detail:
        print("  获取详情失败")
        return False

    # 选择下载链接：优先 CDN 直链，其次网盘
    mp3_cdn = detail.get("music_mp3Url") or ""
    flac_cdn = detail.get("music_flacUrl") or ""

    # 过滤无效值（字符串 "None" 或空值）
    def _valid_url(v):
        return v and v != "None" and v.startswith("http")

    mp3_cdn = mp3_cdn if _valid_url(mp3_cdn) else ""
    flac_cdn = flac_cdn if _valid_url(flac_cdn) else ""

    if prefer_flac:
        audio_url = flac_cdn or mp3_cdn
        fmt = "FLAC" if flac_cdn else "MP3"
    else:
        audio_url = mp3_cdn or flac_cdn
        fmt = "MP3" if mp3_cdn else "FLAC"

    # 显示网盘链接
    pan_links = []
    mp3_pan = detail.get("mp3_url") or ""
    flac_pan = detail.get("flac_url") or ""
    if mp3_pan and mp3_pan != "None" and mp3_pan.startswith("http"):
        pan_links.append(f"夸克网盘(MP3): {mp3_pan}")
    if flac_pan and flac_pan != "None" and flac_pan.startswith("http"):
        pan_links.append(f"夸克网盘(FLAC): {flac_pan}")
    if pan_links:
        print("  网盘链接:")
        for pl in pan_links:
            print(f"    {pl}")

    if not audio_url:
        print("  未获取到在线下载地址，可尝试上面的网盘链接手动下载")
        return False

    print(f"  格式: {fmt}")
    filename = f"{song['artist']} - {song['title']}" if song.get("artist") else song["title"]
    return download_file(audio_url, filename, output_dir)


def interactive_mode(output_dir: str):
    """交互模式：循环搜索和下载"""
    print("=" * 44)
    print("    jywav.com 歌曲搜索下载工具")
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

        # 检查音质并排序
        print(f"\n正在检查 {len(songs)} 首歌曲的音质...")
        for song in songs:
            song["_quality"] = check_song_quality(song)
            time.sleep(0.3)

        # 按音质排序: FLAC > MP3 > 网盘 > 未知
        def _sort_key(s):
            q = s.get("_quality", {})
            if q.get("flac"):
                return (0, s.get("title", ""))
            if q.get("mp3"):
                return (1, s.get("title", ""))
            if q.get("pan"):
                return (2, s.get("title", ""))
            return (3, s.get("title", ""))
        songs.sort(key=_sort_key)

        # 过滤掉完全无法下载的歌曲
        valid_songs = [s for s in songs if any(s["_quality"].values())]
        skipped = len(songs) - len(valid_songs)

        print(f"\n找到 {len(valid_songs)} 首可下载的歌曲" +
              (f"（过滤了 {skipped} 首无资源的）" if skipped else "") + ":\n")
        for i, song in enumerate(valid_songs[:20], 1):
            artist = f" - {song['artist']}" if song.get("artist") else ""
            tag = quality_tag(song["_quality"])
            print(f"  [{i:2d}] {tag:8s} {song['title']}{artist}")

        if len(valid_songs) > 20:
            print(f"  ... 共 {len(valid_songs)} 首，只显示前 20 首")

        if not valid_songs:
            print("  没有可下载的歌曲，换个关键词试试")
            continue

        choice = input("\n下载哪首? 输入编号 (多个用逗号, 0=全部, 回车跳过): ").strip()
        if not choice:
            continue

        if choice == "0":
            indices = list(range(len(valid_songs)))
        else:
            try:
                indices = [int(x.strip()) - 1 for x in choice.split(",")]
            except ValueError:
                print("输入无效，跳过")
                continue

        success = 0
        for idx in indices:
            if 0 <= idx < len(valid_songs):
                if process_song(valid_songs[idx], output_dir):
                    success += 1
                time.sleep(0.5)
            else:
                print(f"编号 {idx + 1} 无效，跳过")
        print(f"\n完成! 成功下载 {success}/{len(indices)} 首")


def main():
    parser = argparse.ArgumentParser(
        description="jywav.com 歌曲搜索与下载工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="示例:\n"
               '  python jywav_search.py "晴天"\n'
               '  python jywav_search.py "周杰伦" -d\n'
               '  python jywav_search.py "稻香" -d -o D:\\Music\n'
               '  python jywav_search.py --interactive\n',
    )
    parser.add_argument("keyword", nargs="?", help="搜索关键词（歌名或歌手名）")
    parser.add_argument("--download", "-d", action="store_true", help="下载歌曲")
    parser.add_argument("--output", "-o", default=None, help="下载目录 (默认: 脚本同目录下 music 文件夹)")
    parser.add_argument("--all", "-a", action="store_true", help="下载所有搜索结果")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出搜索结果")
    parser.add_argument("--flac", action="store_true", help="优先下载 FLAC 无损格式")
    parser.add_argument("--check", "-c", action="store_true", help="检查音质并排序，过滤无资源歌曲")
    parser.add_argument("--limit", "-l", type=int, default=0, help="限制搜索结果数量 (0=不限)")
    parser.add_argument("--interactive", "-i", action="store_true", help="进入交互模式")
    args = parser.parse_args()

    if args.output is None:
        args.output = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music")

    if args.interactive:
        interactive_mode(args.output)
        return

    if not args.keyword:
        interactive_mode(args.output)
        return

    songs = search_songs(args.keyword)

    if not songs:
        print("\n未找到任何结果。")
        sys.exit(1)

    if args.limit > 0:
        songs = songs[:args.limit]

    # 检查音质并排序
    if args.check:
        print(f"\n正在检查 {len(songs)} 首歌曲的音质...")
        for song in songs:
            song["_quality"] = check_song_quality(song)
            time.sleep(0.3)

        songs.sort(key=lambda s: (
            0 if s["_quality"].get("flac") else
            1 if s["_quality"].get("mp3") else
            2 if s["_quality"].get("pan") else 3,
            s.get("title", ""),
        ))

        # 过滤无资源歌曲
        songs = [s for s in songs if any(s["_quality"].values())]

    if args.json:
        print(json.dumps(songs, ensure_ascii=False, indent=2))
        return

    if args.check:
        print(f"\n找到 {len(songs)} 首可下载的歌曲:\n")
    else:
        print(f"\n找到 {len(songs)} 首歌曲:\n")

    for i, song in enumerate(songs, 1):
        artist = f" - {song['artist']}" if song.get("artist") else ""
        tag = quality_tag(song["_quality"]) if "_quality" in song else ""
        if tag:
            print(f"  [{i:2d}] {tag:8s} {song['title']}{artist}")
        else:
            print(f"  [{i:2d}] {song['title']}{artist}")

    if not args.download:
        print(f"\n提示: 添加 --download 参数来下载歌曲")
        return

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
        if process_song(songs[idx], args.output, prefer_flac=args.flac):
            success += 1
        time.sleep(0.5)

    print(f"\n完成! 成功下载 {success}/{len(indices)} 首歌曲")


if __name__ == "__main__":
    main()
