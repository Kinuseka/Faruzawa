# Low-level adapters. Application routes should use the bridge package.
# Backend.provider is a source id (src1, src2, ...). Concrete modules stay local.


def catalog_api():
    from API.registry import catalog_api as _impl

    return _impl()


def catalog_module():
    from API.registry import catalog_module as _impl

    return _impl()


def player_class():
    from API.registry import player_class as _impl

    return _impl()


def image_cdn_base(source_id=None):
    from API.registry import image_cdn

    return image_cdn(source_id)


def primary_image_cdn():
    from API.registry import primary_image_cdn as _impl

    return _impl()
