import streamlit as st
import pandas as pd
import json
import os
import requests
import datetime
import hmac
import hashlib
import uuid

# ==========================================
# 🔒 관리자 설정 (여기에 비밀번호를 입력하세요)
# ==========================================
ADMIN_PASSWORD = ""
DB_FILE = "stores.json"

# ==========================================
# 📩 솔라피 API 설정 (여기에 키를 채워주세요!)
# ==========================================
SOLAPI_API_KEY = ""
SOLAPI_API_SECRET = ""
SENDER_PHONE = ""

# ==========================================
# 📩 문자 발송 함수
# ==========================================
def send_sms(to_phone, message):
    if not SOLAPI_API_KEY or not SOLAPI_API_SECRET or not SENDER_PHONE:
        return False, "API 키가 설정되지 않았습니다."
    
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
        
        res = requests.post(url, headers=headers, json=payload)
        if res.status_code == 200:
            return True, "발송 성공!"
        else:
            return False, f"발송 실패: {res.text}"
    except Exception as e:
        return False, f"오류 발생: {str(e)}"

# ==========================================
# 💾 데이터베이스 함수
# ==========================================
def load_database():
    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}

def save_database(data):
    with open(DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# ==========================================
# 🎨 페이지 설정
# ==========================================
st.set_page_config(
    page_title="관리자 페이지",
    page_icon="🔐",
    layout="wide"
)

# ==========================================
# 🔐 로그인 화면
# ==========================================
if "admin_logged_in" not in st.session_state:
    st.session_state.admin_logged_in = False

if not st.session_state.admin_logged_in:
    # 로그인 화면
    st.markdown("""
    <style>
    .login-container {
        max-width: 400px;
        margin: 100px auto;
        padding: 40px;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        border-radius: 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.3);
    }
    </style>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        st.markdown("## 🔐 관리자 로그인")
        st.markdown("---")
        
        password = st.text_input("비밀번호를 입력하세요", type="password", placeholder="****")
        
        if st.button("🚀 로그인", use_container_width=True):
            if password == ADMIN_PASSWORD:
                st.session_state.admin_logged_in = True
                st.success("✅ 로그인 성공!")
                st.rerun()
            else:
                st.error("❌ 비밀번호가 틀렸습니다.")
        
        st.markdown("---")
        st.caption("💡 기본 비밀번호: 1234")
    
    st.stop()

# ==========================================
# 📊 관리자 대시보드 (로그인 후)
# ==========================================
st.markdown("## 🔐 관리자 대시보드")

# 사이드바 - 로그아웃
with st.sidebar:
    st.markdown("### 👤 관리자 메뉴")
    st.markdown("---")
    
    if st.button("🚪 로그아웃", use_container_width=True):
        st.session_state.admin_logged_in = False
        st.rerun()
    
    st.markdown("---")
    st.caption("📁 데이터 파일: stores.json")

# 데이터 로드
DATABASE = load_database()

# ==========================================
# 📑 탭 구성
# ==========================================
tab1, tab2, tab3 = st.tabs(["📋 가게 관리", "💌 가맹점 초대 발송", "🔐 비밀번호 관리"])

# ==========================================
# 📋 탭1: 가게 관리
# ==========================================
with tab1:
    # 통계 카드
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric(label="🏪 등록된 가게 수", value=f"{len(DATABASE)}개")

    with col2:
        # 빈 아이디 제외한 실제 가게 수
        real_stores = [k for k in DATABASE.keys() if k.strip()]
        st.metric(label="✅ 유효한 가게", value=f"{len(real_stores)}개")

    with col3:
        # 빈 아이디 수
        empty_stores = [k for k in DATABASE.keys() if not k.strip()]
        st.metric(label="⚠️ 빈 데이터", value=f"{len(empty_stores)}개")

    st.markdown("---")

    # ==========================================
    # 📋 가게 목록 테이블
    # ==========================================
    st.markdown("### 📋 가입된 가게 목록")

    if DATABASE:
        # DataFrame 생성
        table_data = []
        for store_id, store_info in DATABASE.items():
            table_data.append({
                "아이디": store_id if store_id else "(빈 값)",
                "가게 이름": store_info.get("name", "-"),
                "연락처": store_info.get("phone", "-"),
                "비밀번호": "🔒 설정됨" if store_info.get("password") else "🔓 미설정",
                "영업 정보": store_info.get("info", "-"),
                "메뉴": store_info.get("menu_text", "-")[:30] + "..." if len(store_info.get("menu_text", "")) > 30 else store_info.get("menu_text", "-"),
            })
        
        df = pd.DataFrame(table_data)
        
        # 테이블 스타일링
        st.dataframe(
            df,
            use_container_width=True,
            hide_index=True,
            column_config={
                "아이디": st.column_config.TextColumn("🔑 아이디", width="small"),
                "가게 이름": st.column_config.TextColumn("🏪 가게 이름", width="medium"),
                "연락처": st.column_config.TextColumn("📞 연락처", width="small"),
                "비밀번호": st.column_config.TextColumn("🔐 비밀번호", width="small"),
                "영업 정보": st.column_config.TextColumn("⏰ 영업 정보", width="medium"),
                "메뉴": st.column_config.TextColumn("📋 메뉴", width="large"),
            }
        )
    else:
        st.info("📭 등록된 가게가 없습니다.")

    st.markdown("---")

    # ==========================================
    # 🗑️ 가게 삭제 기능 (체크박스 방식)
    # ==========================================
    st.markdown("### 🗑️ 가게 삭제")

    if DATABASE:
        st.caption("삭제할 가게를 체크한 후, 아래 삭제 버튼을 누르세요.")
        
        # 체크박스로 삭제할 가게들 선택
        stores_to_delete = []
        
        for store_id in DATABASE.keys():
            store_name = DATABASE[store_id].get('name', '이름없음')
            store_phone = DATABASE[store_id].get('phone', '-')
            
            # 각 가게에 대한 체크박스
            col1, col2, col3 = st.columns([0.5, 2, 2])
            
            with col1:
                is_checked = st.checkbox("", key=f"del_{store_id}", label_visibility="collapsed")
                if is_checked:
                    stores_to_delete.append(store_id)
            
            with col2:
                st.markdown(f"**🔑 {store_id if store_id else '(빈 값)'}**")
            
            with col3:
                st.markdown(f"🏪 {store_name} | 📞 {store_phone}")
        
        st.markdown("---")
        
        # 선택된 가게 수 표시
        if stores_to_delete:
            st.warning(f"⚠️ {len(stores_to_delete)}개의 가게가 선택되었습니다: {', '.join(stores_to_delete)}")
            
            # 삭제 확인
            if "confirm_delete" not in st.session_state:
                st.session_state.confirm_delete = False
            
            col1, col2, col3 = st.columns([1, 1, 2])
            
            with col1:
                if st.button("🗑️ 선택 항목 삭제", type="primary", use_container_width=True):
                    st.session_state.confirm_delete = True
                    st.session_state.stores_to_delete = stores_to_delete
            
            # 삭제 확인 다이얼로그
            if st.session_state.confirm_delete and hasattr(st.session_state, 'stores_to_delete'):
                st.error(f"⚠️ 정말로 {len(st.session_state.stores_to_delete)}개의 가게를 영구 삭제하시겠습니까?")
                st.caption("이 작업은 되돌릴 수 없습니다!")
                
                col_yes, col_no = st.columns(2)
                
                with col_yes:
                    if st.button("✅ 예, 삭제합니다", use_container_width=True):
                        # 삭제 실행
                        for sid in st.session_state.stores_to_delete:
                            if sid in DATABASE:
                                del DATABASE[sid]
                        save_database(DATABASE)
                        st.session_state.confirm_delete = False
                        del st.session_state.stores_to_delete
                        st.success(f"🗑️ 선택한 가게가 삭제되었습니다!")
                        st.rerun()
                
                with col_no:
                    if st.button("❌ 아니오, 취소", use_container_width=True):
                        st.session_state.confirm_delete = False
                        if hasattr(st.session_state, 'stores_to_delete'):
                            del st.session_state.stores_to_delete
                        st.rerun()
        else:
            st.info("💡 삭제할 가게를 체크해주세요.")

    else:
        st.info("삭제할 가게가 없습니다.")

# ==========================================
# 💌 탭2: 가맹점 초대 발송
# ==========================================
with tab2:
    st.markdown("### 💌 가맹점 초대 문자 발송")
    st.markdown("---")
    
    # API 키 설정 상태 확인
    if not SOLAPI_API_KEY or not SOLAPI_API_SECRET or not SENDER_PHONE:
        st.warning("⚠️ 문자 발송을 위해 SOLAPI API 키를 설정해주세요!")
        st.caption("admin.py 상단의 SOLAPI_API_KEY, SOLAPI_API_SECRET, SENDER_PHONE 변수를 채워주세요.")
        st.markdown("---")
    
    # 입력 폼
    st.markdown("#### 📱 수신자 정보")
    
    receiver_phone = st.text_input(
        "받는 사람 전화번호",
        placeholder="01012345678 (숫자만 입력)",
        help="하이픈(-) 없이 숫자만 입력하세요"
    )
    
    st.markdown("#### 🔗 초대 링크")
    
    invite_link = st.text_input(
        "초대 링크",
        value="http://220.76.153.200:8502",
        help="가맹점 가입 페이지 URL"
    )
    
    st.markdown("---")
    
    # 미리보기
    preview_message = f"사장님, 우리동네 배달앱 가입하세요! 링크: {invite_link}"
    
    st.markdown("#### 👀 메시지 미리보기")
    st.info(f"📩 {preview_message}")
    st.caption(f"글자 수: {len(preview_message)}자")
    
    st.markdown("---")
    
    # 발송 버튼
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        if st.button("초대장 보내기 🚀", type="primary", use_container_width=True):
            # 유효성 검사
            if not receiver_phone:
                st.error("❌ 받는 사람 전화번호를 입력해주세요!")
            elif not receiver_phone.isdigit():
                st.error("❌ 전화번호는 숫자만 입력해주세요!")
            elif len(receiver_phone) < 10 or len(receiver_phone) > 11:
                st.error("❌ 올바른 전화번호 형식이 아닙니다!")
            elif not invite_link:
                st.error("❌ 초대 링크를 입력해주세요!")
            elif not SOLAPI_API_KEY or not SOLAPI_API_SECRET or not SENDER_PHONE:
                st.error("❌ SOLAPI API 키가 설정되지 않았습니다!")
            else:
                # 문자 발송
                with st.spinner("📤 문자 발송 중..."):
                    success, result_msg = send_sms(receiver_phone, preview_message)
                
                if success:
                    st.success(f"✅ 초대 문자가 성공적으로 발송되었습니다!")
                    st.balloons()
                else:
                    st.error(f"❌ 발송 실패: {result_msg}")
    
    st.markdown("---")
    st.caption("💡 문자 발송 시 솔라피(Solapi) API를 사용합니다. 요금이 발생할 수 있습니다.")

# ==========================================
# 🔐 탭3: 비밀번호 관리
# ==========================================
with tab3:
    st.markdown("### 🔐 가게 비밀번호 관리")
    st.markdown("---")
    
    # 비밀번호 없는 가게 목록
    stores_without_pw = []
    stores_with_pw = []
    
    for store_id, store_info in DATABASE.items():
        if store_info.get("password"):
            stores_with_pw.append(store_id)
        else:
            stores_without_pw.append(store_id)
    
    # 통계 표시
    col1, col2 = st.columns(2)
    with col1:
        st.metric("🔓 비밀번호 미설정", f"{len(stores_without_pw)}개")
    with col2:
        st.metric("🔒 비밀번호 설정됨", f"{len(stores_with_pw)}개")
    
    st.markdown("---")
    
    # 비밀번호 없는 가게가 있으면 설정 UI 표시
    if stores_without_pw:
        st.warning(f"⚠️ 비밀번호가 설정되지 않은 가게가 {len(stores_without_pw)}개 있습니다!")
        
        st.markdown("#### 🔓 비밀번호 미설정 가게 목록")
        
        for store_id in stores_without_pw:
            store_info = DATABASE[store_id]
            store_name = store_info.get("name", "이름없음")
            
            with st.expander(f"🏪 {store_id} - {store_name}", expanded=False):
                st.markdown(f"**아이디:** `{store_id}`")
                st.markdown(f"**가게 이름:** {store_name}")
                st.markdown(f"**연락처:** {store_info.get('phone', '-')}")
                
                st.markdown("---")
                
                # 비밀번호 설정 폼
                new_pw = st.text_input(
                    "새 비밀번호",
                    type="password",
                    key=f"new_pw_{store_id}",
                    placeholder="4자리 이상 입력"
                )
                new_pw_confirm = st.text_input(
                    "비밀번호 확인",
                    type="password",
                    key=f"new_pw_confirm_{store_id}",
                    placeholder="비밀번호 재입력"
                )
                
                if st.button(f"🔒 비밀번호 설정", key=f"set_pw_{store_id}", use_container_width=True):
                    if not new_pw:
                        st.error("❌ 비밀번호를 입력해주세요!")
                    elif len(new_pw) < 4:
                        st.error("❌ 비밀번호는 4자리 이상이어야 합니다!")
                    elif new_pw != new_pw_confirm:
                        st.error("❌ 비밀번호가 일치하지 않습니다!")
                    else:
                        DATABASE[store_id]["password"] = new_pw
                        save_database(DATABASE)
                        st.success(f"✅ '{store_id}' 비밀번호가 설정되었습니다!")
                        st.balloons()
                        st.rerun()
    else:
        st.success("✅ 모든 가게에 비밀번호가 설정되어 있습니다!")
    
    st.markdown("---")
    
    # 비밀번호 변경 섹션
    st.markdown("#### 🔄 비밀번호 변경")
    
    if DATABASE:
        store_options = list(DATABASE.keys())
        
        selected_store = st.selectbox(
            "비밀번호를 변경할 가게 선택",
            options=store_options,
            format_func=lambda x: f"{x} ({DATABASE[x].get('name', '이름없음')})"
        )
        
        if selected_store:
            has_pw = "🔒 설정됨" if DATABASE[selected_store].get("password") else "🔓 미설정"
            st.caption(f"현재 상태: {has_pw}")
            
            col1, col2 = st.columns(2)
            with col1:
                change_pw = st.text_input(
                    "새 비밀번호",
                    type="password",
                    key="change_pw",
                    placeholder="4자리 이상"
                )
            with col2:
                change_pw_confirm = st.text_input(
                    "비밀번호 확인",
                    type="password",
                    key="change_pw_confirm",
                    placeholder="비밀번호 재입력"
                )
            
            if st.button("🔄 비밀번호 변경", use_container_width=True):
                if not change_pw:
                    st.error("❌ 새 비밀번호를 입력해주세요!")
                elif len(change_pw) < 4:
                    st.error("❌ 비밀번호는 4자리 이상이어야 합니다!")
                elif change_pw != change_pw_confirm:
                    st.error("❌ 비밀번호가 일치하지 않습니다!")
                else:
                    DATABASE[selected_store]["password"] = change_pw
                    save_database(DATABASE)
                    st.success(f"✅ '{selected_store}' 비밀번호가 변경되었습니다!")
                    st.balloons()
    else:
        st.info("등록된 가게가 없습니다.")

# ==========================================
# 📌 하단 정보
# ==========================================
st.markdown("---")
st.caption("🔐 관리자 페이지 | 데이터는 stores.json에 저장됩니다.")
