import streamlit as st
import singbox_converter
import os
import mysql.connector
from passlib.hash import pbkdf2_sha256
import tempfile # Digunakan untuk menyimpan sertifikat CA sementara

# --- Konfigurasi Awal Aplikasi Streamlit ---
st.set_page_config(
    page_title="Swiss Army VPN Tools",
    page_icon="🛠️",
    layout="wide"
)

# --- Inisialisasi Session State ---
if 'logged_in' not in st.session_state:
    st.session_state.logged_in = False
if 'username' not in st.session_state:
    st.session_state.username = None
if 'page_selection' not in st.session_state:
    # Arahkan selalu ke halaman Login/Pengaturan Akun jika belum login
    st.session_state.page_selection = "🔐 Login & Pengaturan Akun"

# --- Fungsi Koneksi Database MySQL Aiven ---
def get_mysql_connection():
    """Mendapatkan koneksi ke database MySQL Aiven menggunakan st.secrets."""
    conn = None
    ca_cert_path = None

    try:
        # Menulis SSL CA content ke file sementara jika disediakan di st.secrets
        if "ssl_ca_content" in st.secrets["mysql"]:
            temp_dir = tempfile.gettempdir() # Dapatkan direktori temp sistem (misal /tmp di Linux)
            ca_cert_path = os.path.join(temp_dir, "aiven_ca.pem") # Nama file sementara

            # Tulis konten sertifikat ke file sementara
            with open(ca_cert_path, "w") as f:
                f.write(st.secrets["mysql"]["ssl_ca_content"])
            # st.info(f"CA certificate ditulis ke file sementara: {ca_cert_path}") # Debugging info, bisa dihapus

        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_ca=ca_cert_path # Gunakan path file sementara
        )
        return conn
    except Exception as e:
        # Menampilkan pesan error yang lebih informatif jika kredensial tidak ditemukan
        if "mysql" not in st.secrets:
            st.error("❌ Kredensial MySQL tidak ditemukan di Streamlit Secrets. Pastikan Anda telah mengaturnya di 'Advanced settings' aplikasi.")
        else:
            st.error(f"❌ Gagal koneksi ke database MySQL Aiven, tod! Pastikan kredensial di 'Advanced settings' Streamlit Cloud benar dan format SSL CA content tepat. Error: {e}")
        return None
    # Tidak perlu finally di sini karena koneksi akan ditutup di fungsi pemanggil

