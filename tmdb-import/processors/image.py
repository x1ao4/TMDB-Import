from PIL import Image, ImageOps
import logging
import re

TYPE_BACKDROP = "backdrop"
TYPE_POSTER = "poster"
TYPE_FITSIZE = "fitsize"

# TMDB backdrop 分辨率与比例要求
BACKDROP_MIN_WIDTH = 1280
BACKDROP_MIN_HEIGHT = 720
BACKDROP_MAX_WIDTH = 3840
BACKDROP_MAX_HEIGHT = 2160
BACKDROP_ASPECT_RATIO = 16 / 9

def _scale_backdrop_resolution(width, height):
    """等比缩放分辨率，使其落在最小与最大分辨率范围内"""
    # 超出最大分辨率时等比缩小
    if width > BACKDROP_MAX_WIDTH or height > BACKDROP_MAX_HEIGHT:
        scale = min(BACKDROP_MAX_WIDTH / width, BACKDROP_MAX_HEIGHT / height)
        width = round(width * scale)
        height = round(height * scale)

    # 低于最小分辨率时等比放大
    if width < BACKDROP_MIN_WIDTH or height < BACKDROP_MIN_HEIGHT:
        scale = max(BACKDROP_MIN_WIDTH / width, BACKDROP_MIN_HEIGHT / height)
        new_width = round(width * scale)
        new_height = round(height * scale)

        # 放大后若超出最大分辨率，则以最大分辨率为上限再次等比缩小
        if new_width > BACKDROP_MAX_WIDTH or new_height > BACKDROP_MAX_HEIGHT:
            scale = min(BACKDROP_MAX_WIDTH / width, BACKDROP_MAX_HEIGHT / height)
            new_width = round(width * scale)
            new_height = round(height * scale)

        width, height = new_width, new_height

    return width, height

def _crop_backdrop_to_16_9(image):
    """居中裁切为 16:9 比例"""
    width, height = image.size
    current_ratio = width / height

    if abs(current_ratio - BACKDROP_ASPECT_RATIO) < 0.001:
        return image

    if current_ratio > BACKDROP_ASPECT_RATIO:
        # 图片过宽，裁切左右
        new_width = round(height * BACKDROP_ASPECT_RATIO)
        left = (width - new_width) // 2
        return image.crop((left, 0, left + new_width, height))

    # 图片过高，裁切上下
    new_height = round(width / BACKDROP_ASPECT_RATIO)
    top = (height - new_height) // 2
    return image.crop((0, top, width, top + new_height))

def process_downloaded_backdrop(image_path):
    """处理下载到本地的 backdrop 图片，满足 TMDB 分辨率与 16:9 比例要求"""
    try:
        convert_to_jpg(image_path)

        image = Image.open(image_path)
        width, height = image.size

        # 第一步：处理分辨率
        target_width, target_height = _scale_backdrop_resolution(width, height)
        if target_width != width or target_height != height:
            image = image.resize((target_width, target_height), Image.Resampling.LANCZOS)

        # 第二步：处理 16:9 比例
        image = _crop_backdrop_to_16_9(image)

        image.save(image_path, format="JPEG", quality=92)
        image.close()
        return True
    except Exception as err:
        logging.error(f"Backdrop 图片处理失败: {err}")
        return False

def convert_to_jpg(image_path):
    image = Image.open(image_path)
    if image.mode != "RGB":
        logging.info(f"Convert {image.mode} to RGB")
        image = image.convert("RGB")
        image.save(image_path, format="JPEG", quality=92)
    elif image.format != "JPEG":
        logging.info(f"Convert {image.format} to JPEG")
        image.save(image_path, format="JPEG", quality=92)
    image.close()

def crop_black_border(image_path):
    try:
        import bordercrop
        image = Image.open(image_path)       
        tempImage = bordercrop.crop(image_path, 2, round(min(image.size[0], image.size[1])*0.9999), 50)
        if (tempImage.size[0] < image.size[0] or tempImage.size[1] < image.size[1]):
            logging.info(f"Original image size: {image.size[0]} * {image.size[1]}")
            logging.info(f"Cropped black border and new image size: {tempImage.size[0]} * {tempImage.size[1]}")
            image = tempImage
            image.save(image_path, format="JPEG", quality=92)
    except Exception as err:
        logging.error(err)
    image.close()

