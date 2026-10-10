# Rich Ethiopia Telegram Bot

Complete membership + digital bookstore bot for the Ethiopian brand **Rich Ethiopia**.

## Features

- Digital bookstore with categories
- Membership plans (Weekly / Monthly / Yearly / Lifetime)
- Manual payment verification (Telebirr + major Ethiopian banks)
- 1-hour free trial (once per user)
- VIP channel invite link generation + automatic removal of expired members
- Full Admin panel inside Telegram
- Amharic + English support
- SQLite database
- PDF delivery after payment approval

---

## A. Architecture (Beginner Explanation)

1. User opens the bot → sees main menu.
2. User chooses Books or Membership → selects item → chooses payment method.
3. User sends transaction reference + receipt photo.
4. Payment is saved as **Pending**.
5. **Only Admin** can Approve / Reject.
6. On Approve:
   - Membership is activated **or** PDF is sent.
   - Single-use invite link to VIP channel is generated.
7. Every 5 minutes the bot checks for expired memberships and removes them from the channel.

All secrets are stored in environment variables (never in the code).

---

## B. Project Structure

```
rich_ethiopia_bot/
├── bot.py                 # Main entry point
├── config.py              # Loads environment variables
├── database.py            # All database operations
├── keyboards.py           # All inline buttons
├── utils.py               # Helpers + translations
├── handlers/
│   ├── start.py
│   ├── books.py
│   ├── membership.py
│   ├── trial.py
│   ├── payment.py
│   ├── admin.py
│   └── common.py
├── data/
│   └── books/             # PDF files stored here
├── requirements.txt
├── .env.example
└── README.md
```

---

## E. Create the Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Choose a name (example: Rich Ethiopia)
4. Choose a username ending with `bot` (example: `RichEthiopiaBot`)
5. Copy the **API Token** (looks like `7123456789:AAH...`)
6. (Optional) Send `/setdescription` and `/setabouttext` to describe your bot
7. Send `/setcommands` and paste:

```
start - Main menu
books - Browse books
membership - Membership plans
trial - Free 1-hour trial
my_status - Check your status
support - Contact support
help - Help
admin - Admin panel (admins only)
```

---

## F. Get Channel ID + Make Bot Admin

1. Create a **Private Channel** on Telegram (this will be your VIP channel).
2. Add your bot as **Administrator** of the channel.
   - Permissions needed:
     - Invite Users via Link
     - Ban Users
3. To get the Channel ID:
   - Forward any message from the channel to **@userinfobot** or **@getidsbot**
   - Or use **@RawDataBot**
   - The ID looks like `-1001234567890` (always starts with `-100`)

---

## H. Environment Variables

On Railway / Render you will set these:

| Variable         | Required | Description                          |
|------------------|----------|--------------------------------------|
| BOT_TOKEN        | Yes      | From BotFather                       |
| ADMIN_IDS        | Yes      | Your Telegram user ID (comma separated if multiple) |
| VIP_CHANNEL_ID   | Yes      | Your private channel ID              |
| VIP_CHANNEL_LINK | No       | Fallback permanent invite link       |

**How to get your User ID:**  
Message **@userinfobot** on Telegram → it will reply with your ID.

---

## G. Android-Friendly Deployment (Railway – Recommended)

### Step 1: Create GitHub account (if you don’t have one)
Use the GitHub mobile app or browser.

### Step 2: Upload the code
1. Create a new repository on GitHub (example: `rich-ethiopia-bot`)
2. Upload all the files from this project into the repository using the GitHub website (you can upload multiple files from your phone).

### Step 3: Deploy on Railway
1. Go to [https://railway.app](https://railway.app) from your Android browser
2. Login with GitHub
3. Click **New Project** → **Deploy from GitHub repo**
4. Select your `rich-ethiopia-bot` repository
5. Railway will detect it is a Python project
6. Go to **Variables** tab and add:
   - `BOT_TOKEN`
   - `ADMIN_IDS`
   - `VIP_CHANNEL_ID`
7. Deploy
8. The bot should start automatically.

### Alternative: Render.com
Similar process. Create a **Web Service**, connect the same GitHub repo, set the environment variables, and use:

**Build Command:** `pip install -r requirements.txt`  
**Start Command:** `python bot.py`

---

## J. How to Add Books + Upload PDFs

1. Open your bot and send `/admin`
2. Or send `/addbook`
3. Send details in this format:

```
How to Start a Business | Starting a Business | 150 | Full guide for Ethiopian entrepreneurs
```

4. The bot will reply with a Book ID (example: `3`)
5. Send the PDF file to the bot with caption:

```
book_id:3
```

The PDF is now linked to that book and will be delivered automatically after payment approval.

---

## I. Testing Checklist

- [ ] `/start` shows main menu in English
- [ ] Language switch to Amharic works
- [ ] `/books` shows categories (after you add books)
- [ ] `/membership` shows the 4 plans
- [ ] `/trial` can be claimed only once
- [ ] Payment flow: select plan → select bank → send reference → send photo
- [ ] Admin receives payment notification + receipt
- [ ] Admin can Approve → user receives invite link / PDF
- [ ] Admin can Reject → user is notified
- [ ] `/my_status` shows correct membership/trial
- [ ] Expired members are removed (wait or change system time for testing)
- [ ] `/admin` only works for ADMIN_IDS
- [ ] `/setmethod 1 Account Name 0912345678` updates bank details

---

## K. How to Test Key Features

**Trial expiration**  
Claim trial → wait 1 hour (or temporarily reduce `TRIAL_DURATION_SECONDS` in `config.py` for testing).

**Membership removal**  
Activate a short plan → wait for expiration checker (runs every 5 minutes) → user should be removed from channel.

**Payment approval**  
Submit a test payment → approve from admin account → check that invite link or PDF is delivered.

**Duplicate prevention**  
Try to submit the same transaction reference twice → should be rejected.

---

## L. Hosting Costs (as of 2025-2026)

| Platform   | Free Tier                          | Paid (approx)      | Notes                              |
|------------|------------------------------------|--------------------|------------------------------------|
| Railway    | Limited free credits monthly       | ~$5/month          | Easiest for beginners              |
| Render     | Free web service (spins down)      | ~$7/month          | Free tier sleeps after inactivity  |
| PythonAnywhere | Free limited                       | $5+/month          | Good alternative                   |

**Important:** Free tiers can change or be removed. For a real business you should use a paid plan so the bot stays online 24/7.

---

## Security Notes

- Never share your `BOT_TOKEN`
- Only put real bank account numbers via `/setmethod` (they stay in the database)
- The bot never auto-approves payments — only the admin can approve after seeing the money
- Screenshots alone are not proof of payment (the bot clearly tells users this)

---

## Support Commands for Admin

```
/admin              - Open admin panel
/setmethod ID Name Number
/activate USER_ID PLAN_ID
/revoke USER_ID [reason]
/addbook            - Start adding a book
```

---

Built for **Rich Ethiopia**.
```
