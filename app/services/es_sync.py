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


#async def index_product(product) 

#async def search_products_es(query: str) 

#async def sync_all_products(db) 