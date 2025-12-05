import os, sys, json, random, time, subprocess, shutil, multiprocessing
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
import pycurl
from bs4 import BeautifulSoup
import genanki
import imageio_ffmpeg
from rich import print
from rich.progress import track
import rich_click as click

config = {
    "should_download": True,
    "should_convert": True,
    "ffmpeg_exe": None,
    "media_path": "collection.media",
    "format": "webp",
    "template": "jsl-ja"
}

def read(file_path: str) -> str:
    try: 
        text = ""
        with open(file_path, "r", encoding="utf-8") as f:
            text = f.read()
        return text
    except:
        print("ファイルが開けませんでした。", file_path)
        sys.exit(1)


def get_categories() -> list:
    json_path = f"{config["media_path"]}/categories.json"

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            jsondata = json.load(f)
    else:
        url = "https://handbook.sign.town/ja/collections?sl=JSL"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except:
            print("WEBページへのアクセスに失敗しました。")
            sys.exit(1)
    
        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")

        if not next_data:
            print("カテゴリリストが見つかりませんでした。")
            sys.exit(1)

        jsondata = json.loads(next_data.string)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jsondata, f, ensure_ascii=False, indent=2)

    cats = jsondata["props"]["pageProps"]["initialData"]
    
    return cats


def get_signs_in_category(cat_id):
    json_path = f"{config["media_path"]}/signs_{cat_id}.json"

    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            jsondata = json.load(f)
    else:
        url = f"https://handbook.sign.town/ja/collections/module/{cat_id}?sl=JSL"
        try:
            response = requests.get(url)
            response.raise_for_status()
        except:
            print("WEBページへのアクセスに失敗しました。")
            sys.exit(1)

        soup = BeautifulSoup(response.text, "html.parser")
        next_data = soup.find("script", id="__NEXT_DATA__")

        if not next_data:
            print("手話リストが見つかりませんでした")
            sys.exit(1)

        jsondata = json.loads(next_data.string)

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(jsondata, f, ensure_ascii=False, indent=2)

    signs = jsondata["props"]["pageProps"]["moduleData"]["signList"]
    return signs


def get_signs(cats: list) -> list:
    signs = []
    for cat in track(cats):
        time.sleep(0.2)
        signs_in_cat = get_signs_in_category(cat["id"])
        
        for sign in signs_in_cat:
            sign["category"] = cat["title"]
            sign["category_id"] = cat["id"]

        signs += signs_in_cat

    return signs


def get_ffmpeg_exe():
    global config
    if config["ffmpeg_exe"]:
        return config["ffmpeg_exe"]

    # Prefer system-installed ffmpeg
    try:
        system_ffmpeg = shutil.which("ffmpeg")
    except Exception:
        system_ffmpeg = None

    if system_ffmpeg:
        config["ffmpeg_exe"] = system_ffmpeg
        return config["ffmpeg_exe"]

    # Fall back to imageio-ffmpeg
    config["ffmpeg_exe"] = imageio_ffmpeg.get_ffmpeg_exe()
    return config["ffmpeg_exe"]


def download_video(url, video_path):
    if os.path.exists(video_path):
        return

    try:
        with open(video_path, "wb") as f:
            curl = pycurl.Curl()
            curl.setopt(curl.URL, url)
            curl.setopt(curl.WRITEDATA, f)
            curl.setopt(curl.NOPROGRESS, False)
            curl.setopt(curl.XFERINFOFUNCTION, lambda dltotal, dlnow, ultotal, ulnow: None)
            curl.perform()
            curl.close()
    except KeyboardInterrupt:
        print("ダウンロードを中断しています...")
        if os.path.exists(video_path):
            os.remove(video_path)
        sys.exit(1)
    except pycurl.error as e:
        print(f"ダウンロードできませんでした。: {e}")
        if os.path.exists(video_path):
            os.remove(video_path)
    except Exception as e:
        print(f"ダウンロードできませんでした。: {e}")
        if os.path.exists(video_path):
            os.remove(video_path)


def convert_to_mp4(input_path, output_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(input_path):
        return

    if os.path.exists(output_path):
        return

    # mp4
    cmd = [
        ffmpeg_exe, "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "28",
        # "-preset", "veryfast",
        "-an",
        "-loglevel", "error",
        output_path
    ]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("コマンドがありません。: ffmpeg")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)


def convert_to_webm(input_path, output_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(input_path):
        return

    if os.path.exists(output_path):
        return

    # webm (vp8)
    # cmd = [
    #     ffmpeg_exe, "-i", input_path,
    #     "-c:v", "libvpx",
    #     "-crf", "28",
    #     "-preset", "veryfast",
    #     "-an",
    #     "-loglevel", "error",
    #     output_path
    # ]
    
    # webm (vp9)
    cmd = [
        ffmpeg_exe, "-i", input_path,
        "-c:v", "libvpx-vp9",
        "-crf", "28",
        "-b:v", "0",
        "-cpu-used", "5",
        "-an",
        "-loglevel", "error",
        output_path
    ]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("コマンドがありません。: ffmpeg")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)


