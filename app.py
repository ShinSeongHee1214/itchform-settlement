import streamlit as st
import pandas as pd

# [디자인] 눈이 편안한 차분한 파스텔 분홍 스타일링
st.set_page_config(page_title="윗치폼 정산 마스터 시스템", layout="wide")

st.markdown("""
    <style>
    div.stButton > button:first-child {
        background-color: #FFB6C1 !important;
        color: white !important;
        border-radius: 8px !important;
        border: none !important;
        padding: 0.6rem 2.5rem !important;
        font-weight: 500 !important;
        font-size: 15px !important;
        display: block;
        margin: 0 auto;
    }
    h1, h2, h3 { color: #DB7093 !important; font-weight: 600 !important; }
    .menu-link {
        display: block;
        padding: 10px 15px;
        color: #475569 !important;
        text-decoration: none !important;
        font-size: 15px;
        font-weight: 500;
        transition: all 0.25s ease-in-out;
        border-radius: 6px;
    }
    .menu-link:hover {
        color: #DB7093 !important; 
        font-weight: 700 !important; 
        background-color: #FFF5F5;
        padding-left: 20px; 
    }
    </style>
""", unsafe_allow_html=True)

def anchor(target_id):
    st.markdown(f"<div id='{target_id}' style='margin-top: -30px;'></div>", unsafe_allow_html=True)

# 세션 상태 기억 장치 가동
if 'manual_confirmed' not in st.session_state: st.session_state.manual_confirmed = {}
if 'deleted_orders' not in st.session_state: st.session_state.deleted_orders = set()
if 'deleted_bank_indexes' not in st.session_state: st.session_state.deleted_bank_indexes = set()
if 'refunded_orders' not in st.session_state: st.session_state.refunded_orders = {}
if 'manual_added_records' not in st.session_state: st.session_state.manual_added_records = [] # 💡 수기 추가 명단 저장소 신설
if 'is_calculated' not in st.session_state: st.session_state.is_calculated = False
if 'search_word' not in st.session_state: st.session_state.search_word = ""

# 사이드바 메뉴바
st.sidebar.markdown("### 🌸 정산 바로가기 메뉴")
st.sidebar.markdown("<a href='#sec_upload' class='menu-link'>📁 데이터 파일 업로드</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_comparison' class='menu-link'>💰 최종 금액 대조판</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m1' class='menu-link'>✅ 입금 확인 완료 명단</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m2' class='menu-link'>⚠️ 금액 불일치 명단</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m3' class='menu-link'>🚨 미입금 명단</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m4' class='menu-link'>❓ 주문서 없는 입금 명단</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m5' class='menu-link'>👥 동명이인 중복 확인 칸</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_m6' class='menu-link'>↩️ 환불 처리 완료 칸</a>", unsafe_allow_html=True)
st.sidebar.markdown("<a href='#sec_download' class='menu-link'>📥 정산 반영 파일 내보내기</a>", unsafe_allow_html=True)

anchor("sec_upload")
st.subheader("📁 데이터 파일 업로드")
col1, col2 = st.columns(2)
with col1:
    order_files = st.file_uploader("윗치폼 주문서 파일 업로드 (여러 개 가능)", type=["csv", "xlsx", "xls"], accept_multiple_files=True)
with col2:
    bank_file = st.file_uploader("은행 입금 내역 파일 업로드", type=["csv", "xlsx", "xls"])

_, btn_space, _ = st.columns([2, 1, 2])
with btn_space:
    if st.button("정산 시작하기", use_container_width=True):
        st.session_state.is_calculated = True

def 파일_안전_로드(uploaded_file):
    if uploaded_file is None: return pd.DataFrame()
    try:
        file_name = uploaded_file.name.lower()
        if file_name.endswith('.csv'):
            try: return pd.read_csv(uploaded_file, encoding='utf-8')
            except Exception:
                uploaded_file.seek(0)
                return pd.read_csv(uploaded_file, encoding='cp949', errors='ignore')
        else:
            try: return pd.read_excel(uploaded_file)
            except Exception:
                uploaded_file.seek(0)
                return pd.read_excel(uploaded_file, header=None)
    except Exception:
        try:
            uploaded_file.seek(0)
            return pd.read_html(uploaded_file)[0].reset_index(drop=True)
        except Exception:
            return pd.DataFrame()

