import json
import threading
import pytest
from scripts import capture_dart_employee_history as dart,capture_fmp_research_expense as fmp

class Response:
 def __init__(self,status,payload):self.code=status;self.body=json.dumps(payload).encode()
 def __enter__(self):return self
 def __exit__(self,*args):pass
 def read(self,n):return self.body[:n]

class NoWait:
 def wait(self):pass

def test_dart_quota_stops_without_retry_or_secret_persistence(monkeypatch):
 calls=[]
 def get(*args,**kwargs):calls.append(1);return Response(200,dict(status='020',message='quota'))
 monkeypatch.setattr(dart,'urlopen',get);stop=threading.Event()
 with pytest.raises(dart.QuotaError,match='020'):
  dart.fetch(dict(corp_code='00000001',fiscal_year=2020),'test-private-value',NoWait(),stop)
 assert stop.is_set() and len(calls)==1
 assert dart.fetch(dict(corp_code='00000001',fiscal_year=2020),'test-private-value',NoWait(),stop) is None
 assert len(calls)==1

def test_dart_backoff_and_safe_envelope(monkeypatch):
 responses=iter([Response(429,{}),Response(503,{}),Response(200,dict(status='013',message='none'))]);delays=[]
 monkeypatch.setattr(dart,'urlopen',lambda *a,**k:next(responses));monkeypatch.setattr(dart.time,'sleep',delays.append)
 result=dart.fetch(dict(corp_code='00000001',fiscal_year=2020),'test-private-value',NoWait(),threading.Event())
 assert delays==[1,2]
 assert 'test-private-value' not in json.dumps(result) and 'crtfc_key' not in result['parameters']
 assert result['payload']['status']=='013' and result['observed_at']

def test_fmp_uses_environment_credential_only_in_request_not_evidence(monkeypatch):
 captured=[]
 def get(req,**kwargs):captured.append(req.full_url);return Response(200,[dict(symbol='005930.KS')])
 monkeypatch.setattr(fmp,'urlopen',get)
 result=fmp.fetch('income-statement',dict(symbol='005930.KS'),'test-private-value',NoWait(),threading.Event())
 assert 'apikey=test-private-value' in captured[0]
 assert 'test-private-value' not in json.dumps(result)

def test_provider_reflected_key_is_never_stored(monkeypatch):
 monkeypatch.setattr(fmp,'urlopen',lambda *a,**k:Response(200,[dict(error='test-private-value')]))
 with pytest.raises(ValueError,match='Reflected'):
  fmp.fetch('income-statement',dict(symbol='005930.KS'),'test-private-value',NoWait(),threading.Event())

def test_fmp_only_credential_does_not_depend_on_dart_or_aws(monkeypatch):
 from scripts import probe_reference_new_information as probe
 monkeypatch.setattr(probe,'_load_environment',lambda:None)
 monkeypatch.setenv('FMP_API_KEY','test-private-value');monkeypatch.delenv('DART_API_KEY',raising=False)
 monkeypatch.setattr(probe.subprocess,'run',lambda *a,**k:pytest.fail('Unneeded AWS secret lookup'))
 assert probe.credentials(required=('FMP_API_KEY',))['FMP_API_KEY']=='test-private-value'
