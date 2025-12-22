"""
A+ Studio Text Generation Service.

This service handles multilingual text generation for A+ images,
including slogans, value propositions, and trust endorsements
with various font styles and color schemes.
"""

from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import json


class TextLanguage(Enum):
    """支持的文案语言"""
    ENGLISH = "English (英语)"
    CHINESE = "中文 (Chinese)"
    SPANISH = "Español (西班牙语)"
    FRENCH = "Français (法语)"
    GERMAN = "Deutsch (德语)"
    JAPANESE = "日本語 (日语)"
    KOREAN = "한국어 (韩语)"
    PORTUGUESE = "Português (葡萄牙语)"
    ITALIAN = "Italiano (意大利语)"
    RUSSIAN = "Русский (俄语)"


class FontStyle(Enum):
    """艺术字体样式"""
    MODERN_SANS = "Modern Sans (现代无衬线)"
    CLASSIC_SERIF = "Classic Serif (经典衬线)"
    BOLD_IMPACT = "Bold Impact (粗体冲击)"
    ELEGANT_SCRIPT = "Elegant Script (优雅手写)"
    TECH_FUTURA = "Tech Futura (科技未来)"
    LUXURY_DIDOT = "Luxury Didot (奢华迪多)"
    FRIENDLY_ROUNDED = "Friendly Rounded (友好圆润)"
    CORPORATE_CLEAN = "Corporate Clean (企业简洁)"
    CREATIVE_BRUSH = "Creative Brush (创意笔刷)"
    VINTAGE_RETRO = "Vintage Retro (复古怀旧)"
    MINIMALIST_THIN = "Minimalist Thin (极简细体)"
    HANDWRITTEN_CASUAL = "Handwritten Casual (手写休闲)"
    GOTHIC_BOLD = "Gothic Bold (哥特粗体)"
    ART_DECO = "Art Deco (装饰艺术)"
    CALLIGRAPHY = "Calligraphy (书法体)"
    STENCIL_MILITARY = "Stencil Military (模板军用)"
    NEON_GLOW = "Neon Glow (霓虹发光)"
    EMBOSSED_3D = "3D Embossed (3D浮雕)"


class ColorScheme(Enum):
    """文字颜色方案"""
    CLASSIC_BLACK = "Classic Black (经典黑色)"
    PURE_WHITE = "Pure White (纯白色)"
    ELEGANT_GOLD = "Elegant Gold (优雅金色)"
    ROYAL_BLUE = "Royal Blue (皇家蓝)"
    DEEP_RED = "Deep Red (深红色)"
    FOREST_GREEN = "Forest Green (森林绿)"
    SUNSET_ORANGE = "Sunset Orange (夕阳橙)"
    PURPLE_LUXURY = "Purple Luxury (奢华紫)"
    SILVER_METALLIC = "Silver Metallic (银色金属)"
    ROSE_GOLD = "Rose Gold (玫瑰金)"
    COPPER_BRONZE = "Copper Bronze (铜色青铜)"
    OCEAN_BLUE = "Ocean Blue (海洋蓝)"
    EMERALD_GREEN = "Emerald Green (翡翠绿)"
    RUBY_RED = "Ruby Red (红宝石)"
    SAPPHIRE_BLUE = "Sapphire Blue (蓝宝石)"
    GRADIENT_RAINBOW = "Gradient Rainbow (彩虹渐变)"
    SUNSET_GRADIENT = "Sunset Gradient (夕阳渐变)"
    OCEAN_GRADIENT = "Ocean Gradient (海洋渐变)"


class TextEffect(Enum):
    """文字效果"""
    NONE = "None (无效果)"
    DROP_SHADOW = "Drop Shadow (投影)"
    OUTLINE = "Outline (描边)"
    GLOW = "Glow (发光)"
    EMBOSS = "Emboss (浮雕)"
    ENGRAVE = "Engrave (雕刻)"
    NEON = "Neon (霓虹)"
    EXTRUDE_3D = "3D Extrude (3D挤出)"
    GRADIENT_FILL = "Gradient Fill (渐变填充)"
    PATTERN_FILL = "Pattern Fill (图案填充)"
    METALLIC = "Metallic (金属质感)"
    GLASS = "Glass (玻璃效果)"
    FIRE = "Fire (火焰效果)"
    ICE = "Ice (冰霜效果)"


