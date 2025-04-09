from dataclasses import dataclass, field, asdict
from typing import *
from enum import Enum
import json


class ImpactType(Enum):
    POSITIVE = 'positive'
    NEGATIVE = 'negative'
    NEUTRAL = 'neutral'


@dataclass(frozen=True)
class Article:
    article_number: str
    article_url: str
    impact_summary_on_query: str
    impact_type_on_query: ImpactType

    def __str__(self) -> str:
        """Convert Article to a JSON string representation suitable for sorting."""
        article_dict = asdict(self)
        article_dict["impact_type_on_query"] = self.impact_type_on_query.value
        return json.dumps(article_dict)

    @classmethod
    def from_string(cls, string: str) -> 'Article':
        """Create an Article instance from its JSON string representation."""
        article_dict = json.loads(string)
        return cls(
            article_number=article_dict["article_number"],
            article_url=article_dict["article_url"],
            impact_summary_on_query=article_dict["impact_summary_on_query"],
            impact_type_on_query=ImpactType(article_dict["impact_type_on_query"])
        )


@dataclass(frozen=True)
class News:
    news_summary: str
    impact_description_on_query: str
    impact_type_on_query: ImpactType
    most_relevant_url: str

    def _serialize(self) -> str:
        """Serialize the object to a JSON string."""
        news_dict = asdict(self)
        news_dict["impact_type_on_query"] = self.impact_type_on_query.value
        return json.dumps(news_dict)
        

@dataclass(frozen=True)
class GenerateRecentNews:
    query: str
    query_meaning: str
    search_terms: Optional[List[str]] = None
    retrieved_urls: Optional[List[str]] = None
    parsed_urls: Optional[Dict[str, str]] = None
    relevant_articles: Optional[List[List[Article]]] = None
    most_impactful_news: Optional[List[News]] = None

    def _serialize_most_impactful_news(self) -> str:
        return [news._serialize() for news in self.most_impactful_news]

    def _serialize(self) -> str:
        return json.dumps(asdict(self), default = str)