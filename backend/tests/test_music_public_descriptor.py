import copy,json
from pathlib import Path
from fastapi import FastAPI
from fastapi.testclient import TestClient
from backend.catalog_truth import public_book_projection
from backend.api.schemas import PublicBookOut
ROOT=Path(__file__).resolve().parents[2]
def book():return json.loads((ROOT/'backend/data/controlled_publications/the-selfish-giant/public_book.json').read_text())
def test_approved_descriptor_survives_actual_fastapi_schema_without_private_assets():
 b=book();d=b['audiobook_active_release']['active_release_descriptor_sha256'];app=FastAPI()
 @app.get('/book',response_model=PublicBookOut)
 def get():return public_book_projection(b)
 result=TestClient(app).get('/book');assert result.status_code==200
 data=result.json();assert data['audiobook_release_descriptor_sha256']==d
 assert not any(k in data for k in ['audiobook_packages','audiobook_public_package_approval','rights_metadata'])
 assert 'version_id' not in result.text

def test_invalid_package_cannot_advertise_descriptor():
 b=book();b['audiobook_public_package_approval']['acceptance_sha256']='0'*64
 assert public_book_projection(b)['audiobook_release_descriptor_sha256']==''

def test_no_package_or_unreleased_returns_empty_descriptor():
 assert PublicBookOut().audiobook_release_descriptor_sha256==''
 assert public_book_projection({'slug':'unknown','audio_enabled':False})['audiobook_release_descriptor_sha256']==''