def convert_to_image(video_path, image_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(video_path):
        return

    if os.path.exists(image_path):
        return

    # gif
    # cmd = [
    #     ffmpeg_exe, "-i", video_path,
    #     "-filter_complex",
    #     "[0:v]fps=20,split[a][b];[a]palettegen[p];[b][p]paletteuse",
    #     "-loop", "0", 
    #     "-loglevel", "error",
    #     image_path,
    # ]

    # webp
    cmd = [
        ffmpeg_exe, "-i", video_path,
        "-vcodec", "libwebp",
        # "-filter:v", "fps=15,scale=384:-1",
        # "-filter:v", "fps=18,scale=384:-1,hqdn3d=3:3:6:6",
        "-filter:v", "fps=18,scale=384:-1",
        "-lossless", "0",
        "-compression_level", "6",
        "-preset", "1",
        "-quality", "70",
        "-loop", "0",
        "-loglevel", "error",
        image_path,
    ]

    try:
        subprocess.run(cmd)
    except FileNotFoundError:
        print("コマンドがありません。: ffmpeg")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)


def multi_run(func, args):
    cpu_count = multiprocessing.cpu_count()
    max_workers = max(1, min(cpu_count // 2, 4)) 

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            futures = []
            for arg in args:
                f = executor.submit(func, *arg)
                futures.append(f)

            for f in track(as_completed(futures), total=len(futures)):
                try:
                    f.result()
                except Exception as e:
                    print("エラーが発生しました。", e)
        except KeyboardInterrupt:
            print("終了しています...")
            executor.shutdown(wait=False, cancel_futures=True)
            sys.exit(1)


def make_media(notes):
    media_path = config["media_path"]
    os.makedirs(media_path, exist_ok=True)

    videos = []
    if config["should_download"]:
        print("動画をダウンロードしています...")
        for n in track(notes):
            video_path = f"{media_path}/{n["rawvideo_file"]}"
            download_video(n["video_url"], video_path)
            videos.append(video_path)

    if config["should_convert"] and config["format"] == "mp4":
        print("動画を圧縮しています...")
        mp4_videos = []
        args = []
        for n in track(notes):
            input_path = f"{media_path}/{n["rawvideo_file"]}"
            output_path = f"{media_path}/{n["mp4_file"]}"
            args.append((video_path))
            mp4_videos.append(video_path)

        multi_run(convert_to_mp4, args)
        return mp4_videos

    if config["should_convert"] and config["format"] == "webm":
        print("webmに変換しています...")
        webm_videos = []
        args = []
        for n in notes:
            input_path = f"{media_path}/{n["rawvideo_file"]}"
            output_path = f"{media_path}/{n["webm_file"]}"
            args.append((input_path, output_path))
            webm_videos.append(output_path)

        multi_run(convert_to_webm, args)
        return webm_videos

    if config["should_convert"] and config["format"] == "webp":
        print("webpに変換しています...")
        images = []
        args = []
        for n in notes:
            video_path = f"{media_path}/{n["rawvideo_file"]}"
            image_path = f"{media_path}/{n["image"]}"
            args.append((video_path, image_path))
            images.append(image_path)
            
        multi_run(convert_to_image, args)
        return images
    
    return videos

def load_templates(filenames):
    template_path = os.path.join(os.path.dirname(__file__), "templates")
    
    templates = {}
    for filename in filenames:
        filepath = os.path.join(template_path, filename)
        data = read(filepath)
        key = filename.split(".")[0]
        templates[key] = data

    return templates

def create_notes(signs: list) -> list[dict]:
    notes = []
    unique_id = ""
    # alphabet = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
    # unique_id = "_" + "".join(random.choice(alphabet) for _ in range(5))

    for sign in signs:
        note_id     = sign["id"]
        definition  = sign["signDefinitions"]["ja"][0]["def"]
        position    = sign["signDefinitions"]["ja"][0]["pos"]
        rawvideo    = f"{note_id}.raw.mp4"
        mp4_file    = f"{note_id}{unique_id}.mp4"
        webm_file   = f"{note_id}{unique_id}.webm"
        video_file  = rawvideo

        if config["should_convert"] and config["format"] == "mp4":
            video_file = mp4_file
        elif config["should_convert"] and config["format"] == "webm":
            video_file = webm_file

        # image_file  = f"{note_id}.gif"
        image_file  = f"{note_id}{unique_id}.webp"
        video_url   = sign["defaultVideoUrl"]
        page_url    = f"https://handbook.sign.town/ja/signs/{note_id}?sl=JSL"
        category    = sign["category"]
        # category_id    = sign["category_id"]

        notes.append({
            "id":  f"{note_id}{unique_id}",
            "def": definition,
            "pos": position,
            "rawvideo_file": rawvideo,
            "mp4_file": mp4_file,
            "webm_file": webm_file,
            "video": video_file,
            "video_tag": f"[sound:{video_file}]",
            "image": image_file,
            "image_tag": f"<img src=\"{image_file}\">",
            "video_url": video_url,
            "page_url": page_url,
            "category": category
        })
        
    return notes


def create_video_model() -> genanki.Model:
    filenames = [
        "style.css",
        "ja-jsl_video_front.template.anki",
        "ja-jsl_video_back.template.anki",
        "jsl-ja_video_front.template.anki",
        "jsl-ja_video_back.template.anki",
    ]
    template_files = load_templates(filenames)
    model_id = random.randrange(1 << 30, 1 << 31)
    templates = []

    if config["template"] in ["ja-jsl", "all"]:
        templates.append({
            "name": "JA->JSL",
            "qfmt": template_files["ja-jsl_video_front"],
            "afmt": template_files["ja-jsl_video_back"],
        })
    if config["template"] in ["jsl-ja", "all"]:
        templates.append({
            "name": "JSL->JA",
            "qfmt": template_files["jsl-ja_video_front"],
            "afmt": template_files["jsl-ja_video_back"],
        })
    model = genanki.Model(
        model_id,
        "JSL",
        fields=[
            {"name": "id"},
            {"name": "def"},
            {"name": "pos"},
            {"name": "video"},
            {"name": "video_tag"},
            {"name": "video_url"},
            {"name": "page_url"},
            {"name": "category"},
        ],
        templates=templates,
        css=template_files["style"],
    )
    return model

def create_image_model() -> genanki.Model:
    filenames = [
        "style.css",
        "ja-jsl_image_front.template.anki",
        "ja-jsl_image_back.template.anki",
        "jsl-ja_image_front.template.anki",
        "jsl-ja_image_back.template.anki",
    ]
    template_files = load_templates(filenames)
    model_id = random.randrange(1 << 30, 1 << 31)
    templates = []

    if config["template"] in ["ja-jsl", "all"]:
        templates.append({
            "name": "JA->JSL",
            "qfmt": template_files["ja-jsl_image_front"],
            "afmt": template_files["ja-jsl_image_back"],
        })
    if config["template"] in ["jsl-ja", "all"]:
        templates.append({
            "name": "JSL->JA",
            "qfmt": template_files["jsl-ja_image_front"],
            "afmt": template_files["jsl-ja_image_back"],
        })
    model = genanki.Model(
        model_id,
        "JSL",
        fields=[
            {"name": "id"},
            {"name": "def"},
            {"name": "pos"},
            {"name": "image_tag"},
            {"name": "video_url"},
            {"name": "page_url"},
            {"name": "category"},
        ],
        templates=templates,
        css=template_files["style"],
    )
    return model

def write_in_apkg(notes: list, media: list, cats: list):
    if config["format"] == "webp":
        model = create_image_model()
    else:
        model = create_video_model()

    decks = {}
    for cat in cats:
        category = cat["title"]
        deck_id = random.randrange(1 << 30, 1 << 31)
        deck = genanki.Deck(
            deck_id,
            f"手話タウンハンドブック::{category}"
        )
        decks[category] = deck

    keys = [f["name"] for f in model.fields]
    for n in notes:
        row = [n.get(key) for key in keys]
        note = genanki.Note(
            model=model,
            fields=row,
        )
        decks[n["category"]].add_note(note)

    package = genanki.Package(list(decks.values()))
    package.media_files = media

    apkg_path = f"手話タウンハンドブック.apkg"
    package.write_to_file(apkg_path)
    print("Ankiパッケージを作成しました。")


@click.command(help="handbook.sign.townをスクレイピングしてAnkiパッケージを作るコマンド")
@click.option("--no-download", is_flag=True,
    help="動画をDLしません")
@click.option("--no-conversion", is_flag=True,
    help="動画を変換しません")
@click.option("--format", "-f", default="webp",
    help="フォーマットを選択",
    show_default=True, show_choices=True,
    type=click.Choice(("mp4", "webm", "webp"), case_sensitive=False))
@click.option("--template", "-t", default="jsl-ja",
    help="テンプレートを選択",
    show_default=True, show_choices=True,
    type=click.Choice(("jsl-ja", "ja-jsl", "all"), case_sensitive=False))
def main(**kwargs):
    global config
    config["should_download"]   = not kwargs["no_download"]
    config["should_convert"] = not kwargs["no_conversion"]
    config["format"]            = kwargs["format"]
    config["template"]          = kwargs["template"]
    
    if not config["should_download"]:
        config["should_convert"] = False

    
    print("カテゴリ一覧を読み込んでいます...")
    cats = get_categories()
    print("各カテゴリの手話一覧を読み込んでいます...")
    signs = get_signs(cats)
    notes = create_notes(signs)
    media = make_media(notes)
    print("Ankiパッケージを生成しています...")
    write_in_apkg(notes, media, cats)

if __name__ == "__main__":
    main()
