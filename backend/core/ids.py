import uuid

def generate_lead_id(prefix="AVI"):
    return f"{prefix}-{str(uuid.uuid4())[:8].upper()}"
