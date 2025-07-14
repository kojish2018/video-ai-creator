#!/usr/bin/env python3
"""
キーワード抽出モジュール

カスタムスクリプトから動画検索に適したキーワードを抽出します。
"""

import re
import jieba
from typing import List, Set
from collections import Counter

class KeywordExtractor:
    """日本語スクリプトからキーワードを抽出するクラス"""
    
    def __init__(self):
        # 除外する一般的な単語（ストップワード）
        self.stop_words = {
            'です', 'ます', 'である', 'ある', 'いる', 'する', 'なる', 'れる', 'られる',
            'この', 'その', 'あの', 'どの', 'これ', 'それ', 'あれ', 'どれ',
            'ここ', 'そこ', 'あそこ', 'どこ', 'こう', 'そう', 'ああ', 'どう',
            'という', 'といった', 'として', 'について', 'による', 'にとって',
            'から', 'まで', 'より', 'など', 'たち', 'とき', 'とも', 'ながら',
            'ため', 'ところ', 'もの', 'こと', 'よう', 'そう', 'はず', 'わけ',
            '私', '僕', '彼', '彼女', '皆', 'みんな', '人', '方', '者',
            'でも', 'けれど', 'しかし', 'だが', 'それでも', 'ただし',
            'そして', 'また', 'さらに', 'つまり', 'なぜなら', 'もちろん',
            'きっと', 'おそらく', 'たぶん', 'まさに', '実際', '確実',
            '今', '昨日', '明日', '今日', '最近', '将来', '未来', '過去',
            '非常', 'とても', 'すごく', 'かなり', 'ちょっと', '少し',
            'すべて', '全て', '多く', '少ない', '大きい', '小さい',
            '新しい', '古い', '良い', '悪い', '高い', '低い', '長い', '短い'
        }
        
        # 動画検索に適したキーワードの優先度
        self.priority_patterns = {
            'technology': ['AI', '人工知能', 'ロボット', 'テクノロジー', 'イノベーション', 'デジタル'],
            'nature': ['自然', '環境', '海', '山', '森', '空', '雲', '花', '動物'],
            'business': ['ビジネス', '企業', '会社', '経済', '市場', '投資', '成長'],
            'lifestyle': ['生活', '健康', '食事', '運動', '家族', '友達', '趣味'],
            'education': ['学習', '教育', '知識', '研究', '科学', '技術', '発見'],
            'entertainment': ['音楽', '映画', 'ゲーム', 'スポーツ', 'アート', 'エンターテイメント']
        }
    
    def extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """
        スクリプトからキーワードを抽出
        
        Args:
            text: 抽出対象のテキスト
            max_keywords: 最大キーワード数
            
        Returns:
            抽出されたキーワードのリスト
        """
        if not text or not text.strip():
            return ['nature', 'landscape']
        
        # テキストをクリーニング
        cleaned_text = self._clean_text(text)
        
        # 単語分割
        words = self._tokenize(cleaned_text)
        
        # キーワード候補を抽出
        candidates = self._extract_candidates(words)
        
        # 重要度でソート
        scored_keywords = self._score_keywords(candidates, cleaned_text)
        
        # 上位キーワードを選択
        keywords = [word for word, score in scored_keywords[:max_keywords]]
        
        # 最低限のキーワードを保証
        if len(keywords) < 2:
            keywords.extend(['nature', 'landscape'])
        
        return keywords[:max_keywords]
    
    def _clean_text(self, text: str) -> str:
        """テキストのクリーニング"""
        # 改行を空白に置換
        text = re.sub(r'\n+', ' ', text)
        # 複数の空白を1つに
        text = re.sub(r'\s+', ' ', text)
        # 句読点前後の空白を調整
        text = re.sub(r'\s*([。！？、，])\s*', r'\1', text)
        return text.strip()
    
    def _tokenize(self, text: str) -> List[str]:
        """テキストを単語に分割"""
        try:
            # jiebaで日本語を分割
            words = jieba.cut(text, cut_all=False)
            return [word.strip() for word in words if len(word.strip()) > 1]
        except Exception:
            # フォールバック: 簡単な分割
            return re.findall(r'[ぁ-んァ-ン一-龥a-zA-Z0-9]+', text)
    
    def _extract_candidates(self, words: List[str]) -> List[str]:
        """キーワード候補を抽出"""
        candidates = []
        
        for word in words:
            # ストップワードをスキップ
            if word in self.stop_words:
                continue
                
            # 長さチェック
            if len(word) < 2 or len(word) > 10:
                continue
                
            # 数字のみをスキップ
            if word.isdigit():
                continue
                
            # ひらがなのみをスキップ（一部例外除く）
            if re.match(r'^[ぁ-ん]+$', word) and word not in ['こころ', 'いのち', 'みらい']:
                continue
                
            candidates.append(word)
        
        return candidates
    
    def _score_keywords(self, candidates: List[str], text: str) -> List[tuple]:
        """キーワードに重要度スコアを付与"""
        word_freq = Counter(candidates)
        scored_keywords = []
        
        for word, freq in word_freq.items():
            score = freq  # 基本スコア（出現回数）
            
            # 優先パターンマッチング
            for category, priority_words in self.priority_patterns.items():
                if any(priority_word in word or word in priority_word for priority_word in priority_words):
                    score += 3
                    break
            
            # 英語・カタカナ用語への加点
            if re.search(r'[A-Za-z]', word) or re.search(r'[ァ-ヶー]', word):
                score += 1
            
            # 長さによる調整
            if 3 <= len(word) <= 6:
                score += 1
            
            scored_keywords.append((word, score))
        
        # スコア順にソート
        scored_keywords.sort(key=lambda x: x[1], reverse=True)
        
        return scored_keywords
    
    def suggest_fallback_keywords(self, theme: str) -> List[str]:
        """テーマに基づいたフォールバックキーワード"""
        theme_lower = theme.lower()
        
        # テーマからカテゴリを推測
        for category, keywords in self.priority_patterns.items():
            for keyword in keywords:
                if keyword.lower() in theme_lower or any(k in theme_lower for k in [keyword.lower()]):
                    return keywords[:3]
        
        # デフォルトフォールバック
        return ['nature', 'landscape', 'abstract']

# 使用例
if __name__ == "__main__":
    extractor = KeywordExtractor()
    
    # テストケース
    test_scripts = [
        "人工知能の未来について考えてみましょう。AIは私たちの生活を大きく変えるでしょう。",
        "美しい自然の中で、動物たちが平和に暮らしています。森や海の環境を大切にしましょう。",
        "ビジネスの世界では、イノベーションが重要です。企業の成長と経済発展を目指しましょう。",
        "これは非常に短いテスト。"
    ]
    
    for i, script in enumerate(test_scripts, 1):
        print(f"\n=== テストケース {i} ===")
        print(f"スクリプト: {script}")
        keywords = extractor.extract_keywords(script)
        print(f"抽出キーワード: {keywords}")