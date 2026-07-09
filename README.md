# 🧬 DOSAGE: Dataset for Optimized Safe Antibiotic Guidelines and Estimates

**Version**: 1.0  
**License**: CC BY 4.0  
**Authors**:  
- Ferdous Wahid Anik (Lead Data Architect & Project Lead)  
- Marzia Zaman (Clinical Advisor)  
- Tahmina Foyez (Pharmacological Reviewer)  
- Khandoker A. Mamun (Supervisor & Technical Advisor)  

**Contact**: mamun@cse.uiu.ac.bd  

---

## 📄 Overview

DOSAGE is a clinically validated, knowledge-based dataset designed to support safe, personalized antibiotic prescribing. It captures standardized, disease-specific, and renal-adjusted dosing guidelines across 98 widely used antibiotics. The dataset is structured to accommodate patient-specific variables including age, weight, creatinine clearance (CrCl), pregnancy risk, and hypersensitivity, enabling integration into automated audit systems, rule-based clinical decision support systems (CDSS), and AI-assisted medication validation workflows.

---

## 📦 Repository Contents

- `d_dose.csv`: Disease-specific dosing regimens based on age, weight, disease, and route of administration  
- `s_dose.csv`: Standardized dosing regimens per antibiotic (not disease-specific)  
- `r_dose.csv`: Renal dose adjustments across CrCl ranges for adult patients  
- `preg_risk.csv`: FDA pregnancy risk classifications (A–X) per antibiotic  
- `generic_disease_map.csv`: Lookup file linking antibiotics to supported diseases  
- `dosage_demo.ipynb`: Sample Python notebook demonstrating how to filter the dataset

---

## 📊 Dataset Field Descriptions

### `d_dose.csv` and `s_dose.csv`
- `generic`: Name of the antibiotic  
- `disease`: Applicable disease (present only in `d_dose.csv`)  
- `min_age_d/m/y`, `max_age_d/m/y`: Age range in days/months/years  
- `min_weight`, `max_weight`: Weight range in kilograms  
- `min_dd_mg`, `max_dd_mg`: Direct daily dose (mg)  
- `min_dw_mg`, `max_dw_mg`: Dose per kg per day (mg/kg/day)  
- `min_dd_iu`, `max_dd_iu`: Direct daily dose in international units (IU)  
- `min_dw_iu`, `max_dw_iu`: Weight-based dose in IU/kg  
- `limit_mg`, `limit_iu`: Maximum dose caps (mg/IU) for DW regimens  
- `route`: Administration method (PO, IV, IM)

### `r_dose.csv`
- `generic`, `disease`, `route`: Antibiotic, indication, and method  
- `min_crcl`, `max_crcl`: CrCl range (mL/min)  
- `min_weight`, `max_weight`: Weight range if applicable  
- `max_dd_mg`, `max_dw_mg`: Maximum daily dose in mg  
- `max_dd_iu`, `max_dw_iu`: Maximum daily dose in IU  
- `flag`: Renal applicability note (e.g. not recommended)

### `preg_risk.csv`
- `generic`: Antibiotic name  
- `r_category`: FDA Pregnancy Risk Category (A–X)

---

## 🔍 Filtering Examples

```python
# Filter disease-specific regimen 
filter_d_dose(generic="Ampicillin", disease="Gastroenteritis", age=12, route="PO")

# Standard regimen by age and route
filter_s_dose(generic="Ciprofloxacin", age=25, route="PO")

# Renal-adjusted dose filtering
filter_r_dose(generic="Cefepime", crcl=25, route="IV")
```
⚠️ Note: The filtering functions are case and spelling-sensitive for both generic and disease values. Please ensure exact matches with the names listed in `generic_disease_map.csv` for generic specific diseases. Aditionally the `route` must be one of: PO, IM, or IV representing oral, intramascular or intrvascular administration.
---

## 📈 Use Cases

- Integration into CDSS or EHR platforms for real-time prescription audits  
- AI model training for personalized dose optimization  
- Medical education tools for pharmacological training  
- Antimicrobial stewardship analysis  
- Validation tools for anomaly detection in prescription datasets

---

## 🚧 Limitations

- The dataset includes 98 antibiotic generics, with over 4,000 validated dosing scenarios  
- Pediatric renal adjustment data is not included  
- Dose frequency and treatment duration are not encoded  
- WHO AWaRe antibiotic classification is not currently mapped

---

## 📣 Citation

If you use this dataset, please cite:

**Anik, F. W., Zaman, M., Foyez, T., & Mamun, K. A.**  
*DOSAGE: A Dataset for Optimized Safe Antibiotic Guidelines and Estimates*, Nature Scientific Data, 2025. DOI: https://www.doi.org/10.1038/s41597-025-05761-8

---

## 🤝 Contributing

Contributions and feedback are welcome. Please open an issue or submit a pull request to help us expand coverage or improve clarity.

---

## 📬 Visit

www.dosage.iriic.uiu.ac.bd

