import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import datetime
import uuid
import time

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (雲端手動版)", 
    layout="wide", 
    page_icon="🇭🇰",
    initial_sidebar_state="expanded"
)

# --- 2. 初始化核心模型 (快取加速) ---
@st.cache_resource
def init_embedding_model():
    # 使用免費輕量級模型轉向量
    return SentenceTransformer('all-MiniLM-L6-v2')

@st.cache_resource
def init_pinecone(api_key):
    return Pinecone(api_key=api_key)

# 載入 Embedding 模型 (只執行一次)
with st.spinner("正在啟動雲端連線..."):
    embed_model = init_embedding_model()

# --- 3. API Key 設定 ---
deepseek_key = st.secrets.get("DEEPSEEK_API_KEY")
pinecone_key = st.secrets.get("PINECONE_API_KEY")

# --- 4. 核心函數：儲存與刪除 ---

def manual_save_to_cloud(subject, question, answer, note_type):
    """手動儲存至雲端"""
    if not index:
        st.error("❌ 未連接 Pinecone，無法儲存。")
        return

    # A. 轉向量
    text_to_embed = f"{subject}: {question}"
    vector = embed_model.encode(text_to_embed).tolist()
    
    # B. 準備資料包
    metadata = {
        "subject": subject,
        "question": question,
        "answer": answer,
        "type": note_type,
        "date": datetime.datetime.now().strftime("%Y-%m-%d"),
        "timestamp": time.time()
    }
    
    # C. 上傳 (Upsert)
    unique_id = str(uuid.uuid4()) # 產生唯一 ID
    try:
        index.upsert(vectors=[(unique_id, vector, metadata)])
        st.toast(f"☁️ 已手動上傳至【{subject}】雲端資料庫！", icon="✅")
    except Exception as e:
        st.error(f"上傳失敗: {e}")

def delete_from_cloud(item_id):
    """從雲端刪除指定 ID 的題目"""
    if not index:
        st.error("未連接 Pinecone")
        return
    
    try:
        # 呼叫 Pinecone 刪除 API
        index.delete(ids=[item_id])
        st.toast("🗑️ 已從雲端永久刪除此題！", icon="✅")
        
        # 等待 1 秒讓雲端處理，然後刷新頁面
        time.sleep(1)
        st.rerun()
    except Exception as e:
        st.error(f"刪除失敗: {e}")

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("DeepSeek x Pinecone Cloud")
    st.divider()
    
    if not deepseek_key:
        deepseek_key = st.text_input("DeepSeek Key", type="password")
    if not pinecone_key:
        pinecone_key = st.text_input("Pinecone Key", type="password")
        
    st.divider()
    
    current_subject = st.selectbox(
        "當前温習科目", 
        ["Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths", "Liberal Studies"]
    )

# 初始化連接
client = None
index = None

if deepseek_key:
    client = OpenAI(api_key=deepseek_key, base_url="https://api.deepseek.com")

if pinecone_key:
    try:
        pc = init_pinecone(pinecone_key)
        index_name = "dse-memory" 
        index = pc.Index(index_name)
        st.sidebar.success("🟢 雲端資料庫已連線")
    except Exception as e:
        st.sidebar.error(f"Pinecone 連線失敗: {e}")

# --- 6. 主功能區 ---
tab_factory, tab_study, tab_review = st.tabs(["🏭 資料清洗", "🎓 智能溫習 (手動存)", "🧠 雲端重溫 (含刪除)"])

# ==========================================
# TAB 1: 資料清洗
# ==========================================
with tab_factory:
    st.header(f"🚀 {current_subject} - 資料清洗")
    col1, col2 = st.columns([1, 1])
    with col1:
        st.subheader("1. 複製指令")
        prompt_text = f"你是一位 DSE {current_subject} 編輯。請將文件整理為 Markdown 筆記。去除雜訊、按課題分類、題目整理為 Q&A。"
        st.code(prompt_text, language="text")
        st.link_button("🔗 前往 DeepSeek 官網", "https://chat.deepseek.com", type="primary")

    with col2:
        st.subheader("2. 備份存檔")
        with st.form("save_txt"):
            txt = st.text_area("貼上內容...", height=200)
            if st.form_submit_button("💾 下載 .txt") and txt:
                st.download_button("📥 點擊下載", txt, f"{current_subject}_Notes.txt")

