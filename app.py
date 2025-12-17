import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import streamlit.components.v1 as components  # 用於製作複製按鈕
import datetime
import uuid
import time
import json

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Copy Button Fix)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# --- 2. 初始化核心模型 ---
@st.cache_resource
def init_embedding_model():
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def init_pinecone(api_key):
    return Pinecone(api_key=api_key)

with st.spinner("正在啟動雲端連線..."):
    embed_model = init_embedding_model()

# --- 3. API Key 設定 ---
deepseek_key = st.secrets.get("DEEPSEEK_API_KEY")
pinecone_key = st.secrets.get("PINECONE_API_KEY")

# --- 4. 核心函數 ---
def manual_save_to_cloud(subject, question, answer, note_type):
    if not index:
        st.error("❌ 未連接 Pinecone")
        return
    text_to_embed = f"{subject}: {question}"
    vector = embed_model.encode(text_to_embed).tolist()
    metadata = {
        "subject": subject, "question": question, "answer": answer,
        "type": note_type, "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "timestamp": time.time()
    }
    unique_id = str(uuid.uuid4())
    try:
        index.upsert(vectors=[(unique_id, vector, metadata)])
        st.toast(f"☁️ 已上傳至【{subject}】資料庫！", icon="✅")
    except Exception as e:
        st.error(f"上傳失敗: {e}")

def delete_from_cloud(item_id):
    if not index: return
    try:
        index.delete(ids=[item_id])
        st.toast("🗑️ 已刪除！", icon="✅")
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"刪除失敗: {e}")

