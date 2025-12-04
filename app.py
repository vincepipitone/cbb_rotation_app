import streamlit as st
from rotation_chart import generate_rotation_chart
import matplotlib.pyplot as plt

st.set_page_config(layout="wide", page_title="CBB Rotation Chart Generator")

st.title("🏀 CBB Rotation Chart Generator")
st.markdown("""
Paste a **StatBroadcast XML URL** or just the **game ID** below.


Then click **Generate Rotation Chart**.
""")

# -------------------------------
# URL INPUT HANDLING
# -------------------------------
user_input = st.text_input("Enter XML URL or Game ID:")

def normalize_url(input_str: str):
    input_str = input_str.strip()
    if input_str.isdigit():
        return f"https://stats.statbroadcast.com/broadcast/xml/basketball/{input_str}.xml"
    return input_str

final_url = normalize_url(user_input)

# -------------------------------
# GENERATE BUTTON
# -------------------------------
if st.button("Generate Rotation Chart"):
    if not user_input.strip():
        st.error("Please enter a valid game ID or StatBroadcast XML URL.")
    else:
        try:
            with st.spinner("Generating rotation chart…"):
                fig = generate_rotation_chart(final_url)

            st.success("Chart generated successfully!")
            st.pyplot(fig, use_container_width=True)

            # Download button
            buf = st.download_button(
                label="⬇️ Download Chart as PNG",
                data=fig_to_png_bytes(fig),
                file_name="rotation_chart.png",
                mime="image/png"
            )

        except Exception as e:
            st.error(f"An error occurred: {e}")

import io

def fig_to_png_bytes(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=200, bbox_inches="tight")
    buf.seek(0)
    return buf.getvalue()

