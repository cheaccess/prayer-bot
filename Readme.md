# 🙏 Prayer Bot for Telegram

This Telegram bot allows users to:
- Request prayers for others
- Volunteer to pray for others
- Join the "Crusade for the Liberation of Man" (КВЛ)

## Features
- Data automatically stored in Google Sheets
- Works 24/7 on Render free tier
- Built using `python-telegram-bot`, `gspread`, and Google API

## Deployment
1. Upload all files to GitHub (including your bot.py and service account JSON)
2. Connect the repository to [Render.com](https://render.com)
3. Create a **new “Worker” service**
4. Add environment variable:
   - `TOKEN`: your Telegram bot token
5. Deploy 🚀
