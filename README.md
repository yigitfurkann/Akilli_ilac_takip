# 🧠 Akıllı İlaç Takip Sistemi  
> Django (Python) + React (Frontend) + Huawei Cloud altyapısı üzerinde çalışan akıllı ilaç takip platformu.

---

## 🚀 Proje Hakkında  
**Akıllı İlaç Takip Sistemi**, kullanıcıların ilaçlarını düzenli kullanmasını sağlamak, hatırlatıcı bildirimler göndermek ve ilaç kullanım geçmişini izlemek amacıyla geliştirilmiştir.  
Sistem, hasta verilerini güvenli bir şekilde saklar ve yönetir. Yönetici paneli ile doktorlar veya yetkili kişiler hastaların ilaçlarını uzaktan kontrol edebilir.

---

## ⚙️ Özellikler  
- 👩‍⚕️ Kullanıcı (Hasta / Doktor) yönetimi  
- 💊 İlaç ekleme, silme, güncelleme işlemleri  
- ⏰ Zamanlı ilaç hatırlatmaları  
- 📊 Günlük / haftalık ilaç kullanım istatistikleri  
- 🧾 SQLite veritabanı + Django Admin yönetimi  
- 🖥️ React tabanlı modern kullanıcı arayüzü  
- ☁️ Huawei Cloud üzerinde Docker ile dağıtım desteği  

---

## 🧩 Kullanılan Teknolojiler  

| Katman | Teknoloji |
|:--|:--|
| **Frontend** | React.js, Axios, Tailwind CSS |
| **Backend** | Django, Django REST Framework |
| **Veritabanı** | SQLite (geliştirme) / PostgreSQL (isteğe bağlı) |
| **Altyapı** | Docker, Docker Compose, Huawei Cloud ECS |
| **Diğer** | GitHub Actions (CI/CD), Environment Variables (.env) |

---

--- 
## 📄 Lisans

FURKAN YİĞİT LİSANSI

Bu proje Furkan YİĞİT tarafından geliştirilmiştir.
Tüm hakları saklıdır.

Kodu eğitim, araştırma veya kişisel öğrenme amacıyla kullanabilirsiniz.
Ticari amaçlı kopyalama, yeniden dağıtım veya yetkisiz kullanım yasaktır.

© 2025 Furkan YİĞİT

## 🛠️ Kurulum ve Çalıştırma  

Aşağıdaki adımları izleyerek projeyi kendi bilgisayarında kolayca çalıştırabilirsin 👇  

```bash
# 🔹 0️⃣ Projeyi klonla
git clone https://github.com/yigitfurkann/Akilli_ilac_takip.git
cd Akilli_ilac_takip

# 🔹 1️⃣ Backend (Django)
cd backend
python -m venv venv
source venv/bin/activate        # Windows için: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
# Django varsayılan olarak http://127.0.0.1:8000 adresinde çalışır.

# 🔹 2️⃣ Frontend (React)
cd ../frontend
npm install
npm start
# React uygulaması http://localhost:3000 adresinde çalışır ve backend'e bağlanır.

# 🔹 3️⃣ Docker ile Çalıştırma (Alternatif)
cd ..
docker-compose up --build
# Bu komut hem backend hem frontend'i aynı anda başlatır. ```



