from typing import Union
from fastapi import FastAPI, Depends

def test_app_exists():
    """App import bo'ladimi?"""
    from main import app
    assert app is not None
    print("✅ App exists and CI works!")