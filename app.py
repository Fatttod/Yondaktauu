import streamlit as st
import singbox_converter # Ini modul yang udah kita bikin bareng
import os

# Konfigurasi halaman
st.set_page_config(
    page_title="Swiss Army VPN Tools",
    page_icon="🛠️",
    layout="wide"
)

# Fungsi untuk membaca template dari file
def load_template_from_file(file_path="singbox-template.txt"):
    """
    Membaca konten template Sing-Box dari file.
    """
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    else:
        # st.error(f"File template '{file_path}' tidak ditemukan di direktori yang sama, tod! Pastikan file ada.")
        return None # Mengembalikan None jika file tidak ditemukan

# --- Fungsi untuk halaman Sing-Box Converter ---
def singbox_converter_page():
    st.header("⚙️ Sing-Box Config Converter")
    st.write("Di sini lo bisa konversi link VPN dan atur config Sing-Box lo.")
    
    # Input area untuk link VPN
    vpn_links = st.text_area("Masukkan link VPN (VMess/VLESS/Trojan), satu link per baris:", height=200)

    # Ambil template dari file secara otomatis
    singbox_template = load_template_from_file()

    converted_config = None
    
    # Tampilkan error jika template tidak ditemukan sebelum tombol konversi
    if singbox_template is None:
        st.error(f"⚠️ File template 'singbox-template.txt' tidak ditemukan di direktori yang sama, tod! Pastikan file ada.")

    if st.button("🚀 Konversi Config"):
        if not vpn_links:
            st.error("⚠️ Link VPN nggak boleh kosong, tod!")
        elif singbox_template is None:
            st.error("⚠️ Template config tidak dapat dimuat karena file 'singbox-template.txt' tidak ditemukan.")
        else:
            try:
                # Panggil fungsi konversi dari singbox_converter.py
                result = singbox_converter.process_singbox_config(vpn_links, singbox_template)
                
                if result["status"] == "success":
                    st.success("✅ Config berhasil dikonversi, mek!")
                    converted_config = result["config_content"]
                    st.code(converted_config, language="json")
                    
                    # Tambahkan tombol download
                    st.download_button(
                        label="⬇️ Download Config JSON",
                        data=converted_config,
                        file_name="converted_singbox_config.json",
                        mime="application/json"
                    )
                else:
                    st.error(f"❌ Gagal konversi: {result['message']}")
            except Exception as e:
                st.error(f"Terjadi error saat memproses konversi: {e}")

# --- Fungsi untuk halaman Media Downloader ---
def media_downloader_page():
    st.header("🎬 Media Downloader")
    st.write("Tempats buat download video/audio dari berbagai platform sosmed.")
    st.info("Fitur ini **Coming Soon**, mek! Sabar ya, lagi digodok biar mantap! 😉")
    # Di sini nanti bakal ada input URL dan pilihan download

# --- Fungsi untuk halaman Login/Pengaturan Akun ---
def login_page():
    st.header("🔐 Login & Pengaturan Akun")
    st.write("Di sini lo bisa login dan atur info repo GitHub lo.")
    st.info("Fitur ini juga **Coming Soon**, tod! Gua lagi nyiapin backend lokalnya biar aman dan stabil. 💪")
    # Di sini nanti bakal ada form login dan pengaturan

# --- Homepage Utama ---
def homepage():
    st.title("🛠️ Swiss Army VPN Tools")
    st.markdown("---")
    st.write("""
    Halo **mek**! Selamat datang di **Swiss Army VPN Tools**! 
    Ini adalah pusat kendali lo buat ngurusin segala hal tentang VPN dan media.
    Pilih fitur yang mau lo pakai di sidebar kiri ya.
    """)
    st.markdown("---")
    
    st.subheader("Fitur yang Tersedia:")

    # Card/Section untuk Sing-Box Converter
    if st.button("⚙️ **Sing-Box Config Converter**", use_container_width=True):
        st.session_state.page_selection = "⚙️ Sing-Box Converter"
        st.rerun()
    st.markdown("Buat ngatur dan ngerapihin konfigurasi Sing-Box lo secara otomatis.")
    st.markdown("---") # Garis pemisah antar fitur

    # Card/Section untuk Media Downloader
    if st.button("🎬 **Media Downloader** (Coming Soon)", use_container_width=True):
        st.session_state.page_selection = "🎬 Media Downloader"
        st.rerun()
    st.markdown("Buat download media dari berbagai platform sosial.")
    st.markdown("---") # Garis pemisah antar fitur

    # Card/Section untuk Login & Pengaturan Akun
    if st.button("🔐 **Login & Pengaturan Akun** (Coming Soon)", use_container_width=True):
        st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
        st.rerun()
    st.markdown("Buat nyimpen settingan lo biar lebih nyaman.")
    st.markdown("---") # Garis pemisah antar fitur
    
    st.subheader("Pesan dari Gua:")
    st.info("Ingat, **tod**! Fitur yang Coming Soon lagi dalam tahap pengembangan. Kopi sama rokoknya udah nyampe ya di markas gua, makasih banyak! 😎")

# --- Sidebar Navigasi ---
st.sidebar.title("Navigasi")

# Gunakan session_state untuk mempertahankan pilihan halaman
if 'page_selection' not in st.session_state:
    st.session_state.page_selection = "🏠 Homepage"

page_selection = st.sidebar.radio(
    "Pilih Halaman:",
    ("🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"),
    index=["🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"].index(st.session_state.page_selection)
)

# Update session_state jika pilihan sidebar berubah
if page_selection != st.session_state.page_selection:
    st.session_state.page_selection = page_selection

# Menampilkan halaman sesuai pilihan user
if st.session_state.page_selection == "🏠 Homepage":
    homepage()
elif st.session_state.page_selection == "⚙️ Sing-Box Converter":
    singbox_converter_page()
elif st.session_state.page_selection == "🎬 Media Downloader":
    media_downloader_page()
elif st.session_state.page_selection == "🔐 Login & Pengaturan Akun":
    login_page()
    
