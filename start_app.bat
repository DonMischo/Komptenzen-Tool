@echo off
cd /d C:\SchulTools\KompetenzenTool
docker compose up -d
start http://localhost:8501
