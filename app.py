import streamlit as st

st.title('🎈 シンプルカウンターアプリ')

if 'count' not in st.session_state:
    st.session_state.count = 0

increment = st.button('カウントアップ')
if increment:
    st.session_state.count += 1

st.write('カウント:', st.session_state.count)