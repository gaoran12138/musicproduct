@echo off
chcp 65001 >nul
cd /d D:\musicProduct
"D:\musicProduct\tools\ffmpeg\bin\ffmpeg.exe" -y -loop 1 -framerate 30 -i "D:\musicProduct\素材\图片\cover_wf.jpg" -i "D:\musicProduct\分轨\WeirdFishes_伴奏\WeirdFishes_伴奏.wav" -filter_complex "[0:v]scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,boxblur=25:5[bgb];[0:v]scale=700:700[fg];[bgb][fg]overlay=(W-w)/2:(H-h)/2,subtitles='D\:/musicProduct/Radiohead_WeirdFishes_歌词.ass'[v]" -map "[v]" -map 1:a -c:v h264_nvenc -preset p7 -cq 22 -c:a aac -b:a 320k -pix_fmt yuv420p -t 318.2 "D:\musicProduct\分轨\WeirdFishes_伴奏_歌词视频.mp4"
echo EXIT=%ERRORLEVEL%
