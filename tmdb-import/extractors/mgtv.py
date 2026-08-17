import json
import logging
from urllib.parse import quote
from ..common import Episode, open_url

# language: zh
# backdrop: 860*484
# Ex:"https://w.mgtv.com/b/419629/17004788.html"
#    "https://www.mgtv.com/h/390933.html"
def is_mgtv_variety_show(collection_id, collection_title):
    if not collection_id or not collection_title:
        return False
    try:
        searchApi = (
            "https://pianku.api.mgtv.com/rider/list/pcweb/v3"
            "?platform=pcweb&channelId=1&pn=1&pc=30&_support=10000000"
            f"&q={quote(collection_title)}"
        )
        logging.debug(f"Program type API url: {searchApi}")
        sourceData = json.loads(open_url(searchApi))
        for item in sourceData.get("data", {}).get("hitDocs", []):
            if str(item.get("clipId")) == str(collection_id):
                return str(item.get("fstlvlId")) == "1"
    except Exception as e:
        logging.warning(f"Failed to detect mgtv program type: {e}")
    return False

def mgtv_extractor(url):
    logging.info("mgtv_extractor is called")

    url = url.split('.html', 1)[0]
    
    collection_id = ""
    for part in url.split('/'):
        if (part.isdigit()):
            collection_id = part
            break
    if collection_id == "":
        return {} 
    

    page = 1
    episodes = {}
    is_variety = False
    while True:
        apiRequest = f"https://pcweb.api.mgtv.com/episode/list?_support=10000000&version=5.5.35&collection_id={collection_id}&page={page}&size=50&&callback="
        #apiRequest = f"https://pcweb.api.mgtv.com/episode/list?_support=10000000&version=5.5.35&video_id={videoID}&page=0&size=50&&callback="
        logging.debug(f"API request url: {apiRequest}")
        soureData = json.loads(open_url(apiRequest))
        if page == 1:
            collection_title = soureData.get("data", {}).get("info", {}).get("title", "")
            is_variety = is_mgtv_variety_show(collection_id, collection_title)
            if is_variety:
                logging.info("Detected variety show, using full title as overview")
        added_count = 0
        for episode in soureData["data"]["list"]:
            if episode["isIntact"] == "1":
                episode_number = episode["t1"]
                episode_name = episode["t2"]
                episode_air_date = episode["ts"].split(' ')[0]
                episode_runtime = episode["time"].split(':')[0]
                episode_overview = ""
                if is_variety:
                    full_title = episode.get("t3", "")
                    if full_title:
                        episode_overview = full_title.rsplit('：', 1)[-1].strip()
                episode_backdrop = episode["img"].rsplit('_', 1)[0]
                if episode_number not in episodes:
                    added_count += 1
                episodes[episode_number] = Episode(episode_number, episode_name, episode_air_date, episode_runtime, episode_overview, episode_backdrop)
        if added_count == 0:
            break
        if soureData["data"]["total_page"] == soureData["data"]["current_page"]:
            break
        else:
            page = page + 1

    return episodes