import json
import os
from typing import Dict, Any, List

# TODO: adjust to your project paths
from app.db import SessionLocal  # type: ignore
from app.models.capability_schema import Capability  # type: ignore

# Get path relative to this script
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


def load_json(path: str) -> Dict[str, Any]:
 full_path = os.path.join(SCRIPT_DIR, path)
 with open(full_path, "r") as f:
  return json.load(f)


def main() -> None:
 data = load_json("capabilities.json")
 caps: List[Dict[str, Any]] = data["capabilities"]

 session = SessionLocal()
 try:
  # Pass 1: upsert rows (without prerequisite_ids)
  name_to_row: Dict[str, Capability] = {}

  for c in caps:
   existing = session.query(Capability).filter(Capability.name == c["name"]).one_or_none()

   if existing is None:
    # Handle soft_gate_requirements - store as JSON string
    sgr = c.get("soft_gate_requirements")
    sgr_json = json.dumps(sgr) if sgr else None
    
    # Handle music21_detection rules
    detection_rule = c.get("music21_detection")
    detection_json = json.dumps(detection_rule) if detection_rule else None
    
    row = Capability(
     name=c["name"],
     display_name=c["display_name"],
     domain=c["domain"],
     subdomain=c.get("subdomain"),
     requirement_type=c.get("requirement_type", "required"),
     prerequisite_ids="[]",  # fill pass 2
     bit_index=c["bit_index"],
     explanation=None,
     difficulty_tier=c.get("difficulty_tier", 1),
     introduction_material_id=None,
     mastery_type=c.get("mastery_type", "single"),
     mastery_count=c.get("mastery_count", 1),
     evidence_required_count=c.get("evidence_required_count", 1),
     evidence_distinct_materials=c.get("evidence_distinct_materials", False),
     evidence_acceptance_threshold=c.get("evidence_acceptance_threshold", 4),
     evidence_qualifier_json=json.dumps(c.get("evidence_qualifier_json", {})),
     difficulty_weight=c.get("difficulty_weight", 1.0),
     soft_gate_requirements=sgr_json,
     music21_detection_json=detection_json,
    )
    session.add(row)
    session.flush()
    name_to_row[c["name"]] = row
   else:
    # update core fields but do not overwrite any future content fields you may add by hand
    existing.display_name = c["display_name"]
    existing.domain = c["domain"]
    existing.subdomain = c.get("subdomain")
    existing.requirement_type = c.get("requirement_type", existing.requirement_type)
    existing.bit_index = c["bit_index"]
    existing.difficulty_tier = c.get("difficulty_tier", existing.difficulty_tier)
    existing.mastery_type = c.get("mastery_type", existing.mastery_type)
    existing.mastery_count = c.get("mastery_count", existing.mastery_count)
    existing.evidence_required_count = c.get("evidence_required_count", existing.evidence_required_count)
    existing.evidence_distinct_materials = c.get("evidence_distinct_materials", existing.evidence_distinct_materials)
    existing.evidence_acceptance_threshold = c.get("evidence_acceptance_threshold", existing.evidence_acceptance_threshold)
    existing.evidence_qualifier_json = json.dumps(c.get("evidence_qualifier_json", {}))
    existing.difficulty_weight = c.get("difficulty_weight", existing.difficulty_weight)
    # Update soft_gate_requirements if provided
    sgr = c.get("soft_gate_requirements")
    if sgr is not None:
     existing.soft_gate_requirements = json.dumps(sgr)
    # Update music21_detection if provided
    detection_rule = c.get("music21_detection")
    if detection_rule is not None:
     existing.music21_detection_json = json.dumps(detection_rule)
    name_to_row[c["name"]] = existing

  session.commit()

  # Refresh name map from DB to ensure we have all rows
  rows = session.query(Capability).all()
  name_to_id = {r.name: r.id for r in rows}

  # Pass 2: resolve prerequisite_names -> prerequisite_ids
  updated = 0
  for c in caps:
   prereq_names = c.get("prerequisite_names", [])
   prereq_ids = []
   for pn in prereq_names:
    if pn not in name_to_id:
     raise RuntimeError(f"Missing prerequisite capability name: {pn} (required by {c['name']})")
    prereq_ids.append(name_to_id[pn])

   row = session.query(Capability).filter(Capability.name == c["name"]).one()
   new_json = json.dumps(prereq_ids)
   if row.prerequisite_ids != new_json:
    row.prerequisite_ids = new_json
    updated += 1

  session.commit()
  print(f"Seed complete. Updated prerequisites for {updated} capabilities.")

 finally:
  session.close()


if __name__ == "__main__":
 main()