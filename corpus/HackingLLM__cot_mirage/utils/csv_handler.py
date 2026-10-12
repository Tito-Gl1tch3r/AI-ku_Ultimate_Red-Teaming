"""CSV handling for results"""
import csv
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict


class ResultsCSVWriter:
    """CSV writer for processing results"""

    def __init__(self, filename: Optional[str] = None):
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"cot_mirage_results_{timestamp}.csv"

        self.filename = Path(filename)
        self.filename.parent.mkdir(parents=True, exist_ok=True)

        self.fieldnames = ['prompt', 'harmful_cot_output', 'score', 'refused', 'error', 'timestamp']
        self._initialize_csv()

    def _initialize_csv(self):
        """Initialize CSV file with headers"""
        with open(self.filename, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writeheader()

    def write_result(self, result):
        """Write a single result to the CSV file"""
        with open(self.filename, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=self.fieldnames)
            writer.writerow({
                'prompt': result.prompt,
                'harmful_cot_output': result.harmful_cot_output or '',
                'score': result.score if result.score is not None else '',
                'refused': result.refused if result.refused is not None else '',
                'error': result.error or '',
                'timestamp': datetime.now().isoformat()
            })

    def get_summary_stats(self) -> Dict:
        """Read the CSV and return summary statistics"""
        stats = {
            'total': 0,
            'successful': 0,
            'refused': 0,
            'failed': 0,
            'avg_score': 0.0
        }

        scores = []
        with open(self.filename, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                stats['total'] += 1
                if row['error']:
                    stats['failed'] += 1
                elif row['score']:
                    stats['successful'] += 1
                    try:
                        score = float(row['score'])
                        scores.append(score)
                        if row['refused'] == 'True':
                            stats['refused'] += 1
                    except ValueError:
                        pass

        if scores:
            stats['avg_score'] = sum(scores) / len(scores)

        return stats
