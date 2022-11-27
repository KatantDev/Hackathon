import os

import aiohttp
import typing
from bs4 import BeautifulSoup
from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


async def get_monastirev(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Монастырёв".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, 100):
            async with session.get(
                    'https://monastirev.ru/search',
                    params={
                        'term': term,
                        'page': page,
                        'perPage': 100,
                        'sortBy': 'name-asc'
                    }
            ) as response:
                text = await response.text()

                soup = BeautifulSoup(text, 'html.parser')
                offers = soup.find('div', {'class': 'listing'}).find_all('div', {'class': 'js-assortment-unit-show'})
                if not offers:
                    return result

                for offer in offers:
                    price = offer.find('div', {'class': 'offer__price-current'}).get_text().strip()
                    data = {
                        'title': offer.get('data-name').strip(),
                        'image': offer.get('data-image-url'),
                        'variant': offer.get('data-variant'),
                        'price': float(price.split('\n')[0]),
                        'description': offer.find('div', {'class': 'offer__description'}).get_text().strip(),
                        'link': 'https://monastirev.ru' + offer.find('a', {'class': 'offer__link'}).get('href')
                    }
                    result.append(data)
        return result


async def get_monastirev_item(url: str) -> typing.Dict:
    """
    Парсинг подробной информации для товара в аптеке "Монастырёв".

    :param url: Ссылка на товар.
    :return result: Информация о товаре
    """
    if 'monastirev.ru' not in url:
        url = f'https://monastirev.ru/offer/vladivostok/{url}'

    async with aiohttp.ClientSession() as session:
        async with session.get(url=url) as response:
            text = await response.text()
            soup = BeautifulSoup(text, 'html.parser')
            result = {
                'title': soup.find('h1', {'class': 'product-page__name'}).get_text(),
                'link': url,
                'image': soup.find('a', {'class': 'magnifier-hover-image'}).get('href'),
                'description': soup.find('div', {'class': 'product-page__name-description'}).get_text(),
                'price': float(soup.find('div', {'class': 'offer__price-current'}).get_text()),
                'additions': {}
            }
            additions = soup.find_all('div', {'class': 'grid__col-tablet-4 grid__col-12'})
            for addition in additions:
                title = addition.find('div', {'class': 'product-page__description-title'}).get_text()
                value = addition.find('div', {'class': 'product-page__description-value'}).get_text().strip()
                result['additions'][title] = value

    return result


async def get_apteka(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Аптека.ру".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        for page in range(0, 100):
            async with session.get(
                    'https://api.apteka.ru/Search/ByPhrase',
                    params={
                        'page': page,
                        'pageSize': 50,
                        'withprice': 'true',
                        'phrase': term,
                        'sort': 'byname'
                    },
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, '
                                      'like Gecko) Version/16.1 Safari/605.1.15 '
                    }
            ) as response:
                json_info = await response.json()
                if not json_info['currentCount']:
                    return result

                for offer in json_info['result']:
                    if offer['humanableUrl'] is None:
                        continue

                    if offer['itemVariantsInfo'] is not None:
                        for variant in offer['itemVariantsInfo']:
                            data = {
                                'id': variant['id'],
                                'title': offer['tradeName'].replace('<em>', '').replace('</em>', ''),
                                'image': offer['photos'][0]['original'],
                                'variant': variant['name'],
                                'price': float(offer['noDiscPrice']),
                                'link': 'https://apteka.ru/product/' + offer['humanableUrl'],
                            }
                            result.append(data)
                    else:
                        data = {
                            'id': offer['uniqueItemInfo']['id'],
                            'title': offer['tradeName'].replace('<em>', '').replace('</em>', ''),
                            'image': offer['photos'][0]['original'],
                            'price': float(offer['noDiscPrice']),
                            'link': 'https://apteka.ru/product/' + offer['humanableUrl'],
                        }
                        result.append(data)
        return result


async def get_apteka25(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Аптека25.рф".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, 100):
            async with session.get(
                    'https://аптека25.рф/api/v1/products/short',
                    params={
                        'allow_suggested_products': 'false',
                        'order_by': 'alphabetically',
                        'page': page,
                        'format': 'json',
                        'city': 1,
                        'query': term
                    }
            ) as response:
                json_info = await response.json()
                if 'error' in json_info:
                    return result

                for offer in json_info['results']:
                    data = {
                        'id': offer['offers'][0]['code'],
                        'title': offer['name'],
                        'image': offer['offers'][0]['image'],
                        'price': float(offer['offers'][0]['price']),
                        'link': 'https://аптека25.рф/product/' + offer['offers'][0]['code'],
                    }
                    result.append(data)
        return result


async def get_minicen(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Миницен".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        async with session.get(
                'https://api.minicen.ru/search/main',
                params={
                    'idTradePoint': 17798,
                    'Request': term,
                    'SearchType': 2,
                    'Sorting': 3,
                    'Page': 1,
                    'PerPage': 1,
                    'dontUseMix': 0,
                    'ApiVersion': 3
                }
        ) as response:
            json_info = await response.json()
            for offer in json_info['Data']['tovar']:
                data = {
                    'id': offer['idRecord'],
                    'image': offer['ImageOriginalPath'],
                    'title': offer['TovarName'],
                    'price': float(offer['Price']) if offer['Price'] is not None else '',
                    'link': 'https://minicen.ru/#!Tovar/' + str(offer['idRecord'])
                }
                result.append(data)
            return result


async def get_gosapteka(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Госаптека".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, 100):
            async with session.get(
                    'https://gosaptekavl.ru/catalog/',
                    params={
                        'w': term,
                        'page': page
                    },
                    cookies={'ga-catalog-sort-search-name': 'au'}
            ) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                offers = soup.find_all('div', {'class': 'el'})
                if not offers:
                    return result

                for offer in offers:
                    footer = offer.find('div', {'class': 'el-footer'})
                    data = {
                        'title': offer.find('div', {'class': 'el-name'}).find('a').get_text(),
                        'image': 'https://gosaptekavl.ru' + offer.find('a').get('orig'),
                        'price': float(offer.find('div', {'class': 'el-price'}).get('pr')),
                        'link': 'https://gosaptekavl.ru' + offer.find('a').get('href')
                    }
                    if footer is not None:
                        offer['description'] = footer.get_text()
                    result.append(data)
        return result


async def get_ovita(term: str) -> typing.List[typing.Dict]:
    """
    Поиск лекарств в аптеке "Овита".

    :param term: Название лекарства для поиска.
    :return result: Список товаров.
    """

    result = []
    async with aiohttp.ClientSession() as session:
        for page in range(1, 100):
            async with session.get(
                    'https://ovita.ru/search/',
                    params={
                        'word': term,
                        'count': 120,
                        'page': page,
                        'sort': 'nameup'
                    }
            ) as response:
                text = await response.text()
                soup = BeautifulSoup(text, 'html.parser')
                offers = soup.find_all('div', {'class': 'product'})
                if not offers:
                    return result

                for offer in offers:
                    price = offer.find('div', {'class': 'product-price-number'}).get_text().replace(' ', '')
                    data = {
                        'image': 'https://ovita.ru' + offer.find('meta', {'itemprop': 'image'}).get('content'),
                        'title': offer.find('div', {'class': 'product-description-name'}).find('a').get_text(),
                        'description': offer.find('div', {'class': 'product-description-text'}).get_text(),
                        'price': float(price),
                        'link': 'https://ovita.ru' +
                                offer.find('div', {'class': 'product-description-name'}).find('a').get('href')
                    }
                    result.append(data)
        return result


@app.get("/get_pharmacies/{pharmacy_id}")
async def get_pharmacies(pharmacy_id: int, query: typing.Union[str, None] = None):
    match pharmacy_id:
        case 1:
            try:
                result = await get_monastirev(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case 2:
            try:
                result = await get_apteka(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case 3:
            try:
                result = await get_apteka25(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case 4:
            try:
                result = await get_minicen(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case 5:
            try:
                result = await get_gosapteka(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case 6:
            try:
                result = await get_ovita(query)
                return {'status': 'ok', 'offers': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case _:
            return {'status': 'error', 'description': 'Pharmacy with this ID not found.'}


@app.get("/get_pharmacy_item/{pharmacy_id}")
async def get_pharmacies(pharmacy_id: int, item: str):
    match pharmacy_id:
        case 1:
            try:
                result = await get_monastirev_item(item)
                return {'status': 'ok', 'item': result}
            except Exception as error:
                return {'status': 'error', 'description': error}
        case _:
            return {'status': 'error', 'description': 'Pharmacy with this ID not found.'}


@app.get("/")
async def version():
    return {"status": "available", "version": os.getenv('VERSION')}
