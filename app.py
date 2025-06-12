import streamlit as st
import os
import mysql.connector
from passlib.hash import pbkdf2_sha256
import tempfile
from github import Github # Import untuk integrasi GitHub
from cryptography.fernet import Fernet # Import untuk enkripsi token GitHub
import singbox_converter # Pastikan ini di-import jika singbox_converter.py ada

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
    st.session_state.page_selection = "🔐 Login & Pengaturan Akun" # Default ke login jika belum login

# Inisialisasi session_state untuk pengaturan GitHub jika belum ada
if 'github_token' not in st.session_state:
    st.session_state.github_token = ""
if 'github_repo_name' not in st.session_state:
    st.session_state.github_repo_name = ""
# 'github_file_path' tidak lagi disimpan di session_state global atau DB
# Ini akan dipilih secara dinamis di halaman converter

# Untuk caching isi repo GitHub
if 'repo_contents_result' not in st.session_state:
    st.session_state.repo_contents_result = {"status": "info", "message": "Belum ada isi repo yang dimuat."}
if 'refresh_repo' not in st.session_state:
    st.session_state.refresh_repo = True # Flag untuk pertama kali atau saat dibutuhkan refresh
if 'selected_github_dir' not in st.session_state:
    st.session_state.selected_github_dir = ""
if 'selected_file_or_dir' not in st.session_state:
    st.session_state.selected_file_or_dir = "(Buat file baru di sini)"

# --- Fungsi Enkripsi/Dekripsi untuk Token GitHub ---
# PENTING: Kunci enkripsi harus diambil dari Streamlit Secrets
# Untuk pengujian lokal pertama kali jika secrets belum diset, bisa generate sementara.
# NAMUN, DI PRODUCTION/DEPLOYMENT, KUNCI INI HARUS PERSISTEN DARI SECRETS.
try:
    ENCRYPTION_KEY = st.secrets["encryption_key"].encode()
    cipher_suite = Fernet(ENCRYPTION_KEY)
except (KeyError, AttributeError):
    st.error("⚠️ Kunci enkripsi 'encryption_key' tidak ditemukan di Streamlit Secrets. Pastikan Anda telah mengaturnya.")
    # Fallback untuk pengembangan/debug lokal jika kunci tidak diset (TIDAK AMAN UNTUK PRODUKSI)
    st.info("Menggunakan kunci enkripsi sementara (tidak persisten). Harap set 'encryption_key' di Streamlit Secrets Anda.")
    # Sebaiknya, hentikan aplikasi jika kunci tidak ditemukan di production
    # Untuk demonstasi, kita akan generate kunci sementara
    ENCRYPTION_KEY = Fernet.generate_key() # Generate kunci sementara (tidak persisten)
    cipher_suite = Fernet(ENCRYPTION_KEY)
    st.code(f"Kunci enkripsi yang perlu Anda tambahkan ke Streamlit Secrets:\nencryption_key = \"{ENCRYPTION_KEY.decode()}\"")


def encrypt_data(data):
    if not data:
        return ""
    try:
        return cipher_suite.encrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        st.error(f"Error saat enkripsi data: {e}")
        return ""

def decrypt_data(data):
    if not data:
        return ""
    try:
        return cipher_suite.decrypt(data.encode('utf-8')).decode('utf-8')
    except Exception as e:
        st.error(f"Error saat dekripsi data: {e}. Token mungkin tidak valid atau kunci enkripsi berubah.")
        return ""

