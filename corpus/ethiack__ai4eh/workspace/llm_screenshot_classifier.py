import os
import json
from pathlib import Path
import google.generativeai as genai
from PIL import Image
from collections import Counter
import time


class ScreenshotClassifier:
    def __init__(self, api_key, screenshots_folder="screenshots"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel("gemini-2.0-flash")
        self.folder = Path(screenshots_folder)
        self.categories = [
            "Social Media",
            "Code/Development",
            "Documentation/Text",
            "Gaming",
            "Video/Media",
            "Settings/System",
            "Email/Communication",
            "E-commerce/Shopping",
            "Error/Alert",
            "Other",
        ]
        self.results = {}

    def classify_image(self, image_path):
        try:
            image = Image.open(image_path)
            prompt = f"Classify this screenshot into one category: {', '.join(self.categories)}. Respond with only the category name."
            response = self.model.generate_content([prompt, image])
            category = response.text.strip()

            # Fuzzy match if exact match fails
            if category not in self.categories:
                for cat in self.categories:
                    if (
                        cat.lower() in category.lower()
                        or category.lower() in cat.lower()
                    ):
                        return cat

                return "Other"

            return category
        except Exception as e:
            print(f"Error processing {image_path.name}: {e}")
            return "Error"

    def run(self, organize_files=False, save_json=True):
        """Main method to classify all images and optionally organize them"""
        if not self.folder.exists():
            print(f"Folder '{self.folder}' not found!")
            return

        # Get all image files
        image_files = [
            f
            for f in self.folder.iterdir()
            if f.suffix.lower() in {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp"}
        ]

        if not image_files:
            print("No images found!")
            return

        print(f"Classifying {len(image_files)} images...")

        # Classify images
        for i, img_path in enumerate(image_files, 1):
            print(f"[{i}/{len(image_files)}] {img_path.name}")
            category = self.classify_image(img_path)
            self.results[img_path.name] = category
            time.sleep(0.5)  # Rate limiting

        # Print summary
        counts = Counter(self.results.values())
        print(f"\nSummary ({len(image_files)} total):")
        for category, count in sorted(counts.items()):
            print(f" {category}: {count}")

        # Organize files if requested
        if organize_files:
            self._organize_files()

        # Save results
        if save_json:
            with open("classification_results.json", "w") as f:
                json.dump(self.results, f, indent=2)

            print("\nResults saved to classification_results.json")

    def _organize_files(self):
        """Move files into category folders"""
        for filename, category in self.results.items():
            if category == "Error":
                continue

            category_folder = self.folder / category
            category_folder.mkdir(exist_ok=True)

            src = self.folder / filename
            dst = category_folder / filename

            if src.exists() and not dst.exists():
                src.rename(dst)
                print(f"Moved {filename} to {category}/")


def main():
    api_key = os.getenv("GEMINI_API_KEY")

    if not api_key:
        print("Set GEMINI_API_KEY environment variable")
        return

    classifier = ScreenshotClassifier(api_key)
    classifier.run(organize_files=False, save_json=True)


if __name__ == "__main__":
    main()
