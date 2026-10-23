#!/usr/bin/env python3
import chardet
import os

csv_path = 'newstock/data/namecode.csv'
with open(csv_path, 'rb') as f:
    result = chardet.detect(f.read())
    print(f'文件编码: {result["encoding"]}')
    print(f'置信度: {result["confidence"]}')
