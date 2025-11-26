from flask import Flask, render_template, request
import pickle
import string
import re
from nltk.corpus import stopwords
from nltk.stem.snowball import SnowballStemmer

app = Flask(__name__)

# --------------------------------
# Load Model & Vectorizer
# --------------------------------
model = pickle.load(open("models/model.pkl", "rb"))
vectorizer = pickle.load(open("models/vectorizer.pkl", "rb"))

ss = SnowballStemmer(language='english')


# --------------------------------
# Text Cleaning Function
# --------------------------------
def transform_text(text):
    text = text.lower()                              # lowercase
    text = re.sub(r'[^a-zA-Z]', ' ', text)           # keep alphabets only
    text = text.split()                              # split words

    cleaned_words = []
    for word in text:
        if word not in stopwords.words('english'):
            cleaned_words.append(ss.stem(word))      # stemming

    return " ".join(cleaned_words)


# --------------------------------
# Routes
# --------------------------------
@app.route('/')
def home():
    return render_template("index.html")


@app.route('/predict', methods=['POST'])
def predict():
    message = request.form['message']

    # Clean message
    transformed_msg = transform_text(message)

    # Vectorize using LOADED vectorizer
    vector_input = vectorizer.transform([transformed_msg])

    # Predict
    result = model.predict(vector_input)[0]

    return render_template("predict.html", prediction=result)


# --------------------------------
# Run Flask App
# --------------------------------
if __name__ == "__main__":
    app.run(debug=True)
