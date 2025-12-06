from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.services.crawler_service import CrawlerService
from app.models.crawler_models import CrawlerDataListResponse, StartCrawlRequest
from typing import Optional

router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
    responses={404: {"description": "Not found"}},
)

# Shared service instance
_crawler_service = CrawlerService()

def get_crawler_service():
    return _crawler_service

@router.get("/list", response_model=CrawlerDataListResponse, tags=["crawler"])
async def get_crawler_data(
    page: int = 1, 
    page_size: int = 20,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Get paginated crawler data.
    """
    try:
        print(f"🐛 get_crawler_data called - page: {page}, page_size: {page_size}")
        data, total = service.get_data(page, page_size)
        return CrawlerDataListResponse(
            success=True,
            data=data,
            total=total,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        print(f"❌ Error in get_crawler_data: {e}")
        return CrawlerDataListResponse(
            success=False,
            message=f"Error fetching data: {str(e)}",
            data=[],
            total=0,
            page=page,
            page_size=page_size
        )

@router.post("/crawl", tags=["crawler"])
async def start_crawl(
    request: StartCrawlRequest,
    background_tasks: BackgroundTasks,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Trigger a background crawl task.
    """
    try:
        print(f"🐛 start_crawl called - pages: {request.pages}")
        # Simple logic: crawl page 1 to requested pages
        # We run this in background to avoid blocking
        background_tasks.add_task(service.crawl_pages, 1, request.pages)
        
        return {
            "success": True, 
            "message": f"Started crawling {request.pages} pages in background."
        }
    except Exception as e:
        print(f"❌ Error in start_crawl: {e}")
        return {
            "success": False, 
            "message": f"Failed to start crawl: {str(e)}"
        }
