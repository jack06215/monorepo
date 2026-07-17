from json import dumps

from regexlib.country.jp import JapanRegex
from regexlib.engine import RegexEngine

engine = RegexEngine(countries=[JapanRegex()])

text = """
【顧客情報】
氏名: 山田 太郎
連絡先: 090-1234-5678（内線 123）
予備番号: 03-1234-5678
郵便番号: 123-4567
個人番号: 123456789012

【システムログ】
Login at 9:30am on 21st of Jan, 2024
Server IPs: 192.168.1.10, fe80::1ff:fe23:4567:890a
Backup hash (SHA256): e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855

【決済】
カード番号: 4111-1111-1111-1111
金額: $1,234.56

【通信】
Email: test.user+notify@example.co.jp
Repo: https://github.com/example-org/private-repo.git

【ノイズ（マッチしてはいけない）】
電話っぽい: 090-1234
郵便っぽい: 123-45678
ランダム数字: 1234567890123
"""
print(dumps(engine.detect(text), indent=2, ensure_ascii=False))
