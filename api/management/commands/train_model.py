# api/management/commands/train_model.py
from django.core.management.base import BaseCommand
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import make_pipeline
import joblib

class Command(BaseCommand):
    help = 'Trains the ML model on the clean_dataset.csv and saves it.'

    def handle(self, *args, **kwargs):
        try:
            self.stdout.write("Loading clean dataset...")
            df = pd.read_csv('api/clean_dataset.csv')
            df.dropna(subset=['text'], inplace=True)

            X = df['text']
            y = df['label']

            model = make_pipeline(TfidfVectorizer(), MultinomialNB())

            self.stdout.write(self.style.WARNING("🤖 Training the AI model... (This may take a moment)"))
            model.fit(X, y)

            joblib.dump(model, 'api/message_classifier.joblib')

            self.stdout.write(self.style.SUCCESS("✅ Model trained and saved successfully as 'message_classifier.joblib'"))

        except FileNotFoundError:
            self.stdout.write(self.style.ERROR("🔥 Error: 'api/clean_dataset.csv' not found. Please run the 'prepare_data' command first."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An unexpected error occurred: {e}"))