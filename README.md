# 🎉 Telegram Giveaway Bot

A powerful Telegram Giveaway Bot with live voting, leaderboard, paid voting system, and much more!

---

## 📁 File Structure

```
giveaway_bot/
│
├── bot.py                  → Main entry point
├── config.py               → Bot token, MongoDB URI, links
├── database.py             → MongoDB collections setup
├── utils.py                → Helper functions
├── font.py                 → Special unicode font
├── requirements.txt        → Python dependencies
├── README.md               → This file
│
└── handlers/
    ├── __init__.py         → Package init (empty file)
    ├── start.py            → /start command + menu buttons
    ├── create_giveaway.py  → New giveaway creation flow
    ├── giveaway.py         → Join, verify, free vote, leave detection
    ├── paid_voting.py      → Paid votes, QR, approve/decline
    ├── my_giveaway.py      → My giveaways, leaderboard, stats, end
    └── router.py           → Smart message router
```

---

## 🖥️ Requirements

### Python Version
```
Python 3.10 or above (Recommended: 3.11 / 3.12)
```

Check your version:
```bash
python --version
```

Download: https://www.python.org/downloads/

### Libraries

| Library | Version | Use |
|---------|---------|-----|
| `python-telegram-bot` | 20.7 | Telegram Bot API |
| `pymongo` | 4.6.1 | MongoDB database |

---

## ⚙️ Installation

```bash
# Step 1 — Install dependencies
pip install -r requirements.txt

# Step 2 — Fill config.py

# Step 3 — Run the bot
python bot.py
```

**Virtual Environment (Recommended):**
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux / macOS
python3 -m venv venv
source venv/bin/activate

pip install -r requirements.txt
python bot.py
```

---

## 🔧 Configuration

Fill these values in `config.py`:

```python
BOT_TOKEN         = "YOUR_BOT_TOKEN"        # From BotFather
MONGO_URI         = "YOUR_MONGODB_URI"      # MongoDB Atlas string
WELCOME_IMAGE_URL = "YOUR_IMAGE_URL"        # Catbox image URL for /start
SUPPORT_URL       = "https://t.me/..."      # Support channel link
OWNER_URL         = "https://t.me/..."      # Owner profile link
```

### BOT_TOKEN
1. Open [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` → give name and username
3. Copy the token

### MONGO_URI (MongoDB Atlas — Free)
1. Go to https://cloud.mongodb.com → Create free cluster (M0)
2. Connect → Drivers → Copy connection string:
   ```
   mongodb+srv://user:pass@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
   ```
3. Replace `user` and `pass` with your credentials

### Your Telegram User ID
Open [@userinfobot](https://t.me/userinfobot) → Send `/start` → Copy your ID

---

## 🤖 Bot Permissions (in Channel)
Make the bot admin with these permissions:
- ✅ Post Messages
- ✅ Edit Messages
- ✅ Delete Messages
- ✅ Add Members *(for leave detection)*

---

## 📌 Commands

| Command | Description |
|---------|-------------|
| `/start` | Open main menu |
| `/cancel` | Cancel any ongoing action |

---

## 🚀 How to Use

### Creating a Giveaway:
```
1. /start → New Giveaway
2. Send description (text or photo)
3. Send channel ID or @username (bot must be admin)
4. Send target channel link (participants will join this)
5. Choose voting type: Free / Paid / Both
6. If paid → send UPI QR photo
7. Set rate: ₹1 = how many votes?
8. Set minimum votes (or 0 to skip)
9. Get your unique join link → share with participants!
```

### Participant Flow:
```
1. Click join link
2. Click "Join Channel"
3. Click "Verify & Submit"
4. Your details get posted in the channel with vote button
5. Share your post link to get more votes!
```

### Free Voting:
- Click emoji button on participant's channel post
- Channel leave → vote gets removed automatically

### Paid Voting:
```
1. Click "Buy Paid Votes" in bot
2. Enter amount in ₹
3. Votes auto-calculated (amount × rate)
4. QR shown → make payment
5. Send screenshot
6. Creator approves → votes added + channel announcement
```

### Managing Your Giveaway (My Giveaway):
```
→ Leaderboard   — See live vote rankings
→ Stats         — Participants, votes, revenue
→ Pause/Resume  — Temporarily stop voting
→ Edit          — Change description or QR
→ End Giveaway  — Post final results, notify all participants
```

---

## 🗄️ MongoDB Collections

| Collection | Data |
|-----------|------|
| `users` | All bot users (for tracking) |
| `giveaways` | Giveaway info and settings |
| `participants` | Verified participants per giveaway |
| `votes` | Free and paid votes |
| `payments` | Payment requests and status |

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎉 Multiple Giveaways | Run multiple giveaways at the same time |
| 🗳️ Free Voting | One vote per user, change allowed |
| 💰 Paid Voting | Buy votes via UPI QR payment |
| 🔀 Free + Paid | Both voting types together |
| 🚪 Leave = Minus | Channel leave removes free vote |
| 🏆 Leaderboard | Live vote rankings |
| 📊 Stats | Revenue, votes, participant count |
| ⏸️ Pause/Resume | Temporarily stop voting |
| ✏️ Edit Giveaway | Update description or QR anytime |
| 🎯 Min Votes | Minimum votes required to end |
| 🔔 Vote Notification | Participant notified on new vote |
| 🎊 End Notification | All participants notified on end |
| 🏅 Rank on End | Each participant sees their final rank |

---

## 🛠️ Troubleshooting

| Problem | Solution |
|---------|----------|
| Bot not responding | Is token correct? Is `python bot.py` running? |
| Post not going to channel | Is bot admin? Are all permissions given? |
| Vote not removing on leave | Did you give "Add Members" permission to bot? |
| MongoDB error | In Atlas → Network Access → Add `0.0.0.0/0` |
| ModuleNotFoundError | Run `pip install -r requirements.txt` |
| Python version error | Use Python 3.10 or above |

---

## 📞 Support

- 🛠️ Support: https://t.me/CarelessxWorld
- 📢 Updates: https://t.me/ll_CarelessxCoder_ll
- 👑 Owner: https://t.me/CarelessxOwner
