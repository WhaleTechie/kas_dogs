# 🐕 KAS Dogs Telegram Bot

**KAS Dogs** is a volunteer-built Telegram bot that helps recognize and track shelter dogs using a photo. It's designed for shelters, volunteers, and potential adopters who want to easily get info on a dog with just a photo.

---

## 📸 What It Does

- `/start` — Welcome message + menu  
- **🔍 Identify a Dog** *(coming soon)* — Send a photo to recognize a dog  
- **🐶 View Catalog** — Browse available dogs with their name, status, and pen  
- `/catalog` — Show all dogs in the database  

- **☕ Support** — [t.me](https://t.me/proseacode)

---

## 🐾 Tech Stack

| Part        | Tech               |
|-------------|--------------------|
| Bot         | Python + Aiogram   |
| Database    | SQLite             |
| Storage     | Local (for now)    |
| Hosting     | Local dev / GitHub |
| Model       | MobileNet (WIP)    |

---

## 🔧 Setup (Dev)

1. **Clone the repo**

```bash
git clone https://github.com/your-username/kas_dogs.git
cd kas_dogs
```
2. **Run the setup script** — this creates a `kasdogs310-env` virtual environment and installs requirements automatically

```bash
bash setup.sh
```
3. **Create a `.env` file** with `BOT_TOKEN=<token>`

4. **Initialize the database**

```bash
python scripts/init_db.py
```
5. **Run the bot**

```bash
python -m bot.main
```

🤝 Want to Help?
Donate a ☕ to support time and hosting

Contribute code or ideas (open source!)

Message @proseacode

📌 About
This project started in a dog shelter in Turkey where over 700 dogs live. The idea: make it easier for volunteers and adopters to identify and learn about dogs using just a photo.

❤️ Made with love, mud, and fur.
---

## License

This project is licensed under the [MIT License](LICENSE).
