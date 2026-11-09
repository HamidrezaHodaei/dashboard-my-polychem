"""
Shared pagination parsing for Phase 4 list endpoints -- API.md §4: "List
endpoints support `?page=`, `?per_page=`, ... default `per_page` capped
(e.g. 100) to prevent unbounded queries."
"""
DEFAULT_PAGE = 1
DEFAULT_PER_PAGE = 20
MAX_PER_PAGE = 100


def parse_pagination(args) -> tuple[int, int]:
    """
    `args` is a Flask `request.args`-like mapping. Never raises -- an
    invalid/missing value silently falls back to the default rather than
    producing a 400, since pagination parameters are a convenience, not
    part of the request's validated body contract (API.md's Pydantic
    validation is reserved for request bodies).
    """
    try:
        page = int(args.get("page", DEFAULT_PAGE))
    except (TypeError, ValueError):
        page = DEFAULT_PAGE
    if page < 1:
        page = DEFAULT_PAGE

    try:
        per_page = int(args.get("per_page", DEFAULT_PER_PAGE))
    except (TypeError, ValueError):
        per_page = DEFAULT_PER_PAGE
    if per_page < 1:
        per_page = DEFAULT_PER_PAGE
    per_page = min(per_page, MAX_PER_PAGE)

    return page, per_page


def paginate_query(query, page: int, per_page: int):
    """
    Applies offset/limit to a SQLAlchemy query and returns
    (items, total). `query.count()` runs before `limit`/`offset` are
    applied -- a second query, but the simplest correct approach and
    consistent across every Phase 4 list endpoint.
    """
    total = query.count()
    items = query.offset((page - 1) * per_page).limit(per_page).all()
    return items, total
