# app/main.py

from fastapi import FastAPI
from contextlib import asynccontextmanager

from .api import auth, consultation

from .business_logic.agents import ProfilerAgent, SupervisorAgent, TherapistAgent, TherapistFactory
from .business_logic.controllers.consultation_controller import ConsultationController
from .business_logic.services.llm_service import create_llm_service
from .data_access.memory.system_initializer import MemorySystemInitializer
from .data_access.repositories.session_repository import SessionRepository
from .data_access.repositories.user_repository import UserRepository

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("--- 应用启动，初始化核心服务 ---")
    
    app.state.llm_service = create_llm_service()
    app.state.memory_manager = await MemorySystemInitializer.initialize_memory_system()
    # create async repositories (they perform async file loading)
    app.state.session_repository = await SessionRepository.create_repo()
    app.state.user_repository = await UserRepository.create_repo()

    profiler = ProfilerAgent(llm_service=app.state.llm_service)
    supervisor = SupervisorAgent(llm_service=app.state.llm_service)
    therapist_factory = TherapistFactory(memory_manager=app.state.memory_manager, llm_service=app.state.llm_service)

    await therapist_factory.ensure_therapist_memories()
    therapists = therapist_factory.create_all_therapists()
    
    app.state.consultation_controller = ConsultationController(
        profiler_agent=profiler,
        therapist_agents=therapists,
        supervisor_agent=supervisor,
        memory_manager=app.state.memory_manager
    )

    print("--- 所有核心服务已准备就绪 (挂载于 app.state) ---")
    yield
    print("--- 应用关闭，正在清理 ---")

app = FastAPI(
    title="心理咨询系统",
    lifespan=lifespan
)

# API路由
app.include_router(auth.router)
app.include_router(consultation.router)

@app.get("/", tags=["Root"])
def read_root():
    return {"status": "ok", "message": "欢迎使用心理咨询后端系统 V2"}