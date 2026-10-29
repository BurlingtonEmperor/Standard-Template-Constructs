import json
import lzma
import os

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

class StandardTemplateConstructs:
    def __init__(self, db_path="stc_database.json.xz", threshold=0.20):
        self.db_path = db_path
        self.threshold = threshold
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 3), stop_words='english')
        
        self.templates = self._load_db()
        self.template_ids = list(self.templates.keys())
        self.matrix = None
        
        if self.templates:
            self._fit_vectorizer()

    def _load_db(self):
        if os.path.exists(self.db_path):
            with lzma.open(self.db_path, "rt", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def save_db(self):
        with lzma.open(self.db_path, "wt", encoding="utf-8") as f:
            json.dump(self.templates, f, indent=2)

    def _fit_vectorizer(self):
        self.template_ids = list(self.templates.keys())
        corpus = [data["corpus"] for data in self.templates.values()]
        self.matrix = self.vectorizer.fit_transform(corpus)

    def add_template(self, template_id, keywords, slots, code_template):
        """Adds a new template to the database and updates the vector space."""
        self.templates[template_id] = {
            "corpus": keywords,
            "slots": slots,
            "code": code_template
        }
        
        # Save compressed to disk using the instance method
        self.save_db()
        
        # Re-fit the vectorizer matrix on the updated templates
        self._fit_vectorizer()
        
        print(f"[STC] Matrix re-fitted! Total templates in memory: {len(self.template_ids)}")

    def offline_match(self, user_prompt):
        if self.matrix is None or not self.template_ids:
            return None, 0.0

        query_vec = self.vectorizer.transform([user_prompt])
        scores = cosine_similarity(query_vec, self.matrix).flatten()
        
        best_idx = scores.argmax()
        best_score = float(scores[best_idx])

        if best_score < self.threshold:
            return None, best_score  # here is where we use the llm.

        return self.template_ids[best_idx], best_score
    
    def offline_fallback(self, user_prompt):
        matched_id, score = self.offline_match(user_prompt)
    
        if not matched_id:
            return "Error: No matching template found in STC database, and you are in Rubric mode."
        
        template_data = self.templates[matched_id]
    
        output = f"""/* ==========================================
        Rubric Mode: Matched '{matched_id}' 
        Confidence Score: {score:.2f}
        Action: Fill in the {{placeholder}} slots manually.
        ========================================== */\n\n"""
        output += template_data["code"]
    
        return output

    def render_template(self, template_id, slot_values):
        code_template = self.templates[template_id]["code"]
        return code_template.format(**slot_values)