import json
import os
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
import uuid
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from model_studio.domain import Rejected, apply
from model_studio.provider import infer, Unconfigured
from model_studio.server import make_handler
from model_studio.store import Store, Conflict


def node(id, type='activity', label=None):
    return dict(id=id, type=type, label=label or id, knowledge='proposed', source='')


def relation(id, a, b, type='flow', label=''):
    return dict(id=id, type=type, source=a, target=b, label=label, knowledge='proposed')


def op(value, action='create', target='node'):
    return dict(id=value['id'], action=action, target=target, node=value if target=='node' else None, relation=value if target=='relation' else None)


def proposal(ops=None, kind='change', message='Uppdaterade modellen'):
    return dict(kind=kind, message=message, assumptions=['Systemstödet behöver verifieras.'], operations=ops or [])


def initial():
    return proposal([op(node('pick',label='Plock')),op(node('pack',label='Pack')),op(node('erp','system','Dynamics 365 F&O')),op(relation('f','pick','pack'),target='relation'),op(relation('s','erp','pick','supports'),target='relation')])


class Chain(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.store=Store(self.tmp.name+'/test.sqlite3')

    def tearDown(self):
        self.tmp.cleanup()

    def commit(self,p,message='Skapa en process'):
        state=self.store.read();id=str(uuid.uuid4())
        base=self.store.reserve(id,state['version'],state['revision'])
        return self.store.commit(id,base,message,p)

    def test_creation_revision_identity_and_branch(self):
        first=self.commit(initial())
        p=proposal([op(node('credit','decision','Godkänd kredit?')),op(node('stop',label='Avslag')),op(relation('yes','credit','pick',label='Ja'),target='relation'),op(relation('no','credit','stop',label='Nej'),target='relation')])
        second=self.commit(p,'Lägg till kreditkontroll med en separat väg vid avslag')
        third=self.commit(proposal([op(node('wms','system','Externt WMS')),op(relation('s','wms','pick','supports'),'update','relation'),op(relation('s2','wms','pack','supports'),target='relation')]),'Låt externt WMS hantera plock och pack')
        self.assertEqual(first['model']['nodes'][0],next(n for n in third['model']['nodes'] if n['id']=='pick'))
        self.assertEqual(next(r for r in third['model']['relations'] if r['id']=='s')['source'],'wms')
        self.assertEqual(len([r for r in second['model']['relations'] if r['source']=='credit']),2)
        self.assertEqual(third['version'],3)

    def test_clarification_and_answer_do_not_mutate(self):
        before=self.commit(initial())
        for kind in ['clarification','answer']:
            after=self.commit(proposal(kind=kind,message='Vilken kontroll menar du?'))
            self.assertEqual(before['model'],after['model'])
            self.assertEqual(before['version'],after['version'])
            self.assertGreater(after['revision'],before['revision'])
        with self.assertRaises(Rejected):
            self.commit(proposal([op(node('oops'))],kind='clarification'))

    def test_invalid_operations_are_atomic(self):
        before=self.commit(initial())
        invalids=[proposal([op(node('new')),op(relation('bad','new','missing'),target='relation')]),
                  proposal([op(node('pick'))]),proposal([op(node('missing'),'update')]),
                  proposal([op(node('pick','role'),'update')]),
                  proposal([op(dict(node('verified'),knowledge='verified',source='AI assertion'))]),
                  proposal([op(relation('bad','erp','pack','flow'),target='relation')])]
        for p in invalids:
            with self.subTest(p=p), self.assertRaises(Rejected): self.commit(p)
            self.assertEqual(before,self.store.read())

    def test_schema_duplicate_id_and_dangling_delete(self):
        model=self.commit(initial())['model']
        p=initial();p['operations'][0]['node']['type']='unknown'
        with self.assertRaises(Rejected): apply(model,p)
        with self.assertRaises(Rejected): apply(model,proposal([op(node('x')),op(node('x'))]))
        deletion=dict(id='pick',action='delete',target='node',node=None,relation=None)
        with self.assertRaises(Rejected): apply(model,proposal([deletion]))

    def test_stale_response_duplicate_and_undo(self):
        base=self.store.read();slow=str(uuid.uuid4());self.store.reserve(slow,0,0)
        changed=self.commit(initial())
        with self.assertRaises(Conflict): self.store.commit(slow,base,'Sena svaret',initial())
        id=str(uuid.uuid4());saved=self.store.reserve(id,changed['version'],changed['revision'])
        with self.assertRaises(Conflict): self.store.reserve(id,changed['version'],changed['revision'])
        undone=self.store.commit(id,saved,'Ångra',undo=True)
        self.assertEqual(undone['model'],base['model']);self.assertEqual(undone['version'],2)
        self.assertFalse(undone['canUndo'])
        with self.assertRaises(Conflict): self.store.commit(id,saved,'Ångra',undo=True)
        with self.assertRaises(Conflict): self.store.reserve(str(uuid.uuid4()),changed['version'],changed['revision'])

    def test_late_answer_cannot_overwrite_dialog(self):
        slow=str(uuid.uuid4());base=self.store.reserve(slow,0,0)
        self.commit(proposal(kind='clarification'))
        with self.assertRaises(Conflict):self.store.commit(slow,base,'old',proposal(kind='answer'))

    def test_persistence(self):
        before=self.commit(initial())
        self.assertEqual(Store(self.store.path).read(),before)

    def test_missing_configuration(self):
        with patch.dict(os.environ,{},clear=True), self.assertRaises(Unconfigured):infer({},[],'Skapa process')

    def test_real_adapter_contract_with_test_transport(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps({'status':'completed','output':[{'type':'message','content':[{'type':'output_text','text':json.dumps(initial())}]}]}).encode()
        with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'configured-model'}), patch('urllib.request.urlopen',return_value=Response()) as transport:
            result=infer({'nodes':[],'relations':[]},[{'role':'user','content':'Tidigare dialog'}],'Skapa en fri process')
            request=transport.call_args.args[0];payload=json.loads(request.data)
            self.assertTrue(payload['text']['format']['strict']);self.assertFalse(payload['store'])
            self.assertIn('Tidigare dialog',payload['input']);self.assertEqual(result,initial())

    def test_concurrent_commits_have_one_winner(self):
        base=self.store.read()
        ids=[str(uuid.uuid4()),str(uuid.uuid4())]
        for id in ids:self.store.reserve(id,0,0)
        barrier=threading.Barrier(2);outcomes=[]
        def run(id):
            barrier.wait()
            try:self.store.commit(id,base,'Create',initial());outcomes.append('ok')
            except Conflict:outcomes.append('conflict')
        threads=[threading.Thread(target=run,args=(id,)) for id in ids]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertCountEqual(outcomes,['ok','conflict'])
        self.assertEqual(self.store.read()['version'],1)

    def test_provider_refusal_and_incomplete_are_rejected(self):
        class Response:
            def __enter__(self):return self
            def __exit__(self,*args):pass
            def read(self,size):return json.dumps(self.value).encode()
        for value in [{'status':'incomplete','output':[]},{'status':'completed','output':[{'type':'message','content':[{'type':'refusal','refusal':'no'}]}]}]:
            response=Response();response.value=value
            with patch.dict(os.environ,{'OPENAI_API_KEY':'test-only','OPENAI_MODEL':'configured-model'}),patch('urllib.request.urlopen',return_value=response),self.assertRaises(Rejected):
                infer({'nodes':[],'relations':[]},[],'Skapa process')

    def test_http_pipeline_and_login(self):
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.store,'a-long-test-password'))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        url='http://127.0.0.1:'+str(server.server_port)
        def post(path,data,cookie=None,origin=None):
            headers={'Content-Type':'application/json'}
            if cookie:headers['Cookie']=cookie
            if origin:headers['Origin']=origin
            return urllib.request.urlopen(urllib.request.Request(url+path,data=json.dumps(data).encode(),headers=headers))
        try:
            with self.assertRaises(urllib.error.HTTPError) as denied:urllib.request.urlopen(url+'/api/state')
            self.assertEqual(denied.exception.code,401)
            with post('/api/login',{'password':'a-long-test-password'}) as response:cookie=response.headers['Set-Cookie'].split(';')[0]
            message='Skapa en Order to Cash-process med Microsoft Dynamics 365 F&O som system.'
            data=dict(message=message,version=0,revision=0,requestId=str(uuid.uuid4()))
            with patch('model_studio.provider.infer',return_value=initial()) as ai:
                with post('/api/chat',data,cookie) as response:state=json.load(response)
                self.assertEqual(state['version'],1)
                ai.assert_called_once_with({'nodes':[],'relations':[]},[],message)
            with self.assertRaises(urllib.error.HTTPError) as denied:post('/api/chat',data,cookie,origin='https://evil.example')
            self.assertEqual(denied.exception.code,403)
            with patch.dict(os.environ,{'OPENAI_API_KEY':'','OPENAI_MODEL':''}):
                data.update(version=1,revision=1,requestId=str(uuid.uuid4()))
                with self.assertRaises(urllib.error.HTTPError) as missing:post('/api/chat',data,cookie)
                self.assertEqual(missing.exception.code,422)
                self.assertEqual(self.store.read()['model'],state['model'])
        finally:server.shutdown();server.server_close();thread.join()


if __name__=='__main__':unittest.main()
