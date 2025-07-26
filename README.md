
# 🐕 KAS Dogs Telegram Bot

**KAS Dogs** is a volunteer-built Telegram bot that helps recognize and track shelter dogs using a photo.
It’s designed for shelters, volunteers, and potential adopters to quickly get information about a dog using just a photo.

👉 **Try it here:** [@kasdogs\_bot](http://t.me/kasdogs_bot)

---

## 📸 What It Does

* `/start` — Welcome message + options
* **🔍 Identify a Dog** — Upload a photo to recognize a dog using AI
* **🐶 View Catalog** — Browse all dogs by category, pen, or shelter sector
* **🧬 View by Breed** *(WIP)* — Search dogs by predicted breed
* **📷 More Photos** — View all available images of a dog as a resized collage
* **☕ Support the Project** — [Donate or follow](https://t.me/proseacode)

---

## 🖼️ Photo Handling

* Each dog has a dedicated folder in **Supabase Storage** named after the dog's unique ID.
* The bot fetches images from these folders and resizes them before sending, optimizing speed and bandwidth.
* Users can view dog profiles with a main photo, and browse more photos as a collage of thumbnails.

---

## 🧠 How It Works

* When a user sends a photo, the bot extracts image features and compares them to embeddings stored in the database.
* If a match is found, the dog’s profile and photos are shown.
* Dogs can also be explored by catalog, pen, or shelter sector.
* We're working on **breed recognition** to allow browsing dogs by predicted breed.

---

## 🐾 Tech Stack

| Part        | Tech                                     |
| ----------- | ---------------------------------------- |
| Bot         | Python 3.10 + Aiogram                    |
| Database    | PostgreSQL in Supabase cloud             |
| Storage     | Supabase Storage (folders by Dog ID)     |
| Hosting     | Local dev(for now) for now               |
| Model       | ResNet18 (torchvision) + embedding match |
| Breed Model | 🐾 (Coming soon) breed classification    |

---

## 🔧 Setup (Dev)

### Requirements

* Python **3.10+**
* pip, virtualenv or bash

### 1. Clone the repo

```bash
git clone https://github.com/your-username/kas_dogs.git
cd kas_dogs
```

### 2. Create virtual environment & install requirements

```bash
bash setup.sh
```

> This creates a virtual environment named `kasdogs310-env` and installs all required packages.

### 3. Add your Bot Token and Supabase credentials

Create a `.env` or `kas_config.py` file with:

```python
BOT_TOKEN = "your-telegram-bot-token"

# Supabase settings
SUPABASE_URL = "https://xxxx.supabase.co"
SUPABASE_KEY = "your-service-role-or-public-key"
```


### 4. Run the bot

```bash
python -m bot.main
```

---

## ✅ Testing

Run the bot and try:

* Send a photo of a known dog → it should return a profile with photos.
* Send a random photo → it should reply “no match found”.
* Use “View Catalog” → filter dogs by pen or category and open profiles.

---

## 🤝 Want to Help?

* Donate a ☕ — [t.me/proseacode](https://t.me/proseacode)
* Open an issue or submit a pull request
* Ideas, designs, suggestions welcome!

📬 Contact: [@proseacode](https://t.me/proseacode)

---

## 📍 About

This project started in a large shelter in Turkey with over 700 dogs.
Volunteers needed a simple way to identify and learn about dogs by photo — and help them find a home.

> ❤️ Made with love, mud, and fur.

---

## 🪪 License

This project is licensed under the [MIT License](LICENSE).

