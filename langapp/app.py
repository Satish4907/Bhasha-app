from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date
import json, os

app = Flask(__name__)
app.config['SECRET_KEY'] = 'bhasha-learning-secret-2024'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///bhasha.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# ─── MODELS ─────────────────────────────────────────────────────────────────

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    native_languages = db.Column(db.String(200), default='Hindi,Bhojpuri,English')
    progress = db.relationship('Progress', backref='user', lazy=True)
    quiz_results = db.relationship('QuizResult', backref='user', lazy=True)

class Progress(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    completed = db.Column(db.Boolean, default=False)
    completed_at = db.Column(db.DateTime)
    xp_earned = db.Column(db.Integer, default=0)

class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    language = db.Column(db.String(50), nullable=False)
    lesson_id = db.Column(db.String(100), nullable=False)
    score = db.Column(db.Integer, default=0)
    total = db.Column(db.Integer, default=0)
    taken_at = db.Column(db.DateTime, default=datetime.utcnow)

class Streak(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    current_streak = db.Column(db.Integer, default=0)
    longest_streak = db.Column(db.Integer, default=0)
    last_activity = db.Column(db.Date)
    total_xp = db.Column(db.Integer, default=0)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# ─── LESSON DATA ─────────────────────────────────────────────────────────────

LANGUAGES = {
    'marathi': {
        'name': 'Marathi', 'native': 'मराठी', 'flag': '🟠',
        'color': '#FF6B35', 'bg': '#FFF3EE',
        'desc': 'Maharashtra chi bhasha — language of your home state!',
        'base': ['Hindi'], 'level': 'Beginner'
    },
    'english': {
        'name': 'English', 'native': 'English', 'flag': '🔵',
        'color': '#4A90D9', 'bg': '#EEF4FB',
        'desc': 'Level up from intermediate to fluent English speaker',
        'base': ['Hindi', 'English'], 'level': 'Intermediate'
    },
    'marwadi': {
        'name': 'Marwadi', 'native': 'मारवाड़ी', 'flag': '🟡',
        'color': '#F5A623', 'bg': '#FFFBF0',
        'desc': 'Rajasthan ki pyari bhasha — rich culture and warm people',
        'base': ['Hindi'], 'level': 'Beginner'
    },
    'sanskrit': {
        'name': 'Sanskrit', 'native': 'संस्कृतम्', 'flag': '🟣',
        'color': '#7B68EE', 'bg': '#F3F0FF',
        'desc': 'Mother of Indian languages — unlock the root of everything',
        'base': ['Hindi'], 'level': 'Advanced'
    }
}

LESSONS = {
    'marathi': [
        {
            'id': 'mar_greet', 'title': 'Greetings', 'icon': '🙏', 'xp': 10,
            'words': [
                {'word': 'नमस्कार', 'roman': 'Namaskar', 'meaning': 'Hello / Greetings', 'hindi': 'नमस्ते'},
                {'word': 'धन्यवाद', 'roman': 'Dhanyavaad', 'meaning': 'Thank you', 'hindi': 'धन्यवाद'},
                {'word': 'हो', 'roman': 'Ho', 'meaning': 'Yes', 'hindi': 'हाँ'},
                {'word': 'नाही', 'roman': 'Naahi', 'meaning': 'No', 'hindi': 'नहीं'},
                {'word': 'माफ करा', 'roman': 'Maaf kara', 'meaning': 'Sorry / Excuse me', 'hindi': 'माफ करो'},
                {'word': 'कसे आहात?', 'roman': 'Kase aahat?', 'meaning': 'How are you?', 'hindi': 'कैसे हो?'},
                {'word': 'ठीक आहे', 'roman': 'Theek aahe', 'meaning': 'I am fine', 'hindi': 'ठीक हूँ'},
            ],
            'quiz': [
                {'q': 'Marathi mein "Haan" kaise kehte hain?', 'options': ['नाही', 'हो', 'माफ करा', 'धन्यवाद'], 'ans': 1},
                {'q': '"Dhanyavaad" ka matlab kya hai?', 'options': ['Hello', 'Sorry', 'Thank you', 'Yes'], 'ans': 2},
                {'q': '"Kase aahat?" ka Hindi translation kya hai?', 'options': ['Kya hua?', 'Kaise ho?', 'Kahan ho?', 'Kaun ho?'], 'ans': 1},
                {'q': 'Marathi mein "No" kaise kehte hain?', 'options': ['हो', 'ठीक', 'नाही', 'माफ'], 'ans': 2},
            ]
        },
        {
            'id': 'mar_numbers', 'title': 'Numbers 1-10', 'icon': '🔢', 'xp': 10,
            'words': [
                {'word': 'एक', 'roman': 'Ek', 'meaning': '1 - One', 'hindi': 'एक'},
                {'word': 'दोन', 'roman': 'Don', 'meaning': '2 - Two', 'hindi': 'दो'},
                {'word': 'तीन', 'roman': 'Teen', 'meaning': '3 - Three', 'hindi': 'तीन'},
                {'word': 'चार', 'roman': 'Chaar', 'meaning': '4 - Four', 'hindi': 'चार'},
                {'word': 'पाच', 'roman': 'Paach', 'meaning': '5 - Five', 'hindi': 'पाँच'},
                {'word': 'सहा', 'roman': 'Saha', 'meaning': '6 - Six', 'hindi': 'छह'},
                {'word': 'सात', 'roman': 'Saat', 'meaning': '7 - Seven', 'hindi': 'सात'},
                {'word': 'आठ', 'roman': 'Aath', 'meaning': '8 - Eight', 'hindi': 'आठ'},
                {'word': 'नऊ', 'roman': 'Nau', 'meaning': '9 - Nine', 'hindi': 'नौ'},
                {'word': 'दहा', 'roman': 'Daha', 'meaning': '10 - Ten', 'hindi': 'दस'},
            ],
            'quiz': [
                {'q': 'Marathi mein "2" kaise kehte hain?', 'options': ['दोन', 'दो', 'दहा', 'तीन'], 'ans': 0},
                {'q': '"Paach" ka matlab kya hai?', 'options': ['4', '6', '5', '7'], 'ans': 2},
                {'q': 'Marathi mein "10" kya hota hai?', 'options': ['नऊ', 'दहा', 'सात', 'आठ'], 'ans': 1},
                {'q': '"Saha" ka matlab kya hai?', 'options': ['5', '6', '7', '8'], 'ans': 1},
            ]
        },
        {
            'id': 'mar_family', 'title': 'Family Words', 'icon': '👨‍👩‍👧', 'xp': 15,
            'words': [
                {'word': 'आई', 'roman': 'Aayi', 'meaning': 'Mother', 'hindi': 'माँ'},
                {'word': 'बाबा', 'roman': 'Baaba', 'meaning': 'Father', 'hindi': 'पिताजी'},
                {'word': 'भाऊ', 'roman': 'Bhau', 'meaning': 'Brother', 'hindi': 'भाई'},
                {'word': 'ताई', 'roman': 'Tai', 'meaning': 'Elder Sister', 'hindi': 'दीदी'},
                {'word': 'मुलगा', 'roman': 'Mulga', 'meaning': 'Son / Boy', 'hindi': 'बेटा / लड़का'},
                {'word': 'मुलगी', 'roman': 'Mulgi', 'meaning': 'Daughter / Girl', 'hindi': 'बेटी / लड़की'},
                {'word': 'आजोबा', 'roman': 'Aajoba', 'meaning': 'Grandfather', 'hindi': 'दादाजी'},
                {'word': 'आजी', 'roman': 'Aaji', 'meaning': 'Grandmother', 'hindi': 'दादी माँ'},
            ],
            'quiz': [
                {'q': 'Marathi mein "Maa" ko kya kehte hain?', 'options': ['ताई', 'आई', 'आजी', 'मुलगी'], 'ans': 1},
                {'q': '"Bhau" ka Hindi mein kya matlab hai?', 'options': ['Pitaji', 'Bhai', 'Dada', 'Beta'], 'ans': 1},
                {'q': '"Aajoba" ka matlab kya hai?', 'options': ['Nana', 'Dada', 'Chacha', 'Bua'], 'ans': 1},
                {'q': 'Marathi mein "Beti" kaise kehte hain?', 'options': ['मुलगा', 'ताई', 'मुलगी', 'आई'], 'ans': 2},
            ]
        },
        {
            'id': 'mar_food', 'title': 'Food & Eating', 'icon': '🍛', 'xp': 15,
            'words': [
                {'word': 'जेवण', 'roman': 'Jevan', 'meaning': 'Food / Meal', 'hindi': 'खाना'},
                {'word': 'पाणी', 'roman': 'Paani', 'meaning': 'Water', 'hindi': 'पानी'},
                {'word': 'भात', 'roman': 'Bhaat', 'meaning': 'Rice', 'hindi': 'चावल'},
                {'word': 'पोळी', 'roman': 'Poli', 'meaning': 'Roti / Chapati', 'hindi': 'रोटी'},
                {'word': 'भाजी', 'roman': 'Bhaaji', 'meaning': 'Vegetable dish', 'hindi': 'सब्ज़ी'},
                {'word': 'चहा', 'roman': 'Chaha', 'meaning': 'Tea', 'hindi': 'चाय'},
                {'word': 'गोड', 'roman': 'God', 'meaning': 'Sweet', 'hindi': 'मीठा'},
                {'word': 'तिखट', 'roman': 'Tikhat', 'meaning': 'Spicy', 'hindi': 'तीखा'},
            ],
            'quiz': [
                {'q': 'Marathi mein "Roti" ko kya kehte hain?', 'options': ['भात', 'भाजी', 'पोळी', 'जेवण'], 'ans': 2},
                {'q': '"Paani" Marathi mein kya hota hai?', 'options': ['पाणी', 'भात', 'चहा', 'गोड'], 'ans': 0},
                {'q': '"Tikhat" ka matlab kya hai?', 'options': ['Sweet', 'Sour', 'Spicy', 'Salty'], 'ans': 2},
                {'q': 'Marathi mein "Chai" kaise kehte hain?', 'options': ['भाजी', 'चहा', 'पाणी', 'भात'], 'ans': 1},
            ]
        },
    ],
    'english': [
        {
            'id': 'eng_formal', 'title': 'Formal Speaking', 'icon': '💼', 'xp': 10,
            'words': [
                {'word': 'Regarding', 'roman': 'ri-GAAR-ding', 'meaning': 'Ke baare mein / Ke sambandh mein', 'hindi': 'के संबंध में'},
                {'word': 'Furthermore', 'roman': 'FUR-ther-more', 'meaning': 'Aur bhi / Iske alawa', 'hindi': 'इसके अलावा'},
                {'word': 'Nevertheless', 'roman': 'nev-er-the-LESS', 'meaning': 'Phir bhi / Fir bhi', 'hindi': 'फिर भी'},
                {'word': 'Consequently', 'roman': 'KON-se-kwent-lee', 'meaning': 'Isliye / Nateejan', 'hindi': 'इसलिए / परिणामस्वरूप'},
                {'word': 'Appreciate', 'roman': 'ah-PREE-shee-ate', 'meaning': 'Takdir karna / Shukriya ada karna', 'hindi': 'सराहना करना'},
                {'word': 'Clarify', 'roman': 'KLAIR-ih-fy', 'meaning': 'Spasht karna / Samjhana', 'hindi': 'स्पष्ट करना'},
                {'word': 'Feasible', 'roman': 'FEE-zih-bul', 'meaning': 'Mumkin / Sambhav', 'hindi': 'संभव'},
            ],
            'quiz': [
                {'q': '"Furthermore" ka matlab kya hai?', 'options': ['Isliye', 'Iske alawa', 'Phir bhi', 'Ke baare mein'], 'ans': 1},
                {'q': 'Iska English kya hoga: "Phir bhi kaam karna hoga"?', 'options': ['Furthermore we must work', 'Nevertheless we must work', 'Consequently we must work', 'Regarding work'], 'ans': 1},
                {'q': '"Feasible" ka matlab kya hai?', 'options': ['Mushkil', 'Sambhav', 'Zaruri', 'Acha'], 'ans': 1},
                {'q': '"Clarify" ka Hindi matlab kya hai?', 'options': ['Puchna', 'Sunna', 'Samjhana', 'Bolna'], 'ans': 2},
            ]
        },
        {
            'id': 'eng_idioms', 'title': 'Common Idioms', 'icon': '💬', 'xp': 15,
            'words': [
                {'word': 'Hit the nail on the head', 'roman': 'hit the nail on the head', 'meaning': 'Bilkul sahi baat kahna', 'hindi': 'बिल्कुल सही बात कहना'},
                {'word': 'Break the ice', 'roman': 'break the ice', 'meaning': 'Baat karna shuru karna (strangers ke beech)', 'hindi': 'बातचीत शुरू करना'},
                {'word': 'Under the weather', 'roman': 'under the weather', 'meaning': 'Thoda beemar ya thaka hua feel karna', 'hindi': 'तबीयत ठीक नहीं'},
                {'word': 'Bite the bullet', 'roman': 'bite the bullet', 'meaning': 'Mushkil situation ko himmat se face karna', 'hindi': 'हिम्मत से सामना करना'},
                {'word': 'Cost an arm and a leg', 'roman': 'cost an arm and a leg', 'meaning': 'Bahut zyada mehenga hona', 'hindi': 'बहुत महंगा होना'},
                {'word': 'Once in a blue moon', 'roman': 'once in a blue moon', 'meaning': 'Bahut kam hi kabhi / rarely', 'hindi': 'बहुत कम'},
            ],
            'quiz': [
                {'q': '"Under the weather" ka matlab kya hai?', 'options': ['Baarish mein hona', 'Beemar feel karna', 'Bahut khush hona', 'Bahut thanda hona'], 'ans': 1},
                {'q': '"Once in a blue moon" use kab karte hain?', 'options': ['Roz', 'Bahut kam', 'Hamesha', 'Kabhi nahi'], 'ans': 1},
                {'q': 'Agar koi cheez "costs an arm and a leg" to iska matlab?', 'options': ['Free hai', 'Bahut sasta hai', 'Bahut mehnga hai', 'Accha deal hai'], 'ans': 2},
                {'q': '"Break the ice" ka matlab kya hai?', 'options': ['Baraf todna', 'Ladna', 'Nai baat shuru karna', 'Kuch todna'], 'ans': 2},
            ]
        },
        {
            'id': 'eng_tenses', 'title': 'Tenses Made Easy', 'icon': '⏰', 'xp': 20,
            'words': [
                {'word': 'I eat rice every day', 'roman': 'Simple Present', 'meaning': 'Main roz chawal khata hoon (routine)', 'hindi': 'सामान्य वर्तमान'},
                {'word': 'I am eating right now', 'roman': 'Present Continuous', 'meaning': 'Main abhi kha raha hoon (abhi ho raha hai)', 'hindi': 'चल रहा है अभी'},
                {'word': 'I ate yesterday', 'roman': 'Simple Past', 'meaning': 'Maine kal khaya tha (ho gaya)', 'hindi': 'बीत गया'},
                {'word': 'I have eaten already', 'roman': 'Present Perfect', 'meaning': 'Main kha chuka hoon (abhi abhi hua)', 'hindi': 'अभी हुआ'},
                {'word': 'I will eat tomorrow', 'roman': 'Simple Future', 'meaning': 'Main kal khaaunga (hoga)', 'hindi': 'होगा आगे'},
                {'word': 'I was eating when you called', 'roman': 'Past Continuous', 'meaning': 'Jab tune call kiya tab main kha raha tha', 'hindi': 'तब हो रहा था'},
            ],
            'quiz': [
                {'q': '"I am studying right now" — yeh kaun sa tense hai?', 'options': ['Simple Present', 'Present Continuous', 'Past Tense', 'Future Tense'], 'ans': 1},
                {'q': '"I went to school" — yeh kaun sa tense hai?', 'options': ['Present Perfect', 'Simple Present', 'Simple Past', 'Future'], 'ans': 2},
                {'q': 'Future mein baat karna ho to kaunsa word use karte hain?', 'options': ['Was', 'Have', 'Will', 'Are'], 'ans': 2},
                {'q': '"I have finished my work" — ka matlab kya hai?', 'options': ['Main kaam kar raha hoon', 'Maine kaam karlia hai', 'Main kaam karunga', 'Kaam hua tha'], 'ans': 1},
            ]
        },
    ],
    'marwadi': [
        {
            'id': 'mar_w_greet', 'title': 'Greetings', 'icon': '🙏', 'xp': 10,
            'words': [
                {'word': 'खम्मा घणी', 'roman': 'Khamma Ghani', 'meaning': 'Traditional Marwadi greeting / Blessings to you', 'hindi': 'नमस्ते / प्रणाम'},
                {'word': 'राम राम', 'roman': 'Ram Ram', 'meaning': 'Hello (very common in Rajasthan)', 'hindi': 'राम राम / नमस्ते'},
                {'word': 'कांई हाल छे?', 'roman': 'Kaai haal chhe?', 'meaning': 'How are you?', 'hindi': 'कैसे हो?'},
                {'word': 'ठीक छूं', 'roman': 'Theek chhoon', 'meaning': 'I am fine', 'hindi': 'ठीक हूँ'},
                {'word': 'हाँ जी', 'roman': 'Haan ji', 'meaning': 'Yes (respectful)', 'hindi': 'हाँ जी'},
                {'word': 'कोनी', 'roman': 'Koni', 'meaning': 'No / Not', 'hindi': 'नहीं'},
                {'word': 'थांकूं', 'roman': 'Thaankoon', 'meaning': 'Thank you', 'hindi': 'धन्यवाद'},
            ],
            'quiz': [
                {'q': 'Rajasthan mein traditional greeting kya hai?', 'options': ['नमस्कार', 'खम्मा घणी', 'सत श्री अकाल', 'आदाब'], 'ans': 1},
                {'q': '"Koni" ka matlab kya hai?', 'options': ['Haan', 'Nahi', 'Shukriya', 'Kaise ho'], 'ans': 1},
                {'q': '"Kaai haal chhe?" ka Hindi translation?', 'options': ['Kya hua?', 'Kahan ho?', 'Kaise ho?', 'Kaun ho?'], 'ans': 2},
                {'q': '"Theek chhoon" ka matlab kya hai?', 'options': ['Mujhe bhook lagi hai', 'Main theek hoon', 'Shukriya', 'Alvida'], 'ans': 1},
            ]
        },
        {
            'id': 'mar_w_daily', 'title': 'Daily Expressions', 'icon': '☀️', 'xp': 15,
            'words': [
                {'word': 'म्हारो', 'roman': 'Mhaaro', 'meaning': 'My / Mine', 'hindi': 'मेरा'},
                {'word': 'थारो', 'roman': 'Thaaro', 'meaning': 'Your / Yours', 'hindi': 'तुम्हारा'},
                {'word': 'खावणो', 'roman': 'Khaavno', 'meaning': 'To eat / Eating', 'hindi': 'खाना'},
                {'word': 'पाणी', 'roman': 'Paani', 'meaning': 'Water', 'hindi': 'पानी'},
                {'word': 'घर', 'roman': 'Ghar', 'meaning': 'Home / House', 'hindi': 'घर'},
                {'word': 'आज', 'roman': 'Aaj', 'meaning': 'Today', 'hindi': 'आज'},
                {'word': 'काल', 'roman': 'Kaal', 'meaning': 'Yesterday / Tomorrow', 'hindi': 'कल'},
                {'word': 'बोत', 'roman': 'Bot', 'meaning': 'Very / A lot', 'hindi': 'बहुत'},
            ],
            'quiz': [
                {'q': '"Mhaaro" ka matlab kya hai?', 'options': ['Tumhara', 'Mera', 'Unka', 'Hamara'], 'ans': 1},
                {'q': '"Bot" ka Hindi matlab kya hai?', 'options': ['Thoda', 'Bahut', 'Kuch', 'Bina'], 'ans': 1},
                {'q': 'Marwadi mein "Tumhara" kaise kehte hain?', 'options': ['म्हारो', 'थारो', 'उनको', 'आपको'], 'ans': 1},
                {'q': '"Khaavno" ka matlab kya hai?', 'options': ['Sona', 'Padhna', 'Khana', 'Chalana'], 'ans': 2},
            ]
        },
        {
            'id': 'mar_w_numbers', 'title': 'Numbers', 'icon': '🔢', 'xp': 10,
            'words': [
                {'word': 'एक', 'roman': 'Ek', 'meaning': '1', 'hindi': 'एक'},
                {'word': 'दो', 'roman': 'Do', 'meaning': '2', 'hindi': 'दो'},
                {'word': 'तीन', 'roman': 'Teen', 'meaning': '3', 'hindi': 'तीन'},
                {'word': 'चार', 'roman': 'Chaar', 'meaning': '4', 'hindi': 'चार'},
                {'word': 'पाँच', 'roman': 'Paanch', 'meaning': '5', 'hindi': 'पाँच'},
                {'word': 'छ', 'roman': 'Chha', 'meaning': '6', 'hindi': 'छह'},
                {'word': 'सात', 'roman': 'Saat', 'meaning': '7', 'hindi': 'सात'},
                {'word': 'आठ', 'roman': 'Aath', 'meaning': '8', 'hindi': 'आठ'},
                {'word': 'नौ', 'roman': 'Nau', 'meaning': '9', 'hindi': 'नौ'},
                {'word': 'दस', 'roman': 'Das', 'meaning': '10', 'hindi': 'दस'},
            ],
            'quiz': [
                {'q': 'Marwadi mein "6" kya hota hai?', 'options': ['पाँच', 'सात', 'छ', 'आठ'], 'ans': 2},
                {'q': '"Das" ka matlab kya hai?', 'options': ['8', '9', '10', '7'], 'ans': 2},
                {'q': 'Marwadi aur Hindi mein 1-5 kya same hain?', 'options': ['Haan, same hain', 'Bilkul alag hain', 'Sirf 1-2 same hain', '3-5 alag hain'], 'ans': 0},
                {'q': '"Nau" ka matlab?', 'options': ['7', '8', '9', '10'], 'ans': 2},
            ]
        },
    ],
    'sanskrit': [
        {
            'id': 'san_basics', 'title': 'Basic Words', 'icon': '📿', 'xp': 15,
            'words': [
                {'word': 'नमः', 'roman': 'Namah', 'meaning': 'Salutation / I bow', 'hindi': 'नमस्कार'},
                {'word': 'अहम्', 'roman': 'Aham', 'meaning': 'I / Me', 'hindi': 'मैं'},
                {'word': 'त्वम्', 'roman': 'Tvam', 'meaning': 'You', 'hindi': 'तुम'},
                {'word': 'एतत्', 'roman': 'Etat', 'meaning': 'This', 'hindi': 'यह'},
                {'word': 'किम्', 'roman': 'Kim', 'meaning': 'What?', 'hindi': 'क्या?'},
                {'word': 'कः', 'roman': 'Kah', 'meaning': 'Who? (male)', 'hindi': 'कौन?'},
                {'word': 'आम्', 'roman': 'Aam', 'meaning': 'Yes', 'hindi': 'हाँ'},
                {'word': 'न', 'roman': 'Na', 'meaning': 'No / Not', 'hindi': 'नहीं'},
                {'word': 'धन्यवादः', 'roman': 'Dhanyavaadah', 'meaning': 'Thank you', 'hindi': 'धन्यवाद'},
            ],
            'quiz': [
                {'q': 'Sanskrit mein "Main" kaise kehte hain?', 'options': ['त्वम्', 'अहम्', 'कः', 'एतत्'], 'ans': 1},
                {'q': '"Na" ka Sanskrit mein matlab kya hai?', 'options': ['Haan', 'Nahi', 'Kya', 'Kaun'], 'ans': 1},
                {'q': '"Kim" ka matlab kya hai?', 'options': ['Kaun?', 'Kahan?', 'Kya?', 'Kab?'], 'ans': 2},
                {'q': '"Tvam" Sanskrit mein kiska liye use hota hai?', 'options': ['Main', 'Tum', 'Woh', 'Hum'], 'ans': 1},
            ]
        },
        {
            'id': 'san_shlokas', 'title': 'Famous Shlokas', 'icon': '🕉️', 'xp': 20,
            'words': [
                {'word': 'सर्वे भवन्तु सुखिनः', 'roman': 'Sarve bhavantu sukhinah', 'meaning': 'May all beings be happy', 'hindi': 'सभी सुखी हों'},
                {'word': 'अहिंसा परमो धर्मः', 'roman': 'Ahimsa paramo dharmah', 'meaning': 'Non-violence is the highest duty', 'hindi': 'अहिंसा सबसे बड़ा धर्म है'},
                {'word': 'योगः कर्मसु कौशलम्', 'roman': 'Yogah karmasu kaushalam', 'meaning': 'Yoga is excellence in action', 'hindi': 'कर्म में कुशलता ही योग है'},
                {'word': 'विद्या ददाति विनयम्', 'roman': 'Vidya dadati vinayam', 'meaning': 'Knowledge gives humility', 'hindi': 'विद्या से विनम्रता आती है'},
                {'word': 'जननी जन्मभूमिश्च स्वर्गादपि गरीयसी', 'roman': 'Janani janmabhumishcha svargadapi gariyasi', 'meaning': 'Mother and motherland are greater than heaven', 'hindi': 'माँ और मातृभूमि स्वर्ग से भी बड़ी है'},
            ],
            'quiz': [
                {'q': '"Sarve bhavantu sukhinah" ka kya arth hai?', 'options': ['Sab padhein', 'Sab khush rahein', 'Sab ladein', 'Sab jeeyein'], 'ans': 1},
                {'q': '"Ahimsa paramo dharmah" mein "paramo" ka matlab?', 'options': ['Chhota', 'Sabse bada', 'Ek', 'Kuch nahi'], 'ans': 1},
                {'q': '"Vidya dadati vinayam" mein "Vidya" ka matlab kya hai?', 'options': ['Dhan', 'Shakti', 'Gyan', 'Prem'], 'ans': 2},
                {'q': 'Gita ka famous shloka "Yogah karmasu..." kiska baare mein hai?', 'options': ['Meditation', 'Khana', 'Kaam mein shreshthata', 'Sona'], 'ans': 2},
            ]
        },
        {
            'id': 'san_roots', 'title': 'Sanskrit Roots in Hindi', 'icon': '🌳', 'xp': 20,
            'words': [
                {'word': 'विद् (vid)', 'roman': 'Vid = to know', 'meaning': 'Gyaan — vidya, video, wisdom sab isi se!', 'hindi': 'जानना → विद्या, विद्वान'},
                {'word': 'कर् (kar)', 'roman': 'Kar = to do', 'meaning': 'Kaam — karma, karta, karan sab isi se!', 'hindi': 'करना → कर्म, कारण'},
                {'word': 'गम् (gam)', 'roman': 'Gam = to go', 'meaning': 'Jaana — gaman, agam, sangam sab isi se!', 'hindi': 'जाना → गमन, आगमन'},
                {'word': 'भू (bhu)', 'roman': 'Bhu = to be / earth', 'meaning': 'Hona ya zameen — bhumi, bharat, bhuvan!', 'hindi': 'होना / धरती → भूमि, भारत'},
                {'word': 'दृश् (drsh)', 'roman': 'Drsh = to see', 'meaning': 'Dekhna — darshan, drishti, drishya sab!', 'hindi': 'देखना → दर्शन, दृष्टि'},
            ],
            'quiz': [
                {'q': '"Karma" word kaunse Sanskrit root se aaya hai?', 'options': ['विद्', 'कर्', 'गम्', 'भू'], 'ans': 1},
                {'q': '"Bhumi" aur "Bharat" dono kaunse Sanskrit root se connected hain?', 'options': ['विद्', 'कर्', 'दृश्', 'भू'], 'ans': 3},
                {'q': '"Darshan" aur "Drishti" kaunse root se bane hain?', 'options': ['गम्', 'भू', 'दृश्', 'विद्'], 'ans': 2},
                {'q': '"Vidya" kaunse Sanskrit root se bani hai?', 'options': ['विद्', 'कर्', 'भू', 'गम्'], 'ans': 0},
            ]
        },
    ]
}

# ─── ROUTES ─────────────────────────────────────────────────────────────────

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        if not username or not email or not password:
            error = 'Sab fields fill karo yaar!'
        elif User.query.filter_by(username=username).first():
            error = 'Yeh username already le liya kisi ne!'
        elif User.query.filter_by(email=email).first():
            error = 'Yeh email already registered hai!'
        elif len(password) < 6:
            error = 'Password kam se kam 6 characters ka hona chahiye'
        else:
            user = User(
                username=username, email=email,
                password_hash=generate_password_hash(password)
            )
            db.session.add(user)
            db.session.flush()
            streak = Streak(user_id=user.id)
            db.session.add(streak)
            db.session.commit()
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('auth.html', mode='register', error=error)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    error = None
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()
        if not user or not check_password_hash(user.password_hash, password):
            error = 'Username ya password galat hai!'
        else:
            login_user(user)
            return redirect(url_for('dashboard'))
    return render_template('auth.html', mode='login', error=error)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    streak = Streak.query.filter_by(user_id=current_user.id).first()
    if not streak:
        streak = Streak(user_id=current_user.id)
        db.session.add(streak)
        db.session.commit()

    lang_stats = {}
    for lang_key, lang_data in LANGUAGES.items():
        lessons = LESSONS.get(lang_key, [])
        completed = Progress.query.filter_by(
            user_id=current_user.id, language=lang_key, completed=True
        ).count()
        lang_stats[lang_key] = {
            'completed': completed,
            'total': len(lessons),
            'pct': int((completed / len(lessons) * 100)) if lessons else 0,
            **lang_data
        }

    recent = QuizResult.query.filter_by(user_id=current_user.id)\
        .order_by(QuizResult.taken_at.desc()).limit(5).all()

    return render_template('dashboard.html',
        lang_stats=lang_stats, streak=streak, recent=recent,
        languages=LANGUAGES
    )

@app.route('/learn/<lang>')
@login_required
def learn(lang):
    if lang not in LANGUAGES:
        return redirect(url_for('dashboard'))
    lessons = LESSONS.get(lang, [])
    completed_ids = {p.lesson_id for p in Progress.query.filter_by(
        user_id=current_user.id, language=lang, completed=True
    ).all()}
    return render_template('learn.html',
        lang=lang, lang_data=LANGUAGES[lang],
        lessons=lessons, completed_ids=completed_ids
    )

@app.route('/lesson/<lang>/<lesson_id>')
@login_required
def lesson(lang, lesson_id):
    if lang not in LANGUAGES:
        return redirect(url_for('dashboard'))
    lessons = LESSONS.get(lang, [])
    lesson_data = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson_data:
        return redirect(url_for('learn', lang=lang))
    done = Progress.query.filter_by(
        user_id=current_user.id, language=lang, lesson_id=lesson_id, completed=True
    ).first()
    return render_template('lesson.html',
        lang=lang, lang_data=LANGUAGES[lang],
        lesson=lesson_data, already_done=bool(done)
    )

@app.route('/quiz/<lang>/<lesson_id>')
@login_required
def quiz(lang, lesson_id):
    if lang not in LANGUAGES:
        return redirect(url_for('dashboard'))
    lessons = LESSONS.get(lang, [])
    lesson_data = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson_data:
        return redirect(url_for('learn', lang=lang))
    return render_template('quiz.html',
        lang=lang, lang_data=LANGUAGES[lang], lesson=lesson_data
    )

@app.route('/api/complete_lesson', methods=['POST'])
@login_required
def complete_lesson():
    data = request.json
    lang = data.get('lang')
    lesson_id = data.get('lesson_id')
    score = data.get('score', 0)
    total = data.get('total', 0)

    lessons = LESSONS.get(lang, [])
    lesson_data = next((l for l in lessons if l['id'] == lesson_id), None)
    if not lesson_data:
        return jsonify({'ok': False})

    existing = Progress.query.filter_by(
        user_id=current_user.id, language=lang, lesson_id=lesson_id
    ).first()

    xp = lesson_data['xp']
    if score == total:
        xp = int(xp * 1.5)  # bonus for perfect

    if not existing:
        prog = Progress(
            user_id=current_user.id, language=lang,
            lesson_id=lesson_id, completed=True,
            completed_at=datetime.utcnow(), xp_earned=xp
        )
        db.session.add(prog)
    else:
        existing.completed = True
        existing.completed_at = datetime.utcnow()

    quiz_result = QuizResult(
        user_id=current_user.id, language=lang,
        lesson_id=lesson_id, score=score, total=total
    )
    db.session.add(quiz_result)

    streak = Streak.query.filter_by(user_id=current_user.id).first()
    today = date.today()
    if streak.last_activity != today:
        if streak.last_activity and (today - streak.last_activity).days == 1:
            streak.current_streak += 1
        else:
            streak.current_streak = 1
        streak.last_activity = today
    if streak.current_streak > streak.longest_streak:
        streak.longest_streak = streak.current_streak
    if not existing:
        streak.total_xp += xp

    db.session.commit()
    return jsonify({'ok': True, 'xp': xp, 'streak': streak.current_streak})

@app.route('/profile')
@login_required
def profile():
    streak = Streak.query.filter_by(user_id=current_user.id).first()
    all_progress = Progress.query.filter_by(user_id=current_user.id, completed=True).all()
    all_quizzes = QuizResult.query.filter_by(user_id=current_user.id).all()

    lang_breakdown = {}
    for lang_key in LANGUAGES:
        done = [p for p in all_progress if p.language == lang_key]
        quizzes = [q for q in all_quizzes if q.language == lang_key]
        avg_score = 0
        if quizzes:
            avg_score = round(sum(q.score/q.total*100 for q in quizzes if q.total) / len(quizzes))
        lang_breakdown[lang_key] = {
            'lessons_done': len(done),
            'total': len(LESSONS.get(lang_key, [])),
            'avg_score': avg_score,
            'xp': sum(p.xp_earned for p in done),
            **LANGUAGES[lang_key]
        }

    return render_template('profile.html',
        streak=streak, lang_breakdown=lang_breakdown,
        total_quizzes=len(all_quizzes),
        languages=LANGUAGES
    )

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    print("\n🙏 Bhasha App chal raha hai!")
    print("   Browser mein jaao: http://localhost:5000\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