def to_csv_bytes_fail_safe(df):
    try: return df.to_csv(index=False).encode('utf-8-sig')
    except Exception: return df.to_csv(index=False).encode('cp949', errors='ignore')

# 정산 엔진 가동
if (order_files and bank_file) and st.session_state.is_calculated:
    try:
        all_orders = []
        for o_file in order_files:
            df = 파일_안전_로드(o_file)
            if df is not None and not df.empty:
                df.columns = df.columns.astype(str).str.strip()
                name_col = next((c for c in df.columns if any(k in c for k in ['입금자명', '구매자', '주문자', '이름'])), None)
                price_col = next((c for c in df.columns if any(k in c for k in ['주문금액', '금액', '가격', '결제'])), None)
                time_col = next((c for c in df.columns if any(k in c for k in ['주문일시', '일시', '날짜', '시간', '등록일'])), None)
                if name_col and price_col:
                    sub_df = df[[name_col, price_col]].copy()
                    sub_df['time'] = df[time_col] if time_col else "확인 불가"
                    sub_df.columns = ['name', 'price', 'time']
                    all_orders.append(sub_df)
                    
        orders_df = pd.concat(all_orders, ignore_index=True)
        orders_df['name'] = orders_df['name'].astype(str).str.strip()
        orders_df['price'] = pd.to_numeric(orders_df['price'].astype(str).str.replace(',', ''), errors='coerce').fillna(0)
        orders_df = orders_df[(orders_df['price'] > 0) & (~orders_df['name'].str.contains('합계|total|nan', case=False, na=False))].reset_index(drop=True)
        orders_df['order_id'] = orders_df.index

        # 실시간 필터링 연동
        filtered_orders_df = orders_df[~orders_df['order_id'].isin(st.session_state.deleted_orders)].copy()
        filtered_orders_df = filtered_orders_df[~filtered_orders_df['order_id'].astype(str).isin(st.session_state.refunded_orders.keys())]

        bank_raw = 파일_안전_로드(bank_file)
        bank_price_col, bank_name_col, bank_time_col = None, None, None
        for col in bank_raw.columns:
            if any(k in str(col) for k in ['입금금액', '금액', '취급액', '받은금액']): bank_price_col = col
            if any(k in str(col) for k in ['입금자명', '적요', '의뢰인', '내용', '거래내용']): bank_name_col = col
            if any(k in str(col) for k in ['거래일시', '일시', '거래일', '날짜', '시간']): bank_time_col = col
            
        if bank_price_col is None: bank_price_col = bank_raw.columns[2]
        if bank_name_col is None: bank_name_col = bank_raw.columns[4]
        if bank_time_col is None: bank_time_col = bank_raw.columns[0]

        bank_rows = []
        for idx, row in bank_raw.iterrows():
            if idx in st.session_state.deleted_bank_indexes: continue
            p_val = str(row[bank_price_col]).replace(',', '')
            n_val = str(row[bank_name_col]).strip()
            price_num = pd.to_numeric(p_val, errors='coerce')
            if pd.notna(price_num) and price_num > 0 and n_val != 'nan' and n_val != '':
                if not any(k in n_val for k in ['합계', '이월', '잔액', '출금']):
                    bank_rows.append({'bank_idx': idx, 'price': price_num, 'name': n_val, 'time': str(row[bank_time_col])})
        bank_tx = pd.DataFrame(bank_rows)

        duplicate_names = set()
        if not filtered_orders_df.empty:
            duplicate_names.update(filtered_orders_df['name'].value_counts()[filtered_orders_df['name'].value_counts() > 1].index.tolist())

        # 💡 수기 추가 명단의 합계 계산 추적 기믹 온
        manual_added_order_sum = sum(item['주문금액'] for item in st.session_state.manual_added_records)
        manual_added_bank_sum = sum(item['실제입금액'] for item in st.session_state.manual_added_records)

        # 수동 조정 완료된 실시간 거래 가액 트랙킹
        manual_total_gain = sum(v['bank_p'] for v in st.session_state.manual_confirmed.values())
        manual_form_change_sum = sum(v['order_p'] for v in st.session_state.manual_confirmed.values() if 'order_p' in v)

        # ⭐️ 총 금액 계산식에 [수기 추가 금액] 연동 반영
        total_refund_amount = sum(item['price'] for item in st.session_state.refunded_orders.values())
        total_order_price = filtered_orders_df['price'].sum() + manual_form_change_sum + manual_added_order_sum
        total_bank_price = (bank_tx['price'].sum() if not bank_tx.empty else 0) - total_refund_amount + manual_total_gain + manual_added_bank_sum

        # 금액 대조판
        anchor("sec_comparison")
        st.subheader("💰 최종 금액 대조 (순수 입금액 합계)")
        c_price1, c_price2, c_price3 = st.columns(3)
        c_price1.metric("📋 윗치폼 총 주문 금액", f"{int(total_order_price):,}원")
        c_price2.metric("🏦 통장 순수 입금액 합계", f"{int(total_bank_price):,}원")
        diff_price = total_bank_price - total_order_price
        with c_price3:
            if diff_price == 0: st.metric("금액 일치 여부", "🎯 100% 완전 일치", delta="0원")
            else: st.metric("금액 일치 여부", "⚠️ 차액 발생", delta=f"{int(diff_price):,}원", delta_color="inverse")

        # 실시간 매칭 엔진 프로세스
        matched_records, price_mismatch, unmatched_orders = [], [], []
        duplicate_groups = {name: {'orders': [], 'banks': []} for name in duplicate_names}
        
        bank_records = bank_tx.to_dict('records') if not bank_tx.empty else []
        for bank in bank_records:
            if bank['name'] in duplicate_groups:
                duplicate_groups[bank['name']]['banks'].append(bank)

        for _, order in filtered_orders_df.iterrows():
            o_id, o_name, o_price = order['order_id'], order['name'], order['price']
            
            # 수동 처리 반영 로직 고도화
            if str(o_id) in st.session_state.manual_confirmed:
                m_info = st.session_state.manual_confirmed[str(o_id)]
                matched_records.append({
                    "order_id": o_id, "bank_idx": None, "이름": o_name, 
                    "주문금액": int(m_info['order_p']), "실제입금액": int(m_info['bank_p']), 
                    "비고": "🛠️ 관리자 수동 교정 승인", "is_manual_add": False, "환불 처리": False, "주문 삭제": False
                })
                continue
                
            if o_name in duplicate_groups:
                duplicate_groups[o_name]['orders'].append(order.to_dict())
                continue
                
            exact_match_idx = next((i for i, b in enumerate(bank_records) if b['name'] == o_name and b['price'] == o_price), -1)
            if exact_match_idx != -1:
                bank = bank_records.pop(exact_match_idx)
                matched_records.append({
                    "order_id": o_id, "bank_idx": bank['bank_idx'], "이름": o_name, 
                    "주문금액": int(o_price), "실제입금액": int(bank['price']), 
                    "비고": "✅ 자동 매칭 성공", "is_manual_add": False, "환불 처리": False, "주문 삭제": False
                })
                continue
                
            name_match_idx = next((i for i, b in enumerate(bank_records) if b['name'] == o_name), -1)
            if name_match_idx != -1:
                bank = bank_records.pop(name_match_idx)
                price_mismatch.append({
                    "order_id": o_id, "bank_idx": bank['bank_idx'], "입금자명": o_name, 
                    "주문 금액": o_price, "통장 입금 금액": bank['price'], "차액": bank['price'] - o_price
                })
            else:
                unmatched_orders.append(order.to_dict())
        
        unknown_bank = [b for b in bank_records if b['name'] not in duplicate_names]
        active_dup_groups = {k: v for k, v in duplicate_groups.items() if len(v['orders']) > 0}

        # 차액 세부 원인 칸 구역
        anchor("sec_reason")
        if diff_price != 0:
            with st.expander("🔍 차액 원인 세부 정밀 칸 분석 (클릭하여 열기)", expanded=True):
                tab1, tab2, tab3 = st.tabs(["🚨 미입금자 명단 칸", "🔺 더 보낸 사람 명단 칸", "❓ 주문서 없는 내역 칸"])
                with tab1:
                    if unmatched_orders: st.dataframe(pd.DataFrame(unmatched_orders)[['name', 'price', 'time']].rename(columns={'name':'주문자','price':'금액'}), height=180, use_container_width=True)
                with tab2:
                    if price_mismatch: st.dataframe(pd.DataFrame(price_mismatch)[['입금자명', '주문 금액', '통장 입금 금액', '차액']], height=180, use_container_width=True)
                with tab3:
                    if unknown_bank: st.dataframe(pd.DataFrame(unknown_bank)[['name', 'price', 'time']].rename(columns={'name':'통장표기명','price':'입금액'}), height=180, use_container_width=True)

        st.subheader("📊 세부 정산 분류판")

        # 🎯 [1번 구역] 입금 확인 완료 명단
        anchor("sec_m1")
        if matched_records or st.session_state.manual_added_records or st.session_state.search_word:
            st.success("🎯 입금 확인 완료 명단 (주문금액 = 입금금액 일치)")
            
            sc_col1, sc_col2 = st.columns([8, 2])
            with sc_col1:
                st.session_state.search_word = st.text_input("🔍 완료 명단 내 성명 실시간 검색", value=st.session_state.search_word, placeholder="검색할 입금자명을 입력하세요.", key="search_box_final").strip()
            with sc_col2:
                st.markdown("<div style='line-height:2.4;'><br></div>", unsafe_allow_html=True)
                if st.button("🔄 검색 초기화", key="clear_final_btn"):
                    st.session_state.search_word = ""
                    st.rerun()
            
            # 메인 대조 완료 명단에 [수기 추가 명단] 실시간 병합 병동 구축
            master_matched_list = []
            for r in matched_records:
                master_matched_list.append(r)
            for idx, r in enumerate(st.session_state.manual_added_records):
                master_matched_list.append({
                    "order_id": f"manual_add_{idx}", "bank_idx": None, "이름": r['이름'],
                    "주문금액": r['주문금액'], "실제입금액": r['실제입금액'], "비고": r['비고'],
                    "is_manual_add": True, "환불 처리": False, "주문 삭제": False
                })
            
            matched_df = pd.DataFrame(master_matched_list) if master_matched_list else pd.DataFrame(columns=['order_id', 'bank_idx', '이름', '주문금액', '실제입금액', '비고', 'is_manual_add', '환불 처리', '주문 삭제'])
            if st.session_state.search_word and not matched_df.empty:
                matched_df = matched_df[matched_df['이름'].str.contains(st.session_state.search_word, na=False, case=False)]
            
            if not matched_df.empty:
                edited_df = st.data_editor(
                    matched_df[['order_id', 'bank_idx', '이름', '주문금액', '실제입금액', '비고', 'is_manual_add', '환불 처리', '주문 삭제']],
                    column_config={
                        "order_id": None, "bank_idx": None, "is_manual_add": None,
                        "이름": st.column_config.TextColumn("이름", disabled=True),
                        "주문금액": st.column_config.NumberColumn("주문금액", format="%d원", disabled=True),
                        "실제입금액": st.column_config.NumberColumn("실제입금액", format="%d원", disabled=True),
                        "비고": st.column_config.TextColumn("비고", disabled=True),
                        "환불 처리": st.column_config.CheckboxColumn("환불 처리", default=False),
                        "주문 삭제": st.column_config.CheckboxColumn("주문 삭제", default=False),
                    },
                    disabled=["이름", "주문금액", "실제입금액", "비고"],
                    key="main_data_editor", use_container_width=True, height=220
                )
                
                rerun_needed = False
                for idx, row in edited_df.iterrows():
                    orig_row = matched_df.iloc[idx]
                    if row['환불 처리'] and not orig_row['환불 처리']:
                        if row['is_manual_add']:
                            # 수기 추가 건 환불 처리
                            st.session_state.refunded_orders[str(row['order_id'])] = {'name': row['이름'], 'price': row['주문금액']}
                            # 수기 원본 리스트에서 제거해 총액 이중 계산 방지
                            st.session_state.manual_added_records = [item for item in st.session_state.manual_added_records if item['이름'] != row['이름']]
                        else:
                            st.session_state.refunded_orders[str(row['order_id'])] = {'name': row['이름'], 'price': row['주문금액']}
                        rerun_needed = True
                        
                    if row['주문 삭제'] and not orig_row['주문 삭제']:
                        if row['is_manual_add']:
                            st.session_state.manual_added_records = [item for item in st.session_state.manual_added_records if item['이름'] != row['이름']]
                        else:
                            st.session_state.deleted_orders.add(row['order_id'])
                            if row['bank_idx'] is not None: st.session_state.deleted_bank_indexes.add(row['bank_idx'])
                        rerun_needed = True
                if rerun_needed: st.rerun()
            else:
                st.info("조건에 맞는 내역이 완료 명단에 없습니다.")
                
            # 💡 [요청사항 반영 2] 명단에 수기로 직접 추가할 수 있는 컨트롤러 하단 결합
            with st.expander("👤 입금 완료 명단에 수기 직접 추가하기 제어 상자", expanded=False):
                add_col1, add_col2, add_col3 = st.columns(3)
                with add_col1: add_name = st.text_input("추가할 성명", key="add_m_name", placeholder="홍길동")
                with add_col2: add_o_p = st.number_input("폼 주문 금액 결정", min_value=0, step=100, value=0, key="add_m_op")
                with add_col3: add_b_p = st.number_input("실제 입금 금액 결정", min_value=0, step=100, value=0, key="add_b_op")
                
                if st.button("➕ 명단에 수기 추가", use_container_width=True):
                    if add_name.strip() != "":
                        st.session_state.manual_added_records.append({
                            "이름": add_name.strip(), "주문금액": add_o_p, "실제입금액": add_b_p, "비고": "✍️ 관리자 서면 수기 직접 추가"
                        })
                        st.success(f"👤 {add_name}님이 완료 명단에 성공적으로 가입 및 합산 연동되었습니다!")
                        st.rerun()
                    else:
                        st.error("성명을 바르게 입력해 주세요.")

        # ⚠️ [2번 구역] 금액 불일치 명단 칸 (💡 요청사항 반영 1: 폼 금액까지 전면 동시 수정 기능 장착!)
        anchor("sec_m2")
        st.markdown("<br>", unsafe_allow_html=True)
        if price_mismatch:
            st.warning("⚠️ 금액 불일치 명단 (주문금액과 입금금액이 다른 사람)")
            pm_view_df = pd.DataFrame(price_mismatch)[['입금자명', '주문 금액', '통장 입금 금액', '차액']]
            st.dataframe(pm_view_df, height=130, use_container_width=True)
            
            with st.expander("🛠️ 금액 불일치 상세 제어 (폼 금액 / 통장 입금액 양방향 동시 교정 상자)", expanded=True):
                for pm in price_mismatch:
                    m_col1, m_col2, m_col3, m_col4, m_col5, m_col6 = st.columns([1.2, 2.2, 2.2, 1.8, 1.8, 1.0])
                    with m_col1: st.markdown(f"👤 **{pm['입금자명']}**")
                    with m_col2: 
                        # 💡 폼 금액도 내 입맛대로 마음껏 고칠 수 있는 수정 칸 배치 완료
                        form_input = st.text_input("폼금액 수정", value=str(int(pm['주문 금액'])), key=f"form_in_{pm['order_id']}", label_visibility="visible")
                    with m_col3: 
                        mism_input = st.text_input("입금액 수정", value=str(int(pm['통장 입금 금액'])), key=f"mism_in_{pm['order_id']}", label_visibility="visible")
                    with m_col4:
                        st.markdown("<div style='line-height:1.4;'><br></div>", unsafe_allow_html=True)
                        if st.button("✅ 강제 승인", key=f"mism_btn_{pm['order_id']}", use_container_width=True):
                            # 두 가지 정보 묶음 주소로 전개하여 연동 트랙에 반환
                            st.session_state.manual_confirmed[str(pm['order_id'])] = {
                                'order_p': float(form_input.replace(',', '')),
                                'bank_p': float(mism_input.replace(',', ''))
                            }
                            st.session_state.deleted_bank_indexes.add(pm['bank_idx'])
                            st.rerun()
                    with m_col5:
                        st.markdown("<div style='line-height:1.4;'><br></div>", unsafe_allow_html=True)
                        if st.button("❌ 내역 삭제", key=f"mism_del_{pm['order_id']}", use_container_width=True):
                            st.session_state.deleted_orders.add(pm['order_id'])
                            st.session_state.deleted_bank_indexes.add(pm['bank_idx'])
                            st.rerun()

        # 🚨 [3번 구역] 미입금 명단 칸
        anchor("sec_m3")
        st.markdown("<br>", unsafe_allow_html=True)
        if unmatched_orders:
            st.error("🚨 미입금 명단 (주문서는 있으나 통장 입금 내역에 없는 사람)")
            um_view_df = pd.DataFrame(unmatched_orders)[['name', 'price', 'time']].rename(columns={'name':'이름','price':'주문금액','time':'제출시간'})
            st.dataframe(um_view_df, height=130, use_container_width=True)
            
            with st.expander("🛠️ 미입금 명단 상세 제어 (수동 확인/주문삭제)", expanded=True):
                for o in unmatched_orders:
                    b_col1, b_col2, b_col3, b_col4, b_col5 = st.columns([2, 2, 3, 2.5, 1.5])
                    with b_col1: st.markdown(f"👤 **{o['name']}**")
                    with b_col2: st.markdown(f"📋 주문: {int(o['price']):,}원")
                    with b_col3: input_val = st.text_input("실제 확인 입금액 입력", value=str(int(o['price'])), key=f"input_{o['order_id']}", label_visibility="collapsed")
                    with b_col4:
                        if st.button("✅ 입금 확인완료 (이동)", key=f"btn_{o['order_id']}", use_container_width=True):
                            st.session_state.manual_confirmed[str(o['order_id'])] = {
                                'order_p': float(o['price']),
                                'bank_p': float(input_val.replace(',', ''))
                            }
                            st.rerun()
                    with b_col5:
                        if st.button("❌ 주문삭제", key=f"del_order_{o['order_id']}", use_container_width=True):
                            st.session_state.deleted_orders.add(o['order_id'])
                            st.rerun()

        # ❓ [4번 구역] 주문서 없는 입금 명단 칸
        anchor("sec_m4")
        st.markdown("<br>", unsafe_allow_html=True)
        if unknown_bank:
            st.info("❓ 주문서 없는 입금 명단 (돈은 들어왔으나 윗치폼 주문서가 없는 내역)")
            ub_view_df = pd.DataFrame(unknown_bank)[['name', 'price', 'time']].rename(columns={'name':'통장표기명','price':'입금액','time':'거래일시'})
            st.dataframe(ub_view_df, height=130, use_container_width=True)
            
            with st.expander("🛠️ 주문서 없는 입금 내역 삭제 제어 상자", expanded=False):
                for b in unknown_bank:
                    ub_col1, ub_col2, ub_col3 = st.columns([4, 4, 2])
                    with ub_col1: st.markdown(f"👤 통장 표기: **{b['name']}** ({b['time']})")
                    with ub_col2: st.markdown(f"🏦 금액: {int(b['price']):,}원")
                    with ub_col3:
                        if st.button("내역삭제", key=f"del_bank_{b['bank_idx']}", use_container_width=True):
                            st.session_state.deleted_bank_indexes.add(b['bank_idx'])
                            st.rerun()

        # 👥 [5번 구역] 동명이인 중복 확인 칸
        anchor("sec_m5")
        st.markdown("<br>", unsafe_allow_html=True)
        if active_dup_groups:
            st.subheader("👥 동명이인 중복 확인 칸")
            for name, group in active_dup_groups.items():
                with st.expander(f"👤 중복 성명 그룹 대상자: {name} (열기/닫기)", expanded=True):
                    orders, banks = group['orders'], group['banks']
                    st.markdown("💡 데이터가 일치하는 건을 골라 개별 승인하거나 일괄 전체 승인을 눌러 처리하세요.")
                    
                    if st.button("✨ 이 그룹 일괄 전체 매칭 승인", key=f"all_app_{name}"):
                        for o_sub, b_sub in zip(orders, banks):
                            st.session_state.manual_confirmed[str(o_sub['order_id'])] = {
                                'order_p': float(o_sub['price']), 'bank_p': float(b_sub['price'])
                            }
                            st.session_state.deleted_bank_indexes.add(b_sub['bank_idx'])
                        st.rerun()
                    
                    grid_col1, grid_col2, grid_col3 = st.columns([4.5, 4.5, 3])
                    with grid_col1:
                        st.markdown("**📝 윗치폼 주문서 접수 내역**")
                        order_options = [f"📝 {int(o['price']):,}원 | 시간: {o['time']}" for o in orders]
                        selected_order_opt = st.radio(f"{name} 폼 선택", order_options, key=f"radio_order_{name}", label_visibility="collapsed")
                        chosen_order = orders[order_options.index(selected_order_opt)]
                    with grid_col2:
                        st.markdown("**💰 실제 통장 입금 내역**")
                        if banks:
                            bank_options = [f"💰 {int(b['price']):,}원 | 시간: {b['time']}" for b in banks]
                            selected_bank_opt = st.radio(f"{name} 통장 선택", bank_options, key=f"radio_bank_{name}", label_visibility="collapsed")
                            chosen_bank = banks[bank_options.index(selected_bank_opt)]
                        else:
                            st.write("⚠️ 입금 내역 없음")
                            chosen_bank = None
                    with grid_col3:
                        st.markdown("**🛠️ 매칭 승인/삭제**")
                        default_val = int(chosen_bank['price']) if chosen_bank else int(chosen_order['price'])
                        m_input = st.text_input("최종 금액 확인", value=str(default_val), key=f"dup_in_{chosen_order['order_id']}", label_visibility="collapsed")
                        btn_c1, btn_c2 = st.columns(2)
                        with btn_c1:
                            if st.button("승인", key=f"dup_approve_{chosen_order['order_id']}", use_container_width=True):
                                st.session_state.manual_confirmed[str(chosen_order['order_id'])] = {
                                    'order_p': float(chosen_order['price']),
                                    'bank_p': float(m_input.replace(',', ''))
                                }
                                if chosen_bank: st.session_state.deleted_bank_indexes.add(chosen_bank['bank_idx'])
                                st.rerun()
                        with btn_c2:
                            if st.button("삭제", key=f"dup_del_{chosen_order['order_id']}", use_container_width=True):
                                st.session_state.deleted_orders.add(chosen_order['order_id'])
                                st.rerun()

        # ↩️ [6번 구역] 환불 처리 완료 칸
        anchor("sec_m6")
        st.markdown("<br>", unsafe_allow_html=True)
        st.subheader("↩️ 환불 처리 완료 칸")
        if st.session_state.refunded_orders:
            refund_rows = [{"환불자 성명": item['name'], "환불 차감 금액": f"-{int(item['price']):,}원", "처리 결과": "환불 및 대조판 차감 완료"} for item in st.session_state.refunded_orders.values()]
            st.dataframe(pd.DataFrame(refund_rows), use_container_width=True, height=130)
        else:
            st.info("아직 환불 처리 완료된 내역이 없습니다.")

        # 📥 최종 결과 엑셀(CSV) 내보내기 구역
        anchor("sec_download")
        st.markdown("<hr>", unsafe_allow_html=True)
        st.subheader("📥 정산 반영 파일 내보내기")
        
        # 1. 원본 주문서 복사 및 상태 구축
        export_list = []
        for _, row in orders_df.iterrows():
            if row['order_id'] in st.session_state.deleted_orders: continue
            
            # 수동 교정 이력이 존재한다면 금액 갱신 처리
            target_price = row['price']
            status_text = "정상입금완료"
            
            if str(row['order_id']) in st.session_state.manual_confirmed:
                target_price = st.session_state.manual_confirmed[str(row['order_id'])]['order_p']
                status_text = "관리자수동교정승인"
            if str(row['order_id']) in st.session_state.refunded_orders:
                status_text = "환불차감완료"
                
            export_list.append({
                "이름": row['name'],
                "최종정산금액": int(target_price),
                "주문시간": row['time'],
                "정산_상태": status_text
            })
            
        # 2. 수기 추가 명단도 엑셀 최종본에 행 단위로 밀어넣어 완전 보존
        for r in st.session_state.manual_added_records:
            export_list.append({
                "이름": r['이름'],
                "최종정산금액": int(r['주문금액']),
                "주문시간": "✍️ 수기 추가 건 (확인 불가)",
                "정산_상태": "수기직접추가완료"
            })
            
        final_orders_export = pd.DataFrame(export_list)
            
        st.download_button(
            label="📋 최종 정정된 윗치폼 주문서 다운로드 (삭제/교정 완벽 반영)",
            data=to_csv_bytes_fail_safe(final_orders_export),
            file_name="최종_정정_윗치폼_주문서.csv",
            mime="text/csv",
            use_container_width=True
        )
            
    except Exception as e:
        st.error(f"파일 연산 도중 예기치 못한 에러가 발생했습니다: {e}")