@dataclass
class TextConfiguration:
    """文字配置"""
    language: TextLanguage
    font_style: FontStyle
    font_weight: str
    color_scheme: ColorScheme
    text_effect: TextEffect
    opacity: float
    position: str
    size: str
    include_background: bool
    background_color: Optional[str] = None


@dataclass
class GeneratedText:
    """生成的文案内容"""
    primary_slogan: str
    secondary_text: str
    trust_endorsement: str
    call_to_action: Optional[str] = None
    language_code: str = "en"
    cultural_context: Optional[str] = None


class APlusTextService:
    """A+ Studio文案生成服务"""
    
    def __init__(self):
        # 语言代码映射
        self.language_codes = {
            TextLanguage.ENGLISH: "en",
            TextLanguage.CHINESE: "zh",
            TextLanguage.SPANISH: "es", 
            TextLanguage.FRENCH: "fr",
            TextLanguage.GERMAN: "de",
            TextLanguage.JAPANESE: "ja",
            TextLanguage.KOREAN: "ko",
            TextLanguage.PORTUGUESE: "pt",
            TextLanguage.ITALIAN: "it",
            TextLanguage.RUSSIAN: "ru"
        }
        
        # 字体样式CSS映射
        self.font_css_mapping = {
            FontStyle.MODERN_SANS: "font-family: 'Helvetica Neue', Arial, sans-serif; font-weight: 300;",
            FontStyle.CLASSIC_SERIF: "font-family: 'Times New Roman', Georgia, serif; font-weight: 400;",
            FontStyle.BOLD_IMPACT: "font-family: Impact, 'Arial Black', sans-serif; font-weight: 900;",
            FontStyle.ELEGANT_SCRIPT: "font-family: 'Brush Script MT', cursive; font-weight: 400;",
            FontStyle.TECH_FUTURA: "font-family: Futura, 'Trebuchet MS', sans-serif; font-weight: 500;",
            FontStyle.LUXURY_DIDOT: "font-family: Didot, 'Times New Roman', serif; font-weight: 300;",
            FontStyle.FRIENDLY_ROUNDED: "font-family: 'Comic Sans MS', cursive; font-weight: 400;",
            FontStyle.CORPORATE_CLEAN: "font-family: 'Segoe UI', Tahoma, sans-serif; font-weight: 400;",
            FontStyle.CREATIVE_BRUSH: "font-family: 'Brush Script MT', fantasy; font-weight: 400;",
            FontStyle.VINTAGE_RETRO: "font-family: 'Courier New', monospace; font-weight: 700;",
            FontStyle.MINIMALIST_THIN: "font-family: 'Helvetica Neue', sans-serif; font-weight: 100;",
            FontStyle.HANDWRITTEN_CASUAL: "font-family: 'Marker Felt', fantasy; font-weight: 400;",
            FontStyle.GOTHIC_BOLD: "font-family: 'Old English Text MT', fantasy; font-weight: 700;",
            FontStyle.ART_DECO: "font-family: 'Broadway', fantasy; font-weight: 400;",
            FontStyle.CALLIGRAPHY: "font-family: 'Edwardian Script ITC', cursive; font-weight: 400;",
            FontStyle.STENCIL_MILITARY: "font-family: 'Stencil', fantasy; font-weight: 700;",
            FontStyle.NEON_GLOW: "font-family: 'Neon', fantasy; font-weight: 400; text-shadow: 0 0 10px currentColor;",
            FontStyle.EMBOSSED_3D: "font-family: Impact, sans-serif; font-weight: 900; text-shadow: 2px 2px 4px rgba(0,0,0,0.5);"
        }
        
        # 颜色方案RGB值映射
        self.color_rgb_mapping = {
            ColorScheme.CLASSIC_BLACK: "#000000",
            ColorScheme.PURE_WHITE: "#FFFFFF", 
            ColorScheme.ELEGANT_GOLD: "#FFD700",
            ColorScheme.ROYAL_BLUE: "#4169E1",
            ColorScheme.DEEP_RED: "#8B0000",
            ColorScheme.FOREST_GREEN: "#228B22",
            ColorScheme.SUNSET_ORANGE: "#FF8C00",
            ColorScheme.PURPLE_LUXURY: "#800080",
            ColorScheme.SILVER_METALLIC: "#C0C0C0",
            ColorScheme.ROSE_GOLD: "#E8B4B8",
            ColorScheme.COPPER_BRONZE: "#CD7F32",
            ColorScheme.OCEAN_BLUE: "#006994",
            ColorScheme.EMERALD_GREEN: "#50C878",
            ColorScheme.RUBY_RED: "#E0115F",
            ColorScheme.SAPPHIRE_BLUE: "#0F52BA",
            ColorScheme.GRADIENT_RAINBOW: "linear-gradient(45deg, #ff0000, #ff8000, #ffff00, #80ff00, #00ff00, #00ff80, #00ffff, #0080ff, #0000ff, #8000ff, #ff00ff, #ff0080)",
            ColorScheme.SUNSET_GRADIENT: "linear-gradient(45deg, #ff6b35, #f7931e, #ffd23f)",
            ColorScheme.OCEAN_GRADIENT: "linear-gradient(45deg, #006994, #0080ff, #00ffff)"
        }
        
        # 多语言文案模板
        self.text_templates = {
            "en": {
                "value_slogans": [
                    "Elevate Your Lifestyle",
                    "Quality That Speaks",
                    "Where Excellence Meets Design",
                    "Crafted for Perfection",
                    "Your Premium Choice",
                    "Redefining Quality Standards",
                    "Experience the Difference",
                    "Built to Last, Made to Impress",
                    "Luxury Within Reach",
                    "Innovation Meets Tradition"
                ],
                "trust_endorsements": [
                    "Trusted by Millions",
                    "Premium Quality Guaranteed",
                    "Industry Leading Excellence",
                    "Customer Favorite Choice",
                    "Professionally Certified",
                    "Award-Winning Design",
                    "Satisfaction Guaranteed",
                    "Top Rated Performance",
                    "Expertly Crafted",
                    "Proven Reliability"
                ],
                "call_to_actions": [
                    "Discover More",
                    "Shop Now",
                    "Experience Quality",
                    "Get Yours Today",
                    "Learn More",
                    "See Details",
                    "Add to Cart",
                    "Buy Now",
                    "Explore Features",
                    "Find Out More"
                ]
            },
            "zh": {
                "value_slogans": [
                    "品质生活，从此开始",
                    "匠心工艺，值得信赖",
                    "追求卓越，成就非凡",
                    "精工细作，品质之选",
                    "让生活更有品质",
                    "专业品质，用心制造",
                    "品味生活，享受品质",
                    "卓越品质，值得拥有",
                    "精致生活，品质之选",
                    "传承工艺，现代品质"
                ],
                "trust_endorsements": [
                    "千万用户信赖之选",
                    "专业品质保证",
                    "行业领先品牌",
                    "用户好评如潮",
                    "权威认证产品",
                    "获奖设计作品",
                    "品质保障承诺",
                    "性能卓越表现",
                    "工匠精神制造",
                    "可靠品质验证"
                ],
                "call_to_actions": [
                    "了解更多",
                    "立即购买",
                    "体验品质",
                    "马上拥有",
                    "查看详情",
                    "探索功能",
                    "加入购物车",
                    "现在购买",
                    "发现更多",
                    "详细了解"
                ]
            },
            "es": {
                "value_slogans": [
                    "Eleva Tu Estilo de Vida",
                    "Calidad Que Habla",
                    "Donde la Excelencia Encuentra el Diseño",
                    "Creado para la Perfección",
                    "Tu Elección Premium",
                    "Redefiniendo Estándares de Calidad",
                    "Experimenta la Diferencia",
                    "Construido para Durar",
                    "Lujo a Tu Alcance",
                    "Innovación y Tradición"
                ],
                "trust_endorsements": [
                    "Confiado por Millones",
                    "Calidad Premium Garantizada",
                    "Excelencia Líder en la Industria",
                    "Elección Favorita del Cliente",
                    "Certificado Profesionalmente",
                    "Diseño Galardonado",
                    "Satisfacción Garantizada",
                    "Rendimiento Mejor Calificado",
                    "Expertamente Elaborado",
                    "Confiabilidad Comprobada"
                ],
                "call_to_actions": [
                    "Descubre Más",
                    "Compra Ahora",
                    "Experimenta Calidad",
                    "Consigue el Tuyo Hoy",
                    "Aprende Más",
                    "Ver Detalles",
                    "Agregar al Carrito",
                    "Comprar Ahora",
                    "Explorar Características",
                    "Descubre Más"
                ]
            },
            "fr": {
                "value_slogans": [
                    "Élevez Votre Style de Vie",
                    "Qualité Qui Parle",
                    "Où l'Excellence Rencontre le Design",
                    "Conçu pour la Perfection",
                    "Votre Choix Premium",
                    "Redéfinir les Standards de Qualité",
                    "Découvrez la Différence",
                    "Construit pour Durer",
                    "Luxe à Votre Portée",
                    "Innovation et Tradition"
                ],
                "trust_endorsements": [
                    "Approuvé par des Millions",
                    "Qualité Premium Garantie",
                    "Excellence Leader de l'Industrie",
                    "Choix Favori des Clients",
                    "Certifié Professionnellement",
                    "Design Primé",
                    "Satisfaction Garantie",
                    "Performance Mieux Notée",
                    "Expertement Conçu",
                    "Fiabilité Prouvée"
                ],
                "call_to_actions": [
                    "Découvrir Plus",
                    "Acheter Maintenant",
                    "Expérience Qualité",
                    "Obtenez le Vôtre Aujourd'hui",
                    "En Savoir Plus",
                    "Voir Détails",
                    "Ajouter au Panier",
                    "Acheter Maintenant",
                    "Explorer Fonctionnalités",
                    "En Savoir Plus"
                ]
            },
            "de": {
                "value_slogans": [
                    "Erhöhen Sie Ihren Lebensstil",
                    "Qualität Die Spricht",
                    "Wo Exzellenz auf Design Trifft",
                    "Für Perfektion Geschaffen",
                    "Ihre Premium-Wahl",
                    "Qualitätsstandards Neu Definieren",
                    "Erleben Sie den Unterschied",
                    "Gebaut um zu Bestehen",
                    "Luxus in Reichweite",
                    "Innovation Trifft Tradition"
                ],
                "trust_endorsements": [
                    "Von Millionen Vertraut",
                    "Premium-Qualität Garantiert",
                    "Branchenführende Exzellenz",
                    "Kundenliebling",
                    "Professionell Zertifiziert",
                    "Preisgekröntes Design",
                    "Zufriedenheit Garantiert",
                    "Top Bewertete Leistung",
                    "Fachmännisch Gefertigt",
                    "Bewährte Zuverlässigkeit"
                ],
                "call_to_actions": [
                    "Mehr Entdecken",
                    "Jetzt Kaufen",
                    "Qualität Erleben",
                    "Holen Sie Sich Ihres Heute",
                    "Mehr Erfahren",
                    "Details Sehen",
                    "In Warenkorb",
                    "Jetzt Kaufen",
                    "Funktionen Erkunden",
                    "Mehr Erfahren"
                ]
            },
            "ja": {
                "value_slogans": [
                    "ライフスタイルを向上させる",
                    "語りかける品質",
                    "卓越性とデザインの出会い",
                    "完璧のために作られた",
                    "あなたのプレミアム選択",
                    "品質基準の再定義",
                    "違いを体験する",
                    "長持ちするように作られた",
                    "手の届く贅沢",
                    "革新と伝統の融合"
                ],
                "trust_endorsements": [
                    "数百万人に信頼される",
                    "プレミアム品質保証",
                    "業界をリードする卓越性",
                    "お客様のお気に入り",
                    "専門的に認定済み",
                    "受賞歴のあるデザイン",
                    "満足保証",
                    "トップ評価の性能",
                    "専門的に作られた",
                    "実証された信頼性"
                ],
                "call_to_actions": [
                    "もっと発見",
                    "今すぐ購入",
                    "品質を体験",
                    "今日手に入れる",
                    "もっと学ぶ",
                    "詳細を見る",
                    "カートに追加",
                    "今すぐ購入",
                    "機能を探索",
                    "もっと知る"
                ]
            },
            "ko": {
                "value_slogans": [
                    "라이프스타일을 높이세요",
                    "말하는 품질",
                    "우수함이 디자인을 만나는 곳",
                    "완벽을 위해 제작됨",
                    "당신의 프리미엄 선택",
                    "품질 기준 재정의",
                    "차이를 경험하세요",
                    "오래 지속되도록 제작됨",
                    "손이 닿는 럭셔리",
                    "혁신과 전통의 만남"
                ],
                "trust_endorsements": [
                    "수백만 명이 신뢰",
                    "프리미엄 품질 보장",
                    "업계 선도적 우수성",
                    "고객 선호 선택",
                    "전문적으로 인증됨",
                    "수상 경력 디자인",
                    "만족 보장",
                    "최고 평점 성능",
                    "전문적으로 제작됨",
                    "입증된 신뢰성"
                ],
                "call_to_actions": [
                    "더 발견하기",
                    "지금 구매",
                    "품질 경험",
                    "오늘 당신 것을 얻으세요",
                    "더 배우기",
                    "세부사항 보기",
                    "장바구니에 추가",
                    "지금 구매",
                    "기능 탐색",
                    "더 알아보기"
                ]
            }
        }
    
    def generate_multilingual_text(
        self,
        product_info: Dict[str, Any],
        text_config: TextConfiguration,
        module_type: str = "identity"
    ) -> GeneratedText:
        """生成多语言文案内容"""
        
        language_code = self.language_codes.get(text_config.language, "en")
        templates = self.text_templates.get(language_code, self.text_templates["en"])
        
        # 根据产品信息选择合适的文案
        primary_slogan = self._select_appropriate_slogan(
            product_info, templates["value_slogans"], language_code
        )
        
        trust_endorsement = self._select_appropriate_endorsement(
            product_info, templates["trust_endorsements"], language_code
        )
        
        call_to_action = self._select_appropriate_cta(
            product_info, templates["call_to_actions"], language_code
        )
        
        # 生成次要文本（根据模块类型）
        secondary_text = self._generate_secondary_text(
            product_info, module_type, language_code
        )
        
        # 获取文化背景信息
        cultural_context = self._get_cultural_context(text_config.language)
        
        return GeneratedText(
            primary_slogan=primary_slogan,
            secondary_text=secondary_text,
            trust_endorsement=trust_endorsement,
            call_to_action=call_to_action,
            language_code=language_code,
            cultural_context=cultural_context
        )
    
    def _select_appropriate_slogan(
        self, 
        product_info: Dict[str, Any], 
        slogans: List[str], 
        language_code: str
    ) -> str:
        """根据产品信息选择合适的标语"""
        
        # 根据产品类别和卖点选择最合适的标语
        product_category = product_info.get("product_category", "").lower()
        selling_points = product_info.get("key_selling_points", [])
        
        # 简单的关键词匹配逻辑
        if any("quality" in point.lower() or "品质" in point for point in selling_points):
            # 优先选择品质相关的标语
            quality_slogans = [s for s in slogans if "quality" in s.lower() or "品质" in s or "qualité" in s.lower()]
            if quality_slogans:
                return quality_slogans[0]
        
        if any("luxury" in point.lower() or "奢华" in point for point in selling_points):
            # 优先选择奢华相关的标语
            luxury_slogans = [s for s in slogans if "luxury" in s.lower() or "奢华" in s or "luxe" in s.lower()]
            if luxury_slogans:
                return luxury_slogans[0]
        
        if "tech" in product_category or "electronic" in product_category or "科技" in product_category:
            # 科技产品优先选择创新相关标语
            tech_slogans = [s for s in slogans if "innovation" in s.lower() or "创新" in s or "tech" in s.lower()]
            if tech_slogans:
                return tech_slogans[0]
        
        # 默认返回第一个标语
        return slogans[0] if slogans else "Premium Quality"
    
    def _select_appropriate_endorsement(
        self, 
        product_info: Dict[str, Any], 
        endorsements: List[str], 
        language_code: str
    ) -> str:
        """根据产品信息选择合适的信任背书"""
        
        competitive_advantages = product_info.get("competitive_advantages", [])
        
        # 根据竞争优势选择背书
        if any("certified" in adv.lower() or "认证" in adv for adv in competitive_advantages):
            cert_endorsements = [e for e in endorsements if "certified" in e.lower() or "认证" in e]
            if cert_endorsements:
                return cert_endorsements[0]
        
        if any("award" in adv.lower() or "获奖" in adv for adv in competitive_advantages):
            award_endorsements = [e for e in endorsements if "award" in e.lower() or "获奖" in e]
            if award_endorsements:
                return award_endorsements[0]
        
        if any("popular" in adv.lower() or "受欢迎" in adv for adv in competitive_advantages):
            popular_endorsements = [e for e in endorsements if "million" in e.lower() or "千万" in e or "favorite" in e.lower()]
            if popular_endorsements:
                return popular_endorsements[0]
        
        # 默认返回第一个背书
        return endorsements[0] if endorsements else "Trusted Quality"
    
    def _select_appropriate_cta(
        self, 
        product_info: Dict[str, Any], 
        ctas: List[str], 
        language_code: str
    ) -> str:
        """根据产品信息选择合适的行动号召"""
        
        # 根据产品类型选择CTA
        product_category = product_info.get("product_category", "").lower()
        
        if "tech" in product_category or "electronic" in product_category:
            tech_ctas = [c for c in ctas if "explore" in c.lower() or "discover" in c.lower() or "探索" in c or "发现" in c]
            if tech_ctas:
                return tech_ctas[0]
        
        # 默认使用购买相关的CTA
        buy_ctas = [c for c in ctas if "buy" in c.lower() or "shop" in c.lower() or "购买" in c]
        if buy_ctas:
            return buy_ctas[0]
        
        return ctas[0] if ctas else "Learn More"
    
    def _generate_secondary_text(
        self, 
        product_info: Dict[str, Any], 
        module_type: str, 
        language_code: str
    ) -> str:
        """生成次要文本内容"""
        
        # 根据模块类型生成不同的次要文本
        if module_type == "identity":
            if language_code == "zh":
                return "让品质成为生活的标准"
            elif language_code == "es":
                return "Haz de la calidad el estándar de vida"
            elif language_code == "fr":
                return "Faire de la qualité le standard de vie"
            elif language_code == "de":
                return "Machen Sie Qualität zum Lebensstandard"
            elif language_code == "ja":
                return "品質を生活の基準にする"
            elif language_code == "ko":
                return "품질을 삶의 기준으로 만드세요"
            else:
                return "Make Quality Your Life Standard"
        
        elif module_type == "sensory":
            if language_code == "zh":
                return "感受每一个细节的精致"
            elif language_code == "es":
                return "Siente la elegancia en cada detalle"
            elif language_code == "fr":
                return "Ressentez l'élégance dans chaque détail"
            elif language_code == "de":
                return "Spüren Sie Eleganz in jedem Detail"
            elif language_code == "ja":
                return "すべての細部にエleganceを感じる"
            elif language_code == "ko":
                return "모든 세부사항에서 우아함을 느끼세요"
            else:
                return "Feel the Elegance in Every Detail"
        
        elif module_type == "extension":
            if language_code == "zh":
                return "多维体验，无限可能"
            elif language_code == "es":
                return "Experiencia multidimensional, posibilidades infinitas"
            elif language_code == "fr":
                return "Expérience multidimensionnelle, possibilités infinies"
            elif language_code == "de":
                return "Mehrdimensionale Erfahrung, unendliche Möglichkeiten"
            elif language_code == "ja":
                return "多次元体験、無限の可能性"
            elif language_code == "ko":
                return "다차원 경험, 무한한 가능성"
            else:
                return "Multidimensional Experience, Infinite Possibilities"
        
        elif module_type == "trust":
            if language_code == "zh":
                return "值得信赖的选择"
            elif language_code == "es":
                return "Una elección en la que puedes confiar"
            elif language_code == "fr":
                return "Un choix en qui vous pouvez avoir confiance"
            elif language_code == "de":
                return "Eine Wahl, der Sie vertrauen können"
            elif language_code == "ja":
                return "信頼できる選択"
            elif language_code == "ko":
                return "신뢰할 수 있는 선택"
            else:
                return "A Choice You Can Trust"
        
        # 默认返回
        return "Premium Experience" if language_code == "en" else "优质体验"
    
    def _get_cultural_context(self, language: TextLanguage) -> str:
        """获取文化背景信息"""
        
        cultural_contexts = {
            TextLanguage.ENGLISH: "Western individualistic culture, emphasis on personal achievement and quality",
            TextLanguage.CHINESE: "重视家庭和谐、品质生活、面子文化",
            TextLanguage.SPANISH: "Cultura familiar, calidez, tradición y modernidad",
            TextLanguage.FRENCH: "Culture de l'élégance, sophistication et art de vivre",
            TextLanguage.GERMAN: "Kultur der Präzision, Qualität und Zuverlässigkeit",
            TextLanguage.JAPANESE: "完璧主義、細部への注意、調和の文化",
            TextLanguage.KOREAN: "혁신과 전통의 조화, 품질과 스타일 중시",
            TextLanguage.PORTUGUESE: "Cultura calorosa, familiar e de hospitalidade",
            TextLanguage.ITALIAN: "Cultura del design, eleganza e stile di vita",
            TextLanguage.RUSSIAN: "Культура качества, традиций и статуса"
        }
        
        return cultural_contexts.get(language, "Universal quality and excellence focus")
    
    def build_text_prompt_enhancement(
        self, 
        generated_text: GeneratedText, 
        text_config: TextConfiguration
    ) -> str:
        """构建文字增强提示词"""
        
        # 获取字体CSS
        font_css = self.font_css_mapping.get(text_config.font_style, "font-family: Arial, sans-serif;")
        
        # 获取颜色值
        color_value = self.color_rgb_mapping.get(text_config.color_scheme, "#000000")
        
        # 构建文字效果描述
        effect_description = self._build_effect_description(text_config.text_effect)
        
        # 构建位置描述
        position_description = self._build_position_description(text_config.position)
        
        # 构建大小描述
        size_description = self._build_size_description(text_config.size)
        
        text_prompt = f"""
        TEXT OVERLAY SPECIFICATIONS:
        
        Primary Text: "{generated_text.primary_slogan}"
        Secondary Text: "{generated_text.secondary_text}"
        Trust Endorsement: "{generated_text.trust_endorsement}"
        
        TYPOGRAPHY SETTINGS:
        - Font Style: {text_config.font_style.value}
        - Font Weight: {text_config.font_weight}
        - Font CSS: {font_css}
        - Text Size: {size_description}
        - Text Color: {color_value} ({text_config.color_scheme.value})
        - Text Opacity: {text_config.opacity}
        
        VISUAL EFFECTS:
        - Text Effect: {text_config.text_effect.value}
        - Effect Description: {effect_description}
        
        POSITIONING:
        - Text Position: {text_config.position}
        - Position Description: {position_description}
        
        BACKGROUND SETTINGS:
        - Include Background: {text_config.include_background}
        """
        
        if text_config.include_background and text_config.background_color:
            text_prompt += f"- Background Color: {text_config.background_color}\n"
        
        text_prompt += f"""
        CULTURAL CONTEXT:
        - Language: {generated_text.language_code}
        - Cultural Notes: {generated_text.cultural_context}
        
        LANGUAGE REQUIREMENTS:
        - ALL TEXT MUST BE IN {generated_text.language_code.upper()} ONLY
        - Do not mix languages in the same image
        - Ensure all text elements follow the specified language
        - No Chinese characters if language is not Chinese
        - No English text if language is not English
        
        INTEGRATION REQUIREMENTS:
        - Text should be clearly readable and well-integrated with the image
        - Maintain visual hierarchy with primary text most prominent
        - Ensure text complements the overall design aesthetic
        - Text should enhance rather than distract from the product
        - Consider cultural appropriateness for the target language
        - STRICT LANGUAGE CONSISTENCY: Use only the specified language throughout
        """
        
        return text_prompt.strip()
    
    def _build_effect_description(self, effect: TextEffect) -> str:
        """构建文字效果描述"""
        
        effect_descriptions = {
            TextEffect.NONE: "Clean text with no additional effects",
            TextEffect.DROP_SHADOW: "Subtle drop shadow behind text for depth",
            TextEffect.OUTLINE: "Contrasting outline around text for visibility",
            TextEffect.GLOW: "Soft glow effect around text for emphasis",
            TextEffect.EMBOSS: "Raised, embossed appearance for premium feel",
            TextEffect.ENGRAVE: "Carved, engraved look for sophistication",
            TextEffect.NEON: "Bright neon glow effect for modern appeal",
            TextEffect.EXTRUDE_3D: "Three-dimensional extruded text effect",
            TextEffect.GRADIENT_FILL: "Gradient color fill within text",
            TextEffect.PATTERN_FILL: "Decorative pattern fill within text",
            TextEffect.METALLIC: "Metallic sheen and reflection effects",
            TextEffect.GLASS: "Transparent glass-like appearance",
            TextEffect.FIRE: "Flame-like effect for dynamic appeal",
            TextEffect.ICE: "Crystalline ice effect for cool aesthetic"
        }
        
        return effect_descriptions.get(effect, "Standard text rendering")
    
    def _build_position_description(self, position: str) -> str:
        """构建位置描述"""
        
        position_descriptions = {
            "Auto (自动)": "Automatically positioned for optimal readability and composition",
            "Top Center (顶部居中)": "Centered at the top of the image",
            "Bottom Center (底部居中)": "Centered at the bottom of the image",
            "Top Left (左上)": "Positioned in the top-left corner",
            "Top Right (右上)": "Positioned in the top-right corner",
            "Bottom Left (左下)": "Positioned in the bottom-left corner",
            "Bottom Right (右下)": "Positioned in the bottom-right corner",
            "Center (居中)": "Centered in the middle of the image",
            "Left Center (左中)": "Centered on the left side",
            "Right Center (右中)": "Centered on the right side"
        }
        
        return position_descriptions.get(position, "Optimally positioned for readability")
    
    def _build_size_description(self, size: str) -> str:
        """构建大小描述"""
        
        size_descriptions = {
            "Small (小)": "Small, subtle text that doesn't dominate",
            "Medium (中)": "Medium-sized text for good visibility",
            "Large (大)": "Large, prominent text for strong impact",
            "Extra Large (超大)": "Extra large text for maximum impact",
            "Auto (自动)": "Automatically sized for optimal readability and composition"
        }
        
        return size_descriptions.get(size, "Appropriately sized for the image")
    
    def get_language_options(self) -> List[str]:
        """获取支持的语言选项"""
        return [lang.value for lang in TextLanguage]
    
    def get_font_style_options(self) -> List[str]:
        """获取字体样式选项"""
        return [style.value for style in FontStyle]
    
    def get_color_scheme_options(self) -> List[str]:
        """获取颜色方案选项"""
        return [color.value for color in ColorScheme]
    
    def get_text_effect_options(self) -> List[str]:
        """获取文字效果选项"""
        return [effect.value for effect in TextEffect]
    
    def validate_text_configuration(self, config: TextConfiguration) -> Dict[str, Any]:
        """验证文字配置"""
        
        validation_result = {
            "is_valid": True,
            "issues": [],
            "suggestions": []
        }
        
        # 检查透明度范围
        if not (0.0 <= config.opacity <= 1.0):
            validation_result["is_valid"] = False
            validation_result["issues"].append("Text opacity must be between 0.0 and 1.0")
        
        # 检查颜色和效果的兼容性
        if config.color_scheme in [ColorScheme.GRADIENT_RAINBOW, ColorScheme.SUNSET_GRADIENT, ColorScheme.OCEAN_GRADIENT]:
            if config.text_effect in [TextEffect.GRADIENT_FILL, TextEffect.PATTERN_FILL]:
                validation_result["suggestions"].append(
                    "Gradient color schemes work best with simple effects like drop shadow or outline"
                )
        
        # 检查字体和效果的兼容性
        if config.font_style == FontStyle.MINIMALIST_THIN and config.text_effect in [TextEffect.EMBOSS, TextEffect.EXTRUDE_3D]:
            validation_result["suggestions"].append(
                "Thin fonts may not work well with heavy 3D effects"
            )
        
        return validation_result