def fit_aspect_ratio(image_path, type, fit_width, fit_height):   
    image = Image.open(image_path)
    image_widith, image_heigh = image.size
    logging.debug(f"Image size: {image_widith} * {image_heigh}")
    if type == TYPE_FITSIZE:
        re_size = (fit_width, fit_height)
        logging.info(f"Resize from {image_widith}*{image_heigh} to {re_size[0]}*{re_size[1]}")
        image = ImageOps.fit(image=image, size=re_size, method=Image.Resampling.LANCZOS, bleed=0.0, centering=(0.5, 0.5))
        image.save(image_path, format="JPEG", quality=85)
    elif type == TYPE_BACKDROP:
        aspectRatio = round(image_widith/image_heigh, 2)
        if aspectRatio == 1.78 and (image_widith >= 1280 and image_heigh >= 720) and (image_widith <= 3840 and image_heigh <= 2160):
            # valid image siez
            pass
        elif aspectRatio == 1.33 and (image_widith >= 960 and image_heigh >= 720) and (image_widith <= 2880 and image_heigh <= 2160):
            # valid image siez
            pass
        elif (aspectRatio >= 1.6 or aspectRatio <= 1.9) and (image_widith >= 860 and image_heigh >= 484):
            # resize image to fit valid size
            re_size = (1280, 720)
            if image_widith < 1280 or image_heigh < 720:
                pass
            elif image_widith > 3840 and image_heigh > 2160:
                re_size = (3840, 2160)
            else:
                if aspectRatio < 1.78:
                    re_size = (image_widith, round(image_widith / 1.7778))
                else:
                    re_size = (round(image_heigh * 1.7778), image_heigh)

            logging.info(f"Resize backdrop from {image_widith}*{image_heigh} to {re_size[0]}*{re_size[1]}")
            image = ImageOps.fit(image=image, size=re_size, method=Image.Resampling.LANCZOS, bleed=0.0, centering=(0.5, 0.5))
            image.save(image_path, format="JPEG", quality=85)
        elif (aspectRatio >= 1.30 or aspectRatio <= 1.36) and (image_widith >= 720 and image_heigh >= 540):
            # resize image to fit valid size
            re_size = (960, 720)
            if image_widith < 1280 or image_heigh < 720:
                pass
            elif image_widith > 2808 and image_heigh > 2160:
                re_size = (2808, 2160)
            else:
                if aspectRatio < 1.78:
                    re_size = (image_widith, round(image_widith / 1.3333))
                else:
                    re_size = (round(image_heigh * 1.3333), image_heigh)

            logging.info(f"Resize backdrop from {image_widith}*{image_heigh} to {re_size[0]}*{re_size[1]}")
            image = ImageOps.fit(image=image, size=re_size, method=Image.Resampling.LANCZOS, bleed=0.0, centering=(0.5, 0.5))
            image.save(image_path, format="JPEG", quality=85)
        else:
            logging.info("Skip: unable to use fit function to meet TMDB requirments")
            return False
    elif type == TYPE_POSTER:
        aspectRatio = round(image_heigh/image_widith, 2)
        if aspectRatio == 1.50 and (image_widith >= 500 and image_heigh >= 750) and (image_widith <= 2000 and image_heigh <= 3000):
            # valid image siez
            pass
        elif (aspectRatio >= 1.40 or aspectRatio <= 1.60) and (image_widith >= 400 and image_heigh >= 600):
            re_size = (500, 750)
            if image_widith < 500 or image_heigh < 750:
                pass
            elif image_widith > 2000 and image_heigh > 3000:
                re_size = (2000, 3000)
            else:
                if aspectRatio < 1.5:
                    re_size = (round(image_heigh/1.5), image_heigh)
                else:
                    re_size = (image_widith, round(image_widith * 1.5))
            logging.info(f"Resize poster from {image_widith}*{image_heigh} to to {re_size[0]}*{re_size[1]}")
            image = ImageOps.fit(image=image, size=re_size, method=Image.Resampling.LANCZOS, bleed=0.0, centering=(0.5, 0.5))
            image.save(image_path, format="JPEG", quality=85)
        else:
            logging.info("Skip: unable to use fit function to meet TMDB requirments")
            return False

    image.close()
    return True

def process_image(image_path, type, fit_width = -1, fit_height = -1, crop_back = True):
    # Convert other format to jpg
    convert_to_jpg(image_path)
    
    # Crop black border
    if crop_back:
        crop_black_border(image_path)
    
    # Fit backdrop aspect ratio
    return fit_aspect_ratio(image_path, type, fit_width, fit_height)

'''
from ..common import ini_webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium import webdriver
import time

# https://www.themoviedb.org/tv/136891/season/1/episode/1/images/backdrops?language=xx
# Not working
def backdrop_thumbs_up(url, driver = None):
    if driver==None:
        driver = ini_webdriver(headless=False, save_user_profile=True, images=True)
    
    driver.get(url)
    
    username = WebDriverWait(driver, timeout=30).until(lambda d: d.find_element(By.CSS_SELECTOR, value="div[class='avatar'] img")).get_attribute("alt")
    print(username)
    backdrop_id = ""
    for card_compact in WebDriverWait(driver, timeout=30).until(lambda d: d.find_elements(By.CSS_SELECTOR, value="li[class='card compact']")):
        print(backdrop_id)
        if len(card_compact.find_elements(By.LINK_TEXT, value=username)) > 0 and card_compact.get_attribute("id") > backdrop_id:
            backdrop_id = card_compact.get_attribute("id")
            print(backdrop_id)

    if backdrop_id != "":
        action = webdriver.ActionChains(driver)
        element = driver.find_element(By.CSS_SELECTOR, value=f"a[id='{backdrop_id}'][class='thumbs_up']")
        time.sleep(1)
        action.move_to_element(element).click(element)
        print("thumbs_up")
'''