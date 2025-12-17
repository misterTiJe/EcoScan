import streamlit as st
import tensorflow as tf
import numpy as np
from PIL import Image, ImageOps
import pandas as pd
import time
import plotly.express as px
import datetime

st.set_page_config(
    page_title="EcoScan - Smart Waste Sorter",
    page_icon="♻️",
    layout="wide",
    initial_sidebar_state="expanded"
)

def local_css(file_name):
    try:
        with open(file_name) as f:
            st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)
    except FileNotFoundError:
        st.warning(f"File {file_name} tidak ditemukan. Pastikan ada di folder project.")

local_css("style.css")

if 'users_db' not in st.session_state:
    st.session_state['users_db'] = {}
if 'current_user' not in st.session_state:
    st.session_state['current_user'] = None
if 'logged_in' not in st.session_state:
    st.session_state['logged_in'] = False
if 'history' not in st.session_state:
    st.session_state['history'] = []

CLASS_LABELS = {
    0: "Cardboard (Karton)", 1: "Glass (Kaca)", 2: "Metal (Logam)",
    3: "Paper (Kertas)", 4: "Plastic (Plastik)", 5: "Trash (Residu)"
}

WASTE_INFO = {
    0: {"action": "Pipihkan.", "bin": "🟦 Tong Biru"},
    1: {"action": "Cuci bersih.", "bin": "⬜ Tong Putih"},
    2: {"action": "Remukkan.", "bin": "🟧 Tong Jingga"},
    3: {"action": "Tumpuk rapi.", "bin": "🟦 Tong Biru"},
    4: {"action": "Lepas label.", "bin": "🟨 Tong Kuning"},
    5: {"action": "Buang ke TPA.", "bin": "⬛ Tong Hitam"}
}

@st.cache_resource
def load_model():
    try:
        return tf.keras.models.load_model('model_sampah.h5')
    except:
        return None

def preprocess_image(image):
    image = ImageOps.fit(image, (180, 180), Image.Resampling.LANCZOS)
    img_array = np.array(image)
    return np.expand_dims(img_array, axis=0)

