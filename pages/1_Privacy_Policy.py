import streamlit as st

st.set_page_config(page_title="Privacy Policy | HydroAegis AI", layout="wide")

st.title("Informativa sulla Privacy")

termly_html = """
<style>
[data-custom-class='body'], [data-custom-class='body'] * {
"""

st.markdown(termly_html, unsafe_allow_html=True)
