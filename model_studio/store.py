"""SQLite transactions serialize commits; inference runs outside the transaction."""
from contextlib import contextmanager
import json
import sqlite3
import uuid
from pathlib import Path
from .domain import Rejected, apply


class Conflict(Rejected):
    pass


class Store:
    def __init__(self, path):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.path = str(path)
        with self.connect() as db:
            db.executescript('''
            CREATE TABLE IF NOT EXISTS state (id INTEGER PRIMARY KEY CHECK(id=1), version INTEGER, revision INTEGER, model TEXT, dialog TEXT);
            INSERT OR IGNORE INTO state VALUES (1,0,0,'{"nodes":[],"relations":[]}','[]');
            CREATE TABLE IF NOT EXISTS history (version INTEGER PRIMARY KEY, model TEXT, summary TEXT, undo_of INTEGER, created TEXT DEFAULT CURRENT_TIMESTAMP);
            INSERT OR IGNORE INTO history(version,model,summary) VALUES (0,'{"nodes":[],"relations":[]}','Tom modell');
            CREATE TABLE IF NOT EXISTS requests (id TEXT PRIMARY KEY, status TEXT);
            CREATE TABLE IF NOT EXISTS sessions (token TEXT PRIMARY KEY, expires INTEGER);
            ''')

    @contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        try:
            with db:
                yield db
        finally:
            db.close()

    def read(self, db=None):
        if db is None:
            with self.connect() as conn:
                return self.read(conn)
        row = db.execute('SELECT * FROM state WHERE id=1').fetchone()
        history = [dict(r) for r in db.execute('SELECT version,summary,created FROM history ORDER BY version DESC LIMIT 50')]
        latest = db.execute('SELECT undo_of FROM history WHERE version=?', (row['version'],)).fetchone()
        return {'version': row['version'], 'revision': row['revision'], 'model': json.loads(row['model']),
                'conversation': json.loads(row['dialog']), 'history': history,
                'canUndo': row['version'] > 0 and latest['undo_of'] is None}

    def reserve(self, request_id, version, revision):
        try:
            uuid.UUID(request_id)
        except (ValueError, TypeError, AttributeError):
            raise Rejected('Ogiltigt anrops-ID.') from None
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            state = self.read(db)
            self.check(state, version, revision)
            try:
                db.execute('INSERT INTO requests VALUES (?,?)', (request_id, 'pending'))
            except sqlite3.IntegrityError:
                raise Conflict('Anropet har redan behandlats. Läs in aktuell modell.') from None
            return state

    @staticmethod
    def check(state, version, revision):
        if type(version) is not int or type(revision) is not int:
            raise Rejected('Version och dialogrevision måste vara heltal.')
        if state['version'] != version or state['revision'] != revision:
            raise Conflict('Modellen eller dialogen har ändrats. Läs in den senaste versionen och försök igen.')

    def fail(self, request_id):
        with self.connect() as db:
            db.execute("UPDATE requests SET status='failed' WHERE id=? AND status='pending'", (request_id,))

    def commit(self, request_id, base, message, proposal=None, undo=False):
        with self.connect() as db:
            db.execute('BEGIN IMMEDIATE')
            current = self.read(db)
            self.check(current, base['version'], base['revision'])
            request = db.execute('SELECT status FROM requests WHERE id=?', (request_id,)).fetchone()
            if not request or request['status'] != 'pending':
                raise Conflict('Anropet har redan avslutats.')
            version, model = current['version'], current['model']
            if undo:
                if not current['canUndo']:
                    raise Rejected('Det finns ingen ny ändring att ångra.')
                model = json.loads(db.execute('SELECT model FROM history WHERE version=?', (version - 1,)).fetchone()['model'])
                summary = 'Ångrade ändring i version ' + str(version)
            else:
                model = apply(model, proposal)
                summary = proposal['message']
            if undo or proposal['kind'] == 'change':
                version += 1
                db.execute('INSERT INTO history(version,model,summary,undo_of) VALUES (?,?,?,?)',
                           (version, json.dumps(model), summary, current['version'] if undo else None))
            assistant = summary
            if not undo and proposal['assumptions']:
                assistant += '\n\nAntaganden:\n' + '\n'.join('• ' + s for s in proposal['assumptions'])
            dialog = (current['conversation'] + [{'role': 'user', 'content': message}, {'role': 'assistant', 'content': assistant}])[-40:]
            db.execute('UPDATE state SET version=?,revision=revision+1,model=?,dialog=? WHERE id=1',
                       (version, json.dumps(model), json.dumps(dialog)))
            db.execute("UPDATE requests SET status='done' WHERE id=?", (request_id,))
            return self.read(db)