def auth_page():
    st.markdown("<h1 style='text-align: center; color: #2E8B57;'>♻️ EcoScan</h1>", unsafe_allow_html=True)
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])

    with tab2:
        st.subheader("Buat Akun Baru")
        with st.form("register_form"):
            new_user = st.text_input("Username Baru")
            new_name = st.text_input("Nama Lengkap")
            new_pass = st.text_input("Password", type='password')
            reg_submit = st.form_submit_button("Daftar")
            if reg_submit:
                if new_user in st.session_state['users_db']:
                    st.error("Username sudah terpakai!")
                elif new_user and new_pass:
                    st.session_state['users_db'][new_user] = {
                        'password': new_pass,
                        'name': new_name,
                        'points': 0,
                        'join_date': datetime.date.today()
                    }
                    st.success("Registrasi berhasil! Silakan Login.")
                else:
                    st.warning("Mohon lengkapi data.")

    with tab1:
        st.subheader("Masuk")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type='password')
            login_submit = st.form_submit_button("Masuk")
            if login_submit:
                user_data = st.session_state['users_db'].get(username)
                if user_data and user_data['password'] == password:
                    st.session_state['logged_in'] = True
                    st.session_state['current_user'] = username
                    st.success("Login Berhasil!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("Username atau Password salah (atau belum register).")
        st.info("💡 **Catatan:** Karena ini demo, data akan hilang jika halaman di-refresh. Silakan Register dulu.")

def home_page():
    user = st.session_state['current_user']
    data = st.session_state['users_db'][user]
    st.title(f"Hai, {data['name']}! 👋")
    st.markdown("Mulai scan sampahmu hari ini untuk bumi yang lebih bersih.")

    c1, c2 = st.columns(2)
    c1.metric("Poin Saya", f"{data['points']} XP")
    c2.metric("Scan Hari Ini", len(st.session_state['history']))

    st.markdown("---")
    st.subheader("📸 Mulai Scan")

    mode = st.radio("Pilih Metode:", ["Upload Gambar", "Kamera"], horizontal=True)
    input_img = None

    if mode == "Upload Gambar":
        input_img = st.file_uploader("Pilih file...", type=['jpg','png','jpeg'])
    else:
        input_img = st.camera_input("Ambil foto")

    if input_img:
        col1, col2 = st.columns([1, 2])
        with col1:
            img = Image.open(input_img)
            st.image(img, caption="Preview", use_container_width=True)
        with col2:
            model = load_model()
            if model:
                with st.spinner("Menganalisis..."):
                    processed = preprocess_image(img)
                    pred = model.predict(processed)
                    score = tf.nn.softmax(pred[0])
                    idx = np.argmax(score)
                    label = CLASS_LABELS[idx]
                    conf = 100 * np.max(score)

                    st.success(f"**Terdeteksi: {label}**")
                    st.progress(int(conf))
                    st.write(f"**Tingkat Keyakinan:** {conf:.2f}%")

                    with st.expander("Lihat Detail Analisis"):
                        probs = score.numpy()
                        chart_data = pd.DataFrame({
                            "Jenis Sampah": [CLASS_LABELS[i] for i in range(6)],
                            "Probabilitas": probs * 100
                        })
                        st.bar_chart(chart_data.set_index("Jenis Sampah"))

                    info = WASTE_INFO[idx]
                    st.info(f"👉 {info['action']} Masukkan ke **{info['bin']}**")

                    img_id = f"{input_img.size}_{len(st.session_state['history'])}"
                    if st.button("✅ Selesai & Klaim Poin", key=img_id):
                        st.session_state['users_db'][user]['points'] += 50
                        st.session_state['history'].append({
                            "user": user,
                            "waktu": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
                            "jenis": label,
                            "poin": "+50"
                        })
                        st.balloons()
                        time.sleep(1)
                        st.rerun()

def history_page():
    st.title("📜 Riwayat Aktivitas")
    user = st.session_state['current_user']
    user_history = [h for h in st.session_state['history'] if h['user'] == user]
    if not user_history:
        st.info("Belum ada riwayat scan.")
    else:
        df = pd.DataFrame(user_history)
        st.dataframe(df[['waktu', 'jenis', 'poin']], use_container_width=True)
        counts = df['jenis'].value_counts().reset_index()
        counts.columns = ['Jenis', 'Jumlah']
        fig = px.bar(counts, x='Jenis', y='Jumlah', color='Jenis', title="Statistik Sampahmu")
        st.plotly_chart(fig, use_container_width=True)

def points_page():
    st.title("🏆 Leaderboard & Poin")
    user = st.session_state['current_user']
    points = st.session_state['users_db'][user]['points']
    level = "Pemula 🌱"
    if points > 100:
        level = "Penggiat Lingkungan 🌿"
    if points > 500:
        level = "Pahlawan Bumi 🌍"
    st.markdown(f"""
    <div class="profile-card">
        <h2>Total Poin: {points} XP</h2>
        <h3 style="color: gold;">{level}</h3>
        <p>Kumpulkan 500 XP untuk mencapai level Pahlawan Bumi!</p>
    </div>
    """, unsafe_allow_html=True)
    progress = min(points / 500, 1.0)
    st.progress(progress)
    st.caption(f"Progress Level: {int(progress*100)}%")
    st.subheader("🎁 Tukarkan Poin (Coming Soon)")
    c1, c2, c3 = st.columns(3)
    c1.button("Voucher E-Wallet (1000 Poin)", disabled=True)
    c2.button("Donasi Pohon (500 Poin)", disabled=True)
    c3.button("Merchandise (2000 Poin)", disabled=True)

def profile_page():
    st.title("👤 Profil Pengguna")
    user = st.session_state['current_user']
    data = st.session_state['users_db'][user]
    col1, col2 = st.columns([1, 2])
    with col1:
        st.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=150)
    with col2:
        st.markdown(f"""
        <div class="profile-card" style="text-align: left;">
            <p><strong>Username:</strong> {user}</p>
            <p><strong>Nama Lengkap:</strong> {data['name']}</p>
            <p><strong>Bergabung Sejak:</strong> {data['join_date']}</p>
            <p><strong>Status Akun:</strong> <span style="color:green; font-weight:bold;">Aktif</span></p>
        </div>
        """, unsafe_allow_html=True)
        if st.button("Edit Profil"):
            st.warning("Fitur edit profil sedang dalam pengembangan.")

def settings_page():
    st.title("⚙️ Pengaturan")
    st.subheader("Tampilan")
    st.toggle("Mode Gelap (Dark Mode)", value=False)
    st.subheader("Notifikasi")
    st.toggle("Email Newsletter", value=True)
    st.toggle("Pengingat Harian", value=False)
    st.divider()
    st.subheader("Keamanan")
    if st.button("Ubah Password"):
        st.info("Silakan hubungi admin untuk reset password.")
    st.divider()
    st.error("Zona Bahaya")
    if st.button("Hapus Akun", type="primary"):
        st.error("Akun tidak dapat dihapus di mode demo.")

def main():
    if not st.session_state['logged_in']:
        auth_page()
    else:
        with st.sidebar:
            st.title("EcoScan 🌿")
            st.write(f"Halo, **{st.session_state['users_db'][st.session_state['current_user']]['name']}**")
            menu = st.radio(
                "Navigasi",
                ["🏠 Halaman Utama", "📜 Histori", "🏆 Poin", "👤 Profil", "⚙️ Pengaturan"],
                label_visibility="collapsed"
            )
            st.markdown("---")
            if st.button("🚪 Logout"):
                st.session_state['logged_in'] = False
                st.session_state['current_user'] = None
                st.rerun()

        if "Halaman Utama" in menu:
            home_page()
        elif "Histori" in menu:
            history_page()
        elif "Poin" in menu:
            points_page()
        elif "Profil" in menu:
            profile_page()
        elif "Pengaturan" in menu:
            settings_page()

if __name__ == "__main__":
    main()