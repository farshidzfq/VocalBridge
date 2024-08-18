import kivy
kivy.require('2.0.0')
from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.scrollview import ScrollView
from kivy.uix.textinput import TextInput
from kivy.core.text import LabelBase
from kivy.lang import Builder
from kivy.clock import Clock
import speech_recognition as sr
from googletrans import Translator
import arabic_reshaper
from bidi.algorithm import get_display
import json
import os

# Register custom fonts
LabelBase.register(name='BNazanin', fn_regular='B Nazanin.ttf')
LabelBase.register(name='TimesNewRoman', fn_regular='Times New Roman.ttf')

Builder.load_string("""
<MainWidget>:
    orientation: 'vertical'
    padding: 20
    spacing: 20
    canvas.before:
        Color:
            rgba: 0.9, 0.9, 0.9, 1
        Rectangle:
            pos: self.pos
            size: self.size
    Label:
        id: status
        text: 'Press the button and start speaking'
        font_name: 'TimesNewRoman'
        font_size: '24sp'
        color: 0, 0, 0, 1
        size_hint_y: None
        height: self.texture_size[1]
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '200dp'
        padding: 10
        spacing: 10
        canvas.before:
            Color:
                rgba: 0.8, 0.8, 0.8, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: 'Source Text'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            color: 0, 0, 0, 1
            size_hint_y: None
            height: self.texture_size[1]
        ScrollView:
            size_hint_y: None
            height: '100dp'
            Label:
                id: source
                text: ''
                font_name: 'TimesNewRoman'
                font_size: '24sp'
                color: 0, 0, 0, 1
                halign: 'center'
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '200dp'
        padding: 10
        spacing: 10
        canvas.before:
            Color:
                rgba: 0.8, 0.8, 0.8, 1
            Rectangle:
                pos: self.pos
                size: self.size
        Label:
            text: 'Translated Text'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            color: 0, 0, 0, 1
            size_hint_y: None
            height: self.texture_size[1]
        ScrollView:
            size_hint_y: None
            height: '100dp'
            Label:
                id: result
                text: ''
                font_name: 'BNazanin'
                font_size: '24sp'
                color: 0, 0, 0, 1
                halign: 'center'
                size_hint_y: None
                height: self.texture_size[1]
                text_size: self.width, None
    BoxLayout:
        size_hint_y: None
        height: '50dp'
        spacing: 10
        Button:
            text: 'Load History'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            background_color: 0.2, 0.6, 0.8, 1
            color: 1, 1, 1, 1
            on_press: root.load_history()
        Button:
            text: 'Start Listening'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            background_color: 0.2, 0.6, 0.8, 1
            color: 1, 1, 1, 1
            on_press: root.start_listening()
        Button:
            text: 'Save History'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            background_color: 0.2, 0.6, 0.8, 1
            color: 1, 1, 1, 1
            on_press: root.save_history()
    BoxLayout:
        orientation: 'vertical'
        size_hint_y: None
        height: '100dp'
        padding: 10
        spacing: 10
        Label:
            text: 'Manual Input'
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            color: 0, 0, 0, 1
            size_hint_y: None
            height: self.texture_size[1]
        TextInput:
            id: manual_input
            font_name: 'TimesNewRoman'
            font_size: '24sp'
            height: '50dp'
            multiline: False
            on_text_validate: root.translate_manual_text(self.text)
""")

class MainWidget(BoxLayout):
    def __init__(self, **kwargs):
        super(MainWidget, self).__init__(**kwargs)
        self.recognizer = sr.Recognizer()
        self.translator = Translator()
        self.listening = False
        self.history = []
        self.temp_audio_file = "temp_audio.wav"

    def start_listening(self):
        if not self.listening:
            self.ids.status.text = "Listening..."
            self.ids.status.color = (1, 0, 0, 1)  # Red color for listening state
            self.listening = True
            Clock.schedule_once(self.listen, 0)

    def listen(self, dt):
        if self.listening:
            with sr.Microphone() as source:
                try:
                    audio = self.recognizer.listen(source, timeout=5)
                    self.save_audio_file(audio)
                    text = self.recognizer.recognize_google(audio)
                    self.ids.source.text = text
                    self.ids.source.height = self.ids.source.texture_size[1]
                    self.ids.status.text = "Recognized Text: " + text
                    self.ids.status.color = (0, 1, 0, 1)  # Green color for successful recognition
                    translation = self.translate_text(text)
                    self.update_translation(translation)
                    self.history.append((text, translation))
                except sr.UnknownValueError:
                    self.show_error("Google Speech Recognition could not understand audio")
                except sr.RequestError as e:
                    self.show_error(f"Request error from Google Speech Recognition service; {e}")
                except sr.WaitTimeoutError:
                    self.show_error("Listening timed out while waiting for phrase to start")
                except Exception as e:
                    self.show_error(f"An error occurred during listening: {e}")
                finally:
                    self.cleanup_audio_file()

    def show_error(self, message):
        self.ids.status.text = message
        self.ids.status.color = (1, 0, 0, 1)  # Red color for error

    def save_audio_file(self, audio):
        try:
            with open(self.temp_audio_file, "wb") as f:
                f.write(audio.get_wav_data())
        except Exception as e:
            self.show_error(f"Failed to save audio file: {e}")

    def cleanup_audio_file(self):
        try:
            if os.path.exists(self.temp_audio_file):
                os.remove(self.temp_audio_file)
        except Exception as e:
            self.show_error(f"Failed to clean up audio file: {e}")

    def translate_text(self, text):
        try:
            translation = self.translator.translate(text, dest='fa').text
            reshaped_text = arabic_reshaper.reshape(translation)
            bidi_text = get_display(reshaped_text)
            return bidi_text
        except Exception as e:
            self.show_error(f"Translation error: {e}")
            return ""

    def update_translation(self, translation):
        self.ids.result.text = translation
        self.ids.result.height = self.ids.result.texture_size[1]

    def translate_manual_text(self, text):
        translation = self.translate_text(text)
        self.ids.source.text = text
        self.update_translation(translation)
        self.history.append((text, translation))

    def save_history(self):
        try:
            with open('translation_history.json', 'w') as f:
                json.dump(self.history, f)
            self.ids.status.text = "History saved successfully"
            self.ids.status.color = (0, 1, 0, 1)  # Green color for success
        except Exception as e:
            self.show_error(f"Error saving history: {e}")

    def load_history(self):
        try:
            with open('translation_history.json', 'r') as f:
                self.history = json.load(f)
            self.ids.status.text = "History loaded successfully"
            self.ids.status.color = (0, 1, 0, 1)  # Green color for success
            if self.history:
                last_entry = self.history[-1]
                self.ids.source.text = last_entry[0]
                self.update_translation(last_entry[1])
        except json.JSONDecodeError:
            self.show_error("Error decoding history file. It may be corrupted.")
        except FileNotFoundError:
            self.show_error("History file not found.")
        except Exception as e:
            self.show_error(f"Error loading history: {e}")

class VoiceTranslationApp(App):
    def build(self):
        return MainWidget()

if __name__ == '__main__':
    VoiceTranslationApp().run()
