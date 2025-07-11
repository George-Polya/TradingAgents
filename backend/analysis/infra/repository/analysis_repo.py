from analysis.domain.repository.analysis_repo import IAnalysisRepository
from sqlmodel import Session, select
from analysis.domain.analysis import Analysis as AnalysisVO
from analysis.infra.db_models.analysis import Analysis, AnalysisStatus
from analysis.interface.dto import TradingAnalysisRequest
from utils.db_utils import row_to_dict
from sqlalchemy.orm import selectinload
from datetime import datetime, date
import logging

logger = logging.getLogger(__name__)

class AnalysisRepository(IAnalysisRepository):
    def __init__(self, session: Session):
        self.session = session

    def find_by_member_id(self, member_id: str) -> list[AnalysisVO] | None:
        try:
            query = select(Analysis).where(Analysis.member_id == member_id).order_by(Analysis.created_at.desc())
            analyses = self.session.exec(query).all()
            
            if not analyses:
                return None
            
            return [AnalysisVO(**row_to_dict(analysis)) for analysis in analyses]
        except Exception as e:
            logger.error(f"❌ 멤버별 분석 조회 실패: {str(e)}")
            self.session.rollback()
            raise

    def find_by_id(self, analysis_id: str) -> AnalysisVO | None:
        try:
            analysis = self.session.get(Analysis, analysis_id)
            if not analysis:
                return None
            return AnalysisVO(**row_to_dict(analysis))
        except Exception as e:
            logger.error(f"❌ 분석 ID로 조회 실패: {str(e)}")
            self.session.rollback()
            raise

    def save(self, analysis: AnalysisVO) -> AnalysisVO:
        try:
            new_analysis = Analysis(
                **analysis.model_dump()
            )
            
            self.session.add(new_analysis)
            self.session.flush()
            
            return analysis
        except Exception as e:
            logger.error(f"❌ 분석 저장 실패: {str(e)}")
            self.session.rollback()
            raise

    def update(self, analysis_vo: AnalysisVO) -> AnalysisVO | None:
        try:
            analysis = self.session.get(Analysis, analysis_vo.id)
            logger.info(f"🔄 분석 업데이트 - Analysis ID: {analysis_vo.id}")
            if not analysis:
                return None

            # AnalysisVO의 데이터를 SQLModel 객체에 업데이트
            analysis_data = analysis_vo.model_dump(exclude_unset=True)
            
            analysis.updated_at = datetime.now()
            analysis.sqlmodel_update(analysis_data)
            
            self.session.add(analysis)
            self.session.flush()
            

            return AnalysisVO(**row_to_dict(analysis))
        except Exception as e:
            logger.error(f"❌ 분석 업데이트 실패: {str(e)}")
            self.session.rollback()
            raise