# --- Fungsi Koneksi Database MySQL Aiven ---
def get_mysql_connection():
    """Mendapatkan koneksi ke database MySQL Aiven menggunakan st.secrets."""
    conn = None
    ca_cert_path = None

    try:
        # Menulis SSL CA content ke file sementara jika disediakan di st.secrets
        if "ssl_ca_content" in st.secrets.get("mysql", {}): # Gunakan .get() untuk keamanan
            temp_dir = tempfile.gettempdir() # Dapatkan direktori temp sistem (misal /tmp di Linux)
            ca_cert_path = os.path.join(temp_dir, "aiven_ca.pem") # Nama file sementara

            with open(ca_cert_path, "w") as f:
                f.write(st.secrets["mysql"]["ssl_ca_content"])
            # st.info(f"CA certificate ditulis ke file sementara: {ca_cert_path}") # Debugging info, bisa dihapus

        conn = mysql.connector.connect(
            host=st.secrets["mysql"]["host"],
            port=st.secrets["mysql"]["port"],
            user=st.secrets["mysql"]["user"],
            password=st.secrets["mysql"]["password"],
            database=st.secrets["mysql"]["database"],
            ssl_ca=ca_cert_path
        )
        return conn
    except Exception as e:
        if "mysql" not in st.secrets:
            st.error("❌ Kredensial MySQL tidak ditemukan di Streamlit Secrets. Pastikan Anda telah mengaturnya di 'Advanced settings' aplikasi.")
        else:
            st.error(f"❌ Gagal koneksi ke database MySQL Aiven, tod! Pastikan kredensial di 'Advanced settings' Streamlit Cloud benar dan format SSL CA content tepat. Error: {e}")
        return None

def init_db():
    """Menginisialisasi tabel users jika belum ada di MySQL."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            # PERHATIKAN: Kolom github_file_path di-hapus dari tabel users
            c.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password_hash VARCHAR(255) NOT NULL,
                    github_token_encrypted TEXT,    
                    github_repo_name VARCHAR(255)
                )
            ''')
            conn.commit()
        except Exception as e:
            st.error(f"Error saat inisialisasi tabel database: {e}")
        finally:
            if conn:
                conn.close()

def add_user(username, password):
    """Menambahkan user baru ke database MySQL."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            password_hash = pbkdf2_sha256.hash(password)
            # Saat daftar, kolom GitHub dibiarkan NULL dulu
            c.execute("INSERT INTO users (username, password_hash, github_token_encrypted, github_repo_name) VALUES (%s, %s, NULL, NULL)", (username, password_hash))
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

