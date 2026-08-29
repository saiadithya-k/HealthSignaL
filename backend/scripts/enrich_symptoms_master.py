import json
import re
import os

CORE_DIR = os.path.join(os.path.dirname(__file__), "..", "app", "core")
SYMPTOMS_PATH = os.path.join(CORE_DIR, "symptoms_master.json")

def generate_aliases_for_symptom(symptom_id: str, name: str, category: str) -> list[str]:
    aliases = set()
    
    # 1. Check if name has parenthesis e.g. "Shortness of breath (Dyspnea)"
    clean_name = name
    paren_match = re.search(r'\((.*?)\)', name)
    if paren_match:
        inside = paren_match.group(1).strip()
        outside = re.sub(r'\(.*?\)', '', name).strip()
        aliases.add(inside.lower())
        aliases.add(outside.lower())
        clean_name = outside
    else:
        aliases.add(name.lower())
    
    # 2. Add specific clinical & common synonyms based on name / ID
    name_lower = name.lower()
    
    # General / Systemic
    if "fever" in name_lower:
        aliases.update(["pyrexia", "high temp", "high temperature", "febrile", "burning up", "hot body"])
    if "chill" in name_lower or "cold" in name_lower:
        aliases.update(["shivering", "rigors", "feeling chilly", "goosebumps"])
    if "sweat" in name_lower:
        aliases.update(["perspiration", "diaphoresis", "night sweats", "profuse sweating"])
    if "fatigue" in name_lower or "weakness" in name_lower or "malaise" in name_lower:
        aliases.update(["tiredness", "exhaustion", "low energy", "worn out", "asthenia", "feeling drained"])
    if "body ache" in name_lower or "pain" in name_lower:
        aliases.update(["myalgia", "aching", "soreness", "generalized ache"])
    if "appetite" in name_lower:
        aliases.update(["anorexia", "not eating", "poor appetite", "loss of hunger"])
    if "weight" in name_lower:
        aliases.update(["unexplained weight change", "slimming", "rapid weight loss"])
    if "dehydration" in name_lower:
        aliases.update(["dry mouth", "extreme thirst", "hypovolemia"])
    if "dizziness" in name_lower or "faint" in name_lower:
        aliases.update(["lightheadedness", "vertigo", "presyncope", "syncope", "wooziness", "passing out"])
    if "lethargy" in name_lower:
        aliases.update(["sluggishness", "drowsiness", "somnolence", "unresponsive"])
        
    # Respiratory
    if "cough" in name_lower:
        aliases.update(["tussis", "hacking", "productive cough", "dry hacking cough", "chest cough"])
    if "sputum" in name_lower or "phlegm" in name_lower or "hemoptysis" in name_lower:
        aliases.update(["coughing mucus", "blood in spit", "phlegm coughing", "rusty sputum"])
    if "shortness of breath" in name_lower or "dyspnea" in name_lower or "difficulty breathing" in name_lower:
        aliases.update(["breathlessness", "SOB", "hard to breathe", "air hunger", "gasping"])
    if "rapid breathing" in name_lower or "tachypnea" in name_lower:
        aliases.update(["hyperventilation", "fast breathing", "panting"])
    if "wheez" in name_lower:
        aliases.update(["whistling breath", "stridor", "asthma attack"])
    if "chest" in name_lower and ("tight" in name_lower or "pain" in name_lower or "discomfort" in name_lower):
        aliases.update(["thoracic pain", "angina", "tight chest", "chest pressure"])
    if "nose" in name_lower or "nasal" in name_lower or "rhinorrhea" in name_lower or "sneez" in name_lower:
        aliases.update(["runny nose", "blocked nose", "rhinitis", "congestion", "coryza", "stuffy nose"])
    if "throat" in name_lower or "voice" in name_lower or "hoarse" in name_lower:
        aliases.update(["pharyngitis", "scratchy throat", "painful swallowing", "dysphonia", "laryngitis"])
    if "oxygen" in name_lower:
        aliases.update(["hypoxia", "low spo2", "desaturation", "oxygen drop"])
        
    # Gastrointestinal
    if "nausea" in name_lower or "vomit" in name_lower:
        aliases.update(["queasiness", "emesis", "throwing up", "puking", "upset stomach", "retching"])
    if "diarrhea" in name_lower or "stool" in name_lower:
        aliases.update(["loose motions", "watery stool", "bowel run", "dysentery", "bloody stool", "melena"])
    if "abdominal" in name_lower or "belly" in name_lower or "stomach" in name_lower:
        aliases.update(["tummy ache", "cramps", "colic", "stomach spasm", "belly pain"])
    if "jaundice" in name_lower or "yellow" in name_lower:
        aliases.update(["icterus", "yellow skin", "yellow eyes", "bilirubinemia"])
    if "constipation" in name_lower:
        aliases.update(["hard stool", "difficulty passing stool", "obstipation"])
    if "heartburn" in name_lower or "reflux" in name_lower:
        aliases.update(["acid reflux", "GERD", "pyrosis", "indigestion", "dyspepsia"])
        
    # Neurological
    if "headache" in name_lower:
        aliases.update(["cephalalgia", "head pain", "migraine", "throbbing head", "cranial pain"])
    if "neck" in name_lower and "stiff" in name_lower:
        aliases.update(["nuchal rigidity", "meningismus", "neck stiffness"])
    if "confusion" in name_lower or "disorient" in name_lower:
        aliases.update(["delirium", "altered mental state", "fogginess", "brain fog", "dazed"])
    if "seizure" in name_lower or "convulsion" in name_lower:
        aliases.update(["fits", "epileptic attack", "shaking fit", "tremor"])
    if "paralysis" in name_lower or "numbness" in name_lower or "tingling" in name_lower:
        aliases.update(["paresthesia", "loss of sensation", "pins and needles", "weak limbs", "stroke sign"])
    if "loss of taste" in name_lower or "loss of smell" in name_lower:
        aliases.update(["anosmia", "ageusia", "smell loss", "taste loss"])
        
    # Musculoskeletal
    if "joint" in name_lower or "arthr" in name_lower:
        aliases.update(["arthralgia", "joint swelling", "joint stiffness", "rheumatism"])
    if "muscle" in name_lower or "myalgia" in name_lower:
        aliases.update(["muscle spasms", "muscle pain", "muscle cramps"])
    if "back" in name_lower:
        aliases.update(["lumbago", "backache", "lower back pain", "spine pain"])
        
    # Dermatological / Rash
    if "rash" in name_lower or "skin" in name_lower:
        aliases.update(["exanthem", "eruption", "maculopapular", "hives", "urticaria", "pruritus", "itching"])
    if "lesion" in name_lower or "ulcer" in name_lower or "blister" in name_lower:
        aliases.update(["vesicles", "bullae", "skin sores", "petechiae", "purpura"])
        
    # Eye / Ocular
    if "eye" in name_lower or "vision" in name_lower:
        aliases.update(["conjunctivitis", "pink eye", "blurred vision", "photophobia", "watery eyes", "eye redness"])
        
    # Ear / Nose / Throat
    if "ear" in name_lower or "hearing" in name_lower:
        aliases.update(["otalgia", "earache", "tinnitus", "ringing ear", "ear discharge"])
        
    # Urinary / Renal
    if "urin" in name_lower:
        aliases.update(["dysuria", "hematuria", "frequent urination", "burning micturition", "dark urine"])
        
    # Bleeding / Hematological
    if "bleed" in name_lower or "hemorrhage" in name_lower or "bruis" in name_lower:
        aliases.update(["epistaxis", "nosebleed", "bruising", "ecchymosis", "bleeding gums"])

    # Mental / Behavioral
    if "anxiety" in name_lower or "panic" in name_lower or "depress" in name_lower:
        aliases.update(["nervousness", "restlessness", "agitation", "low mood"])
        
    # Ensure standard simplified fallback alias from name itself
    words = [w.strip() for w in re.split(r'[\s\(\)/,-]+', name) if len(w.strip()) > 2]
    if words:
        aliases.add(" ".join(words).lower())
        
    # Remove empty or trivial strings
    cleaned = sorted(list(set(a.strip() for a in aliases if a and len(a.strip()) > 1)))
    return cleaned

def main():
    with open(SYMPTOMS_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
        
    symptoms = data.get("symptoms", [])
    print(f"Loaded {len(symptoms)} symptoms from {SYMPTOMS_PATH}")
    
    updated_symptoms = []
    for s in symptoms:
        sid = s.get("symptom_id")
        name = s.get("name")
        cat = s.get("category", "General / Systemic")
        sevs = s.get("severities", ["mild", "moderate", "severe"])
        syns = s.get("associated_syndromes", ["unspecified_community_cluster"])
        
        aliases = generate_aliases_for_symptom(sid, name, cat)
        
        updated_symptoms.append({
            "symptom_id": sid,
            "name": name,
            "category": cat,
            "severities": sevs,
            "associated_syndromes": syns,
            "aliases": aliases
        })
        
    data["symptoms"] = updated_symptoms
    data["total_symptoms"] = len(updated_symptoms)
    
    with open(SYMPTOMS_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
        
    print(f"Successfully enriched all {len(updated_symptoms)} symptoms with aliases!")

if __name__ == "__main__":
    main()
