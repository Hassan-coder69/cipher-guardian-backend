# api/classifier.py

def classify_text(text):
    lower_case_text = text.lower()
    
    # Keywords that indicate a threat
    red_flags = ["threat", "hack", "kill", "attack", "expose you", "doxx you", "fuck", "shit", "bitch", "asshole", "cunt", "kutte", "kameene", "chutiya", "madarchod"]
    
    # Keywords that indicate potential spam or phishing
    yellow_flags = ["prize", "winner", "congratulations", "claim", "lottery", "free money", "investment", "verify your account", "urgent", "click this link", "inaam jeeta"]

    if any(keyword in lower_case_text for keyword in red_flags):
        return 'red'
    if any(keyword in lower_case_text for keyword in yellow_flags):
        return 'yellow'
        
    return 'green'