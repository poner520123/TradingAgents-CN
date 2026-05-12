from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from app.services.crawler_service import CrawlerService
from app.models.crawler_models import CrawlerDataListResponse, StartCrawlRequest
from typing import Optional

router = APIRouter(
    prefix="/crawler",
    tags=["crawler"],
    responses={404: {"description": "Not found"}},
)

def get_crawler_service():
    # Create a new instance each time to ensure we use the latest code
    return CrawlerService()

@router.get("/list", response_model=CrawlerDataListResponse, tags=["crawler"])
async def get_crawler_data(
    page: int = 1, 
    page_size: int = 20,
    user_name: Optional[str] = None,
    stock_name: Optional[str] = None,
    stock_code: Optional[str] = None,
    min_success_rate: Optional[float] = None,
    reason: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Get paginated crawler data with filtering.
    
    Filter parameters:
    - user_name: Filter by user name (regex match)
    - stock_name: Filter by stock name (regex match)
    - stock_code: Filter by stock code (regex match)
    - min_success_rate: Filter by minimum success rate
    - reason: Filter by reason (regex match)
    - start_date/end_date: Filter by date range
    """
    try:
        print(f"🐛 get_crawler_data called - page: {page}, page_size: {page_size}, user_name: {user_name}, stock_name: {stock_name}, stock_code: {stock_code}, min_success_rate: {min_success_rate}, reason: {reason}, start_date: {start_date}, end_date: {end_date}")
        data, total = service.get_data(page, page_size, user_name, stock_name, stock_code, min_success_rate, reason, start_date, end_date)
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

@router.get("/top-users", tags=["crawler"])
async def get_top_users(
    limit: int = 30,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Get top users by success rate.
    """
    try:
        print(f"🐛 get_top_users called - limit: {limit}")
        users = service.get_top_users_by_success_rate(limit)
        return {
            "success": True,
            "data": users,
            "total": len(users)
        }
    except Exception as e:
        print(f"❌ Error in get_top_users: {e}")
        return {
            "success": False,
            "message": f"Error fetching top users: {str(e)}",
            "data": [],
            "total": 0
        }

@router.get("/summary", tags=["crawler"])
async def get_crawler_summary(
    stock_name: Optional[str] = None,
    stock_code: Optional[str] = None,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Get crawler data summary statistics filtered by stock name or code.
    
    Provides aggregated statistics including:
    - Total records count
    - Average success rate
    - Top users for the specified stock
    - Date range of records
    """
    try:
        print(f"🐛 get_crawler_summary called - stock_name: {stock_name}, stock_code: {stock_code}")
        summary = service.get_stock_summary(stock_name, stock_code)
        return {
            "success": True,
            "data": summary
        }
    except Exception as e:
        print(f"❌ Error in get_crawler_summary: {e}")
        return {
            "success": False,
            "message": f"Error fetching summary: {str(e)}",
            "data": {}
        }

@router.get("/stock-list", tags=["crawler"])
async def get_stock_list(
    keyword: Optional[str] = None,
    limit: int = 50,
    service: CrawlerService = Depends(get_crawler_service)
):
    """
    Get unique stock list with optional keyword filtering.
    
    Returns a list of unique stocks from crawler data, 
    supporting filtering by stock name or code.
    """
    try:
        print(f"🐛 get_stock_list called - keyword: {keyword}, limit: {limit}")
        stocks = service.get_unique_stocks(keyword, limit)
        return {
            "success": True,
            "data": stocks,
            "total": len(stocks)
        }
    except Exception as e:
        print(f"❌ Error in get_stock_list: {e}")
        return {
            "success": False,
            "message": f"Error fetching stock list: {str(e)}",
            "data": [],
            "total": 0
        }
