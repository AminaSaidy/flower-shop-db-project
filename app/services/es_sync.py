from elasticsearch import AsyncElasticsearch
from app.core.config import settings

es = AsyncElasticsearch([settings.ES_URL])

INDEX = settings.ES_INDEX

async def ensure_index():
    exists = await es.indices.exists(index=INDEX)
    if not exists:
        await es.indices.create(index=INDEX, body={
            "mappings": {
                "properties": {
                    "id":       {"type": "keyword"},     
                    "name":     {"type": "text"},         
                    "color":    {"type": "keyword"},      
                    "occasion": {"type": "keyword"},      
                    "price":    {"type": "float"},        
                    "is_active":{"type": "boolean"},
                }
            }
        })


async def index_product(product) -> None:
    await ensure_index()
    await es.index(index=INDEX, id=str(product.id), document={
        "id":        str(product.id),
        "name":      product.name,
        "color":     product.color,
        "occasion":  product.occasion,
        "price":     product.price,
        "is_active": product.is_active,
    })


async def search_products_es(query: str) -> list:
    await ensure_index()
    response = await es.search(index=INDEX, body={
        "query": {
            "bool": {
                "must": [
                    {"match": {"name": {"query": query, "fuzziness": "AUTO"}}},
                ],
                "filter": [
                    {"term": {"is_active": True}}
                ]
            }
        }
    })
    
    return [
        {"id": hit["_source"]["id"], "name": hit["_source"]["name"],
         "price": hit["_source"]["price"], "score": hit["_score"]}
        for hit in response["hits"]["hits"]
    ]


async def sync_all_products(db) -> None:
    from sqlalchemy import select
    from app.db.models import Product
    result = await db.execute(select(Product).where(Product.is_active == True))
    products = result.scalars().all()
    for p in products:
        await index_product(p)
    print(f"✓ Indexed {len(products)} products into Elasticsearch")