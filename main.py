from kivymd.app import MDApp
from kivymd.uix.screen import MDScreen
from kivymd.uix.datatables import MDDataTable
from kivymd.uix.button import MDRaisedButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.dialog import MDDialog
from kivy.metrics import dp
import requests, re, json
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher
from android import mActivity
from jnius import autoclass

Intent = autoclass('android.content.Intent')
Uri = autoclass('android.net.Uri')

class MainScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.channels = []
        self.favorites = self.load_fav()

    def load_fav(self):
        try:
            with open('favorites.json', encoding='utf-8') as f:
                return json.load(f)
        except:
            return []

    def save_fav(self):
        with open('favorites.json', 'w', encoding='utf-8') as f:
            json.dump(self.favorites, f)

    def load_playlist(self):
        url = self.ids.url_field.text.strip()
        if not url:
            self.show_dialog("Введи URL плейлиста!")
            return
        try:
            r = requests.get(url, timeout=20)
            r.raise_for_status()
            self.parse_m3u(r.text)
            self.update_table()
            self.show_dialog(f"✅ Загружено {len(self.channels)} каналов!")
        except Exception as e:
            self.show_dialog(f"❌ Ошибка: {str(e)}")

    def parse_m3u(self, text):
        self.channels.clear()
        lines = text.splitlines()
        i = 0
        while i < len(lines):
            if lines[i].startswith('#EXTINF:'):
                inf = lines[i][8:]
                name = re.search(r',(.+)', inf)
                name = name.group(1).strip() if name else 'Unknown'
                group = re.search(r'group-title="([^"]+)"', inf)
                group = group.group(1) if group else 'Без группы'
                url = lines[i+1].strip() if i+1 < len(lines) and not lines[i+1].startswith('#') else ''
                if url:
                    self.channels.append({'name': name, 'group': group, 'url': url})
                i += 1
            i += 1

    def update_table(self):
        data = [(ch['name'][:45], ch['group'][:30]) for ch in self.channels[:200]]
        self.ids.table.row_data = data

    def ai_clean(self):
        self.show_dialog("🚀 ИИ-очистка запущена... подожди 30-60 сек")
        seen = {ch['url']: ch for ch in self.channels}
        self.channels = list(seen.values())
        unique = []
        for ch in self.channels:
            if not any(SequenceMatcher(None, ch['name'].lower(), u['name'].lower()).ratio() > 0.85 for u in unique):
                unique.append(ch)
        self.channels = unique

        def is_live(url):
            try:
                return requests.head(url, timeout=5, allow_redirects=True).status_code < 400
            except:
                return False

        with ThreadPoolExecutor(max_workers=25) as ex:
            live = [ch for ch, ok in zip(self.channels, ex.map(is_live, [c['url'] for c in self.channels])) if ok]
        self.channels = live
        self.update_table()
        self.show_dialog(f"🎉 ИИ готов! Осталось {len(self.channels)} живых каналов")

    def play_channel(self, instance_table, row):
        idx = row
        if idx < len(self.channels):
            url = self.channels[idx]['url']
            intent = Intent(Intent.ACTION_VIEW)
            intent.setDataAndType(Uri.parse(url), "video/*")
            mActivity.startActivity(Intent.createChooser(intent, "Открыть в плеере"))

    def show_dialog(self, text):
        MDDialog(text=text, size_hint=(0.85, None)).open()

class ForgeApp(MDApp):
    def build(self):
        self.theme_cls.theme_style = "Dark"
        self.theme_cls.primary_palette = "Blue"
        return MainScreen()

if __name__ == '__main__':
    ForgeApp().run()
