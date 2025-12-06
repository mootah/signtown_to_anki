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
    "format": "avif",
    "template": "jsl-ja",
    "template_data": {}
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
    for cat in track(cats, description=""):
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

    fragment_path = f"{video_path}.part"

    try:
        with open(fragment_path, "wb") as f:
            curl = pycurl.Curl()
            curl.setopt(curl.URL, url)
            curl.setopt(curl.WRITEDATA, f)
            curl.perform()
            curl.close()
    except pycurl.error as e:
        try:
            media_path = config["media_path"]
            fragments = [f for f in os.listdir(media_path) if f.endswith(".part")]
            for f in fragments:
                os.remove(os.path.join(media_path, f))
        except:
            pass

        code, _ = e.args
        if code == 23:
            raise(KeyboardInterrupt)
        raise(e)
    
    os.rename(fragment_path, video_path)


def convert_to_mp4(input_path, output_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(input_path):
        return

    if os.path.exists(output_path):
        return

    cmd = [
        ffmpeg_exe, "-i", input_path,
        "-vcodec", "libx264",
        "-crf", "28",
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


def convert_to_webp(video_path, image_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(video_path):
        return

    if os.path.exists(image_path):
        return

    cmd = [
        ffmpeg_exe, "-i", video_path,
        "-vcodec", "libwebp",
        "-filter:v", "fps=18,scale=384:-1",
        "-lossless", "0",
        "-compression_level", "6",
        "-preset", "1",
        "-quality", "80",
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


def convert_to_avif(video_path, image_path):
    ffmpeg_exe = get_ffmpeg_exe()

    if not os.path.exists(video_path):
        return

    if os.path.exists(image_path):
        return

    cmd = [
        ffmpeg_exe, "-i", video_path,
        "-filter:v", "fps=25,scale=420:-1",
        "-c:v", "libsvtav1",
        "-pix_fmt", "yuv420p",
        "-crf", "28",
        "-preset", "4",
        "-an",
        "-loglevel", "error",
        image_path,
    ]

    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        print("コマンドがありません。: ffmpeg")
        sys.exit(1)
    except Exception as e:
        print(e)
        sys.exit(1)


def multi_run(func, args):
    cpu_count = multiprocessing.cpu_count()
    max_workers = max(1, min(cpu_count // 2, 8)) 

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        try:
            futures = []
            for arg in args:
                f = executor.submit(func, *arg)
                futures.append(f)

            for f in track(as_completed(futures), total=len(futures), description=""):
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
    videos = []

    if not config["should_download"]:
        return videos

    print("動画をダウンロードしています...")
    try:
        for n in track(notes, description=""):
            video_path = f"{media_path}/{n["original_video_file"]}"
            download_video(n["video_url"], video_path)
            videos.append(video_path)
    except KeyboardInterrupt:
        print("ダウンロードを中断しました。")
        sys.exit(1)
    except Exception as e:
        print(f"ダウンロードできませんでした。: {e}")
        sys.exit(1)

    output_media = []

    if config["should_convert"] and config["format"] == "mp4":
        print("動画を圧縮しています...")
        args = []
        for n in note:
            input_path = f"{media_path}/{n["original_video_file"]}"
            output_path = f"{media_path}/{n["video"]}"
            args.append((input_path, output_path))
            output_media.append(output_path)

        multi_run(convert_to_mp4, args)

    elif config["should_convert"]:
        print(f"{config["format"]}に変換しています...")
        args = []
        for n in notes:
            input_path = f"{media_path}/{n["original_video_file"]}"
            output_path = f"{media_path}/{n["media_file"]}"
            args.append((input_path, output_path))
            output_media.append(output_path)

        if config["format"] == "webm":
            multi_run(convert_to_webm, args)
        elif config["format"] == "webp":
            multi_run(convert_to_webp, args)
        elif config["format"] == "avif":
            multi_run(convert_to_avif, args)

    return output_media


def load_templates():
    if config["template_data"]:
        return config["template_data"]

    template_path = os.path.join(os.path.dirname(__file__), "templates")
    try:
        all_files = os.listdir(template_path)
    except Exception:
        print("テンプレートが見つかりませんでした:", template_path)
        sys.exit(1)

    filenames = [
        f for f in all_files
            if os.path.isfile(os.path.join(template_path, f))
    ]

    for filename in filenames:
        filepath = os.path.join(template_path, filename)
        data = read(filepath)
        key = filename.split(".")[0]
        config["template_data"][key] = data

    return config["template_data"]

def create_notes(signs: list) -> list[dict]:
    notes = []
    ext = config["format"]

    for sign in signs:
        note_id        = sign["id"]
        definition     = sign["signDefinitions"]["ja"][0]["def"]
        # position       = sign["signDefinitions"]["ja"][0]["pos"]
        original_video = f"{note_id}.raw.mp4"
        media_file  = f"{note_id}.{ext}"
        video_url   = sign["defaultVideoUrl"]
        page_url    = f"https://handbook.sign.town/ja/signs/{note_id}?sl=JSL"
        category    = sign["category"]
        # category_id    = sign["category_id"]
        
        if not config["should_download"]:
            media_file = ""
        elif not config["should_convert"]:
            media_file = original_video

        notes.append({
            "id":  f"{note_id}",
            "def": definition,
            "original_video_file": original_video,
            "media_file": media_file,
            "video": media_file,
            "video_tag": f"[sound:{media_file}]",
            "image": media_file,
            "image_tag": f"<img src=\"{media_file}\">",
            "video_url": video_url,
            "page_url": page_url,
            "category": category
        })
        
    return notes


def create_video_model() -> genanki.Model:
    template_files = load_templates()
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
            {"name": "video"},
            {"name": "video_tag"},
            {"name": "video_url"},
            {"name": "page_url"},
        ],
        templates=templates,
        css=template_files["style"],
    )
    return model

def create_image_model() -> genanki.Model:
    template_files = load_templates()
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
            {"name": "image_tag"},
            {"name": "video_url"},
            {"name": "page_url"},
        ],
        templates=templates,
        css=template_files["style"],
    )
    return model

def write_in_apkg(notes: list, media: list, cats: list):
    if config["format"] in ["webp", "avif"]:
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
@click.option("--format", "-f", default="avif",
    help="フォーマットを選択",
    show_default=True, show_choices=True,
    type=click.Choice(("mp4", "webm", "webp", "avif"), case_sensitive=False))
@click.option("--template", "-t", default="jsl-ja",
    help="テンプレートを選択",
    show_default=True, show_choices=True,
    type=click.Choice(("jsl-ja", "ja-jsl", "all"), case_sensitive=False))
def main(**kwargs):
    global config
    config["should_download"]   = not kwargs["no_download"]
    config["should_convert"]    = not kwargs["no_conversion"]
    config["format"]            = kwargs["format"]
    config["template"]          = kwargs["template"]
    
    if not config["should_download"]:
        config["should_convert"] = False
    if not config["should_convert"]:
        config["format"] = "mp4"

    media_path = config["media_path"]
    os.makedirs(media_path, exist_ok=True)

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

