"""Reference-build connection with the user's valid AWS CLI session.

Some SDK SSO caches expire while the AWS CLI still has valid role credentials.
Use only the supported CLI Secrets Manager API; never inspect browser/cache
tokens or persist secrets. The ordinary Silver connection controls still apply.
"""
from __future__ import annotations

import json
import os
import subprocess

from engine import silver


def connect(*, read_only=True):
    silver._load_environment()
    secret_id=os.environ.get('SILVER_DB_SECRET_ID')
    previous={key:os.environ.get(key) for key in ('SILVER_DB_URL','SILVER_DB_SECRET_ID')}
    if secret_id:
        profile=os.environ.get('AWS_PROFILE','teamalpha')
        region=os.environ.get('AWS_REGION') or os.environ.get('AWS_DEFAULT_REGION') or 'ap-northeast-2'
        try:
            result=subprocess.run(['aws','secretsmanager','get-secret-value','--secret-id',secret_id,
                                   '--profile',profile,'--region',region,'--output','json'],
                                  capture_output=True,text=True,timeout=45)
        except Exception:
            raise RuntimeError('Authorized AWS secret retrieval unavailable') from None
        if result.returncode:
            raise RuntimeError('AWS CLI secret retrieval failed; refresh the authorized AWS login')
        try:
            payload=json.loads(json.loads(result.stdout)['SecretString'])
            url=payload.get('SILVER_DB_URL')
        except (ValueError,KeyError,TypeError,AttributeError):
            raise RuntimeError('Authorized database secret format is invalid') from None
        if not isinstance(url,str) or not url:
            raise RuntimeError('Authorized database secret has no connection URL')
        # In-memory only, also prevents dotenv from restoring the SDK secret path.
        os.environ['SILVER_DB_URL']=url
        os.environ['SILVER_DB_SECRET_ID']=''
    try:
        return silver.connect(read_only=read_only)
    except Exception:
        raise RuntimeError('Authorized database connection unavailable; check tunnel/login') from None
    finally:
        for key,value in previous.items():
            if value is None:os.environ.pop(key,None)
            else:os.environ[key]=value
