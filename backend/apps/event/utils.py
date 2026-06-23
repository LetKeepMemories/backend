from slugify import slugify


def build_slug_base(*, event_type_slug: str, first_name: str, last_name: str) -> str:
    """Mirrors the two URL examples in the spec: a birthday slug embeds the
    word "birthday" (domain.com/wishes/sunday-birthday) while a memorial (or
    any other type) just uses the full name (domain.com/memorial/john-doe).
    """
    if event_type_slug == "birthday":
        return f"{first_name}-birthday"
    if last_name:
        return f"{first_name}-{last_name}"
    return first_name


def generate_unique_slug(model_cls, base_text: str) -> str:
    base_slug = slugify(base_text) or "occasion"
    slug = base_slug
    counter = 1
    while model_cls.objects.filter(slug=slug).exists():
        counter += 1
        slug = f"{base_slug}-{counter}"
    return slug
