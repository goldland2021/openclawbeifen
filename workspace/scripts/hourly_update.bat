@chcp 65001 >nul
@echo off
cd /d C:\Users\Administrator\.openclaw\workspace
python3 -X utf8 scripts\update_mt5_data.py 1>>data\mt5_update.log 2>&1
