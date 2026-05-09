@echo off
cd /d C:\Users\Administrator\.openclaw\workspace
echo [%date% %time%] 开始周线数据更新和回顾 >> data\weekly_review.log
python3 scripts\update_mt5_data.py >> data\weekly_review.log 2>&1
echo. >> data\weekly_review.log
python3 scripts\w1_review.py >> data\weekly_review.log 2>&1
echo [%date% %time%] 完成 >> data\weekly_review.log
