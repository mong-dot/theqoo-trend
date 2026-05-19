"""
더쿠 핫게 크롤러 + 단어 트렌드 분석기
--------------------------------------
사용법:
  pip3 install requests beautifulsoup4
  python3 theqoo_crawler.py

결과:
  - theqoo_data.json 으로 저장 (dashboard.html이 읽음)
  - 30분마다 자동 반복 실행
"""

import requests
from bs4 import BeautifulSoup
import json
import time
import re
from datetime import datetime
from collections import Counter

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Referer": "https://theqoo.net/",
    "Accept-Language": "ko-KR,ko;q=0.9",
}

BASE_URL     = "https://theqoo.net"
HOT_URL      = "https://theqoo.net/hot"
OUTPUT_FILE  = "theqoo_data.json"
INTERVAL_MIN = 30
PAGES        = 3

STOPWORDS = {
    "이", "그", "저", "것", "수", "등", "및", "의", "가", "을", "를",
    "은", "는", "에", "도", "로", "와", "과", "하", "다", "에서",
    "이다", "있다", "없다", "한", "이런", "저런", "그런", "더", "또",
    "진짜", "정말", "완전", "너무", "그냥", "어떻게", "왜", "뭐",
}


def get_hot_posts(page=1):
    url = f"{HOT_URL}?page={page}"
    try:
        res = requests.get(url, headers=HEADERS, timeout=10)
        res.raise_for_status()
    except requests.RequestException as e:
        print(f"  [오류] 페이지 {page}: {e}")
        return []

    soup  = BeautifulSoup(res.text, "html.parser")
    posts = []

    for row in soup.find_all("tr"):
        if "notice" in row.get("class", []):
            continue
        title_td = row.find("td", class_="title")
        if not title_td:
            continue
        title_tag = title_td.find("a")
        if not title_tag:
            continue

        title = title_tag.get_text(strip=True)
        href  = title_tag.get("href", "")
        link  = BASE_URL + href if href.startswith("/") else href

        time_td = row.find("td", class_="time")
        date    = time_td.get_text(strip=True) if time_td else "N/A"

        view_td = row.find("td", class_="m_no")
        views   = view_td.get_text(strip=True).replace(",", "") if view_td else "0"

        reply_tag = title_td.find("span", class_="replyNum")
        replies   = reply_tag.get_text(strip=True) if reply_tag else "0"

        if title:
            posts.append({"title": title, "link": link, "date": date, "views": views, "replies": replies})

    return posts


def crawl_all():
    all_posts = []
    for page in range(1, PAGES + 1):
        print(f"  [{page}/{PAGES}] 크롤링 중...")
        all_posts.extend(get_hot_posts(page))
        time.sleep(1.5)
    return all_posts


def extract_words(posts):
    counter = Counter()
    for post in posts:
        words = re.findall(r"[가-힣]{2,}", post["title"])
        for word in words:
            if word not in STOPWORDS:
                counter[word] += 1
    return counter


def get_top_views(posts, n=10):
    return sorted(posts, key=lambda p: int(re.sub(r"[^\d]", "", p["views"]) or "0"), reverse=True)[:n]


def load_existing_data():
    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {"history": [], "snapshots": []}


def save_data(data):
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def run_once():
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"\n{'='*45}\n  크롤링 시작: {now}\n{'='*45}")

    posts      = crawl_all()
    word_count = extract_words(posts)
    top_views  = get_top_views(posts, n=10)

    snapshot = {
        "timestamp": now,
        "total":     len(posts),
        "top_words": word_count.most_common(50),
        "top_posts": top_views,
        "all_posts": posts,
    }

    data = load_existing_data()
    data["snapshots"].append(snapshot)
    data["snapshots"] = data["snapshots"][-48:]
    data["history"].append({"timestamp": now, "top_words": word_count.most_common(20)})
    data["history"] = data["history"][-48:]
    data["latest"]  = snapshot

    save_data(data)
    print(f"  ✅ 저장 완료 ({len(posts)}개) | 상위 단어: {word_count.most_common(5)}")


def main():
    print("더쿠 핫게 트렌드 크롤러 시작!")
    print(f"주기: {INTERVAL_MIN}분 | 종료: Ctrl+C\n")
    while True:
        try:
            run_once()
        except Exception as e:
            print(f"[오류] {e}")
        next_time = datetime.fromtimestamp(time.time() + INTERVAL_MIN * 60).strftime("%H:%M:%S")
        print(f"  ⏰ 다음 실행: {next_time}\n")
        time.sleep(INTERVAL_MIN * 60)


if __name__ == "__main__":
    main()