# ==========================================
# TAB 2: 智能溫習
# ==========================================
with tab_study:
    st.header(f"🎓 {current_subject} - 衝刺模式")
    col_input, col_main = st.columns([1, 2])
    with col_input:
        input_method = st.radio("來源", ["📂 上傳", "📋 貼上"], horizontal=True)
        notes_text = ""
        if input_method == "📋 貼上":
            notes_text = st.text_area("貼上筆記：", height=300)
        else:
            files = st.file_uploader("上傳 .txt", type=["txt"], accept_multiple_files=True)
            if files:
                for f in files: notes_text += f"\n---\n{f.read().decode('utf-8')}"
        audio = st.file_uploader("音檔", type=["mp3"])

    with col_main:
        if not notes_text:
            st.info("👈 請先載入筆記")
        else:
            if not client: st.error("缺 API Key"); st.stop()

            sub1, sub2, sub3 = st.tabs(["🎧 聽書", "💬 問答", "✍️ 模擬卷"])
            
            with sub1:
                if audio: st.audio(audio)
                with st.expander("筆記內容"): st.markdown(notes_text)

            with sub2:
                if "messages" not in st.session_state: st.session_state.messages = []
                for m in st.session_state.messages: st.chat_message(m["role"]).write(m["content"])
                
                if q := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.chat_message("user").write(q)
                    with st.chat_message("assistant"):
                        rag = f"你係 DSE {current_subject} 導師。根據筆記用廣東話答：\n{notes_text[:12000]}"
                        ans = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":rag},{"role":"user","content":q}]).choices[0].message.content
                        st.markdown(ans)
                        
                        st.button(
                            "☁️ 手動存入雲端", 
                            key=f"cloud_save_{len(st.session_state.messages)}",
                            on_click=manual_save_to_cloud,
                            args=(current_subject, q, ans, "問答"),
                            type="secondary"
                        )
                    st.session_state.messages.append({"role": "assistant", "content": ans})

            with sub3:
                c1, c2, c3 = st.columns([2,2,1])
                with c1: diff = st.select_slider("難度", ["L3","L4","L5","L5**"], "L4")
                with c2: qt = st.radio("題型", ["MC","LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                
                if st.button("🚀 生成題目"):
                    prompt = f"""
                    DSE {current_subject} 出卷員。出 {num} 條 {diff} {qt}。
                    重要：先列題目，插入 `<<<SPLIT>>>`，再列答案。
                    MC 選項垂直分行。數學公式用 $LaTeX$。
                    筆記：{notes_text[:6000]}
                    """
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    q_part, a_part = res.split("<<<SPLIT>>>") if "<<<SPLIT>>>" in res else (res, "見上方")
                    st.session_state['cloud_quiz'] = {"q": q_part, "a": a_part}

                if 'cloud_quiz' in st.session_state:
                    quiz = st.session_state['cloud_quiz']
                    st.markdown("### 📝 試題"); st.markdown(quiz['q'])
                    with st.expander("🔐 答案"): st.markdown(quiz['a'])
                    
                    st.divider()
                    st.button(
                        "☁️ 手動存入雲端", 
                        key="cloud_save_quiz",
                        on_click=manual_save_to_cloud,
                        args=(current_subject, quiz['q'], quiz['a'], f"{diff} {qt} 模擬卷"),
                        type="primary"
                    )

# ==========================================
# TAB 3: 雲端重溫 (新增刪除功能)
# ==========================================
with tab_review:
    st.header("🧠 雲端錯題庫")
    
    if not index:
        st.warning("⚠️ 請先設定 Pinecone API Key。")
        st.stop()

    col_filter, col_refresh = st.columns([3, 1])
    with col_filter:
        filter_subject = st.selectbox("📂 選擇雲端資料夾 (Subject)", ["顯示全部", "Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths"])
    
    with col_refresh:
        st.write("") 
        if st.button("🔄 刷新列表"):
            st.rerun()

    st.markdown("---")

    try:
        dummy_vector = [0.0] * 384
        
        meta_filter = {}
        if filter_subject != "顯示全部":
            meta_filter = {"subject": filter_subject}

        with st.spinner("正在讀取雲端資料..."):
            query_response = index.query(
                vector=dummy_vector,
                top_k=50, 
                include_metadata=True,
                filter=meta_filter if meta_filter else None
            )
        
        matches = query_response['matches']
        
        if not matches:
            st.info(f"📭 雲端資料庫中暫時沒有【{filter_subject}】的紀錄。")
        else:
            st.success(f"☁️ 找到 {len(matches)} 條紀錄")
            
            for match in matches:
                item_id = match['id'] # 獲取唯一 ID
                data = match['metadata']
                q_text = data.get('question', 'No Question')
                a_text = data.get('answer', 'No Answer')
                sub_tag = data.get('subject', 'General')
                date_tag = data.get('date', '')
                type_tag = data.get('type', 'Note')
                
                with st.container():
                    st.markdown(f"""
                    <div style="background-color:#e8f4f9; padding:10px; border-radius:5px 5px 0 0; border-left: 5px solid #0068c9;">
                        <b>{sub_tag}</b> <small style="color:grey;">| {type_tag} | {date_tag}</small>
                    </div>
                    """, unsafe_allow_html=True)
                    
                    st.markdown(f"""
                    <div style="border:1px solid #ddd; border-top:none; padding:15px; border-radius:0 0 5px 5px; margin-bottom:10px;">
                        {q_text}
                    </div>
                    """, unsafe_allow_html=True)
                    
                    # 答案區 (包含刪除按鈕)
                    with st.expander("👁️ 點擊顯示答案與管理"):
                        st.markdown(a_text)
                        
                        st.divider()
                        
                        col_del, col_space = st.columns([1, 4])
                        with col_del:
                            # 刪除按鈕
                            st.button(
                                "🗑️ 永久刪除此題", 
                                key=f"del_{item_id}", # 使用 ID 作為 key，確保每個按鈕唯一
                                on_click=delete_from_cloud,
                                args=(item_id,), # 傳遞 ID 給刪除函數
                                type="primary"
                            )
                        with col_space:
                            st.caption("⚠️ 刪除後無法復原")
                        
    except Exception as e:
        st.error(f"讀取雲端失敗: {e}")
