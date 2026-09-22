from essentials.tools import remove_ep_flair, remove_cdn_host, append_query
from essentials.cache_session import APIBackendSession
from urllib.parse import urlparse, urlunparse
from constants import Constants
from bs4 import BeautifulSoup
import frzw_exceptions
import requests.exceptions
import itertools

session = APIBackendSession

class EpisodeScraper:
    """Scrape for available episodes"""
    def __init__(self, url: str):
        self.url = url
        parsed_url = urlparse(Constants.gogocdn)
        self.ajax_url = urlunparse(parsed_url._replace(netloc=f"ajax.{parsed_url.netloc}"))
        response = session.get(url)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            code = e.response.status_code
            raise frzw_exceptions.NotFoundEpisode(f"[Scraping Error] Error scraping, site returned http code: {code}", parent=response) #Placeholder error, might use custom one, but for now use Attribute error for scraping issues
        self.parser = BeautifulSoup(response.content, 'html.parser')
    
    def _parse_url(self):
        return urlparse(self.url)
    
    def get_anime_id(self):
        return self.parser.find('input', class_='movie_id')['value']

    def get_episodes(self):
        anime_id = self.get_anime_id()
        ep_start = 0 # assume always starts at 0
        ep_end = int(self.parser.find('a',class_='active')['ep_end'])
        response = session.get(f"{self.ajax_url}/ajax/load-list-episode?ep_start={ep_start}&ep_end={ep_end}&id={anime_id}")
        if response.status_code != 200:
            return []
        episode_soup = BeautifulSoup(response.content, 'html.parser')
        episodes = episode_soup.find_all('li')
        episodic_flairs = []
        for parsed_ep in reversed(episodes):
            episode_id  = parsed_ep.find('div', class_ = 'name').text.strip().replace('EP ', '')
            dataform = { 
                episode_id: {
                    'episode-flair':  parsed_ep.find('a')['href'].strip(),
                }
            }
            episodic_flairs.append(dataform)
        return episodic_flairs

    def get_episode_count(self):
        "Returns maximum episodes"
        return len(self.get_episodes())
    
    def get_episode_link(self, value: str, adjustment = None):
        "Returns a link of a specific episode, returns None if invalid"
        try:
            target = []
            for i, each in enumerate(self.get_episodes()):
                if value in each:
                    if adjustment:
                        put_in = i+adjustment
                        if put_in < 0:
                            target = []
                        elif put_in > self.get_episode_count():
                            target = []
                        else:
                            target = self.get_episodes()[i+adjustment]
                    else:
                        target = each
        except IndexError:
            target = []
        return target

    def get_episode_id(self, value):
        "Deprecated as of 0.3.1"
        url_parsed = self._parse_url()
        title_flair = url_parsed.path.split("/")[-1]
        return f"{title_flair}-episode-{value}"

    def get_anime_details(self):
        summary = self.get_summary()
        genre = self.get_genre()
        date_released = self.get_date_released()
        status = self.get_status()
        title = self.get_title()
        cover = self.get_cover()
        episode_count = self.get_episode_count()
        episode_meta = self.get_episodes()
        final_data = {}
        final_data['description'] = summary
        final_data['genre'] = genre
        final_data['date_released'] = date_released
        final_data['status'] = status
        final_data['title'] = title
        final_data['cover'] = cover
        final_data['episodes'] = episode_count
        final_data['episode_meta'] = episode_meta
        return final_data
        
    
    def get_id(self):
        url_parsed = self._parse_url()
        return url_parsed.path.split("/")[-1]
    
    def _get_info_page(self):
        return self.parser.find('div', class_='anime_info_body_bg')
        
    def _get_grouped(self, target):
        groups =  self.parser.find_all('p', class_='type')
        for group in groups:
            if group.find('span').text.strip() == target:
                return group

    def get_summary(self):
        return self.parser.find('div', class_='description').text.strip()
    
    def get_genre(self):
        genre_div = self._get_grouped('Genre:')
        genres =  genre_div.find_all('a')
        genre_found = tuple(genre.text.strip() for genre in genres)
        return genre_found
    
    def get_date_released(self):
        date_released = self._get_grouped('Released:')
        return date_released.text.strip().replace('Released: ','')

    def get_status(self):
        status = self._get_grouped('Status:')
        return status.find('a').text.strip()
    
    def get_title(self):
        return self._get_info_page().find('h1').text.strip()
    
    def get_cover(self):
        return remove_cdn_host(self._get_info_page().find('img')['src'])

class AnimeInfo:
    """Fetch Anime info"""
    def __init__(self, url: str):
        ...


