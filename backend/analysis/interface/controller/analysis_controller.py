from typing import Annotated
from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, status, WebSocket, WebSocketDisconnect
from analysis.interface.dto import (
    AnalysisSessionResponse,
    TradingAnalysisRequest,
    AnalysisResultResponse
)
from utils.auth import get_current_member, CurrentMember, get_current_member_websocket
from dependency_injector.wiring import inject, Provide
from analysis.application.analysis_service import AnalysisService
from utils.containers import Container
from analysis.application.websocket_manager import WebSocketManager
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/analysis", tags=["analysis"])

@router.get("/", response_model=list[AnalysisSessionResponse])
@inject
def get_analysis_list_for_member(
    current_member: Annotated[CurrentMember, Depends(get_current_member)],
    analysis_service: Annotated[AnalysisService, Depends(Provide[Container.analysis_service])]
):
    """
    현재 로그인한 사용자의 모든 분석 세션 목록을 조회합니다.
    """
    analyses = analysis_service.get_analysis_list(current_member.id)
    return [
        AnalysisSessionResponse(
            id=analysis.id,
            ticker=analysis.ticker,
            status=analysis.status,
            shallow_thinker=analysis.shallow_thinker,
            deep_thinker=analysis.deep_thinker
        ) for analysis in analyses
    ]

@router.post("/start", status_code=201, response_model=AnalysisSessionResponse)
@inject
def start_analysis_session(
    request: TradingAnalysisRequest,
    current_member: Annotated[CurrentMember, Depends(get_current_member)],
    analysis_service: Annotated[AnalysisService, Depends(Provide[Container.analysis_service])],
    background_tasks: BackgroundTasks
):
    """
    새로운 분석 세션을 시작합니다.
    
    """
    try:
        new_analysis = analysis_service.create_analysis(current_member.id, request, background_tasks)
        return AnalysisSessionResponse(
            **new_analysis.model_dump()
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start analysis: {str(e)}"
        )

@router.get("/{analysis_id}", response_model=AnalysisResultResponse)
@inject
def get_analysis_result(
    analysis_id: str,
    current_member: Annotated[CurrentMember, Depends(get_current_member)],
    analysis_service: Annotated[AnalysisService, Depends(Provide[Container.analysis_service])]
):
    """
    특정 분석 세션의 결과를 조회합니다.
    """
    analysis = analysis_service.get_analysis_by_id(analysis_id, current_member.id)
    
    return AnalysisResultResponse(
        id=analysis.id,
        ticker=analysis.ticker,
        analysis_date=analysis.analysis_date.isoformat() if hasattr(analysis.analysis_date, 'isoformat') else str(analysis.analysis_date),
        status=analysis.status,
        market_report=analysis.market_report,
        news_report=analysis.news_report,
        fundamentals_report=analysis.fundamentals_report,
        investment_debate_state=analysis.investment_debate_state,
        trader_investment_plan=analysis.trader_investment_plan,
        risk_debate_state=analysis.risk_debate_state,
        final_trade_decision=analysis.final_trade_decision,
        final_report=analysis.final_report,
        created_at=analysis.created_at.isoformat(),
        completed_at=analysis.completed_at.isoformat() if analysis.completed_at else None,
        error_message=analysis.error_message
    )

@router.get("/{analysis_id}/status")
@inject
def get_analysis_status(
    analysis_id: str,
    current_member: Annotated[CurrentMember, Depends(get_current_member)],
    analysis_service: Annotated[AnalysisService, Depends(Provide[Container.analysis_service])]
):
    """
    분석 진행 상황을 조회합니다.
    """
    analysis = analysis_service.get_analysis_by_id(analysis_id, current_member.id)
    
    return {
        "analysis_id": analysis.id,
        "status": analysis.status,
        "ticker": analysis.ticker,
        "analysis_date": analysis.analysis_date,
        "created_at": analysis.created_at.isoformat(),
        "updated_at": analysis.updated_at.isoformat(),
        "error_message": analysis.error_message
    }

@router.websocket("/ws")
@inject
async def websocket_endpoint(
    websocket: WebSocket,
    websocket_manager: Annotated[WebSocketManager, Depends(Provide[Container.websocket_manager])] = None
):
    """
    WebSocket endpoint for real-time analysis updates with enhanced security
    """
    current_member = None
    
    # Authenticate user
    try:
        access_token = websocket.query_params.get("token")
        if not access_token:
            await websocket.close(code=1008, reason="Unauthorized")
            return
        current_member = get_current_member_websocket(access_token)
    except Exception as e:
        logger.error(f"WebSocket authentication failed: {e}")
        await websocket.close(code=1008, reason="Authentication failed")
        return
    
    # Connect websocket
    connected = await websocket_manager.connect(websocket, current_member.id)
    if not connected:
        return
    
    # Message handling loop
    try:
        while True:
            data = await websocket.receive_text()
            await handle_websocket_message(websocket, websocket_manager, current_member.id, data)
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected for member {current_member.id}")
    except Exception as e:
        logger.error(f"WebSocket error for member {current_member.id}: {e}")
        await websocket.close(code=1011, reason="Internal server error")
    finally:
        await websocket_manager.disconnect(websocket, current_member.id)


async def handle_websocket_message(
    websocket: WebSocket,
    websocket_manager: WebSocketManager,
    member_id: str,
    data: str
):
    """Handle individual WebSocket messages"""
    try:
        # Validate and parse message
        message = await websocket_manager.handle_message(websocket, member_id, data)
        
        # Process message types
        if message.get("type") == "ping":
            await websocket.send_json({"type": "pong", "timestamp": message.get("timestamp")})
        elif message.get("type") == "heartbeat":
            pass  # Already handled in handle_message
        else:
            logger.debug(f"Received message: {message.get('type')} from {member_id}")
            
    except ValueError as e:
        await websocket.send_json({
            "type": "error",
            "message": str(e),
            "code": "VALIDATION_ERROR"
        })
        
        # Close connection for rate limit violations
        if "Rate limit exceeded" in str(e):
            await websocket.close(code=1008, reason="Rate limit exceeded")
            raise WebSocketDisconnect()
    except Exception as e:
        logger.error(f"Unexpected error handling message: {e}", exc_info=True)
