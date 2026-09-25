"""Browse and series metadata for the app (provider-neutral facade)."""

from API import catalog_api, catalog_module
import frzw_exceptions


def _paginate(scraper, page: int):
    paginator = catalog_module().paginator
    try:
        scraper = paginator(scraper, page)
    except frzw_exceptions.NotFoundPagination:
        raise
    pagination = scraper.get_pagination()
    if page < 1 or page > pagination["page_total"]:
        raise frzw_exceptions.NotFoundPagination(
            f"Page {page} out of range (1-{pagination['page_total']})"
        )
    return scraper.get_titles(), pagination


class Catalog:
    def __init__(self) -> None:
        self._api = catalog_api()

    def home_sections(self):
        rows = getattr(self._api, "home_section_rows", None)
        if callable(rows):
            return rows()
        popular = self._api.popular().get_titles()
        new = self._api.new().get_titles()
        return {"trending": popular, "popular": popular, "new": new}

    def lister(self, kind: str, page: int):
        if kind == "popular":
            scraper = self._api.popular()
        elif kind == "new":
            scraper = self._api.new()
        else:
            raise ValueError(f"Unknown list kind: {kind}")
        return _paginate(scraper, page)

    def search(self, query: str, page: int):
        search_res = self._api.search_anime(search_query=query)
        if not search_res or not search_res.get_result_count():
            return None
        paginator = catalog_module().paginator
        try:
            search_res = paginator(search_res, page)
        except frzw_exceptions.NotFoundPagination:
            return None
        pagination = search_res.get_pagination()
        if page < 1 or page > pagination["page_total"]:
            return None
        return search_res.get_titles(), pagination

    def series_for_flair(self, title_flair: str):
        return self._api.search_flair(title_flair)

    def prewatch(self, title_flair: str):
        series = self.series_for_flair(title_flair)
        if not series:
            return None
        details = series.get_anime_details()
        details["episode_keys"] = [
            list(each.keys())[0] for each in details.get("episode_meta")
        ]
        print(title_flair)
        details["episode_raw"] = [
            list(each.keys())[0].replace(".", "-") for each in details.get("episode_meta")
        ]
        return details

    def sitemap_entries(self, kind: str):
        if kind == "new":
            new = self._api.new().get_titles()
            return {
                "title": [result["raw_flair"] for result in new],
                "episode": [result["episode"] for result in new],
            }
        if kind == "popular":
            pop = self._api.popular().get_titles()
            return {"title": [result["raw_flair"] for result in pop]}
        raise ValueError(f"Unknown sitemap kind: {kind}")


catalog = Catalog()
