"""News data model."""

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


class BaseNewsModel(BaseModel):
    """Base model for news-related data."""

    model_config = ConfigDict(
        alias_generator=to_camel,
        extra="ignore",
    )


class Provider(BaseNewsModel):
    """Provider information for a news article."""

    display_name: str | None = Field(None, description="Name of the news provider")
    url: str | None = Field(None, description="URL of the news provider")


class Resolution(BaseNewsModel):
    """Resolution information for a news article thumbnail."""

    url: str | None = Field(None, description="URL of the image")
    width: int | None = Field(None, description="Width of the image")
    height: int | None = Field(None, description="Height of the image")
    tag: str | None = Field(None, description="Resolution (e.g., original or other resolution)")


class Thumbnail(BaseNewsModel):
    """Thumbnail information for a news article."""

    original_url: str | None = Field(None, description="Original URL of the image")
    original_width: int | None = Field(None, description="Original width of the image")
    original_height: int | None = Field(None, description="Original height of the image")
    caption: str | None = Field(None, description="Caption for the image")
    resolutions: list[Resolution] | None = Field(
        None,
        description="List of different image resolutions",
    )


class CanonicalUrl(BaseNewsModel):
    """Canonical URL information for a news article."""

    url: str | None = Field(None, description="Canonical URL of the article")
    site: str | None = Field(None, description="Yahoo subdomain")
    region: str | None = Field(None, description="Region of the article")
    lang: str | None = Field(None, description="Language of the article")


class ClickThroughUrl(BaseNewsModel):
    """Click-through URL information for a news article."""

    url: str | None = Field(None, description="Click-through URL of the article")
    site: str | None = Field(None, description="Yahoo subdomain")
    region: str | None = Field(None, description="Region of the article")
    lang: str | None = Field(None, description="Language of the article")


class Metadata(BaseNewsModel):
    """Metadata for a news article."""

    editors_pick: bool | None = Field(
        None,
        description="Indicates if the article is an editor's pick",
    )


class PremiumFinance(BaseNewsModel):
    """Premium finance information for a news article."""

    is_premium_news: bool | None = Field(None, description="Indicates if the article is premium")
    is_premium_free_news: bool | None = Field(
        None,
        description="Indicates if the article is free premium news",
    )


class Finance(BaseNewsModel):
    """Finance information for a news article."""

    premium_finance: PremiumFinance | None = Field(None, description="Premium finance details")


class StorylineItem(BaseNewsModel):
    """A single item in a storyline."""

    content: "Content"


class Storyline(BaseNewsModel):
    """Storyline information for a news article."""

    storyline_items: list["StorylineItem"] | None


class Content(BaseNewsModel):
    """Content of a news article."""

    id: str | None
    content_type: str | None = Field(None, description="Type of content (e.g., STORY)")
    title: str | None = Field(None, description="Title of the article")
    description: str | None = Field(None, description="Description of the article")
    summary: str | None = Field(None, description="Summary of the article")
    pub_date: str | None = Field(None, description="Publication date of the article")
    display_time: str | None = Field(None, description="Display time of the article")
    is_hosted: bool | None = Field(None, description="Indicates if the article is hosted")
    bypass_modal: bool | None = Field(None, description="Indicates if modal can be bypassed")
    preview_url: str | None = Field(None, description="Preview URL of the article")
    thumbnail: Thumbnail | None = None
    provider: Provider | None = None
    canonical_url: CanonicalUrl | None = None
    click_through_url: ClickThroughUrl | None = None
    metadata: Metadata | None = None
    finance: Finance | None = None
    storyline: Storyline | None = Field(None, description="Storyline of the article")


class NewsRow(BaseNewsModel):
    """A single news article row."""

    id: str
    content: Content


class NewsResponse(BaseNewsModel):
    """News response for a symbol."""

    news: list[NewsRow]
