import streamlit as st
import singbox_converter # Ini modul yang udah kita bikin bareng

# Konfigurasi halaman
st.set_page_config(
    page_title="Swiss Army VPN Tools",
    page_icon="🛠️",
    layout="wide"
)

# --- Fungsi untuk halaman Sing-Box Converter ---
def singbox_converter_page():
    st.header("⚙️ Sing-Box Config Converter")
    st.write("Di sini lo bisa konversi link VPN dan atur config Sing-Box lo.")
    
    # Input area untuk link VPN
    vpn_links = st.text_area("Masukkan link VPN (VMess/VLESS/Trojan), satu link per baris:", height=200)

    # Input area untuk template config Sing-Box
    singbox_template = st.text_area("Masukkan template config Sing-Box (JSON):", height=400, help="Pastikan ini adalah JSON yang valid.")

    converted_config = None
    if st.button("🚀 Konversi Config"):
        if not vpn_links or not singbox_template:
            st.error("⚠️ Link VPN atau template config nggak boleh kosong, tod!")
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
    st.write("- **⚙️ Sing-Box Config Converter**: Buat ngatur dan ngerapihin konfigurasi Sing-Box lo secara otomatis.")
    st.write("- **🎬 Media Downloader**: Buat download media dari berbagai platform sosial (soon).")
    st.write("- **🔐 Login & Pengaturan Akun**: Buat nyimpen settingan lo biar lebih nyaman (soon).")
    st.markdown("---")
    
    st.subheader("Pesan dari Gua:")
    st.info("Ingat, **tod**! Fitur yang Coming Soon lagi dalam tahap pengembangan. Kopi sama rokoknya udah nyampe ya di markas gua, makasih banyak! 😎")

# --- Sidebar Navigasi ---
st.sidebar.title("Navigasi")
page_selection = st.sidebar.radio(
    "Pilih Halaman:",
    ("🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun")
)

# Menampilkan halaman sesuai pilihan user
if page_selection == "🏠 Homepage":
    homepage()
elif page_selection == "⚙️ Sing-Box Converter":
    singbox_converter_page()
elif page_selection == "🎬 Media Downloader":
    media_downloader_page()
elif page_selection == "🔐 Login & Pengaturan Akun":
    login_page()
