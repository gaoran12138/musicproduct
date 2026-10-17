"""解压 cudatoolkit + cudnn 到 tools\\cuda\\bin（GPU 运行时 DLL 部署）"""
import os, shutil, tarfile, zipfile

os.makedirs(r"D:\musicProduct\tools\cuda\bin", exist_ok=True)
dest = r"D:\musicProduct\tools\cuda\bin"

# 1) cudatoolkit .tar.bz2 -> Library/bin/*.dll
tk = r"D:\musicProduct\tools\cuda\cudatoolkit.tar.bz2"
extract_dir = r"D:\musicProduct\tools\cuda\tk_extract"
os.makedirs(extract_dir, exist_ok=True)
print("extracting cudatoolkit...")
with tarfile.open(tk, "r:bz2") as t:
    t.extractall(extract_dir)
count = 0
for root, _, files in os.walk(extract_dir):
    for f in files:
        if f.lower().endswith(".dll"):
            shutil.copy2(os.path.join(root, f), os.path.join(dest, f))
            count += 1
print(f"cudatoolkit dlls copied: {count}")
shutil.rmtree(extract_dir, ignore_errors=True)

# 2) cudnn zip -> cuda/bin/*.dll
cz = r"D:\musicProduct\tools\cuda\cudnn.zip"
extract_dir2 = r"D:\musicProduct\tools\cuda\cudnn_extract"
os.makedirs(extract_dir2, exist_ok=True)
print("extracting cudnn...")
with zipfile.ZipFile(cz) as z:
    z.extractall(extract_dir2)
count = 0
for root, _, files in os.walk(extract_dir2):
    for f in files:
        if f.lower().endswith(".dll"):
            shutil.copy2(os.path.join(root, f), os.path.join(dest, f))
            count += 1
print(f"cudnn dlls copied: {count}")
shutil.rmtree(extract_dir2, ignore_errors=True)

print("ALL DLLS:")
for f in sorted(os.listdir(dest)):
    print("  ", f, os.path.getsize(os.path.join(dest, f)) // (1024 * 1024), "MB")
