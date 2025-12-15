import streamlit as st
import google.generativeai as genai
import datetime
import os
import json
import requests
import time
import hmac
import hashlib
import uuid
import qrcode
import io
from PIL import Image
from audio_recorder_streamlit import audio_recorder
import speech_recognition as sr

# [NEW] PDF 만드는 도구들
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader

# ==========================================
# 🔑 사장님의 비밀 열쇠
# ==========================================
GOOGLE_API_KEY = "AIzaSyDWPo6d9e2YsvHhKGs1vO-LYx1yatoFsmo"
SOLAPI_API_KEY = "NCSR1SXBMOH13MYO"
SOLAPI_API_SECRET = "S8T5X4B5PBFLDUDIAUB1ZOHLB8SIRQIY"
SENDER_PHONE = "01023847447"
# ==========================================

# 1. AI 연결
genai.configure(api_key=GOOGLE_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# 2. 이미지 폴더 확인
IMG_DIR = "images"
if not os.path.exists(IMG_DIR):
    os.makedirs(IMG_DIR)

# 3. 음성 인식 함수
def transcribe_audio(audio_bytes):
    """음성을 텍스트로 변환"""
    try:
        recognizer = sr.Recognizer()
        # 오디오 바이트를 파일로 저장 후 인식
        audio_file = io.BytesIO(audio_bytes)
        with sr.AudioFile(audio_file) as source:
            audio_data = recognizer.record(source)
        # Google Speech Recognition (무료, 한국어)
        text = recognizer.recognize_google(audio_data, language="ko-KR")
        return text
    except sr.UnknownValueError:
        return None  # 음성 인식 실패
    except sr.RequestError:
        return None  # API 요청 실패
    except Exception:
        # WAV 형식이 아닐 경우 대체 처리
        try:
            import tempfile
            recognizer = sr.Recognizer()
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
                tmp.write(audio_bytes)
                tmp_path = tmp.name
            
            with sr.AudioFile(tmp_path) as source:
                audio_data = recognizer.record(source)
            
            os.unlink(tmp_path)  # 임시 파일 삭제
            text = recognizer.recognize_google(audio_data, language="ko-KR")
            return text
        except:
            return None

# 4. 문자 발송 함수
def send_sms(to_phone, message):
    try:
        date = datetime.datetime.now().astimezone().isoformat()
        salt = str(uuid.uuid4().hex)
        data = date + salt
        signature = hmac.new(
            SOLAPI_API_SECRET.encode("utf-8"), data.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        header = f"HMAC-SHA256 apiKey={SOLAPI_API_KEY}, date={date}, salt={salt}, signature={signature}"
        url = "https://api.solapi.com/messages/v4/send"
        headers = {"Authorization": header, "Content-Type": "application/json"}
        payload = {"message": {"to": to_phone, "from": SENDER_PHONE, "text": message}}
        requests.post(url, headers=headers, json=payload)
        return True
    except:
        return False

# 5. 장부 관리
DB_FILE = 'stores.json'
if not os.path.exists(DB_FILE):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump({}, f)

def load_database():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_database(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

DATABASE = load_database()

# [NEW] A4용지 PDF 생성 함수 (3열 x 4행 = 12개)
def create_a4_pdf(qr_img_byte, store_name):
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    
    qr_size = 50 * mm
    margin_x = 15 * mm
    margin_y = 20 * mm
    gap_x = 10 * mm
    gap_y = 15 * mm
    
    rows = 4
    cols = 3
    
    image_reader = ImageReader(io.BytesIO(qr_img_byte.getvalue()))

    for r in range(rows):
        for col in range(cols):
            x = margin_x + (col * (qr_size + gap_x))
            y = height - margin_y - ((r + 1) * (qr_size + gap_y))
            c.drawImage(image_reader, x, y, width=qr_size, height=qr_size)
            c.setFont("Helvetica", 10)
            c.drawString(x, y - 5*mm, f"{store_name} - Scan Me")
            
    c.save()
    buffer.seek(0)
    return buffer

# ==========================================
# 📱 화면 시작
# ==========================================
st.set_page_config(page_title="우리동네 맛집", page_icon="🍱", layout="wide")

with st.sidebar:
    st.title("🍱 배달 플랫폼")
    menu = st.radio("메뉴 선택", ["🏠 매장 입장", "📝 가게 등록"])

# ------------------------------------------------
# 📝 가게 등록 + QR코드 생성
# ------------------------------------------------
if menu == "📝 가게 등록":
    st.header("📝 사장님 전용 페이지")
    
    tab1, tab2 = st.tabs(["📝 가게 등록", "🖨️ QR코드 인쇄"])

    with tab1:
        with st.form("reg_form"):
            c1, c2 = st.columns(2)
            with c1:
                in_id = st.text_input("아이디 (영어)", placeholder="meat")
                in_pw = st.text_input("비밀번호", type="password", placeholder="****")
                in_name = st.text_input("가게 이름 (영어 권장)", placeholder="Meat Shop") 
            with c2:
                in_pw_confirm = st.text_input("비밀번호 확인", type="password", placeholder="****")
                in_phone = st.text_input("사장님 휴대폰", placeholder="01012345678")
            
            uploaded_files = st.file_uploader("매장 사진", accept_multiple_files=True)
            in_info = st.text_input("영업 정보", placeholder="연중무휴 / 10:00 ~ 22:00")
            in_menu = st.text_area("메뉴 목록", placeholder="갈비살 - 34000원", height=150)
            
            if st.form_submit_button("가게 등록하기"):
                if not in_id or not in_pw:
                    st.error("❌ 아이디와 비밀번호를 입력해주세요!")
                elif in_pw != in_pw_confirm:
                    st.error("❌ 비밀번호가 일치하지 않습니다!")
                elif len(in_pw) < 4:
                    st.error("❌ 비밀번호는 4자리 이상이어야 합니다!")
                elif in_id in DATABASE:
                    st.error("❌ 이미 사용 중인 아이디입니다!")
                else:
                    saved_filenames = []
                    if uploaded_files:
                        for uploaded_file in uploaded_files:
                            file_path = os.path.join(IMG_DIR, uploaded_file.name)
                            with open(file_path, "wb") as f:
                                f.write(uploaded_file.getbuffer())
                            saved_filenames.append(uploaded_file.name)
                    
                    img_string = ",".join(saved_filenames)
                    DATABASE[in_id] = {
                        "name": in_name, "phone": in_phone, "info": in_info,
                        "menu_text": in_menu, "img_files": img_string,
                        "password": in_pw
                    }
                    save_database(DATABASE)
                    st.success(f"🎉 '{in_name}' 등록 완료!")

    with tab2:
        st.subheader("🖨️ QR코드 출력 센터")
        
        qr_url = st.text_input("연결할 주소", value="https://my-delivery-app.streamlit.app")
        store_name_print = st.text_input("인쇄될 가게 이름 (영어)", value="My Store")
        
        if st.button("QR코드 생성하기"):
            qr_img = qrcode.make(qr_url)
            img_byte_arr = io.BytesIO()
            qr_img.save(img_byte_arr, format='PNG')
            
            c1, c2 = st.columns([1, 2])
            with c1:
                st.image(img_byte_arr, caption="미리보기", width=200)
            
            with c2:
                st.success("✅ QR코드 생성 완료!")
                st.write("아래 버튼을 누르면 **A4용지 12개 배치 파일(PDF)**을 다운로드합니다.")
                
                pdf_data = create_a4_pdf(img_byte_arr, store_name_print)
                
                st.download_button(
                    label="📄 A4용지용(12개) PDF 다운로드",
                    data=pdf_data,
                    file_name="qr_codes_a4.pdf",
                    mime="application/pdf"
                )
                st.info("💡 다운로드된 파일을 열고 [인쇄]를 누른 뒤, 사장님 프린터를 선택하세요!")

# ------------------------------------------------
# 🏠 매장 입장
# ------------------------------------------------
elif menu == "🏠 매장 입장":
    if "store_id" not in st.session_state:
        st.header("🔑 매장 로그인")
        
        col1, col2 = st.columns(2)
        with col1:
            login_id = st.text_input("아이디 입력")
        with col2:
            login_pw = st.text_input("비밀번호 입력", type="password")
        
        if st.button("입장하기", use_container_width=True):
            if not login_id or not login_pw:
                st.error("❌ 아이디와 비밀번호를 모두 입력해주세요!")
            elif login_id not in DATABASE:
                st.error("❌ 없는 아이디입니다.")
            elif DATABASE[login_id].get("password", "") != login_pw:
                st.error("❌ 비밀번호가 틀렸습니다.")
            else:
                st.session_state["store_id"] = login_id
                st.success("✅ 로그인 성공!")
                st.rerun()
    else:
        store = DATABASE[st.session_state["store_id"]]
        st.title(f"🏠 {store['name']}")
        
        if "img_files" in store and store["img_files"]:
            file_list = store["img_files"].split(",")
            cols = st.columns(2)
            for index, file_name in enumerate(file_list):
                if file_name:
                    img_path = os.path.join(IMG_DIR, file_name)
                    if os.path.exists(img_path):
                        cols[index % 2].image(img_path, use_container_width=True)
        
        st.divider()
        st.info(f"⏰ {store['info']} | 📞 {store['phone']}")
        
        with st.expander("📋 메뉴판 펼쳐보기", expanded=True):
            st.text(store['menu_text'])
            
        if "messages" not in st.session_state:
            st.session_state.messages = [{"role": "assistant", "content": "어서오세요! 주문 도와드릴까요?"}]
        
        if "voice_text" not in st.session_state:
            st.session_state.voice_text = ""

        for msg in st.session_state.messages:
            st.chat_message(msg["role"]).write(msg["content"])

        # 음성 입력 섹션
        st.markdown("---")
        col1, col2 = st.columns([1, 4])
        
        with col1:
            st.markdown("🎤 **음성 주문**")
            audio_bytes = audio_recorder(
                text="",
                recording_color="#e74c3c",
                neutral_color="#3498db",
                icon_size="2x",
                pause_threshold=2.0,
                sample_rate=16000
            )
        
        with col2:
            if audio_bytes:
                with st.spinner("🔊 음성 인식 중..."):
                    transcribed = transcribe_audio(audio_bytes)
                    if transcribed:
                        st.session_state.voice_text = transcribed
                        st.success(f"🎯 인식된 내용: **{transcribed}**")
                    else:
                        st.warning("음성을 인식하지 못했습니다. 다시 시도해주세요.")
            
            if st.session_state.voice_text:
                if st.button(f"📤 '{st.session_state.voice_text}' 전송하기", use_container_width=True):
                    prompt = st.session_state.voice_text
                    st.session_state.voice_text = ""
                    
                    st.session_state.messages.append({"role": "user", "content": prompt})
                    
                    try:
                        full_prompt = f"가게:{store['name']}\n메뉴:{store['menu_text']}\n손님:{prompt}\n주문인지 판단해."
                        bot_reply = model.generate_content(full_prompt).text
                    except Exception as e:
                        bot_reply = f"죄송합니다. AI 응답 오류가 발생했습니다: {e}"
                    
                    st.session_state.messages.append({"role": "assistant", "content": bot_reply})
                    
                    if "주문" in prompt:
                        st.toast("문자 전송 중...", icon="🚀")
                        send_sms(store['phone'], f"[주문] {prompt}")
                        st.balloons()
                    
                    st.rerun()
        
        st.markdown("---")
        st.caption("💡 마이크 버튼을 누르고 말씀하세요. 또는 아래에 직접 입력하세요.")

        # 텍스트 입력
        if prompt := st.chat_input("주문 내용 입력 (또는 위에서 음성으로 입력)"):
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.chat_message("user").write(prompt)

            try:
                full_prompt = f"가게:{store['name']}\n메뉴:{store['menu_text']}\n손님:{prompt}\n주문인지 판단해."
                bot_reply = model.generate_content(full_prompt).text
            except Exception as e:
                bot_reply = f"죄송합니다. AI 응답 오류가 발생했습니다: {e}"
            
            st.session_state.messages.append({"role": "assistant", "content": bot_reply})
            st.chat_message("assistant").write(bot_reply)

            if "주문" in prompt:
                st.toast("문자 전송 중...", icon="🚀")
                send_sms(store['phone'], f"[주문] {prompt}")
                st.balloons()