def get_user_settings(username):
    """Mengambil pengaturan user (termasuk GitHub) dari database."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor(dictionary=True) # Mengembalikan hasil sebagai dictionary
            c.execute("SELECT github_token_encrypted, github_repo_name FROM users WHERE username = %s", (username,))
            result = c.fetchone()
            return result
        except Exception as e:
            st.error(f"Error saat mengambil pengaturan user: {e}")
            return None
        finally:
            if conn:
                conn.close()
    return None

def update_user_settings(username, github_token_encrypted, github_repo_name):
    """Mengupdate pengaturan user (termasuk GitHub) di database."""
    conn = get_mysql_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute("""
                UPDATE users 
                SET github_token_encrypted = %s, 
                    github_repo_name = %s
                WHERE username = %s
            """, (github_token_encrypted, github_repo_name, username))
            conn.commit()
            return True
        except Exception as e:
            st.error(f"Error saat mengupdate pengaturan user: {e}")
            return False
        finally:
            if conn:
                conn.close()
    return False

# Panggil inisialisasi database saat aplikasi dimulai
init_db()

# --- Fungsi untuk membaca template dari file ---
def load_template_from_file(file_path="singbox-template.txt"):
    if os.path.exists(file_path):
        with open(file_path, "r") as f:
            return f.read()
    else:
        return None

# --- Fungsi untuk membaca isi repositori GitHub ---
@st.cache_data(ttl=300) # Cache hasil selama 5 menit
def list_repo_contents_cached(token, repo_name, path=""):
    """
    Membaca isi direktori (file/folder) dari repositori GitHub.
    Mengembalikan list dari dict berisi {'name': 'file_name', 'path': 'full/path/to/file', 'type': 'file'/'dir'}
    """
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        contents = repo.get_contents(path, ref="main") # Asumsi branch 'main'
        
        # Filter hanya file dan direktori, bukan submodule atau symlink
        filtered_contents = []
        for item in contents:
            if item.type == "file" or item.type == "dir":
                filtered_contents.append({'name': item.name, 'path': item.path, 'type': item.type})
        
        return {"status": "success", "contents": filtered_contents}
    except Exception as e:
        # Handle cases like repo not found, token invalid, path not found
        if "Not Found" in str(e) or "Bad credentials" in str(e):
            return {"status": "error", "message": f"Repositori atau path '{repo_name}/{path}' tidak ditemukan, atau Personal Access Token GitHub tidak valid/tidak punya akses. Error: {e}"}
        return {"status": "error", "message": f"Gagal membaca isi repo GitHub: {e}"}

# --- Fungsi untuk update config ke GitHub ---
def update_config_to_github(token, repo_name, file_path, content):
    try:
        g = Github(token)
        repo = g.get_repo(repo_name)
        
        # Cek apakah file sudah ada atau belum
        try:
            # Dapatkan konten file yang sudah ada
            contents = repo.get_contents(file_path, ref="main") # Asumsi branch 'main'
            # Jika file ada, update isinya
            repo.update_file(contents.path, "Update config dari Swiss Army VPN Tools", content, contents.sha, branch="main")
            st.success(f"✅ Config berhasil diupdate di GitHub: `{repo_name}/{file_path}`")
        except Exception as e:
            # Jika file belum ada, buat file baru
            if "Not Found" in str(e) or "404" in str(e): # GitHub API returns 404 if file not found
                repo.create_file(file_path, "Upload config dari Swiss Army VPN Tools", content, branch="main")
                st.success(f"✅ Config berhasil diupload baru di GitHub: `{repo_name}/{file_path}`")
            else:
                st.error(f"❌ Error saat mengakses atau mengupdate file di GitHub: {e}")
                st.info("Pastikan Nama Repositori GitHub dan Path File Config benar, serta token lo punya izin 'repo' (full control of private repositories).")

    except Exception as e:
        st.error(f"❌ Gagal koneksi atau otentikasi GitHub: {e}")
        st.info("Cek lagi Personal Access Token GitHub lo di halaman 'Login & Pengaturan Akun', tod! Pastikan punya izin 'repo' (Full control of private repositories).")

# --- Fungsi untuk halaman Sing-Box Converter ---
def singbox_converter_page():
    st.header("⚙️ Sing-Box Config Converter")
    st.write("Di sini lo bisa konversi link VPN dan atur config Sing-Box lo.")

    # --- DEBUGGING GITHUB SESSION STATE ---
    st.info(f"DEBUG: Logged In: {st.session_state.logged_in}")
    st.info(f"DEBUG: GitHub Token (first 10 chars): {st.session_state.github_token[:10] if st.session_state.github_token else 'EMPTY'}")
    "st.info(f"DEBUG: GitHub Repo: {st.session_state.github_repo_name if st.session_state.github_repo_name else 'EMPTY'}")
    # --- END DEBUGGING ---
    vpn_links = st.text_area("Masukkan link VPN (VMess/VLESS/Trojan):", height=200)
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
                    
                    # --- UI untuk Update ke GitHub ---
                    if st.session_state.logged_in and \
                       st.session_state.github_token and \
                       st.session_state.github_repo_name:
                        
                        st.markdown("---")
                        st.subheader("⬆️ Update Config ke GitHub")
                        st.info("Sekarang pilih atau masukkan path file config di repo lo.")
                        
                        current_repo_name = st.session_state.github_repo_name

                        # Tombol untuk refresh/list isi repo
                        if st.button("Refresh Isi Repo GitHub", key="refresh_repo_contents"):
                            st.session_state.refresh_repo = True
                            st.session_state.selected_github_dir = "" # Reset ke root saat refresh
                            st.session_state.selected_file_or_dir = "(Buat file baru di sini)" # Reset pilihan
                            st.cache_data.clear() # Clear cache untuk konten repo
                            st.rerun()
                        
                        # Hanya list jika ada token dan repo name
                        if st.session_state.github_token and st.session_state.github_repo_name:
                            # Tampilkan breadcrumb
                            st.markdown(f"**Lokasi saat ini:** `{current_repo_name}/{st.session_state.selected_github_dir}/`")
                            
                            path_parts = [p for p in st.session_state.selected_github_dir.split('/') if p]
                            breadcrumb_paths = []
                            current_path_breadcrumb_display = ""
                            breadcrumb_paths.append(("Root", "")) # Opsi kembali ke root

                            for part in path_parts:
                                current_path_breadcrumb_display = os.path.join(current_path_breadcrumb_display, part).replace("\\", "/")
                                breadcrumb_paths.append((part, current_path_breadcrumb_display))

                            cols_breadcrumb = st.columns(len(breadcrumb_paths))
                            for i, (part_display, path_value) in enumerate(breadcrumb_paths):
                                with cols_breadcrumb[i]:
                                    if st.button(part_display, key=f"breadcrumb_{i}"):
                                        st.session_state.selected_github_dir = path_value.strip('/')
                                        st.session_state.refresh_repo = True # Force refresh
                                        st.cache_data.clear() # Clear cache untuk konten repo
                                        st.rerun()

                            # Cek apakah perlu refresh atau pertama kali
                            if st.session_state.get('refresh_repo', True):
                                with st.spinner(f"Membaca isi repo '{current_repo_name}/{st.session_state.selected_github_dir}'..."):
                                    repo_contents_result = list_repo_contents_cached( # Gunakan fungsi cached
                                        st.session_state.github_token,
                                        current_repo_name,
                                        st.session_state.selected_github_dir
                                    )
                                    st.session_state.repo_contents_result = repo_contents_result
                                st.session_state.refresh_repo = False # Reset flag

                            if st.session_state.repo_contents_result and st.session_state.repo_contents_result["status"] == "success":
                                contents = st.session_state.repo_contents_result["contents"]
                                # Urutkan: direktori dulu, baru file, lalu urut abjad
                                contents.sort(key=lambda x: (x['type'] != 'dir', x['name'].lower()))

                                options = ["(Buat file baru di sini)"] # Opsi default
                                for item in contents:
                                    if item['type'] == 'dir':
                                        options.append(f"📁 {item['name']}/")
                                    else:
                                        options.append(f"📄 {item['name']}")
                                
                                # Simpan pilihan path terakhir
                                # Pastikan pilihan sebelumnya masih ada di options, kalau tidak, reset ke default
                                if st.session_state.selected_file_or_dir not in options:
                                    st.session_state.selected_file_or_dir = options[0]

                                file_selection_idx = options.index(st.session_state.selected_file_or_dir)

                                selected_option = st.selectbox(
                                    "Pilih file yang mau diupdate, atau pilih direktori:",
                                    options,
                                    index=file_selection_idx,
                                    key="github_file_or_dir_selector"
                                )
                                st.session_state.selected_file_or_dir = selected_option # Simpan pilihan

                                github_target_file_path = ""
                                if selected_option == "(Buat file baru di sini)":
                                    # User akan memasukkan nama file baru
                                    new_file_name = st.text_input("Nama file baru (contoh: config.json)", key="new_github_file_name_input")
                                    if new_file_name: # Hanya buat path jika nama file tidak kosong
                                        github_target_file_path = os.path.join(st.session_state.selected_github_dir, new_file_name).replace("\\", "/")
                                    else:
                                        st.warning("Masukkan nama file baru untuk disimpan.")
                                else:
                                    # Jika memilih file atau folder yang ada
                                    if selected_option.startswith("📁 "):
                                        folder_name = selected_option.replace("📁 ", "").strip('/')
                                        st.session_state.selected_github_dir = os.path.join(st.session_state.selected_github_dir, folder_name).replace("\\", "/")
                                        st.session_state.refresh_repo = True # Force refresh
                                        st.cache_data.clear() # Clear cache untuk konten repo
                                        st.rerun() # Rerun untuk masuk ke folder baru
                                    else: # Ini adalah file yang dipilih
                                        file_name = selected_option.replace("📄 ", "")
                                        github_target_file_path = os.path.join(st.session_state.selected_github_dir, file_name).replace("\\", "/")

                                if github_target_file_path: # Hanya tampilkan tombol jika path sudah valid
                                    st.text_input("Path file yang akan diupdate:", value=github_target_file_path, disabled=True)
                                    if st.button("⬆️ Update Config ke GitHub", key="github_update_button_final"):
                                        update_config_to_github(
                                            st.session_state.github_token,
                                            current_repo_name,
                                            github_target_file_path, # Gunakan path yang dipilih/dibuat
                                            converted_config
                                        )
                            else:
                                st.error(st.session_state.repo_contents_result["message"])
                                st.info("Pastikan Personal Access Token dan Nama Repositori GitHub lo benar di halaman 'Login & Pengaturan Akun'.")
                        else:
                            st.info("Login dulu dan isi Personal Access Token serta Nama Repositori GitHub di halaman 'Login & Pengaturan Akun' untuk bisa update config ke GitHub, tod!")

                else:
                    st.error(f"❌ Gagal konversi: {result['message']}")
            except Exception as e:
                st.error(f"Terjadi error saat memproses konversi: {e}")

# ... (sisa kode lainnya tetap sama) ...

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
        st.info("Untuk mengupdate config ke GitHub, lo perlu Personal Access Token (PAT) GitHub yang punya izin 'repo' (Full control of private repositories) dan nama repo tujuan.")
        
        # Ambil nilai dari session_state untuk di-isi ke input field
        github_token_input = st.text_input("Personal Access Token GitHub", 
                                            type="password", 
                                            key="github_pat", 
                                            value=st.session_state.github_token)
        github_repo_name_input = st.text_input("Nama Repositori GitHub (contoh: user/nama-repo)", 
                                                key="github_repo", 
                                                value=st.session_state.github_repo_name)
        # github_file_path_input Dihapus dari sini
        
        if st.button("Simpan Pengaturan GitHub", key="save_github_settings_button"):
            encrypted_token = encrypt_data(st.session_state.github_token) # Gunakan st.session_state yang sudah diupdate oleh input field
            
            # Simpan ke database
            if update_user_settings(st.session_state.username, 
                                     encrypted_token, 
                                     st.session_state.github_repo_name):
                st.success("Pengaturan GitHub berhasil disimpan ke database.")
            else:
                st.error("Gagal menyimpan pengaturan GitHub ke database.")
            # Setelah simpan, reset flag refresh repo agar nanti di converter page dia list ulang
            st.session_state.refresh_repo = True 
            st.session_state.selected_github_dir = "" # Reset ke root
            st.session_state.selected_file_or_dir = "(Buat file baru di sini)" # Reset pilihan file
            st.cache_data.clear() # Clear cache untuk konten repo
            # No rerun needed here, as inputs already update session state
            
        st.markdown("---")
        # --- Tombol Logout ---
        if st.button("Logout", key="logout_button"):
            st.session_state.logged_in = False
            st.session_state.username = None
            st.session_state.page_selection = "🔐 Login & Pengaturan Akun" # Redirect ke login page
            st.success("Berhasil Logout.")
            # Hapus juga info GitHub dari session_state saat logout
            st.session_state.github_token = ""
            st.session_state.github_repo_name = ""
            # st.session_state.github_file_path = "" # Dihapus
            st.session_state.selected_github_dir = "" # Reset dir selection
            st.session_state.selected_file_or_dir = "(Buat file baru di sini)" # Reset file selection
            st.session_state.refresh_repo = True # Ensure refresh on next access
            st.cache_data.clear() # Clear cache for user-specific data
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
                
                # Ambil pengaturan GitHub dari database setelah login sukses
                user_settings = get_user_settings(username_login)
                if user_settings:
                    st.session_state.github_token = decrypt_data(user_settings['github_token_encrypted'])
                    st.session_state.github_repo_name = user_settings['github_repo_name']
                
                st.session_state.page_selection = "🏠 Homepage" # Redirect ke homepage setelah login
                # Set refresh flag to true so that the repo contents are fetched on next view
                st.session_state.refresh_repo = True 
                st.session_state.selected_github_dir = "" # Reset selected dir
                st.session_state.selected_file_or_dir = "(Buat file baru di sini)" # Reset selected file
                st.cache_data.clear() # Clear cache for user-specific data
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
    st.session_state.page_selection = "🔐 Login & Pengaturan Akun"
    login_page()
else:
    st.sidebar.title(f"Halo, {st.session_state.username}!")
    st.sidebar.markdown("---")
    page_selection_sidebar = st.sidebar.radio(
        "Pilih Halaman:",
        ("🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"),
        index=["🏠 Homepage", "⚙️ Sing-Box Converter", "🎬 Media Downloader", "🔐 Login & Pengaturan Akun"].index(st.session_state.page_selection)
    )

    if page_selection_sidebar != st.session_state.page_selection:
        st.session_state.page_selection = page_selection_sidebar
        st.rerun()

    if st.session_state.page_selection == "🏠 Homepage":
        homepage()
    elif st.session_state.page_selection == "⚙️ Sing-Box Converter":
        singbox_converter_page()
    elif st.session_state.page_selection == "🎬 Media Downloader":
        media_downloader_page()
    elif st.session_state.page_selection == "🔐 Login & Pengaturan Akun":
        login_page()
 