#Notice: The exceptions with Attribute errors are only placeholders
class Goscraper:
    """GoGoAnime lister"""
    def __init__(self, url: str):
        self.url = url
        self.session = session
        #Scrape Data from WEB
        response = self.session.get(url)
        try:
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            code = e.response.status_code
            if code == 404:
                raise frzw_exceptions.NotFoundPagination(f"[Not found] Error scraping, site returned http code: {code}", parent=response) #Placeholder error, might use custom one, but for now use Attribute error for scraping issues
            else:
                raise frzw_exceptions.ScrapingError(f"[Scraping Error] Error scraping, site returned http code: {code}", parent=response) #Placeholder error, might use custom one, but for now use Attribute error for scraping issues
                
        self.parsed = BeautifulSoup(response.content, 'html.parser')

    def _get_titles_raw(self, fetch):
        """
        Scrapes website and returns a ResultSet object
        associated_episodes: Returns an episode number if the title is a direct episode link, usually this is true for home page. Returns None if nothing is found
        associated_flair: Returns a list of flairs of the specific title, usually from the same index, Flairs can be processed into URLS. Returns None if nothing is found
        """
        open('reference.html', 'w', encoding='utf-8').write(self.parsed.prettify())
        if fetch=="episode":
            return self.parsed.find_all('p', class_='episode')
        elif fetch=="flair":
            titles = self.parsed.find_all('p',class_='name')
            flairs = []
            for flair in titles:
                pre_proc = flair.find('a')['href']
                flairs.append(pre_proc)
            return flairs
        elif fetch=="cover":
            covers = self.parsed.find_all('div', class_='img')
            covered = []
            for cover in covers:
                pre_proc = cover.find('img')['src']
                covered.append(pre_proc)
            return covered
        elif fetch=="name":
            return self.parsed.find_all('p',class_='name')

    def _get_genres_raw(self, associated_flair = False):
        """
        Scrapes website for available genres. Returns ResultSet
        By default returns only the name of each genre 
        associated_flair: Returns a list of flairs of the specific genre, they are usually in the same index. Flairs can be processed into URLS. Returns None if nothing is found
        """
        top_genre = self.parsed.find('li', class_='movie genre hide')
        genre_container = top_genre.find('ul')
        genre_all = genre_container.find_all('a')
        genre_data = []
        for genre in genre_all:
            if associated_flair:
                genre_data.append(genre['href'])
            else:
                genre_data.append(genre)
        return(genre_data)
    
    def get_titles(self):
        """Returns a user friendly data of the available titles and flairs."""
        titles = self._get_titles_raw(fetch="name")
        episodes = self._get_titles_raw(fetch='episode')
        flairs = self._get_titles_raw(fetch='flair')
        covers = self._get_titles_raw(fetch='cover')
        scrape_res = []
        for (title, episode, flair, cover) in itertools.zip_longest(titles, episodes, flairs, covers) :
            raw_flair = remove_ep_flair(flair)
            raw_cover = remove_cdn_host(cover)
            scrape_data = {
                "title_name": None,
                "episode": None,
                "episode_raw": None,
                "flair": None,
                "raw_flair": None,
                'cover': None
            }
            scrape_data["title_name"] = title.text.strip()
            if episode:
                scrape_data["episode"] = episode.text.replace("Episode ", "").strip()
                scrape_data["episode_raw"] = episode.text.replace("Episode ", "").strip().replace('.', '-')
            scrape_data["flair"] = flair
            scrape_data["raw_flair"] = raw_flair
            scrape_data["cover"] = raw_cover
            scrape_res.append(scrape_data)
        return scrape_res

    def get_result_count(self):
        "Returns the number of results"
        return len(self.get_titles())
    
    def get_pagination(self):
        """Gets the pagination of the webpage and returns the current page and the total pages available"""
        pagination_scraped = self.parsed.find('ul',class_='pagination-list')
        if not pagination_scraped: # If we cannot find a pagination-list then assume a one page
            return {
                'page_on': 1,
                'page_total': 1
            }
        current_page = int(pagination_scraped.find('li', class_ ="selected").text.strip())
        all_pagination = pagination_scraped.find_all('a')
        total_page = int(all_pagination[-1]['data-page'])
        # total_page = len(pagination_scraped.find_all('a'))
        pagination_data = {
            'page_on': current_page,
            'page_total': total_page
        }
        return pagination_data
    
    def get_genres(self):
        "Returns a user friendly data of the available genres and flairs."
        genre_names = self._get_genres_raw()
        genre_flairs = self._get_genres_raw(associated_flair=True)
        genre_processed_data = []
        for (name, flair) in itertools.zip_longest(genre_names, genre_flairs):
            genre_scraped = {
                "genre-name": None,
                "flair": None
            }
            genre_scraped["genre-name"] = name.text.strip()
            genre_scraped["flair"] = flair
            genre_processed_data.append(genre_scraped)
        return genre_processed_data

class GogoAPI:
    def __init__(self) -> None:
        self.url = Constants.gogoanime
    
    def search_anime(self, search_query: str) -> Goscraper:
        var = search_query.replace(" ", "%20")
        url = f'{self.url}/search.html?keyword={var}'
        try:
            return Goscraper(url=url)
        except frzw_exceptions.ScrapingError:
            #If scraping issues arises then return None. 
            #If it is unexpected then we will know, but its better to be safe than sorry.
            return None
    
    def search_flair(self, flair): 
        url = f"{self.url}/category/{flair}"
        try:
            return EpisodeScraper(url=url)
        except frzw_exceptions.NotFoundEpisode:
            return None
    def new(self):
        return Goscraper(url=self.url)

    def popular(self):
        url = f'{self.url}/popular.html'
        return Goscraper(url=url)

def paginator(target: Goscraper, topage):
    urlcurr = target.url
    return Goscraper(append_query(urlcurr, "page", topage))
if __name__ == '__main__':
    from ..constants import Constants
    from ..essentials.tools import remove_ep_flair, remove_cdn_cover
    GoAPI = GogoAPI()
    go = GoAPI.search_anime('steins')
    # print(episode.get_episode_link(49))