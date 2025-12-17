import streamlit as st
from openai import OpenAI
from pinecone import Pinecone
from sentence_transformers import SentenceTransformer
import streamlit.components.v1 as components
import datetime
import uuid
import time
import json
import random
import re

# --- 1. 頁面設定 ---
st.set_page_config(
    page_title="DSE 智能温習系統 (Weighted All-Subject)", 
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

def clean_latex(text):
    if not text: return ""
    # 修復 LaTeX 格式，將 \[ \] 和 \( \) 轉換為 Streamlit 支援的格式
    text = re.sub(r'\\\[(.*?)\\\]', r'$$\1$$', text, flags=re.DOTALL)
    text = re.sub(r'\\\((.*?)\\\)', r'$\1$', text, flags=re.DOTALL)
    return text

def manual_save_to_cloud(subject, question, answer, note_type):
    if not index:
        st.error("❌ 未連接 Pinecone")
        return
    
    # 存入前清洗格式
    question = clean_latex(question)
    answer = clean_latex(answer)
    
    text_to_embed = f"{subject}: {question}"
    vector = embed_model.encode(text_to_embed).tolist()
    
    metadata = {
        "subject": subject,
        "question": question,
        "answer": answer,
        "type": note_type,
        "date_added": datetime.datetime.now().strftime("%Y-%m-%d"),
        "weight": 20.0, # 初始權重設為高
        "timestamp": time.time()
    }
    
    unique_id = str(uuid.uuid4())
    try:
        index.upsert(vectors=[(unique_id, vector, metadata)])
        st.toast(f"☁️ 已存入【{subject}】！", icon="✅")
        # 清除緩存，確保新題目能被讀取
        if 'card_pool' in st.session_state: del st.session_state['card_pool']
    except Exception as e:
        st.error(f"上傳失敗: {e}")

def update_weight(item_id, rating):
    if not index: return
    new_weight = 20.0
    msg = ""
    if rating == 1:
        new_weight = 20.0
        msg = "🔴 標記為【完全不熟悉】(下題機率極高)"
    elif rating == 2:
        new_weight = 5.0
        msg = "🟡 標記為【不太熟悉】(下題機率中等)"
    elif rating == 3:
        new_weight = 1.0
        msg = "🟢 標記為【初步熟悉】(下題機率較低)"
    
    try:
        index.update(id=item_id, set_metadata={"weight": new_weight})
        st.toast(msg, icon="📊")
        # 清除當前卡片，強制換卡
        if 'current_card_data' in st.session_state:
            del st.session_state['current_card_data']
        # 稍微延遲讓用戶看到提示
        time.sleep(0.3)
    except Exception as e:
        st.error(f"更新失敗: {e}")

def delete_from_cloud(item_id):
    if not index: return
    try:
        index.delete(ids=[item_id])
        st.toast("🗑️ 已刪除！", icon="✅")
        if 'current_card_data' in st.session_state:
            del st.session_state['current_card_data']
        if 'card_pool' in st.session_state:
            del st.session_state['card_pool']
        time.sleep(0.5)
        st.rerun()
    except Exception as e:
        st.error(f"刪除失敗: {e}")

# 跳過按鈕的回調
def skip_card():
    if 'current_card_data' in st.session_state:
        del st.session_state['current_card_data']

def copy_button_component(text_to_copy):
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
            const btn = document.getElementById('copyBtn');
            btn.innerText = "✅ 複製成功！";
            btn.style.backgroundColor = "#4CAF50";
            setTimeout(() => {{ btn.innerText = "📋 點擊複製所有指令"; btn.style.backgroundColor = "#FF4B4B"; }}, 2000);
        }}
        </script>
        <button id="copyBtn" onclick="copyToClipboard()" style="width: 100%; background-color: #FF4B4B; color: white; border: none; padding: 12px 20px; border-radius: 8px; cursor: pointer; font-weight: bold; font-size: 16px;">📋 點擊複製所有指令</button>
        """, height=60
    )

# --- 5. 側邊欄 ---
with st.sidebar:
    st.title("🇭🇰 DSE 備戰中心")
    st.caption("Auto LaTeX Fix")
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
tab_factory, tab_study, tab_review = st.tabs(["🏭 資料清洗", "🎓 智能溫習", "🧠 權重抽卡 (Flashcard)"])

# ==========================================
# TAB 1: 資料清洗
# ==========================================
with tab_factory:
    st.header(f"🚀 {current_subject} - 資料清洗")
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("1. 獲取指令")
        prompt_text = f"""(請上傳 PDF/圖片) 你是一位 DSE {current_subject} 編輯..."""
        st.text_area("預覽", prompt_text, height=150)
        copy_button_component(prompt_text)
        st.link_button("🔗 前往 DeepSeek", "https://chat.deepseek.com", type="primary")
    with c2:
        st.subheader("2. 備份")
        with st.form("save"):
            txt = st.text_area("貼上內容...", height=250)
            if st.form_submit_button("💾 下載") and txt:
                st.download_button("📥 下載", txt, f"{current_subject}_Notes.txt")

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
                for m in st.session_state.messages: 
                    st.chat_message(m["role"]).write(clean_latex(m["content"]))
                
                if q := st.chat_input("輸入問題..."):
                    st.session_state.messages.append({"role": "user", "content": q})
                    st.chat_message("user").write(q)
                    with st.chat_message("assistant"):
                        rag = f"DSE 導師，用廣東話答。數學公式請用單個 $ 包住。\n筆記：{notes[:12000]}"
                        ans = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"system","content":rag},{"role":"user","content":q}]).choices[0].message.content
                        display_ans = clean_latex(ans)
                        st.markdown(display_ans)
                        st.button("☁️ 加入題庫", key=f"s_{len(st.session_state.messages)}", on_click=manual_save_to_cloud, args=(current_subject, q, ans, "問答"))
                    st.session_state.messages.append({"role": "assistant", "content": ans})
            
            with s3:
                c1,c2,c3 = st.columns([2,2,1])
                with c1: diff = st.select_slider("難度", ["L3","L4","L5","L5**"], "L4")
                with c2: qt = st.radio("題型", ["MC","LQ"], horizontal=True)
                with c3: num = st.number_input("數量", 1, 10, 1)
                if st.button("🚀 出題"):
                    prompt = f"DSE 出卷員。出 {num} 條 {diff} {qt}。1.先列題目，插入 `<<<SPLIT>>>`，再列答案。2.MC垂直分行。3.數學公式必須用單個 $ 包住。筆記：{notes[:6000]}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}]).choices[0].message.content
                    q_p, a_p = res.split("<<<SPLIT>>>") if "<<<SPLIT>>>" in res else (res, "見上方")
                    st.session_state['q'] = {"q": q_p, "a": a_p}
                
                if 'q' in st.session_state:
                    quiz = st.session_state['q']
                    st.markdown("### 試題")
                    st.markdown(clean_latex(quiz['q']))
                    with st.expander("答案"): 
                        st.markdown(clean_latex(quiz['a']))
                    st.button("☁️ 加入題庫", key="sq", on_click=manual_save_to_cloud, args=(current_subject, quiz['q'], quiz['a'], "模擬卷"))

# ==========================================
# TAB 3: 權重機率抽卡 (Cross-Subject Fix)
# ==========================================
with tab_review:
    st.header("🧠 權重抽卡温習 (Flashcard)")
    
    if not index: st.warning("⚠️ 請先設定 Pinecone Key"); st.stop()

    # 控制台
    c_filt, c_reset = st.columns([3, 1])
    with c_filt: 
        f_sub = st.selectbox("📂 選擇學科抽題", ["顯示全部", "Biology", "Chemistry", "Economics", "Chinese", "English", "History", "Maths"])
    
    # 篩選變更偵測
    if 'last_filter' not in st.session_state:
        st.session_state.last_filter = f_sub
    
    if st.session_state.last_filter != f_sub:
        if 'card_pool' in st.session_state: del st.session_state['card_pool']
        if 'current_card_data' in st.session_state: del st.session_state['current_card_data']
        st.session_state.last_filter = f_sub
        st.rerun()

    with c_reset:
        st.write("")
        st.button("⏭️ 下一張 / 刷新", on_click=skip_card)

    st.markdown("---")

    try:
        # 1. 獲取題庫池
        if 'card_pool' not in st.session_state:
            dummy = [0.0] * 384
            # 如果選顯示全部，filter 設為 None，抓取更多題目 (500) 以確保隨機性
            meta_filter = {"subject": f_sub} if f_sub != "顯示全部" else None
            top_k_count = 500 if f_sub == "顯示全部" else 200
            
            with st.spinner(f"正在從雲端載入{f_sub}題庫..."):
                res = index.query(vector=dummy, top_k=top_k_count, include_metadata=True, filter=meta_filter)
                st.session_state['card_pool'] = res['matches']
        
        pool = st.session_state['card_pool']

        # 2. 檢查題庫
        if not pool:
            st.info(f"📭 題庫中暫時沒有【{f_sub}】的紀錄。")
        else:
            # 顯示統計
            sub_count = {}
            for p in pool:
                s = p['metadata'].get('subject', 'Unknown')
                sub_count[s] = sub_count.get(s, 0) + 1
            
            caption_text = f"📚 題庫總數: {len(pool)} 題"
            if f_sub == "顯示全部":
                caption_text += f" (包含: {', '.join([f'{k}:{v}' for k,v in sub_count.items()])})"
            st.caption(caption_text)

            # 3. 抽卡邏輯 (核心)
            if 'current_card_data' not in st.session_state:
                # 提取權重
                weights = [float(m['metadata'].get('weight', 20.0)) for m in pool]
                # 隨機抽取 (這裡會根據所有題目的權重進行跨學科抽取)
                chosen_card = random.choices(pool, weights=weights, k=1)[0]
                st.session_state['current_card_data'] = chosen_card

            # 4. 顯示卡片
            card = st.session_state['current_card_data']
            data = card['metadata']
            mid = card['id']
            w = float(data.get('weight', 20.0))
            
            w_label = "🔴 高頻複習" if w == 20.0 else ("🟡 中頻複習" if w == 5.0 else "🟢 低頻複習")
            w_color = "#ff4b4b" if w == 20.0 else ("#ffa500" if w == 5.0 else "#28a745")

            st.markdown(f"""
            <div style="border: 2px solid {w_color}; border-radius: 10px; padding: 20px; margin-bottom: 20px; background-color: white;">
                <div style="display:flex; justify-content:space-between; margin-bottom:10px;">
                    <span style="font-weight:bold; color:#0068c9; font-size:1.1em;">{data.get('subject')}</span>
                    <span style="background-color:{w_color}; color:white; padding:2px 8px; border-radius:5px; font-size:0.8em;">{w_label}</span>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            with st.container():
                st.markdown(clean_latex(data.get('question')))

            with st.expander("👁️ 翻開答案 (Check Answer)", expanded=True):
                st.markdown("### ✅ 解析")
                st.markdown(clean_latex(data.get('answer')))
                st.divider()
                st.markdown("#### 🧠 熟悉度評分 (Auto Next)")
                
                c1, c2, c3, c4 = st.columns(4)
                
                # 按鈕 callback 會自動清除 current_card_data，觸發下次 render 時重新抽卡
                with c1: 
                    st.button("🔴 完全不熟", key="btn_hard", on_click=update_weight, args=(mid, 1), use_container_width=True)
                with c2: 
                    st.button("🟡 不太熟", key="btn_med", on_click=update_weight, args=(mid, 2), use_container_width=True)
                with c3: 
                    st.button("🟢 初步熟悉", key="btn_easy", on_click=update_weight, args=(mid, 3), use_container_width=True)
                with c4: 
                    st.button("🗑️ 刪除", key="btn_del", on_click=delete_from_cloud, args=(mid,), use_container_width=True)

    except Exception as e:
        st.error(f"系統錯誤: {e}")