# --- [新功能] JavaScript 複製按鈕組件 ---
def copy_button_component(text_to_copy):
    # 使用 json.dumps 確保文字格式在 JS 中不會出錯 (處理換行和引號)
    js_text = json.dumps(text_to_copy)
    
    components.html(
        f"""
        <script>
        function copyToClipboard() {{
            const str = {js_text};
            const el = document.createElement('textarea');
            el.value = str;
            document.body.appendChild(el);
            el.select();
            document.execCommand('copy');
            document.body.removeChild(el);
            
            // 改變按鈕文字提示成功
            const btn = document.getElementById('copyBtn');
            btn.innerText = "✅ 複製成功！";
            btn.style.backgroundColor = "#4CAF50";
            
            // 2秒後變回原樣
            setTimeout(() => {{
                btn.innerText = "📋 點擊複製所有指令";
                btn.style.backgroundColor = "#FF4B4B";
            }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="
            width: 100%;
            background-color: #FF4B4B; 
            color: white; 
            border: none; 
            padding: 12px 20px; 
            border-radius: 8px; 
            cursor: pointer;
            font-family: sans-serif;
            font-weight: bold;
            font-size: 16px;
            transition: 0.3s;
        ">
            📋 點擊複製所有指令
        </button>
        """,
        height=60
    )

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("DeepSeek x Pinecone Cloud")
    st.divider()
    if not deepseek_key: deepseek_key = st.text_input("DeepSeek Key", type="password")
    if not pinecone_key: pinecone_key = st.text_input("Pinecone Key", type="password")
    st.divider()
    current_subject = st.selectbox("當前温習科目", ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"])

client = None
index = None
if deepseek_key: client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")
if pinecone_key:
    try:
        pc = init_pinecone(pinecone_key)
        index = pc.Index("dse-memory")
        st.sidebar.success("🟢 雲端已連線")
    except Exception as e:
        st.sidebar.error(f"連線失敗: {e}")

# --- 6. 主功能區 ---
tab_factory, tab_study, tab_review = st.tabs(["🏭 資料清洗", "🎓 智能溫習", "🧠 雲端重溫"])

# ==========================================
# TAB 1: 資料清洗 (已加入複製按鈕)
# ==========================================
with tab_factory:
    st.header(f"🚀 {current_subject} - 資料清洗")
    c1, c2 = st.columns(2)
    
    with c1:
        st.subheader("1. 獲取指令")
        
        # 定義指令文字
        prompt_text = f"""
        (請上傳附件 PDF/圖片)
        你是一位香港 DSE {current_subject} 的專業教材編輯。
        請閱讀我上傳的文件，並將其整理為一份「結構清晰」的 Markdown 筆記。
        
        要求：
        1. 【去蕪存菁】：去除頁碼、廣告、重複的考試規則。
        2. 【結構化】：按課題 (Topic) 使用 # 和 ## 標題分類。
        3. 【關鍵詞】：保留所有 DSE 專用術語 (Keywords)。
        4. 【題目】：如果內容包含題目與答案，請整理為 Q: ... A: ... 格式。
        5. 【輸出】：直接輸出整理後的內容，不需要開場白。
        """
        
        # 顯示文字框 (讓用戶可以看，也可以手動選)
        st.text_area("指令預覽 (按下方法按鈕複製)", prompt_text, height=250)
        
        # [重點] 這裡插入了自定義的 JavaScript 按鈕
        copy_button_component(prompt_text)
        
        st.markdown("---")
        st.link_button("🔗 前往 DeepSeek 官網貼上", "https://chat.deepseek.com", type="primary")

    with c2:
        st.subheader("2. 備份存檔")
        with st.form("save"):
            txt = st.text_area("貼上 DeepSeek 整理後的內容...", height=300)
            if st.form_submit_button("💾 下載 .txt") and txt:
                st.download_button("📥 點擊下載", txt, f"{current_subject}_Notes.txt")

# ==========================================
# TAB 2: 智能溫習
# ==========================================
with tab_study:
    st.header(f"🎓 {current_subject} - 衝刺模式")
    c_in, c_main = st.columns([1, 2])
    with c_in:
        method = st.radio("來源", ["📂 上傳", "📋 貼上"], horizontal=True)
        notes = ""
        if method == "📋 貼上": notes = st.text_area("貼上筆記：", height=300)
        else:
            files = st.file_uploader("上傳 .txt", type=["txt"], accept_multiple_files=True)
            if files:
                for f in files: notes += f"\n---\n{f.read().decode('utf-8')}"
        audio = st.file_uploader("音檔", type=["mp3"])

    with c_main:
        if not notes: st.info("👈 請先載入筆記")
        else:
            if not client: st.error("缺 API Key"); st.stop()
            s1, s2, s3 = st.tabs(["🎧 聽書", "💬 問答", "✍️ 模擬卷"])
            
            with s1:
                if audio: st.audio(audio)
                with st.expander("筆記"): st.markdown(notes)
            
            with s2:
                if "messages" not in st.session_state: st.session_state.messages = []
                for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
                if q := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.chat_message("user").write(q)
                    with st.chat_message("assistant"):
                        rag = f"DSE {current_subject} 導師，用廣東話答：\n{notes[:12000]}"
                        ans = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":rag},{"role":"user","content":q}]).choices[0].message.content
                        st.markdown(ans)
                        st.button("☁️ 存入雲端", key=f"save_{len(st.session_state.messages)}", on_click=manual_save_to_cloud, args=(current_subject, q, ans, "問答"))
                    st.session_state.messages.append({"role": "assistant", "content": ans})
            
            with s3:
                c1, c2, c3 = st.columns([2,2,1])
                with c1: diff = st.select_slider("難度", ["L3","L4","L5","L5**"], "L4")
                with c2: qt = st.radio("題型", ["MC","LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                if st.button("🚀 生成題目"):
                    prompt = f"""
                    DSE {current_subject} 出卷員。出 {num} 條 {diff} {qt}。
                    1. 先列題目，插入 `<<<SPLIT>>>`，再列答案。
                    2. MC 選項垂直分行。
                    3. 數學公式必須用 $LaTeX$ (如 $x^2$)。
                    筆記：{notes[:6000]}
                    """
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    q_part, a_part = res.split("<<<SPLIT>>>") if "<<<SPLIT>>>" in res else (res, "見上方")
                    st.session_state['c_quiz'] = {"q": q_part, "a": a_part}
                
                if 'c_quiz' in st.session_state:
                    quiz = st.session_state['c_quiz']
                    st.markdown("### 📝 試題"); st.markdown(quiz['q'])
                    with st.expander("🔐 答案"): st.markdown(quiz['a'])
                    st.button("☁️ 存入雲端", key="save_quiz", on_click=manual_save_to_cloud, args=(current_subject, quiz['q'], quiz['a'], "模擬卷"))

# ==========================================
# TAB 3: 雲端重溫
# ==========================================
with tab_review:
    st.header("🧠 雲端錯題庫")
    if not index: st.warning("⚠️ 請先設定 Pinecone Key"); st.stop()

    c_filt, c_ref = st.columns([3, 1])
    with c_filt: f_sub = st.selectbox("📂 選擇雲端資料夾", ["顯示全部", "Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths"])
    with c_ref: 
        st.write("")
        if st.button("🔄 刷新"): st.rerun()

    st.markdown("---")

    try:
        dummy = [0.0] * 384
        filt = {"subject": f_sub} if f_sub != "顯示全部" else None
        
        with st.spinner("讀取雲端..."):
            res = index.query(vector=dummy, top_k=50, include_metadata=True, filter=filt)
        
        matches = res['matches']
        if not matches: st.info(f"📭 暫無【{f_sub}】紀錄")
        else:
            st.success(f"☁️ 同步 {len(matches)} 條紀錄")
            for match in matches:
                mid = match['id']
                data = match['metadata']
                st.markdown(f"""
                <div style="background-color:#e8f4f9; padding:8px; border-radius:5px 5px 0 0; border-left: 5px solid #0068c9; margin-top: 15px;">
                    <b>{data.get('subject')}</b> <small style="color:grey;">| {data.get('type')} | {data.get('date')}</small>
                </div>
                """, unsafe_allow_html=True)
                with st.container():
                    st.markdown(data.get('question', 'No Question'))
                with st.expander("👁️ 顯示答案與管理"):
                    st.markdown(data.get('answer', 'No Answer'))
                    st.divider()
                    st.button("🗑️ 永久刪除", key=f"del_{mid}", on_click=delete_from_cloud, args=(mid,), type="primary")
    except Exception as e:
        st.error(f"讀取錯誤: {e}")
