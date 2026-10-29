import streamlit as st
from openai import OpenAI

from flask import Flask, render_template, request, jsonify;
from flask_socketio import SocketIO, emit;

import subprocess
import sys

import json
import re

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtWebEngineWidgets import QWebEngineView

from threading import Timer;

from stc_database import *

stc = StandardTemplateConstructs()

class MiniBrowser(QMainWindow):
  def __init__(self, url):
    super().__init__()
        
    self.setWindowTitle("Standard Template Constructs")
    self.resize(1280, 720)  
        
    self.browser = QWebEngineView()
    self.browser.setUrl(QUrl(url))
        
    self.browser.setContextMenuPolicy(Qt.ContextMenuPolicy.NoContextMenu)
        
    self.setCentralWidget(self.browser)

URL = "http://127.0.0.1:5002"
app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

client = OpenAI(base_url="http://localhost:8080/v1", api_key="local")

def request_generated_stc(user_prompt):
    system_prompt = (
        "You are an expert meta-programming agent for Standard Template Constructs (STC). "
        "You MUST return a valid JSON object and NOTHING ELSE. No conversational intro, no outro. "
        "Your JSON object must contain EXACTLY these four keys:\n"
        "1. 'template_id': a unique snake_case string (ex: 'fast_api_get')\n"
        "2. 'keywords': a descriptive string of keywords (ex: 'fastapi get route endpoint python api rest json')\n"
        "3. 'slots': a list of variable placeholder names (ex: ['route_path', 'return_message'])\n"
        "4. 'code': the raw code string using Python-style braces for placeholders"
    )

    prompt = f"Create a Standard Template Construct for this request: {user_prompt}"
    
    try:
        response = client.chat.completions.create(
            model="models\\NVIDIA-Nemotron-3.5-Lightning-30B-A3B-Q4_0.gguf",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )

        llm_output_text = response.choices[0].message.content
        print(f"Raw LLM Output:\n{llm_output_text}") 

        if not llm_output_text or not llm_output_text.strip():
            raise ValueError("LLM returned an empty string response.")

        cleaned_text = llm_output_text.strip()
        
        if cleaned_text.startswith("```"):
            cleaned_text = re.sub(r"^```(?:json)?\s*", "", cleaned_text)
            cleaned_text = re.sub(r"\s*```$", "", cleaned_text)
            
        parsed_data = json.loads(cleaned_text)
        
        template_id = parsed_data.get("template_id")
        keywords = parsed_data.get("keywords")
        slots = parsed_data.get("slots")
        code = parsed_data.get("code")
        
        stc.add_template(template_id, keywords, slots, code)
        return template_id, code

    except Exception as e:
        print(f"[STC ERROR] JSON Decoding or LLM error: {e}")
        return "error_template", f"# [STC ERROR] Failed to parse model output for: {user_prompt}"

@app.route('/')
def index():
  return render_template("index.html")

@app.route('/llm_comm', methods=["POST"])
def llm_comm ():
  message_json = request.get_json()

  prompt = message_json.get("llm_prompt")
  mode_set = message_json.get("rubric")
  template_id, confidence = stc.offline_match(prompt)

  if mode_set == "1":
    return stc.offline_fallback(prompt)

  if not template_id or confidence < stc.threshold:
    request_generated_stc(prompt)
    return "Error: Template not found in database. Creating new template..."
    
  template_data = stc.templates[template_id]
  required_slots = template_data["slots"]

  system_prompt = (
    "You are an automated parameter extractor for Standard Template Constructs (STC). "
    "Your only job is to extract values from the user prompt to fill the requested slots. "
    "Return ONLY a valid JSON object mapping the slot names to their extracted values. No markdown formatting, no conversational text."
  )

  processed_prompt = f"Template Slots Needed: {required_slots}\nUser Request: {prompt}"

  response = client.chat.completions.create(
    model="local-model",
    messages=[
        {"role" : "system", "content" : system_prompt},
        {"role" : "user", "content" : processed_prompt}
    ],
    response_format={"type": "json_object"}, # Forces strict JSON output
    temperature=0.0
  )

  llm_output_json = response.choices[0].message.content
  slot_values = json.loads(llm_output_json)

  final_code = stc.render_template(template_id, slot_values)
  return final_code

def begin_window():
  l_app = QApplication(sys.argv)

  window = MiniBrowser(URL)
  window.show()

  sys.exit(l_app.exec())

if __name__ == '__main__':
  Timer(1, begin_window).start()
  socketio.run(app, port=5002, debug=True, use_reloader=False)
