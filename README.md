# 🛍️ ShopGenie-AI

### AI-Powered Product Recommendation System

ShopGenie-AI is an AI-powered product recommendation web application that helps users discover suitable products based on their preferences, requirements, and budget.

The application analyzes user inputs and provides personalized product recommendations with match scores and explanations.

---

## 🚀 Features

- 🤖 AI-powered product recommendations
- 🎯 Personalized product matching
- 💰 Budget-based recommendations
- 📊 Product match percentage
- 💡 AI-generated recommendation explanations
- 🛒 Product details with "View Product" links
- 🎨 Modern and responsive user interface
- 🔐 Secure API-key configuration using environment variables

---

## 🧠 How It Works

1. The user enters their product requirements.
2. ShopGenie-AI processes the user's preferences.
3. The application uses AI to analyze the available products.
4. Products are ranked according to how well they match the user's requirements.
5. The application displays the best matches along with:
   - Product name
   - Price
   - Specifications
   - Match percentage
   - Reason for recommendation
   - Product link

---

## 🛠️ Technologies Used

### Frontend
- HTML5
- CSS3
- JavaScript

### Backend
- Python
- Flask

### AI
- Google Gemini API

### Tools
- Git
- GitHub
- Visual Studio Code

---

## 📁 Project Structure

```text
ShopGenie-AI/
│
├── app.py
├── requirements.txt
├── .env.example
├── .gitignore
│
├── static/
│   ├── style.css
│   └── script.js
│
└── templates/
    ├── index.html
    └── results.html