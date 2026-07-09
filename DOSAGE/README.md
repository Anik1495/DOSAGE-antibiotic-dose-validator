# 🧬 DOSAGE Validator — Rule-Based Antibiotic Dose Checker

**License**: MIT (code) — see `data/SOURCE.md` for the dataset's own license (CC BY 4.0)  
**Authors**:  
- Ferdous Wahid Anik (Lead Developer & Project Lead)  
- Marzia Zaman (Clinical Advisor)  
- Tahmina Foyez (Pharmacological Reviewer)  
- Khandoker A. Mamun (Supervisor & Technical Advisor)  

**Contact**: mamun@cse.uiu.ac.bd

---

## 📄 Overview

This is a rule-based clinical decision support tool (FastAPI web app) that validates antibiotic prescriptions against patient-specific parameters — age, weight, renal function (CrCl), and pregnancy status. Given a prescribed dose, it flags overdose, underdose, wrong administration route, or renal adjustment issues, with a 15% tolerance band applied to dosing rules.

It supports two modes:
- **Single medication check** — validate one prescription via a web form.
- **Batch check** — upload a CSV of multiple prescriptions and get a validation report back, downloadable as CSV.

The rules and reference ranges the app validates against come from the **DOSAGE dataset** (see "Data" below) — a knowledge base covering 98 antibiotic generics and over 4,000 dosing scenarios, published in *Nature Scientific Data*.

---

## 🚀 Running locally

1. Clone the repo and install dependencies:
   ```bash
   git clone https://github.com/<your-username>/DOSAGE.git
   cd DOSAGE
   pip install -r requirements.txt
   ```
2. Download the dataset and add it to the `data/` folder — see `data/SOURCE.md` for the download link and `data/README.md` for the exact filenames/columns expected.
3. Run the app:
   ```bash
   uvicorn main:app --reload
   ```
4. Open `http://127.0.0.1:8000` in your browser.

No database or API keys are required — the app reads the dataset directly from the `data/` folder at startup.

---

## 📦 Repository Contents

- `main.py` — FastAPI backend: dose validation logic, renal/pregnancy checks, single and batch endpoints
- `templates/`, `static/` — front-end (HTML form, CSS, JS) for the web app
- `data/` — where the dataset CSVs go locally (not committed; see `data/SOURCE.md`)
- `notebooks/` — Jupyter notebooks with test cases exercising the validation rules
- `requirements.txt`, `render.yaml`, `Procfile` — dependencies and deployment config

---

## 📊 Data

This tool validates against the **DOSAGE dataset**: disease-specific dosing, standard dosing, renal-adjusted dosing, and pregnancy risk classifications for 98 antibiotics.

The dataset is published separately and is **not bundled in this repo**. Download it and see the field-by-field documentation at:

**Figshare:** https://figshare.com/s/7da6474b776654003959

**Citation:**
Anik, F. W., Zaman, M., Foyez, T., & Mamun, K. A. *DOSAGE: A Dataset for Optimized Safe Antibiotic Guidelines and Estimates*, Nature Scientific Data, 2025. DOI: https://www.doi.org/10.1038/s41597-025-05761-8

---

## 🧪 Test Notebooks

The `notebooks/` folder contains Jupyter notebooks exercising the validation logic against known test cases (overdose, underdose, renal edge cases, pregnancy flags, etc.).

---

## 📈 Use Cases

- Integration into CDSS or EHR platforms for real-time prescription audits
- Medical education tools for pharmacological training
- Antimicrobial stewardship analysis
- Reference implementation for AI-assisted medication validation workflows built on the DOSAGE dataset

---

## 🤝 Contributing

Contributions and feedback are welcome. Please open an issue or submit a pull request.

---

## 📬 Visit

www.dosage.iriic.uiu.ac.bd
