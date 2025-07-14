#!/usr/bin/env python3
"""
カスタムスクリプトのキーワード抽出機能をテストするスクリプト
"""

from keyword_extractor import KeywordExtractor
import json

def test_keyword_extraction():
    """カスタムスクリプトキーワード抽出のテスト"""
    
    extractor = KeywordExtractor()
    
    test_cases = [
        {
            "name": "AI技術テーマ",
            "script": "人工知能技術の発展により、私たちの生活は劇的に変化しています。AIロボットが医療現場で活躍し、自動運転車が道路を走る未来が現実になりつつあります。",
            "expected_keywords": ["人工知能", "AI", "ロボット", "テクノロジー", "医療"]
        },
        {
            "name": "自然・環境テーマ",
            "script": "美しい自然環境を守ることは、私たちの責任です。森林の動物たちと共存し、海の生態系を保護しましょう。地球温暖化を防ぐため、今すぐ行動を起こしましょう。",
            "expected_keywords": ["自然", "環境", "動物", "森林", "海"]
        },
        {
            "name": "ビジネステーマ",
            "script": "現代のビジネス環境では、イノベーションが成功の鍵となります。企業は市場の変化に対応し、新しい価値を創造する必要があります。",
            "expected_keywords": ["ビジネス", "イノベーション", "企業", "市場", "価値"]
        },
        {
            "name": "短いスクリプト",
            "script": "これは短いテストです。",
            "expected_keywords": ["テスト", "nature", "landscape"]
        }
    ]
    
    print("=== カスタムスクリプト キーワード抽出テスト ===\n")
    
    for i, test_case in enumerate(test_cases, 1):
        print(f"テストケース {i}: {test_case['name']}")
        print(f"スクリプト: {test_case['script']}")
        
        # キーワード抽出
        extracted_keywords = extractor.extract_keywords(test_case['script'])
        
        print(f"抽出されたキーワード: {extracted_keywords}")
        
        # 期待されるキーワードとの比較
        expected = test_case['expected_keywords']
        overlap = set(extracted_keywords) & set(expected)
        
        print(f"期待されるキーワード: {expected}")
        print(f"マッチしたキーワード: {list(overlap)}")
        print(f"マッチ率: {len(overlap)}/{len(expected)} ({len(overlap)/len(expected)*100:.1f}%)")
        print("-" * 50)
    
    print("\n=== 動画検索への適用テスト ===")
    
    # 実際の動画検索を想定した処理
    sample_script = """
    最新のAI技術が医療分野に革命をもたらしています。
    ロボット手術や画像診断の精度向上により、
    患者の治療成績が大幅に改善されています。
    """
    
    keywords = extractor.extract_keywords(sample_script)
    print(f"サンプルスクリプト: {sample_script.strip()}")
    print(f"動画検索用キーワード: {keywords}")
    
    # 従来の方法（テーマのみ）との比較
    theme = "AI医療技術"
    print(f"\n従来の方法（テーマのみ）: [{theme}]")
    print(f"新しい方法（キーワード抽出）: {keywords}")
    print(f"キーワード数の増加: {len([theme])} → {len(keywords)}")

if __name__ == "__main__":
    test_keyword_extraction()