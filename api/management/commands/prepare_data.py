# api/management/commands/prepare_data.py
from django.core.management.base import BaseCommand
import pandas as pd

class Command(BaseCommand):
    help = 'Loads and processes datasets to create a clean_dataset.csv for training.'

    def handle(self, *args, **kwargs):
        all_data = []
        self.stdout.write("Starting data preparation...")

        try:
            df_spam = pd.read_csv('SMSSpamCollection', sep='\t', header=None, names=['label_raw', 'text'], encoding='utf-8')
            df_spam['label'] = df_spam['label_raw'].map({'ham': 'green', 'spam': 'yellow'})
            df_spam_clean = df_spam[['text', 'label']]
            all_data.append(df_spam_clean)
            self.stdout.write(self.style.SUCCESS(f"✅ Processed {len(df_spam_clean)} records from SMSSpamCollection."))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING("⚠️ SMSSpamCollection file not found. Skipping."))

        try:
            df_labeled = pd.read_csv('labeled_data.csv', encoding='utf-8')
            df_labeled['label'] = df_labeled['class'].map({0: 'red', 1: 'red', 2: 'green'})
            df_labeled.rename(columns={'tweet': 'text'}, inplace=True)
            df_labeled_clean = df_labeled[['text', 'label']]
            all_data.append(df_labeled_clean)
            self.stdout.write(self.style.SUCCESS(f"✅ Processed {len(df_labeled_clean)} records from labeled_data.csv."))
        except FileNotFoundError:
            self.stdout.write(self.style.WARNING("⚠️ labeled_data.csv file not found. Skipping."))

        if not all_data:
            self.stdout.write(self.style.ERROR("🔥 No data processed. Exiting."))
            return

        final_df = pd.concat(all_data, ignore_index=True)
        final_df = final_df.sample(frac=1).reset_index(drop=True)
        final_df.to_csv('api/clean_dataset.csv', index=False)
        
        self.stdout.write(self.style.SUCCESS("\n🎉 --- Success! --- 🎉"))
        self.stdout.write(f"Created clean_dataset.csv with {len(final_df)} total records.")
        self.stdout.write("Label distribution:")
        self.stdout.write(str(final_df['label'].value_counts()))