def init_db():
    """Menginisialisasi tabel users jika belum ada di MySQL."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            # Gunakan VARCHAR(255) yang cukup besar untuk password hash
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL
                )
            ''')
            conn.commit()
            # st.success("Database users siap!") # Debugging info, bisa dihapus
        except Exception as e:
            st.error(f"Error saat inisialisasi tabel database: {e}")
        finally:
            if conn: # Pastikan conn tidak None sebelum ditutup
                conn.close()

def add_user(username, password):
    """Menambahkan user baru ke database MySQL."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            password_hash = pbkdf2_sha256.hash(password)
            c.execute("INSERT INTO users (username, password_hash) VALUES (%s, %s)", (username, password_hash))
            conn.commit()
            return True
        except mysql.connector.Error as err:
            if err.errno == mysql.connector.errorcode.ER_DUP_ENTRY:
                st.error("Username sudah ada, tod! Coba username lain.")
            else:
                st.error(f"Error saat mendaftarkan user: {err}")
            return False
        except Exception as e:
            st.error(f"Error tak terduga saat mendaftarkan user: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

def verify_user(username, password):
    """Memverifikasi username dan password user dari database MySQL."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("SELECT password_hash FROM users WHERE username = %s", (username,))
            result = c.fetchone()
            
            if result:
                password_hash = result[0]
                return pbkdf2_sha256.verify(password, password_hash)
            return False
        except Exception as e:
            st.error(f"Error saat verifikasi user: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

# Panggil inisialisasi database saat aplikasi dimulai
# Ini akan membuat tabel 'users' jika belum ada
init_db()

# --- Fungsi untuk membaca template dari file ---
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

    # Tombol Konversi
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
    
    # Tampilkan jika sudah login
    if st.session_state.logged_in:
        st.success(f"Halo, {st.session_state.username}! Lo udah login.")
        st.markdown("---")
        st.subheader("Pengaturan Akun & GitHub")
        st.write("Di sini lo bisa simpen info repo GitHub dan token lo.")
        st.info("Fitur penyimpanan ini **Coming Soon**, akan terintegrasi dengan sistem login.")
        if st.button("Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.page_selection = "🔐 Login & Pengaturan Akun" # Redirect ke login page
            st.success("Berhasil Logout.")
            st.rerun() # Muat ulang halaman untuk mencerminkan status logout
        return # Keluar dari fungsi agar tidak menampilkan form login/daftar lagi

    # Tampilkan form login/daftar jika belum login
    login_tab, signup_tab = st.tabs(["Login", "Daftar"])

    with login_tab:
        st.subheader("Masuk ke Akun Lo")
        username_login = st.text_input("Username", key="username_login")
        password_login = st.text_input("Password", type="password", key="password_login")
        if st.button("Login", key="do_login_button"):
            if verify_user(username_login, password_login):
                st.session_state.logged_in = True
                st.session_state.username = username_login
                st.session_state.page_selection = "🏠 Homepage" # Redirect ke homepage setelah login
                st.success(f"Login Berhasil! Selamat datang, {username_login}!")
                st.rerun()
            else:
                st.error("Username atau Password salah, tod!")

    with signup_tab:
        st.subheader("Bikin Akun Baru")
        # Inisialisasi session_state untuk nilai input agar bisa di-reset
        if 'signup_username_value' not in st.session_state:
            st.session_state.signup_username_value = ""
        if 'signup_password_value' not in st.session_state:
            st.session_state.signup_password_value = ""
        if 'signup_confirm_password_value' not in st.session_state:
            st.session_state.signup_confirm_password_value = ""

        # Gunakan nilai dari session_state untuk input widget
        username_signup_input = st.text_input("Username Baru", key="username_signup_form_input", value=st.session_state.signup_username_value)
        password_signup_input = st.text_input("Password Baru", type="password", key="password_signup_form_input", value=st.session_state.signup_password_value)
        confirm_password_signup_input = st.text_input("Konfirmasi Password", type="password", key="confirm_password_signup_form_input", value=st.session_state.signup_confirm_password_value)
        
        if st.button("Daftar", key="do_signup_button"):
            if not username_signup_input or not password_signup_input or not confirm_password_signup_input:
                st.error("Semua kolom harus diisi, tod!")
            elif password_signup_input != confirm_password_signup_input:
                st.error("Konfirmasi Password nggak cocok, mek!")
            else:
                if add_user(username_signup_input, password_signup_input):
                    st.success(f"Akun '{username_signup_input}' berhasil didaftarkan! Silakan Login.")
                    # Reset nilai di session_state setelah berhasil daftar
                    st.session_state.signup_username_value = "" 
                    st.session_state.signup_password_value = ""
                    st.session_state.signup_confirm_password_value = ""
                    st.rerun() # Muat ulang untuk mengosongkan input field
                # else: Error sudah ditangani di fungsi add_user

# --- Homepage Utama ---
def homepage():
    st.title("🛠️ Swiss Army VPN Tools")
    st.markdown("---")
    st.write(f"""
    Halo **{st.session_state.username if st.session_state.username else 'mek'}**! Selamat datang di **Swiss Army VPN Tools**! 
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

    if st.button("🔐 **Login & Pengaturan Akun**", use_container_width=True):
        st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
        st.rerun()
    st.markdown("Buat nyimpen settingan lo biar lebih nyaman.")
    st.markdown("---")
    
    st.subheader("Pesan dari Gua:")
    st.info("Ingat, **tod**! Fitur yang Coming Soon lagi dalam tahap pengembangan. Kopi sama rokoknya udah nyampe ya di markas gua, makasih banyak! 😎")

# --- Kontrol Navigasi Utama ---
if not st.session_state.logged_in:
    # Jika belum login, paksa ke halaman login dan tampilkan
    st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
    login_page()
else:
    # Sidebar Navigasi jika sudah login
    st.sidebar.title(f"Halo, {st.session_state.username}!")
    st.sidebar.markdown("---")
    page_selection_sidebar = st.sidebar.radio(
        "Pilih Halaman:",
        ("🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"),
        index=["🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"].index(st.session_state.page_selection)
    )

    if page_selection_sidebar != st.session_state.page_selection:
        st.session_state.page_selection = page_selection_sidebar
        st.rerun() # Penting untuk rerender halaman jika pilihan sidebar berubah

    # Menampilkan halaman sesuai pilihan user
    if st.session_state.page_selection == "🏠 Homepage":
        homepage()
    elif st.session_state.page_selection == "⚙️ Sing-Box Converter":
        singbox_converter_page()
    elif st.session_state.page_selection == "🎬 Media Downloader":
        media_downloader_page()
    elif st.session_state.page_selection == "🔐 Login & Pengaturan Akun":
        login_page()
                
