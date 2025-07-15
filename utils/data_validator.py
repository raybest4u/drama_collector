# utils/data_validator.py
import re
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)


class ValidationLevel(Enum):
    """验证级别"""
    STRICT = "strict"
    MODERATE = "moderate"
    LENIENT = "lenient"


class DataType(Enum):
    """数据类型"""
    DRAMA = "drama"
    CHARACTER = "character"
    PLOT_POINT = "plot_point"


@dataclass
class ValidationResult:
    """验证结果"""
    is_valid: bool
    errors: List[str]
    warnings: List[str]
    cleaned_data: Dict[str, Any]
    quality_score: float
    validation_metadata: Dict[str, Any]


class DataValidator:
    """数据验证和清洗器"""
    
    def __init__(self, validation_level: ValidationLevel = ValidationLevel.MODERATE):
        self.validation_level = validation_level
        self.validation_rules = self._load_validation_rules()
        self.cleaning_rules = self._load_cleaning_rules()
        
        logger.info(f"数据验证器初始化完成，验证级别: {validation_level.value}")
    
    def validate_drama_data(self, data: Dict[str, Any]) -> ValidationResult:
        """验证剧目数据"""
        errors = []
        warnings = []
        cleaned_data = data.copy()
        
        # 基础字段验证
        required_fields = ['id', 'title']
        for field in required_fields:
            if not data.get(field):
                errors.append(f"缺少必需字段: {field}")
        
        # 字段类型验证
        field_validators = {
            'title': self._validate_title,
            'year': self._validate_year,
            'rating': self._validate_rating,
            'summary': self._validate_summary,
            'genres': self._validate_genres,
            'casts': self._validate_casts,
            'directors': self._validate_directors,
            'episodes_count': self._validate_episodes_count
        }
        
        for field, validator in field_validators.items():
            if field in data:
                try:
                    is_valid, cleaned_value, field_errors, field_warnings = validator(data[field])
                    
                    if not is_valid and self.validation_level == ValidationLevel.STRICT:
                        errors.extend(field_errors)
                    elif field_errors:
                        warnings.extend(field_errors)
                    
                    warnings.extend(field_warnings)
                    
                    if cleaned_value is not None:
                        cleaned_data[field] = cleaned_value
                        
                except Exception as e:
                    error_msg = f"验证字段 {field} 时出错: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
        
        # 数据一致性验证
        consistency_errors, consistency_warnings = self._validate_data_consistency(cleaned_data)
        errors.extend(consistency_errors)
        warnings.extend(consistency_warnings)
        
        # 计算质量得分
        quality_score = self._calculate_quality_score(cleaned_data, errors, warnings)
        
        # 添加验证元数据
        validation_metadata = {
            'validation_timestamp': datetime.utcnow().isoformat(),
            'validation_level': self.validation_level.value,
            'data_completeness': self._calculate_completeness(cleaned_data),
            'field_count': len(cleaned_data),
            'has_required_fields': all(field in cleaned_data for field in required_fields)
        }
        
        is_valid = len(errors) == 0
        
        return ValidationResult(
            is_valid=is_valid,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data,
            quality_score=quality_score,
            validation_metadata=validation_metadata
        )
    
    def validate_character_data(self, data: Dict[str, Any]) -> ValidationResult:
        """验证角色数据"""
        errors = []
        warnings = []
        cleaned_data = data.copy()
        
        # 角色数据特定验证
        if not data.get('name'):
            errors.append("角色缺少姓名")
        
        # 清洗角色名
        if 'name' in data:
            cleaned_name = self._clean_character_name(data['name'])
            if cleaned_name:
                cleaned_data['name'] = cleaned_name
            else:
                warnings.append("角色名称清洗后为空")
        
        # 验证角色属性
        if 'traits' in data:
            cleaned_traits = self._clean_character_traits(data['traits'])
            cleaned_data['traits'] = cleaned_traits
        
        quality_score = self._calculate_quality_score(cleaned_data, errors, warnings)
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings,
            cleaned_data=cleaned_data,
            quality_score=quality_score,
            validation_metadata={'type': 'character'}
        )
    
    def batch_validate(self, data_list: List[Dict[str, Any]], 
                      data_type: DataType) -> List[ValidationResult]:
        """批量验证数据"""
        results = []
        
        validator_map = {
            DataType.DRAMA: self.validate_drama_data,
            DataType.CHARACTER: self.validate_character_data,
        }
        
        validator = validator_map.get(data_type)
        if not validator:
            raise ValueError(f"不支持的数据类型: {data_type}")
        
        for i, data in enumerate(data_list):
            try:
                result = validator(data)
                results.append(result)
            except Exception as e:
                logger.error(f"批量验证第 {i} 项失败: {str(e)}")
                results.append(ValidationResult(
                    is_valid=False,
                    errors=[f"验证失败: {str(e)}"],
                    warnings=[],
                    cleaned_data=data,
                    quality_score=0.0,
                    validation_metadata={'batch_index': i}
                ))
        
        return results
    
    def filter_high_quality_data(self, validation_results: List[ValidationResult],
                                min_quality_score: float = 7.0) -> List[Dict[str, Any]]:
        """过滤高质量数据"""
        high_quality_data = []
        
        for result in validation_results:
            if result.is_valid and result.quality_score >= min_quality_score:
                high_quality_data.append(result.cleaned_data)
        
        logger.info(f"从 {len(validation_results)} 条记录中筛选出 {len(high_quality_data)} 条高质量数据")
        
        return high_quality_data
    
    def _validate_title(self, title: Any) -> Tuple[bool, Optional[str], List[str], List[str]]:
        """验证标题"""
        errors = []
        warnings = []
        
        if not isinstance(title, str):
            return False, None, ["标题必须是字符串"], []
        
        # 清洗标题
        cleaned_title = self._clean_title(title)
        
        if not cleaned_title:
            return False, None, ["标题不能为空"], []
        
        if len(cleaned_title) < 2:
            errors.append("标题过短")
        elif len(cleaned_title) > 100:
            warnings.append("标题过长")
        
        # 检查特殊字符
        if re.search(r'[<>\"\'&]', cleaned_title):
            warnings.append("标题包含特殊字符")
        
        return len(errors) == 0, cleaned_title, errors, warnings
    
    def _validate_year(self, year: Any) -> Tuple[bool, Optional[int], List[str], List[str]]:
        """验证年份"""
        errors = []
        warnings = []
        
        if year is None:
            return True, None, [], ["年份为空"]
        
        try:
            year_int = int(year)
        except (ValueError, TypeError):
            return False, None, ["年份格式无效"], []
        
        current_year = datetime.now().year
        
        if year_int < 1900:
            errors.append("年份过早")
        elif year_int > current_year + 2:
            errors.append("年份无效（未来年份）")
        elif year_int > current_year:
            warnings.append("年份为未来年份")
        
        return len(errors) == 0, year_int, errors, warnings
    
    def _validate_rating(self, rating: Any) -> Tuple[bool, Optional[float], List[str], List[str]]:
        """验证评分"""
        errors = []
        warnings = []
        
        if rating is None:
            return True, None, [], ["评分为空"]
        
        try:
            rating_float = float(rating)
        except (ValueError, TypeError):
            return False, None, ["评分格式无效"], []
        
        if rating_float < 0:
            errors.append("评分不能为负数")
        elif rating_float > 10:
            errors.append("评分不能超过10")
        elif rating_float == 0:
            warnings.append("评分为0，可能是默认值")
        
        return len(errors) == 0, rating_float, errors, warnings
    
    def _validate_summary(self, summary: Any) -> Tuple[bool, Optional[str], List[str], List[str]]:
        """验证剧情简介"""
        errors = []
        warnings = []
        
        if not isinstance(summary, str):
            return False, None, ["剧情简介必须是字符串"], []
        
        cleaned_summary = self._clean_text(summary)
        
        if not cleaned_summary:
            return True, "", [], ["剧情简介为空"]
        
        if len(cleaned_summary) < 10:
            warnings.append("剧情简介过短")
        elif len(cleaned_summary) > 2000:
            warnings.append("剧情简介过长")
        
        return True, cleaned_summary, errors, warnings
    
    def _validate_genres(self, genres: Any) -> Tuple[bool, Optional[List[str]], List[str], List[str]]:
        """验证类型"""
        errors = []
        warnings = []
        
        if not isinstance(genres, list):
            return False, None, ["类型必须是列表"], []
        
        cleaned_genres = []
        for genre in genres:
            if isinstance(genre, str) and genre.strip():
                cleaned_genres.append(genre.strip())
        
        if not cleaned_genres:
            warnings.append("类型列表为空")
        elif len(cleaned_genres) > 10:
            warnings.append("类型过多")
        
        return True, cleaned_genres, errors, warnings
    
    def _validate_casts(self, casts: Any) -> Tuple[bool, Optional[List[str]], List[str], List[str]]:
        """验证演员列表"""
        return self._validate_string_list(casts, "演员", max_count=20)
    
    def _validate_directors(self, directors: Any) -> Tuple[bool, Optional[List[str]], List[str], List[str]]:
        """验证导演列表"""
        return self._validate_string_list(directors, "导演", max_count=5)
    
    def _validate_episodes_count(self, episodes: Any) -> Tuple[bool, Optional[int], List[str], List[str]]:
        """验证集数"""
        errors = []
        warnings = []
        
        if episodes is None:
            return True, None, [], ["集数为空"]
        
        try:
            episodes_int = int(episodes)
        except (ValueError, TypeError):
            return False, None, ["集数格式无效"], []
        
        if episodes_int < 1:
            errors.append("集数必须大于0")
        elif episodes_int > 200:
            warnings.append("集数过多")
        
        return len(errors) == 0, episodes_int, errors, warnings
    
    def _validate_string_list(self, data: Any, field_name: str, 
                             max_count: int = 10) -> Tuple[bool, Optional[List[str]], List[str], List[str]]:
        """验证字符串列表"""
        errors = []
        warnings = []
        
        if not isinstance(data, list):
            return False, None, [f"{field_name}必须是列表"], []
        
        cleaned_list = []
        for item in data:
            if isinstance(item, str) and item.strip():
                cleaned_item = item.strip()
                if len(cleaned_item) <= 50:  # 限制单个项目长度
                    cleaned_list.append(cleaned_item)
                else:
                    warnings.append(f"{field_name}项目过长: {cleaned_item[:20]}...")
        
        if len(cleaned_list) > max_count:
            warnings.append(f"{field_name}数量过多")
        
        return True, cleaned_list, errors, warnings
    
    def _validate_data_consistency(self, data: Dict[str, Any]) -> Tuple[List[str], List[str]]:
        """验证数据一致性"""
        errors = []
        warnings = []
        
        # 年份与评分一致性
        year = data.get('year')
        rating = data.get('rating')
        
        if year and rating and isinstance(year, int) and isinstance(rating, (int, float)):
            if year < 2000 and rating > 9:
                warnings.append("早期作品评分异常高")
        
        # 标题与类型一致性
        title = data.get('title', '').lower()
        genres = data.get('genres', [])
        
        if '爱情' in title or '恋爱' in title:
            if not any('爱情' in genre or 'romance' in genre.lower() for genre in genres):
                warnings.append("标题暗示爱情主题但类型中未体现")
        
        return errors, warnings
    
    def _calculate_quality_score(self, data: Dict[str, Any], 
                                errors: List[str], warnings: List[str]) -> float:
        """计算质量得分 (0-10)"""
        base_score = 10.0
        
        # 错误扣分
        base_score -= len(errors) * 2
        
        # 警告扣分
        base_score -= len(warnings) * 0.5
        
        # 完整性加分
        completeness = self._calculate_completeness(data)
        base_score *= (0.5 + 0.5 * completeness)
        
        return max(0.0, min(10.0, base_score))
    
    def _calculate_completeness(self, data: Dict[str, Any]) -> float:
        """计算数据完整性 (0-1)"""
        important_fields = [
            'title', 'year', 'summary', 'genres', 'rating',
            'casts', 'directors', 'episodes_count'
        ]
        
        filled_fields = sum(1 for field in important_fields 
                           if data.get(field) and str(data[field]).strip())
        
        return filled_fields / len(important_fields)
    
    def _clean_title(self, title: str) -> str:
        """清洗标题"""
        if not title:
            return ""
        
        # 移除前后空白
        title = title.strip()
        
        # 移除多余空格
        title = re.sub(r'\s+', ' ', title)
        
        # 移除特殊标记
        title = re.sub(r'【.*?】', '', title)  # 移除【】内容
        title = re.sub(r'\[.*?\]', '', title)  # 移除[]内容
        
        return title.strip()
    
    def _clean_text(self, text: str) -> str:
        """清洗文本"""
        if not text:
            return ""
        
        # 移除多余空白
        text = re.sub(r'\s+', ' ', text)
        
        # 移除HTML标签
        text = re.sub(r'<[^>]+>', '', text)
        
        # 移除特殊字符
        text = re.sub(r'[^\u4e00-\u9fff\w\s，。！？；：""''（）【】]', '', text)
        
        return text.strip()
    
    def _clean_character_name(self, name: str) -> str:
        """清洗角色名"""
        if not name:
            return ""
        
        # 移除称谓
        titles_to_remove = ['先生', '女士', '小姐', '老师', '医生', '总裁']
        for title in titles_to_remove:
            name = name.replace(title, '')
        
        return name.strip()
    
    def _clean_character_traits(self, traits: List[str]) -> List[str]:
        """清洗角色特征"""
        if not traits:
            return []
        
        cleaned_traits = []
        for trait in traits:
            if isinstance(trait, str):
                cleaned_trait = trait.strip()
                if cleaned_trait and len(cleaned_trait) <= 20:
                    cleaned_traits.append(cleaned_trait)
        
        # 去重
        return list(set(cleaned_traits))
    
    def _load_validation_rules(self) -> Dict:
        """加载验证规则"""
        return {
            'strict': {
                'required_fields': ['id', 'title', 'year', 'summary'],
                'allow_empty_optional': False
            },
            'moderate': {
                'required_fields': ['id', 'title'],
                'allow_empty_optional': True
            },
            'lenient': {
                'required_fields': ['id'],
                'allow_empty_optional': True
            }
        }
    
    def _load_cleaning_rules(self) -> Dict:
        """加载清洗规则"""
        return {
            'text_cleaning': {
                'remove_html': True,
                'normalize_whitespace': True,
                'remove_special_chars': True
            },
            'list_cleaning': {
                'remove_empty': True,
                'deduplicate': True,
                'trim_whitespace': True
            }
        }