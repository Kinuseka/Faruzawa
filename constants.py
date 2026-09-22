import textwrap
import yaml

version = "v0.4.2"
version_label = "Beta"


class Configuration:
    def __init__(self, name="config.yml"):
        self.name = name

    def load(self):
        "Load, returns itself"
        with open(self.name, "r") as f:
            self.data = yaml.safe_load(f)
        return self
    
    def __getattr__(self, name):
        return self.data[name] or None

class _BaseConstants(Configuration):
    def __init__(self, name="config.yml"):
        super().__init__(name)
        self.load()
    #Backend
    @property
    def gogoanime(self):
        return self.data['Backend']['gogoanime']
    @property
    def gogocdn(self):
        return self.data['Backend']['gogocdn']
    @property
    def useragent(self):
        return self.data['Backend']['useragent']
    @property
    def key(self):
        return self.data['Backend']['key']
    @property
    def videocdn(self):
        return self.data['Backend']['videocdn']
    #Website
    @property
    def server_name(self):
        return self.data['Website']['server_name']
    @property
    def full_name(self):
        return self.data['Website']['full_name'].format(server_name=self.server_name)
    #SEO
    @property
    def robots_txt(self):
        return self.data['SEO']['robots_txt'].format(server_name=self.server_name)

class _BaseCache(Configuration):
    def __init__(self, main, name="config.yml"):
        super().__init__(name)
        self.main = main
        self.load()
    @property
    def site_cachetype(self):
        return self.data[self.main]['cache_type']
    @property
    def site_hostname(self):
        return self.data[self.main]['hostname']
    @property
    def site_port(self):
        return self.data[self.main]['port']
    @property
    def site_db_name(self):
        return self.data[self.main]['db_name']
    @property
    def site_expires_on(self):
        return self.data[self.main]['expires_on']
    @property
    def site_expires_after(self):
        return self.data[self.main]['expires_after']

Constants = _BaseConstants()
