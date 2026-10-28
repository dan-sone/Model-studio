"""Domain constraints independent of provider, storage and diagram layout."""
from copy import deepcopy
from jsonschema import Draft202012Validator


def obj(properties):
    return {"type": "object", "properties": properties, "required": list(properties), "additionalProperties": False}


def string(limit=1000):
    return {"type": "string", "minLength": 1, "maxLength": limit}


ID = {"type": "string", "pattern": "^[a-zA-Z0-9_-]{1,64}$"}
NODE = obj({"id": ID, "type": {"enum": ["activity", "decision", "role", "system"]}, "label": string(160), "knowledge": {"enum": ["proposed", "verified"]}, "source": {"type": "string", "maxLength": 1000}})
RELATION = obj({"id": ID, "type": {"enum": ["flow", "responsible_for", "supports"]}, "source": ID, "target": ID, "label": {"type": "string", "maxLength": 160}, "knowledge": {"enum": ["proposed", "verified"]}})
OPERATION = obj({"action": {"enum": ["create", "update", "delete"]}, "target": {"enum": ["node", "relation"]}, "id": ID, "node": {"anyOf": [NODE, {"type": "null"}]}, "relation": {"anyOf": [RELATION, {"type": "null"}]}})
PROPOSAL = obj({"kind": {"enum": ["change", "clarification", "answer"]}, "message": string(4000), "assumptions": {"type": "array", "items": string(500), "maxItems": 20}, "operations": {"type": "array", "items": OPERATION, "maxItems": 200}})
MODEL = obj({"nodes": {"type": "array", "items": NODE, "maxItems": 100}, "relations": {"type": "array", "items": RELATION, "maxItems": 200}})


class Rejected(ValueError):
    pass


def validate(schema, data):
    if not Draft202012Validator(schema).is_valid(data):
        raise Rejected("Svaret följer inte modellens schema. Ingen ändring sparades.")


def validate_model(model):
    validate(MODEL, model)
    nodes = {n['id']: n for n in model['nodes']}
    ids = [x['id'] for x in model['nodes'] + model['relations']]
    if len(set(ids)) != len(ids):
        raise Rejected("Objekt-ID måste vara unika.")
    for n in model['nodes']:
        if n['knowledge'] == 'verified' and not n['source'].strip():
            raise Rejected("Verifierat innehåll kräver en källa.")
    for r in model['relations']:
        a, b = nodes.get(r['source']), nodes.get(r['target'])
        if not a or not b or a == b:
            raise Rejected("Relationen saknar giltiga ändpunkter.")
        process = {'activity', 'decision'}
        valid = ((r['type'] == 'flow' and a['type'] in process and b['type'] in process)
                 or (r['type'] == 'responsible_for' and a['type'] == 'role' and b['type'] in process)
                 or (r['type'] == 'supports' and a['type'] == 'system' and b['type'] in process))
        if not valid:
            raise Rejected("Relationstypen passar inte objektens typer.")
    return model


def apply(model, proposal):
    validate(PROPOSAL, proposal)
    if proposal['kind'] != 'change':
        if proposal['operations']:
            raise Rejected("Svar och följdfrågor får inte ändra modellen.")
        return deepcopy(model)
    if not proposal['operations']:
        raise Rejected("Ändringsförslaget saknar ändringar.")
    result = deepcopy(model)
    touched = set()
    for op in proposal['operations']:
        if op['id'] in touched:
            raise Rejected("Ett objekt får bara ändras en gång per förslag.")
        touched.add(op['id'])
        collection = result['nodes' if op['target'] == 'node' else 'relations']
        old = next((x for x in collection if x['id'] == op['id']), None)
        value = op[op['target']]
        other = op['relation' if op['target'] == 'node' else 'node']
        if other is not None:
            raise Rejected("Operationen innehåller fel objekttyp.")
        if op['action'] == 'create' and any(x['id'] == op['id'] for x in result['nodes'] + result['relations']):
            raise Rejected("Objektet finns redan.")
        if op['action'] != 'create' and old is None:
            raise Rejected("Objektet som ska ändras finns inte.")
        if op['action'] == 'delete':
            if value is not None:
                raise Rejected("Borttagning får inte innehålla ett nytt värde.")
            collection.remove(old)
        else:
            if value is None or value['id'] != op['id']:
                raise Rejected("Befintliga identiteter måste bevaras.")
            if value['knowledge'] != 'proposed' and value != old:
                raise Rejected("AI-genererat innehåll måste anges som förslag.")
            if old is not None:
                if op['target'] == 'node' and value['type'] != old['type']:
                    raise Rejected("Objektets typ får inte bytas under samma ID.")
                collection.remove(old)
            collection.append(value)
    return validate_model(result)
