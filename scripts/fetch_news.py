#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上海高考新闻抓取脚本
从官方渠道抓取高考相关新闻资讯
"""

import os
import json
import re
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import hashlib

# 配置
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(SCRIPT_DIR)
DATA_DIR = os.path.join(PROJECT_DIR, 'data')
NEWS_FILE = os.path.join(DATA_DIR, 'news.json')

# 新闻源配置
NEWS_SOURCES = {
    'shmeea': {
        'name': '上海招考热线',
        'url': 'https://www.shmeea.edu.cn/page/24100/index.html',
        'type': '官方公布',
        'parser': 'parse_shmeea'
    },
    'gaokao': {
        'name': '阳光高考网',
        'url': 'https://gaokao.chsi.com.cn/gkxx/zszcgd/index.jsp',
        'type': '官方公布',
        'parser': 'parse_gaokao'
    }
}

# 请求头
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
}


def load_existing_news():
    """加载现有新闻数据"""
    if os.path.exists(NEWS_FILE):
        with open(NEWS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'news': [], 'categories': [], 'sources': [], 'update_time': ''}


def save_news(data):
    """保存新闻数据"""
    data['update_time'] = datetime.now().strftime('%Y-%m-%d')
    data['next_update'] = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    with open(NEWS_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"新闻数据已保存到 {NEWS_FILE}")


def generate_id(title, date):
    """根据标题和日期生成唯一ID"""
    content = f"{title}_{date}"
    return int(hashlib.md5(content.encode()).hexdigest()[:8], 16) % 10000


def parse_shmeea(html):
    """解析上海招考热线新闻"""
    news_list = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        # 查找新闻列表
        items = soup.select('.news-list li, .list li, .article-list li')

        for item in items[:10]:  # 最多抓取10条
            link = item.find('a')
            if not link:
                continue

            title = link.get_text(strip=True)
            href = link.get('href', '')

            # 获取日期
            date_text = item.find(class_='date')
            if date_text:
                date_str = date_text.get_text(strip=True)
            else:
                # 尝试从文本中提取日期
                date_match = re.search(r'(\d{4}-\d{2}-\d{2})', item.get_text())
                date_str = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')

            # 过滤高考相关新闻
            keywords = ['高考', '招生', '录取', '志愿', '分数线', '报名', '考试']
            if any(kw in title for kw in keywords):
                news_list.append({
                    'id': generate_id(title, date_str),
                    'title': title,
                    'category': '高考政策' if '政策' in title or '通知' in title else '招生动态',
                    'source': '上海招考热线',
                    'source_url': 'https://www.shmeea.edu.cn' + href if href.startswith('/') else href,
                    'source_type': '官方公布',
                    'publish_date': date_str,
                    'summary': title[:50] + '...' if len(title) > 50 else title,
                    'content': '',
                    'tags': ['上海高考'],
                    'is_top': False,
                    'view_count': 0
                })
    except Exception as e:
        print(f"解析上海招考热线失败: {e}")

    return news_list


def parse_gaokao(html):
    """解析阳光高考网新闻"""
    news_list = []
    try:
        soup = BeautifulSoup(html, 'html.parser')
        items = soup.select('.news-list li, .list-item, .article-item')

        for item in items[:10]:
            link = item.find('a')
            if not link:
                continue

            title = link.get_text(strip=True)
            href = link.get('href', '')

            date_text = item.find(class_='date')
            date_str = date_text.get_text(strip=True) if date_text else datetime.now().strftime('%Y-%m-%d')

            keywords = ['上海', '高考', '招生', '录取', '志愿']
            if any(kw in title for kw in keywords):
                news_list.append({
                    'id': generate_id(title, date_str),
                    'title': title,
                    'category': '招生动态',
                    'source': '阳光高考网',
                    'source_url': href if href.startswith('http') else 'https://gaokao.chsi.com.cn' + href,
                    'source_type': '官方公布',
                    'publish_date': date_str,
                    'summary': title[:50] + '...' if len(title) > 50 else title,
                    'content': '',
                    'tags': ['招生动态'],
                    'is_top': False,
                    'view_count': 0
                })
    except Exception as e:
        print(f"解析阳光高考网失败: {e}")

    return news_list


def fetch_news_from_source(source_key):
    """从指定源抓取新闻"""
    source = NEWS_SOURCES.get(source_key)
    if not source:
        return []

    print(f"正在抓取: {source['name']}")
    try:
        response = requests.get(source['url'], headers=HEADERS, timeout=30)
        response.encoding = 'utf-8'

        parser_func = globals().get(source['parser'])
        if parser_func:
            return parser_func(response.text)
    except Exception as e:
        print(f"抓取 {source['name']} 失败: {e}")

    return []


def merge_news(existing_news, new_news):
    """合并新旧新闻，去重"""
    existing_ids = {n['id'] for n in existing_news}

    merged = existing_news.copy()
    for news in new_news:
        if news['id'] not in existing_ids:
            merged.insert(0, news)  # 新新闻插入前面

    # 按日期排序
    merged.sort(key=lambda x: x.get('publish_date', ''), reverse=True)

    return merged[:100]  # 保留最新100条


def update_categories(data):
    """更新分类信息"""
    data['categories'] = [
        {"id": "policy", "name": "高考政策", "description": "高考相关政策法规、改革动态"},
        {"id": "score", "name": "分数线", "description": "各批次分数线、高校录取分数线"},
        {"id": "guide", "name": "志愿填报", "description": "志愿填报技巧、策略指导"},
        {"id": "news", "name": "招生动态", "description": "高校招生信息、专业变化"}
    ]


def update_sources(data):
    """更新来源信息"""
    data['sources'] = [
        {"name": "上海招考热线", "url": "https://www.shmeea.edu.cn", "type": "官方公布", "description": "上海市教育考试院官方网站"},
        {"name": "阳光高考网", "url": "https://gaokao.chsi.com.cn", "type": "官方公布", "description": "教育部高校招生阳光工程指定平台"},
        {"name": "教育部", "url": "https://www.moe.gov.cn", "type": "官方公布", "description": "中华人民共和国教育部官网"},
        {"name": "上海市教委", "url": "https://edu.sh.gov.cn", "type": "官方公布", "description": "上海市教育委员会官网"},
        {"name": "本站整理", "url": "", "type": "网络公开", "description": "本站根据公开资料整理"}
    ]


def main():
    """主函数"""
    print("=" * 50)
    print("上海高考新闻抓取脚本")
    print(f"执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)

    # 加载现有数据
    data = load_existing_news()
    existing_news = data.get('news', [])

    print(f"现有新闻数量: {len(existing_news)}")

    # 抓取新闻
    all_new_news = []
    for source_key in NEWS_SOURCES:
        new_news = fetch_news_from_source(source_key)
        all_new_news.extend(new_news)
        print(f"  {NEWS_SOURCES[source_key]['name']}: 获取 {len(new_news)} 条")

    # 合并新闻
    if all_new_news:
        data['news'] = merge_news(existing_news, all_new_news)
        print(f"合并后新闻数量: {len(data['news'])}")

    # 更新元数据
    update_categories(data)
    update_sources(data)

    # 保存
    save_news(data)

    print("=" * 50)
    print("抓取完成!")
    print("=" * 50)


if __name__ == '__main__':
    main()
