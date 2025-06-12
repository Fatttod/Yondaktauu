import streamlit as st
import singbox_converter
import os

# Konfigurasi halaman
st.set_page_config(
    page_title="Swiss Army VPN Tools",
    page_icon="🛠️",
    layout="wide"
)

# Inisialisasi session state untuk status login
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'page_selection' not in st.session_state:
    st.session_state.page_selection = "🏠 Homepage" # Default jika sudah login

# Fungsi untuk membaca template dari file
def load_template_from_file(file_path="singbox-template.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    else:
        return None

# --- Fungsi untuk halaman Sing-Box Converter ---
def singbox_converter_page():
    st.header("⚙️ Sing-Box Config Converter")
    st.write("Di sini lo bisa konversi link VPN dan atur config Sing-Box lo.")
    
    vpn_links = st.text_area("Masukkan link VPN (VMess/VLESS/Trojan), satu link per baris:", height=200)
    singbox_template = load_template_from_file()

    if singbox_template is None:
        st.error(f"⚠️ File template 'singbox-template.txt' tidak ditemukan di direktori yang sama, tod! Pastikan file ada.")

    if st.button("🚀 Konversi Config"):
        if not vpn_links:
            st.error("⚠️ Link VPN nggak boleh kosong, tod!")
        elif singbox_template is None:
            st.error("⚠️ Template config tidak dapat dimuat karena file 'singbox-template.txt' tidak ditemukan.")
        else:
            try:
                result = singbox_converter.process_singbox_config(vpn_links, singbox_template)
                
                if result["status"] == "success":
                    st.success("✅ Config berhasil dikonversi, mek!")
                    converted_config = result["config_content"]
                    st.code(converted_config, language="json")
                    
                    st.download_button(
                        label="⬇️ Download Config JSON",
                        data=converted_config,
                        file_name="converted_singbox_config.json",
                        mime="application/json",
                        key="download_button"
                    )
                    
                    st.button(
                        label="⬆️ Update ke GitHub (Coming Soon)",
                        on_click=lambda: st.info("Fitur Update ke GitHub akan tersedia setelah fitur Login & Pengaturan Akun selesai, tod!"),
                        key="github_update_button"
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

# --- Fungsi untuk halaman Login/Pengaturan Akun ---
def login_page():
    st.header("🔐 Login & Pengaturan Akun")
    st.write("Di sini lo bisa login atau daftar akun.")
    
    login_tab, signup_tab = st.tabs(["Login", "Daftar"])

    with login_tab:
        st.subheader("Masuk ke Akun Lo")
        username_login = st.text_input("Username", key="username_login")
        password_login = st.text_input("Password", type="password", key="password_login")
        if st.button("Login", key="do_login_button"):
            # Placeholder untuk logika login
            if username_login == "user" and password_login == "pass": # Contoh kredensial dummy
                st.session_state.logged_in = True
                st.session_state.page_selection = "🏠 Homepage" # Redirect ke homepage setelah login
                st.success("Login Berhasil! Selamat datang!")
                st.rerun()
            else:
                st.error("Username atau Password salah, tod!")
            st.info("Logika login sebenarnya akan membutuhkan database lokal.")

    with signup_tab:
        st.subheader("Bikin Akun Baru")
        username_signup = st.text_input("Username Baru", key="username_signup")
        password_signup = st.text_input("Password Baru", type="password", key="password_signup")
        confirm_password_signup = st.text_input("Konfirmasi Password", type="password", key="confirm_password_signup")
        if st.button("Daftar", key="do_signup_button"):
            # Placeholder untuk logika daftar
            if password_signup != confirm_password_signup:
                st.error("Konfirmasi Password nggak cocok, mek!")
            elif username_signup and password_signup:
                st.success(f"Akun '{username_signup}' berhasil didaftarkan (placeholder).")
                st.info("Logika pendaftaran sebenarnya akan menyimpan data di database lokal.")
                # Setelah daftar, bisa langsung login atau dialihkan ke halaman login
            else:
                st.error("Username dan Password nggak boleh kosong, tod!")

    if st.session_state.logged_in:
        st.markdown("---")
        st.subheader("Pengaturan Akun & GitHub")
        st.write("Di sini lo bisa simpen info repo GitHub dan token lo.")
        st.info("Fitur penyimpanan ini **Coming Soon**, akan terintegrasi dengan sistem login.")
        if st.button("Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.session_state.page_selection = "🔐 Login & Pengaturan Akun" # Redirect ke login page
            st.success("Berhasil Logout.")
            st.rerun()

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

    if st.button("⚙️ **Sing-Box Config Converter**", use_container_width=True):
        st.session_state.page_selection = "⚙️ Sing-Box Converter"
        st.rerun()
    st.markdown("Buat ngatur dan ngerapihin konfigurasi Sing-Box lo secara otomatis.")
    st.markdown("---")

    if st.button("🎬 **Media Downloader** (Coming Soon)", use_container_width=True):
        st.session_state.page_selection = "🎬 Media Downloader"
        st.rerun()
    st.markdown("Buat download media dari berbagai platform sosial.")
    st.markdown("---")

    if st.button("🔐 **Login & Pengaturan Akun**", use_container_width=True): # Tidak lagi "Coming Soon" labelnya
        st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
        st.rerun()
    st.markdown("Buat nyimpen settingan lo biar lebih nyaman.")
    st.markdown("---")
    
    st.subheader("Pesan dari Gua:")
    st.info("Ingat, **tod**! Fitur yang Coming Soon lagi dalam tahap pengembangan. Kopi sama rokoknya udah nyampe ya di markas gua, makasih banyak! 😎")

# --- Kontrol Navigasi Utama ---
if not st.session_state.logged_in:
    # Jika belum login, paksa ke halaman login
    st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
    login_page()
else:
    # Sidebar Navigasi jika sudah login
    st.sidebar.title("Navigasi")
    page_selection = st.sidebar.radio(
        "Pilih Halaman:",
        ("🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"),
        index=["🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"].index(st.session_state.page_selection)
    )

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
    
