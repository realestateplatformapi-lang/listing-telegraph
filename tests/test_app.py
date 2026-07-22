import json
import base64
import tempfile
import unittest
from io import BytesIO
from pathlib import Path
from unittest import mock

import app


class FakeResponse:
    def __init__(self, content=b"", payload=None, url="https://images.example/photo.jpg", content_type="image/jpeg", status_code=200):
        self.content = content
        self._payload = payload
        self.url = url
        self.status_code = status_code
        self.headers = {"Content-Type": content_type}

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class AppTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        root = Path(self.temp.name)
        self.originals = {
            "DATA_ROOT": app.DATA_ROOT,
            "PACKAGES_ROOT": app.PACKAGES_ROOT,
            "DB_PATH": app.DB_PATH,
            "LOGO_PATH": app.LOGO_PATH,
            "LOGO_URL": app.LOGO_URL,
            "AI_ENDPOINT": app.AI_ENDPOINT,
            "AI_PACKAGES_ROOT": app.AI_PACKAGES_ROOT,
            "AI_MODE": app.AI_MODE,
            "AI_TOKEN": app.AI_TOKEN,
            "SOURCE_LISTINGS_ROOT": app.SOURCE_LISTINGS_ROOT,
            "AI_REQUIRED": app.AI_REQUIRED,
            "MEDIA_GITHUB_REPO": app.MEDIA_GITHUB_REPO,
            "MEDIA_GITHUB_BRANCH": app.MEDIA_GITHUB_BRANCH,
            "GITHUB_TOKEN": app.GITHUB_TOKEN,
        }
        app.DATA_ROOT = root / "data"
        app.PACKAGES_ROOT = app.DATA_ROOT / "packages"
        app.DB_PATH = app.DATA_ROOT / "block3.sqlite3"
        app.LOGO_PATH = root / "logo.jpg"
        app.LOGO_PATH.write_bytes(b"logo" * 1024)
        app.LOGO_URL = ""
        app.AI_ENDPOINT = ""
        app.AI_MODE = "browser"
        app.AI_TOKEN = ""
        app.SOURCE_LISTINGS_ROOT = None
        app.AI_REQUIRED = False
        app.MEDIA_GITHUB_REPO = ""
        app.MEDIA_GITHUB_BRANCH = "media"
        app.GITHUB_TOKEN = ""
        app.init_storage()

    def tearDown(self):
        for name, value in self.originals.items():
            setattr(app, name, value)
        self.temp.cleanup()

    def payload(self):
        return {
            "internal_id": "203781",
            "source": "https://rieltor.ua/flats-sale/view/203781/",
            "translations": {
                "uk": {"title": "Квартира", "text": "Світла квартира з ремонтом."},
                "en": {"title": "Apartment", "text": "A bright renovated apartment."},
            },
            "details": {"area": "97", "floor": "7/18"},
            "prices": {"UAH": "4000000", "USD": "97000", "EUR": "89000"},
            "images": ["https://images.example/photo.jpg"],
        }

    def test_public_text_removes_source_and_agent_sentences(self):
        text = "Світла квартира. Телефонуйте рієлтору. Комісія 3%."
        self.assertEqual(app.sanitize_public_text(text), "Світла квартира.")

    def test_rieltor_gallery_rejects_icons_avatars_and_site_art(self):
        images = [
            "https://rieltor.ua/img/menu/icon_menu_flats.svg",
            "https://rieltor-images.lunstatic.net/rieltor-ua-01/120/120/avatars/1.jpg",
            "https://market-images.lunstatic.net/lun-ua/310/310/images/offers/preview.jpg",
            "https://market-images.lunstatic.net/lun-ua/t.1.0.0/1600/1200/images/offers/room.jpg",
            "https://rieltor.ua/img/mastercard.svg",
        ]
        self.assertEqual(
            app.listing_photo_urls(images, "https://rieltor.ua/flats-rent/view/12883087/"),
            [images[3]],
        )

    def test_title_rejects_rieltor_resource_tail(self):
        self.assertEqual(
            app.sanitize_title("Apartment - RIELTOR.UAResource 1Resource 1"),
            "Apartment",
        )

    @mock.patch.object(app, "safe_remote_url", return_value=True)
    @mock.patch.object(app.requests, "get")
    def test_package_persists_original_final_logo_and_manifest(self, get, _safe):
        get.return_value = FakeResponse(content=b"image" * 1024)
        result = app.create_package(self.payload())
        package = app.PACKAGES_ROOT / "203781"
        manifest = json.loads((package / "manifest.json").read_text(encoding="utf-8"))
        html = (package / "uk.html").read_text(encoding="utf-8")
        self.assertEqual(result["photo_count"], 1)
        self.assertEqual(result["processed"], ["/packages/203781/photos/01.jpg"])
        self.assertEqual(result["originals"], ["/packages/203781/originals/01.jpg"])
        self.assertTrue((app.DATA_ROOT / "listings/203781/original/01.jpg").is_file())
        self.assertTrue((app.DATA_ROOT / "listings/203781/final/01.jpg").is_file())
        self.assertTrue((package / "assets/kyiv-estate-logo.jpg").is_file())
        self.assertLess(html.index("photos/01.jpg"), html.index("assets/kyiv-estate-logo.jpg"))
        self.assertEqual(manifest["ai_processing"]["result"], "original_verified")

    @mock.patch.object(app, "safe_remote_url", return_value=True)
    @mock.patch.object(app.requests, "get")
    def test_package_keeps_user_photo_order(self, get, _safe):
        get.side_effect = [
            FakeResponse(content=b"first" * 1024, url="https://images.example/first.jpg"),
            FakeResponse(content=b"second" * 1024, url="https://images.example/second.jpg"),
        ]
        payload = self.payload()
        payload["images"] = ["https://images.example/first.jpg", "https://images.example/second.jpg"]
        payload["processing_mode"] = "browser"
        payload["media_choices"] = [{"order": 2, "kind": "processed"}, {"order": 1, "kind": "processed"}]
        app.create_package(payload)
        manifest = json.loads((app.PACKAGES_ROOT / "203781/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual([item["order"] for item in manifest["photos"]], [2, 1])

    def test_telegraph_content_places_logo_after_primary_photo(self):
        content = app.telegraph_content(
            self.payload(), "uk", "Опис квартири.",
            ["https://telegra.ph/file/main.jpg", "https://telegra.ph/file/second.jpg"],
            "https://telegra.ph/file/logo.jpg",
        )
        images = [node["attrs"]["src"] for node in content if node.get("tag") == "img"]
        self.assertEqual(images[:2], ["https://telegra.ph/file/main.jpg", "https://telegra.ph/file/logo.jpg"])

    @mock.patch.object(app, "github_media_images")
    def test_durable_media_preserves_photo_and_logo_order(self, upload):
        app.MEDIA_GITHUB_REPO = "realestateplatformapi-lang/listing-telegraph"
        app.GITHUB_TOKEN = "secret"
        photo = app.DATA_ROOT / "photo.jpg"
        logo = app.DATA_ROOT / "logo.jpg"
        photo.parent.mkdir(parents=True, exist_ok=True)
        photo.write_bytes(b"photo" * 1024)
        logo.write_bytes(b"logo" * 1024)
        upload.return_value = ["https://raw.example/photo.jpg", "https://raw.example/logo.jpg"]
        self.assertEqual(app.durable_image_urls([photo, logo], "203781"), upload.return_value)
        upload.assert_called_once_with([photo, logo], "203781")

    @mock.patch.object(app.requests, "post")
    def test_telegraph_upload_is_cached_by_hash(self, post):
        post.return_value = FakeResponse(payload=[{"src": "/file/stable.jpg"}])
        image = app.DATA_ROOT / "final.jpg"
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"stable" * 1024)
        first = app.telegraph_image(image)
        second = app.telegraph_image(image)
        self.assertEqual(first, "https://telegra.ph/file/stable.jpg")
        self.assertEqual(first, second)
        self.assertEqual(post.call_count, 1)

    @mock.patch.object(app, "edit_page")
    @mock.patch.object(app, "publish_page")
    @mock.patch.object(app, "telegraph_image")
    @mock.patch.object(app, "safe_remote_url", return_value=True)
    @mock.patch.object(app.requests, "get")
    def test_publish_saves_bilingual_urls_in_manifest(self, get, _safe, upload, publish, edit):
        get.return_value = FakeResponse(content=b"image" * 1024)
        upload.side_effect = lambda path: "https://telegra.ph/file/logo.jpg" if Path(path).name == "kyiv-estate-logo.jpg" else "https://telegra.ph/file/photo.jpg"
        publish.side_effect = ["https://telegra.ph/ua-page", "https://telegra.ph/en-page"]
        edit.side_effect = lambda page_url, _title, _content: page_url
        urls = app.publish_bilingual(self.payload())
        manifest = json.loads((app.PACKAGES_ROOT / "203781/manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(urls["uk"], "https://telegra.ph/ua-page")
        self.assertEqual(manifest["telegraph"]["en"], "https://telegra.ph/en-page")
        self.assertEqual(edit.call_count, 2)
        second = app.publish_bilingual(self.payload())
        self.assertEqual(second, urls)
        self.assertEqual(publish.call_count, 2)
        self.assertEqual(edit.call_count, 4)

    @mock.patch.object(app.requests, "get")
    @mock.patch.object(app.requests, "post")
    def test_windows_ai_lane_returns_only_certified_package_photos(self, post, get):
        ai_root = Path(self.temp.name) / "ai-packages"
        photos = ai_root / "A203781" / "photos"
        photos.mkdir(parents=True)
        (photos / "01.jpg").write_bytes(b"clean")
        app.AI_ENDPOINT = "http://127.0.0.1:8793"
        app.AI_PACKAGES_ROOT = ai_root
        post.return_value = FakeResponse(payload={"job_id": "a" * 32})
        get.return_value = FakeResponse(payload={"job_id": "a" * 32, "status": "ready", "internal_id": "A203781"})
        result = app.ai_package_photos(self.payload())
        self.assertEqual(result, [photos / "01.jpg"])
        self.assertEqual(post.call_args.kwargs["json"]["value"], "203781")

    @mock.patch.object(app.requests, "get")
    def test_remote_ai_package_downloads_certified_photos(self, get):
        app.AI_ENDPOINT = "https://windows-ai.example"
        get.side_effect = [
            FakeResponse(content=b"clean" * 1024, content_type="image/jpeg"),
            FakeResponse(content=b"clean2" * 1024, content_type="image/jpeg"),
        ]
        photos = app.download_remote_ai_photos("203781", 2, {"X-Block3-Token": "secret"})
        self.assertEqual([path.name for path in photos], ["01.jpg", "02.jpg"])
        self.assertTrue(all(path.is_file() for path in photos))
        self.assertEqual(get.call_args_list[0].kwargs["headers"]["X-Block3-Token"], "secret")

    @mock.patch.object(app, "ai_package_photos")
    @mock.patch.object(app.requests, "get")
    def test_expired_cdn_uses_preserved_block2_originals(self, get, ai_photos):
        get.side_effect = app.requests.RequestException("expired")
        source_root = Path(self.temp.name) / "block2-listings"
        preserved = source_root / "olx" / "203781" / "original"
        preserved.mkdir(parents=True)
        (preserved / "01.jpg").write_bytes(b"preserved-original")
        clean = Path(self.temp.name) / "certified" / "01.jpg"
        clean.parent.mkdir(parents=True)
        clean.write_bytes(b"certified-final")
        app.SOURCE_LISTINGS_ROOT = source_root
        app.AI_ENDPOINT = "http://127.0.0.1:8793"
        ai_photos.return_value = [clean]
        result = app.save_approved_photos("203781", self.payload()["images"], self.payload())
        original = Path(result[0]["original_path"])
        self.assertEqual(original.read_bytes(), b"preserved-original")
        self.assertEqual(Path(result[0]["final_path"]).read_bytes(), b"certified-final")

    @mock.patch.object(app.time, "sleep")
    @mock.patch.object(app.requests, "get")
    @mock.patch.object(app.requests, "post")
    def test_windows_ai_poll_tolerates_busy_worker_timeout(self, post, get, _sleep):
        ai_root = Path(self.temp.name) / "ai-packages"
        photos = ai_root / "A203781" / "photos"
        photos.mkdir(parents=True)
        (photos / "01.jpg").write_bytes(b"clean")
        app.AI_ENDPOINT = "http://127.0.0.1:8793"
        app.AI_PACKAGES_ROOT = ai_root
        post.return_value = FakeResponse(payload={"job_id": "a" * 32})
        get.side_effect = [app.requests.RequestException("busy"), FakeResponse(payload={"status": "ready", "internal_id": "A203781"})]
        self.assertEqual(app.ai_package_photos(self.payload()), [photos / "01.jpg"])

    @mock.patch.object(app.requests, "get")
    @mock.patch.object(app.requests, "post")
    def test_windows_ai_reuses_last_certified_package_after_retry_failure(self, post, get):
        ai_root = Path(self.temp.name) / "ai-packages"
        photos = ai_root / "B95B6E5C759" / "photos"
        photos.mkdir(parents=True)
        (photos / "01.jpg").write_bytes(b"certified")
        app.AI_ENDPOINT = "http://127.0.0.1:8793"
        app.AI_PACKAGES_ROOT = ai_root
        post.return_value = FakeResponse(payload={"job_id": "b" * 32})
        get.return_value = FakeResponse(payload={"status": "failed", "internal_id": "B95B6E5C759", "error": "two source files failed"})
        self.assertEqual(app.ai_package_photos(self.payload()), [photos / "01.jpg"])

    def test_wsgi_health_and_existing_interface(self):
        captured = {}

        def start_response(status, headers):
            captured["status"] = status
            captured["headers"] = dict(headers)

        health = b"".join(app.app({"PATH_INFO": "/health", "REQUEST_METHOD": "GET", "wsgi.input": BytesIO()}, start_response))
        self.assertEqual(captured["status"], "200 OK")
        self.assertTrue(json.loads(health)["ok"])
        page = b"".join(app.app({"PATH_INFO": "/", "REQUEST_METHOD": "GET", "wsgi.input": BytesIO()}, start_response))
        self.assertEqual(captured["status"], "200 OK")
        self.assertIn(b"KYIV ESTATE", page)
        self.assertNotIn(b"Fast import with source photos", page)
        self.assertNotIn(b"Removes people, agency images and watermarks", page)

    def test_pdf_places_logo_after_first_property_photo(self):
        pixel = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=")
        photo_root = app.PACKAGES_ROOT / "203781" / "photos"
        photo_root.mkdir(parents=True)
        first, second = photo_root / "01.png", photo_root / "02.png"
        first.write_bytes(pixel)
        second.write_bytes(pixel)
        app.LOGO_PATH.write_bytes(pixel)
        payload = self.payload()
        payload.update({"processing_mode": "ai", "language": "en", "title": "Apartment", "text": "Description"})
        with mock.patch("reportlab.platypus.SimpleDocTemplate") as document, mock.patch("reportlab.platypus.Image") as image:
            document.return_value.build.return_value = None
            app.make_pdf(payload)
        sources = [str(call.args[0]) for call in image.call_args_list]
        self.assertEqual(sources[:3], [str(first), str(app.DATA_ROOT / "assets" / "kyiv-estate-logo.jpg"), str(second)])


if __name__ == "__main__":
    unittest.main()
