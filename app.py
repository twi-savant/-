import os
import json
import time
import streamlit as st
import speech_recognition as sr
from dotenv import load_dotenv
from google import genai
from google.genai import types

# 1. ページ初期設定
st.set_page_config(
    page_title="2言語同時翻訳 & カタカナ発音",
    page_icon="🔤",
    layout="centered"
)

# 2. セッション状態の初期化
if "translation_count" not in st.session_state:
    st.session_state.translation_count = 0
if "history" not in st.session_state:
    st.session_state.history = []

# 3. 環境変数の読み込みとGeminiクライアントの初期化
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")

if not api_key:
    st.error("エラー: GEMINI_API_KEY が設定されていません。")
    st.stop()

client = genai.Client(api_key=api_key)

def process_translation(text: str):
    prompt = f"""
    以下の入力文を翻訳し、指定されたJSONフォーマットのみで出力してください。

    入力文: "{text}"

    【出力フォーマット】
    {{
        "english": "英語翻訳文",
        "phonetic_katakana": "英語の発音に近いカタカナ表記（例: ウェア イズ ザ ステーション）",
        "japanese": "日本語翻訳文"
    }}
    """
    try:
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json"
            )
        )
        st.session_state.translation_count += 1
        return json.loads(response.text)
    except Exception as e:
        st.error(f"APIエラーが発生しました: {e}")
        return None

def add_to_history(item):
    st.session_state.history.insert(0, item)
    if len(st.session_state.history) > 20:
        st.session_state.history.pop()

# --- カスタムCSS（ボタン拡大 & グレー文字用スタイル） ---
st.markdown("""
    <style>
    /* 音声録音UIの拡大 */
    div[data-testid="stAudioInput"] {
        transform: scale(1.3);
        transform-origin: top left;
        margin-bottom: 25px;
    }
    /* ボタンの大型化 */
    .stButton > button {
        font-size: 22px !important;
        padding: 18px 36px !important;
        height: auto !important;
        font-weight: bold !important;
        border-radius: 12px !important;
    }
    /* マイク認識音声の薄いグレー表示スタイル */
    .recognized-speech-gray {
        color: #7f8c8d !important;
        font-size: 16px;
        font-style: italic;
        background-color: #f8f9fa;
        padding: 10px 14px;
        border-radius: 8px;
        border-left: 4px solid #bdc3c7;
        margin: 10px 0 20px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- UI画面の構築 ---
st.title("🔤 2言語同時翻訳 ＆ カタカナ発音")
st.caption("EVEN G2 搭載を見据えたリアルタイム翻訳プロトタイプ")

mic_list = ["📱 スマホ標準マイク", "👓 EVEN G2 グラスマイク", "🎧 外部無線集音マイク"]
selected_mic = st.selectbox("🎙️ 使用マイクを選択:", mic_list)

st.markdown("---")

input_mode = st.radio("入力方法を選択:", ("🎤 マイク音声入力", "⌨️ テキスト手入力"), horizontal=True)

if input_mode == "🎤 マイク音声入力":
    col1, col2 = st.columns([2, 1])
    
    with col1:
        st.write(f"**使用マイク:** {selected_mic}")
        st.write("👇 **タップして録音開始**")
        audio_value = st.audio_input("マイク録音")
        
        if audio_value:
            recognizer = sr.Recognizer()
            try:
                with sr.AudioFile(audio_value) as source:
                    audio_data = recognizer.record(source)
                    recognized_text = recognizer.recognize_google(audio_data, language="ja-JP")
                    
                    # 💡 【追加機能】マイクが認識した音声を「薄いグレーの文字」で画面表示
                    st.markdown(
                        f'<div class="recognized-speech-gray">🎙️ <b>マイク認識音声:</b> 「{recognized_text}」</div>', 
                        unsafe_allow_html=True
                    )
                    
                    with st.spinner("Geminiで翻訳中..."):
                        translation = process_translation(recognized_text)
                        if translation:
                            add_to_history({
                                "type": "single",
                                "time": time.strftime("%H:%M:%S"),
                                "data": translation
                            })
            except sr.UnknownValueError:
                st.error("音声を読み取れませんでした。もう一度お話しください。")
            except Exception as e:
                st.error(f"音声認識エラー: {e}")

    with col2:
        st.metric(label="現在の実行回数", value=f"{st.session_state.translation_count} 回")
        st.caption("※無料枠目安: 15回/分, 1500回/日")

else:
    target_text = st.text_input("翻訳したい日本語を入力:", placeholder="例: 一番近い駅はどこですか？")
    col1, col2 = st.columns([2, 1])
    with col1:
        if st.button("翻訳を実行", type="primary", use_container_width=True):
            if target_text:
                translation = process_translation(target_text)
                if translation:
                    add_to_history({
                        "type": "single",
                        "time": time.strftime("%H:%M:%S"),
                        "data": translation
                    })
    with col2:
        st.metric(label="現在の実行回数", value=f"{st.session_state.translation_count} 回")

# 最新翻訳結果の表示
if st.session_state.history:
    latest = st.session_state.history[0]
    st.subheader("🖥️ 表示イメージ（EVEN G2 上下画面想定）")
    t = latest["data"]
    st.info(f"**[上段 ➔ EN]**\n### {t.get('english')}\n*{t.get('phonetic_katakana')}*")
    st.success(f"**[下段 ➔ JP]**\n### {t.get('japanese')}")

st.markdown("---")

# 履歴機能
st.subheader("📜 翻訳履歴（直近20件）")
if not st.session_state.history:
    st.caption("まだ履歴はありません。")
else:
    for item in st.session_state.history:
        data = item["data"]
        st.text(f"⏱️ [{item['time']}] {data.get('japanese')} ➔ {data.get('english')}")