import json
import logging
import re
from datetime import datetime
from ..common import Episode, open_url

CN_NUMS = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
PART_ORDER = {"上": 0, "中": 2, "下": 4}

def _cn_to_int(value):
    if value.isdigit():
        return int(value)
    return CN_NUMS.get(value, 99)

def _episode_part_order(title):
    ep_match = re.search(r"第(\d+)期", title)
    if not ep_match:
        return 99

    ep_num = ep_match.group(1)
    prefix = f"第{ep_num}期"

    part_match = re.search(rf"{re.escape(prefix)}\(([一二三四五六七八九十\d]+)\)", title)
    if part_match:
        return (_cn_to_int(part_match.group(1)) - 1) * 2

    part_match = re.search(rf"{re.escape(prefix)}(上|中|下)(?:\s|：|$)", title)
    if part_match:
        return PART_ORDER[part_match.group(1)]

    if title.startswith(prefix + "超长抢先"):
        return 1
    if "纯享上" in title:
        return 10
    if "纯享下" in title:
        return 11
    if "高分舞台" in title:
        return 12
    if title.startswith(prefix + "衍生"):
        return 13

    return 20

def _variety_sort_key(episode):
    title = episode.get("shortTitle") or episode.get("subtitle") or episode.get("name") or ""
    period = episode.get("period", "")
    issue_time = episode.get("issueTime", 0)

    ep_match = re.search(r"第(\d+)期", title)
    if ep_match:
        return (period, int(ep_match.group(1)), _episode_part_order(title), issue_time)

    return (period, 0, 99, issue_time)

def _clean_episode_overview(name, overview):
    if not overview:
        return overview

    overview = overview.strip()
    if not name:
        return overview

    prefix_match = re.match(r"^(第\d+期(?:\([一二三四五六七八九十\d]+\)|上|中|下)?)", name)
    if not prefix_match:
        return overview

    prefix = prefix_match.group(1)
    escaped = re.escape(prefix)

    for pattern in (
        rf"^{escaped}\s+",
        rf"^{escaped}：\s*",
    ):
        overview, count = re.subn(pattern, "", overview, count=1)
        if count:
            break

    if re.fullmatch(r"第\d+期", prefix):
        for theme_pattern in (
            rf"^{escaped}主题：\s*",
            rf"^{escaped}主题",
        ):
            overview, count = re.subn(theme_pattern, "", overview, count=1)
            if count:
                break

    return overview

def _parse_episode(episode, episode_number, prefer_short_title=False):
    if prefer_short_title and episode.get("shortTitle"):
        episode_name = episode["shortTitle"]
    else:
        episode_name = episode["subtitle"]
    episode_air_date = episode["period"]
    duration = episode["duration"].split(':')
    episode_runtime = ""
    if len(duration) == 3:
        episode_runtime = str(int(duration[0]) * 60 + int(duration[1]))
    elif len(duration) == 2:
        episode_runtime = duration[0]
    _nl_placeholder = "\\p"
    desc = episode["description"].strip()
    episode_overview = (
        desc.replace("。\n", "。" + _nl_placeholder)
        .replace("！\n", "！" + _nl_placeholder)
        .replace("？\n", "？" + _nl_placeholder)
        .replace("…\n", "…" + _nl_placeholder)
        .replace("”\n", "”" + _nl_placeholder)
        .replace("\n", "")
        .replace(_nl_placeholder, "\n")
    )
    episode_overview = _clean_episode_overview(episode_name, episode_overview)
    episode_backdrop = episode["imageUrl"]

    pixel = ("0", "0")
    for imageSize in episode.get("imageSize", []):
        size = imageSize.split('_')
        if pixel == ("0", "0"):
            pixel = size
        else:
            if int(size[0]) > int(pixel[0]):
                pixel = size
    if pixel != ("0", "0"):
        episode_backdrop = episode_backdrop.rsplit(".", 1)[0] + f"_{pixel[0]}_{pixel[1]}.jpg"

    return Episode(episode_number, episode_name, episode_air_date, episode_runtime, episode_overview, episode_backdrop)

def _fetch_variety_episodes(album_id, base_data):
    year_start = year_end = datetime.now().year
    if base_data.get("firstVideo") and base_data["firstVideo"].get("period"):
        year_start = int(base_data["firstVideo"]["period"][:4])
    if base_data.get("latestVideo") and base_data["latestVideo"].get("period"):
        year_end = int(base_data["latestVideo"]["period"][:4])

    source_id = base_data.get("sourceId") or album_id
    if not source_id:
        source_id = album_id

    all_episodes = []
    for year in range(year_start, year_end + 1):
        api_request = f"https://pcw-api.iqiyi.com/album/source/svlistinfo?cid=6&sourceid={source_id}&timelist={year}"
        logging.debug(f"API request url: {api_request}")
        source_data = json.loads(open_url(api_request))
        all_episodes.extend(source_data.get("data", {}).get(str(year), []))

    all_episodes.sort(key=_variety_sort_key)

    episodes = {}
    for episode_number, episode in enumerate(all_episodes, start=1):
        episodes[episode_number] = _parse_episode(episode, episode_number, prefer_short_title=True)

    return episodes

def _fetch_drama_episodes(album_id):
    api_request = f"https://pcw-api.iqiyi.com/albums/album/avlistinfo?aid={album_id}&page=1&size=999&callback="
    logging.debug(f"API request url: {api_request}")
    source_data = json.loads(open_url(api_request))
    episodes = {}
    for episode in source_data["data"]["epsodelist"]:
        episode_number = episode["order"]
        episodes[episode_number] = _parse_episode(episode, episode_number)
    return episodes

# language: zh
# Ex:"https://www.iqiyi.com/v_ik3832z0go.html"
def iqiyi_extractor(url):
    logging.info("iqiyi_extractor is called")
    webPage = open_url(url)
    if url.__contains__("iqiyi.com/lib/m_"):
        albumId = re.search(r'movlibalbumaid=\"(\d+)\"', str(webPage)).group(1)
    else:
        albumId = re.search(r'\"albumId\":(\d+),\"channelId', str(webPage)).group(1)
    logging.info(f"album_id: {albumId}")
    apiRequest = f"https://pcw-api.iqiyi.com/album/album/baseinfo/{albumId}"
    logging.debug(f"API request: {apiRequest}")
    soureData = json.loads(open_url(apiRequest))
    album_url = soureData["data"]["url"]
    logging.info(f"album_url: {album_url}")
    name = soureData["data"]["name"]
    logging.info(f"name: {name}")
    cover = soureData["data"]["imageUrl"]
    logging.info(f"Image: {cover}")
    description = soureData["data"]["description"]
    logging.info(f"description: {description}")

    channel_id = soureData["data"].get("channelId")
    if channel_id == 6:
        logging.info("Detected variety show, using svlistinfo API")
        episodes = _fetch_variety_episodes(albumId, soureData["data"])
    else:
        episodes = _fetch_drama_episodes(albumId)

    return episodes
