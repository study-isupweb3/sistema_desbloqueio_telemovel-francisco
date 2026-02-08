mport uuid
from typing import Annotated, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import Depends, FastAPI, HTTPException, Query, status
from datetime import date, datetime
from enum import Enum

# Enums para tipos específicos
class TipoParto(str, Enum):
    NORMAL = "Normal"
    CESARIA = "Cesária"

class EstadoCivil(str, Enum):
    SOLTEIRO = "Solteiro"
    CASADO = "Casado"
    DIVORCIADO = "Divorciado"
    VIUVO = "Viúvo"
    UNIAO_ESTAVEL = "União Estável"

class GrupoSanguineo(str, Enum):
    A_POSITIVO = "A+"
    A_NEGATIVO = "A-"
    B_POSITIVO = "B+"
    B_NEGATIVO = "B-"
    AB_POSITIVO = "AB+"
    AB_NEGATIVO = "AB-"
    O_POSITIVO = "O+"
    O_NEGATIVO = "O-"

class SexoBebe(str, Enum):
    MASCULINO = "Masculino"
    FEMININO = "Feminino"

# Tabelas da base de dados
class Gestante(SQLModel, table=True):
    id_gestante: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    nome: str = Field(nullable=False)
    data_nascimento: date = Field(nullable=False)
    bi: str = Field(index=True, unique=True, nullable=False)
    telefone: str = Field(nullable=False)
    endereco: str = Field(nullable=False)
    grupo_sanguineo: GrupoSanguineo = Field(nullable=False)
    estado_civil: EstadoCivil = Field(nullable=False)
    data_registo: datetime = Field(default_factory=datetime.now)

class ProfissionalSaude(SQLModel, table=True):
    id_profissional: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    nome: str = Field(nullable=False)
    especialidade: str = Field(nullable=False)
    telefone: str = Field(nullable=False)
    email: str = Field(index=True, unique=True, nullable=False)

class ConsultaPrenatal(SQLModel, table=True):
    id_consulta: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    data_consulta: date = Field(nullable=False)
    idade_gestacional: int = Field(nullable=False)  # em semanas
    peso: float = Field(nullable=False)  # em kg
    tensao_arterial: str = Field(nullable=False)  # Ex: "120/80"
    observacoes: Optional[str] = Field(default=None)
    id_gestante: uuid.UUID = Field(foreign_key="gestante.id_gestante", nullable=False)
    id_profissional: uuid.UUID = Field(foreign_key="profissionalsaude.id_profissional", nullable=False)

class Exame(SQLModel, table=True):
    id_exame: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    tipo_exame: str = Field(nullable=False)
    data_exame: date = Field(nullable=False)
    resultado: Optional[str] = Field(default=None)
    id_gestante: uuid.UUID = Field(foreign_key="gestante.id_gestante", nullable=False)

class Parto(SQLModel, table=True):
    id_parto: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    data_parto: date = Field(nullable=False)
    tipo_parto: TipoParto = Field(nullable=False)
    complicacoes: Optional[str] = Field(default=None)
    peso_bebe: float = Field(nullable=False)  # em kg
    sexo_bebe: SexoBebe = Field(nullable=False)
    id_gestante: uuid.UUID = Field(foreign_key="gestante.id_gestante", nullable=False, unique=True)
    id_profissional: uuid.UUID = Field(foreign_key="profissionalsaude.id_profissional", nullable=False)

# Modelos para atualização (PATCH)
class GestanteUpdate(SQLModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    endereco: Optional[str] = None
    grupo_sanguineo: Optional[GrupoSanguineo] = None
    estado_civil: Optional[EstadoCivil] = None

class ProfissionalSaudeUpdate(SQLModel):
    nome: Optional[str] = None
    especialidade: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None

class ConsultaPrenatalUpdate(SQLModel):
    data_consulta: Optional[date] = None
    idade_gestacional: Optional[int] = None
    peso: Optional[float] = None
    tensao_arterial: Optional[str] = None
    observacoes: Optional[str] = None
    id_profissional: Optional[uuid.UUID] = None

class ExameUpdate(SQLModel):
    tipo_exame: Optional[str] = None
    data_exame: Optional[date] = None
    resultado: Optional[str] = None

class PartoUpdate(SQLModel):
    data_parto: Optional[date] = None
    tipo_parto: Optional[TipoParto] = None
    complicacoes: Optional[str] = None
    peso_bebe: Optional[float] = None
    sexo_bebe: Optional[SexoBebe] = None
    id_profissional: Optional[uuid.UUID] = None

##### CONFIGURACAO DA BASE DE DADOS ####
db_file = "maternidade.db"
url = f"sqlite:///{db_file}"
engine = create_engine(url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

# CORREÇÃO: Definir DBSession corretamente
DBSession = Annotated[Session, Depends(get_session)]

app = FastAPI(title="API de Gestão de Maternidade", 
              description="API para gerenciamento de dados de gestantes, consultas, exames e partos",
              version="1.0.0")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

#### GESTANTE APIENDPOINTS ###
@app.post("/gestantes", response_model=Gestante, status_code=status.HTTP_201_CREATED)
def criar_gestante(gestante: Gestante, session: DBSession):
    """Cria uma nova gestante no sistema."""
    # Verificar se BI já existe
    existing = session.exec(
        select(Gestante).where(Gestante.bi == gestante.bi)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="BI já cadastrado para outra gestante"
        )
    
    session.add(gestante)
    session.commit()
    session.refresh(gestante)
    return gestante

@app.get("/gestantes", response_model=list[Gestante])
def listar_gestantes(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista todas as gestantes com paginação."""
    return session.exec(
        select(Gestante).offset(skip).limit(limit)
    ).all()

@app.get("/gestantes/{gestante_id}", response_model=Gestante)
def buscar_gestante(gestante_id: uuid.UUID, session: DBSession):
    """Busca uma gestante pelo ID."""
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    return gestante

@app.get("/gestantes/bi/{bi}", response_model=Gestante)
def buscar_gestante_por_bi(bi: str, session: DBSession):
    """Busca uma gestante pelo número do BI."""
    gestante = session.exec(
        select(Gestante).where(Gestante.bi == bi)
    ).first()
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    return gestante

@app.patch("/gestantes/{gestante_id}", response_model=Gestante)
def atualizar_gestante(
    gestante_id: uuid.UUID, 
    dados: GestanteUpdate, 
    session: DBSession
):
    """Atualiza parcialmente os dados de uma gestante."""
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    # Atualizar apenas os campos fornecidos
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(gestante, key, value)
    
    session.add(gestante)
    session.commit()
    session.refresh(gestante)
    return gestante

@app.delete("/gestantes/{gestante_id}")
def deletar_gestante(gestante_id: uuid.UUID, session: DBSession):
    """Remove uma gestante do sistema."""
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    # Verificar se existem registros dependentes
    consultas = session.exec(
        select(ConsultaPrenatal).where(ConsultaPrenatal.id_gestante == gestante_id)
    ).first()
    
    if consultas:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir gestante com consultas registradas"
        )
    
    session.delete(gestante)
    session.commit()
    return {"mensagem": "Gestante removida com sucesso"}

#### PROFISSIONAL_SAUDE APIENDPOINTS ###
@app.post("/profissionais", response_model=ProfissionalSaude, status_code=status.HTTP_201_CREATED)
def criar_profissional(profissional: ProfissionalSaude, session: DBSession):
    """Cria um novo profissional de saúde."""
    # Verificar se email já existe
    existing = session.exec(
        select(ProfissionalSaude).where(ProfissionalSaude.email == profissional.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado para outro profissional"
        )
    
    session.add(profissional)
    session.commit()
    session.refresh(profissional)
    return profissional

@app.get("/profissionais", response_model=list[ProfissionalSaude])
def listar_profissionais(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    especialidade: Optional[str] = None,
    session: DBSession
):
    """Lista profissionais de saúde, com filtro opcional por especialidade."""
    query = select(ProfissionalSaude)
    if especialidade:
        query = query.where(ProfissionalSaude.especialidade == especialidade)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/profissionais/{profissional_id}", response_model=ProfissionalSaude)
def buscar_profissional(profissional_id: uuid.UUID, session: DBSession):
    """Busca um profissional de saúde pelo ID."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    return profissional

@app.patch("/profissionais/{profissional_id}", response_model=ProfissionalSaude)
def atualizar_profissional(
    profissional_id: uuid.UUID, 
    dados: ProfissionalSaudeUpdate, 
    session: DBSession
):
    """Atualiza parcialmente os dados de um profissional de saúde."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    # Verificar se novo email já existe (se estiver sendo atualizado)
    if dados.email and dados.email != profissional.email:
        existing = session.exec(
            select(ProfissionalSaude).where(ProfissionalSaude.email == dados.email)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado para outro profissional"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(profissional, key, value)
    
    session.add(profissional)
    session.commit()
    session.refresh(profissional)
    return profissional

@app.delete("/profissionais/{profissional_id}")
def deletar_profissional(profissional_id: uuid.UUID, session: DBSession):
    """Remove um profissional de saúde do sistema."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    # Verificar se existem consultas ou partos associados
    consultas = session.exec(
        select(ConsultaPrenatal).where(ConsultaPrenatal.id_profissional == profissional_id)
    ).first()
    
    partos = session.exec(
        select(Parto).where(Parto.id_profissional == profissional_id)
    ).first()
    
    if consultas or partos:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir profissional com consultas ou partos registrados"
        )
    
    session.delete(profissional)
    session.commit()
    return {"mensagem": "Profissional de saúde removido com sucesso"}

#### CONSULTA_PRENATAL APIENDPOINTS ###
@app.post("/consultas", response_model=ConsultaPrenatal, status_code=status.HTTP_201_CREATED)
def criar_consulta(consulta: ConsultaPrenatal, session: DBSession):
    """Registra uma nova consulta pré-natal."""
    # Verificar se gestante existe
    gestante = session.get(Gestante, consulta.id_gestante)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    # Verificar se profissional existe
    profissional = session.get(ProfissionalSaude, consulta.id_profissional)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    session.add(consulta)
    session.commit()
    session.refresh(consulta)
    return consulta

@app.get("/consultas", response_model=list[ConsultaPrenatal])
def listar_consultas(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    gestante_id: Optional[uuid.UUID] = None,
    profissional_id: Optional[uuid.UUID] = None,
    session: DBSession
):
    """Lista consultas pré-natais com filtros opcionais."""
    query = select(ConsultaPrenatal)
    
    if gestante_id:
        query = query.where(ConsultaPrenatal.id_gestante == gestante_id)
    
    if profissional_id:
        query = query.where(ConsultaPrenatal.id_profissional == profissional_id)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/consultas/{consulta_id}", response_model=ConsultaPrenatal)
def buscar_consulta(consulta_id: uuid.UUID, session: DBSession):
    """Busca uma consulta pré-natal pelo ID."""
    consulta = session.get(ConsultaPrenatal, consulta_id)
    if not consulta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta pré-natal não encontrada"
        )
    return consulta

@app.get("/gestantes/{gestante_id}/consultas", response_model=list[ConsultaPrenatal])
def consultas_por_gestante(
    gestante_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista todas as consultas pré-natais de uma gestante específica."""
    # Verificar se gestante existe
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    return session.exec(
        select(ConsultaPrenatal)
        .where(ConsultaPrenatal.id_gestante == gestante_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.patch("/consultas/{consulta_id}", response_model=ConsultaPrenatal)
def atualizar_consulta(
    consulta_id: uuid.UUID, 
    dados: ConsultaPrenatalUpdate, 
    session: DBSession
):
    """Atualiza parcialmente os dados de uma consulta pré-natal."""
    consulta = session.get(ConsultaPrenatal, consulta_id)
    if not consulta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta pré-natal não encontrada"
        )
    
    # Verificar se novo profissional existe (se estiver sendo atualizado)
    if dados.id_profissional:
        profissional = session.get(ProfissionalSaude, dados.id_profissional)
        if not profissional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profissional de saúde não encontrado"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(consulta, key, value)
    
    session.add(consulta)
    session.commit()
    session.refresh(consulta)
    return consulta

@app.delete("/consultas/{consulta_id}")
def deletar_consulta(consulta_id: uuid.UUID, session: DBSession):
    """Remove uma consulta pré-natal do sistema."""
    consulta = session.get(ConsultaPrenatal, consulta_id)
    if not consulta:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Consulta pré-natal não encontrada"
        )
    
    session.delete(consulta)
    session.commit()
    return {"mensagem": "Consulta pré-natal removida com sucesso"}

#### EXAME APIENDPOINTS ###
@app.post("/exames", response_model=Exame, status_code=status.HTTP_201_CREATED)
def criar_exame(exame: Exame, session: DBSession):
    """Registra um novo exame realizado por uma gestante."""
    # Verificar se gestante existe
    gestante = session.get(Gestante, exame.id_gestante)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    session.add(exame)
    session.commit()
    session.refresh(exame)
    return exame

@app.get("/exames", response_model=list[Exame])
def listar_exames(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    gestante_id: Optional[uuid.UUID] = None,
    tipo_exame: Optional[str] = None,
    session: DBSession
):
    """Lista exames com filtros opcionais."""
    query = select(Exame)
    
    if gestante_id:
        query = query.where(Exame.id_gestante == gestante_id)
    
    if tipo_exame:
        query = query.where(Exame.tipo_exame == tipo_exame)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/exames/{exame_id}", response_model=Exame)
def buscar_exame(exame_id: uuid.UUID, session: DBSession):
    """Busca um exame pelo ID."""
    exame = session.get(Exame, exame_id)
    if not exame:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exame não encontrado"
        )
    return exame

@app.get("/gestantes/{gestante_id}/exames", response_model=list[Exame])
def exames_por_gestante(
    gestante_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista todos os exames de uma gestante específica."""
    # Verificar se gestante existe
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    return session.exec(
        select(Exame)
        .where(Exame.id_gestante == gestante_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.patch("/exames/{exame_id}", response_model=Exame)
def atualizar_exame(
    exame_id: uuid.UUID, 
    dados: ExameUpdate, 
    session: DBSession
):
    """Atualiza parcialmente os dados de um exame."""
    exame = session.get(Exame, exame_id)
    if not exame:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exame não encontrado"
        )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(exame, key, value)
    
    session.add(exame)
    session.commit()
    session.refresh(exame)
    return exame

@app.delete("/exames/{exame_id}")
def deletar_exame(exame_id: uuid.UUID, session: DBSession):
    """Remove um exame do sistema."""
    exame = session.get(Exame, exame_id)
    if not exame:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exame não encontrado"
        )
    
    session.delete(exame)
    session.commit()
    return {"mensagem": "Exame removido com sucesso"}

#### PARTO APIENDPOINTS ###
@app.post("/partos", response_model=Parto, status_code=status.HTTP_201_CREATED)
def criar_parto(parto: Parto, session: DBSession):
    """Registrar um novo parto."""
    # Verificar se gestante existe
    gestante = session.get(Gestante, parto.id_gestante)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    # Verificar se gestante já tem parto registrado
    existing_parto = session.exec(
        select(Parto).where(Parto.id_gestante == parto.id_gestante)
    ).first()
    if existing_parto:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gestante já tem um parto registrado"
        )
    
    # Verificar se profissional existe
    profissional = session.get(ProfissionalSaude, parto.id_profissional)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    session.add(parto)
    session.commit()
    session.refresh(parto)
    return parto

@app.get("/partos", response_model=list[Parto])
def listar_partos(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    tipo_parto: Optional[TipoParto] = None,
    session: DBSession
):
    """Lista partos com filtro opcional por tipo de parto."""
    query = select(Parto)
    
    if tipo_parto:
        query = query.where(Parto.tipo_parto == tipo_parto)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/partos/{parto_id}", response_model=Parto)
def buscar_parto(parto_id: uuid.UUID, session: DBSession):
    """Busca um parto pelo ID."""
    parto = session.get(Parto, parto_id)
    if not parto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parto não encontrado"
        )
    return parto

@app.get("/gestantes/{gestante_id}/parto", response_model=Parto)
def parto_por_gestante(gestante_id: uuid.UUID, session: DBSession):
    """Busca o parto de uma gestante específica."""
    parto = session.exec(
        select(Parto).where(Parto.id_gestante == gestante_id)
    ).first()
    
    if not parto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não tem parto registrado"
        )
    
    return parto

@app.patch("/partos/{parto_id}", response_model=Parto)
def atualizar_parto(
    parto_id: uuid.UUID, 
    dados: PartoUpdate, 
    session: DBSession
):
    """Atualiza parcialmente os dados de um parto."""
    parto = session.get(Parto, parto_id)
    if not parto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parto não encontrado"
        )
    
    # Verificar se novo profissional existe (se estiver sendo atualizado)
    if dados.id_profissional:
        profissional = session.get(ProfissionalSaude, dados.id_profissional)
        if not profissional:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Profissional de saúde não encontrado"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(parto, key, value)
    
    session.add(parto)
    session.commit()
    session.refresh(parto)
    return parto

@app.delete("/partos/{parto_id}")
def deletar_parto(parto_id: uuid.UUID, session: DBSession):
    """Remove um parto do sistema."""
    parto = session.get(Parto, parto_id)
    if not parto:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parto não encontrado"
        )
    
    session.delete(parto)
    session.commit()
    return {"mensagem": "Parto removido com sucesso"}

#### ENDPOINTS ADICIONAIS PARA FILTROS ####
@app.get("/profissionais/especialidade/{especialidade}", response_model=list[ProfissionalSaude])
def profissionais_por_especialidade(
    especialidade: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista profissionais por especialidade."""
    return session.exec(
        select(ProfissionalSaude)
        .where(ProfissionalSaude.especialidade == especialidade)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/consultas/profissional/{profissional_id}", response_model=list[ConsultaPrenatal])
def consultas_por_profissional(
    profissional_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista consultas realizadas por um profissional específico."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    return session.exec(
        select(ConsultaPrenatal)
        .where(ConsultaPrenatal.id_profissional == profissional_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/partos/profissional/{profissional_id}", response_model=list[Parto])
def partos_por_profissional(
    profissional_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista partos realizados por um profissional específico."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    return session.exec(
        select(Parto)
        .where(Parto.id_profissional == profissional_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/consultas/periodo")
def consultas_por_periodo(
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)"),
    session: DBSession
):
    """Lista consultas realizadas em um período específico."""
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial não pode ser maior que data final"
        )
    
    consultas = session.exec(
        select(ConsultaPrenatal)
        .where(ConsultaPrenatal.data_consulta >= data_inicio)
        .where(ConsultaPrenatal.data_consulta <= data_fim)
    ).all()
    
    return {
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "total_consultas": len(consultas),
        "consultas": consultas
    }

@app.get("/exames/tipo/{tipo_exame}", response_model=list[Exame])
def exames_por_tipo(
    tipo_exame: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista exames por tipo específico."""
    return session.exec(
        select(Exame)
        .where(Exame.tipo_exame == tipo_exame)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/partos/tipo/{tipo_parto}", response_model=list[Parto])
def partos_por_tipo(
    tipo_parto: TipoParto,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista partos por tipo específico."""
    return session.exec(
        select(Parto)
        .where(Parto.tipo_parto == tipo_parto)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/gestantes/estado-civil/{estado_civil}", response_model=list[Gestante])
def gestantes_por_estado_civil(
    estado_civil: EstadoCivil,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista gestantes por estado civil."""
    return session.exec(
        select(Gestante)
        .where(Gestante.estado_civil == estado_civil)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/gestantes/grupo-sanguineo/{grupo_sanguineo}", response_model=list[Gestante])
def gestantes_por_grupo_sanguineo(
    grupo_sanguineo: GrupoSanguineo,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    session: DBSession
):
    """Lista gestantes por grupo sanguíneo."""
    return session.exec(
        select(Gestante)
        .where(Gestante.grupo_sanguineo == grupo_sanguineo)
        .offset(skip)
        .limit(limit)
    ).all()

#### ENDPOINTS DE RELATÓRIOS ####
@app.get("/relatorios/gestantes-sem-parto")
def gestantes_sem_parto(session: DBSession):
    """Lista gestantes que ainda não tiveram parto registrado."""
    # Buscar todas as gestantes
    todas_gestantes = session.exec(select(Gestante)).all()
    
    # Buscar todas as gestantes que já têm parto
    gestantes_com_parto = session.exec(
        select(Parto.id_gestante)
    ).all()
    
    # Filtrar gestantes sem parto
    gestantes_sem_parto = []
    for gestante in todas_gestantes:
        if gestante.id_gestante not in gestantes_com_parto:
            gestantes_sem_parto.append(gestante)
    
    return {
        "total_gestantes_sem_parto": len(gestantes_sem_parto),
        "gestantes": gestantes_sem_parto
    }

@app.get("/relatorios/gestantes-com-exames-pendentes")
def gestantes_com_exames_pendentes(session: DBSession):
    """Lista gestantes que têm exames sem resultado registrado."""
    # Buscar exames sem resultado
    exames_sem_resultado = session.exec(
        select(Exame).where(Exame.resultado == None)
    ).all()
    
    # Agrupar por gestante
    gestantes_exames_pendentes = {}
    for exame in exames_sem_resultado:
        if exame.id_gestante not in gestantes_exames_pendentes:
            gestante = session.get(Gestante, exame.id_gestante)
            gestantes_exames_pendentes[exame.id_gestante] = {
                "gestante": gestante,
                "exames_pendentes": []
            }
        gestantes_exames_pendentes[exame.id_gestante]["exames_pendentes"].append({
            "id_exame": exame.id_exame,
            "tipo_exame": exame.tipo_exame,
            "data_exame": exame.data_exame
        })
    
    return {
        "total_gestantes_com_exames_pendentes": len(gestantes_exames_pendentes),
        "detalhes": list(gestantes_exames_pendentes.values())
    }

@app.get("/relatorios/profissionais-mais-atendimentos")
def profissionais_mais_atendimentos(
    top: int = Query(10, ge=1, le=50, description="Número de profissionais a retornar"),
    session: DBSession
):
    """Lista os profissionais com mais atendimentos (consultas + partos)."""
    # Buscar todos os profissionais
    profissionais = session.exec(select(ProfissionalSaude)).all()
    
    profissionais_atendimentos = []
    
    for profissional in profissionais:
        # Contar consultas
        total_consultas = session.exec(
            select(ConsultaPrenatal)
            .where(ConsultaPrenatal.id_profissional == profissional.id_profissional)
        ).all()
        
        # Contar partos
        total_partos = session.exec(
            select(Parto)
            .where(Parto.id_profissional == profissional.id_profissional)
        ).all()
        
        total_atendimentos = len(total_consultas) + len(total_partos)
        
        profissionais_atendimentos.append({
            "profissional": profissional,
            "total_consultas": len(total_consultas),
            "total_partos": len(total_partos),
            "total_atendimentos": total_atendimentos
        })
    
    # Ordenar por total de atendimentos (decrescente)
    profissionais_atendimentos.sort(key=lambda x: x["total_atendimentos"], reverse=True)
    
    return {
        "top": top,
        "profissionais": profissionais_atendimentos[:top]
    }

#### ENDPOINTS DE ESTATÍSTICAS ####
@app.get("/estatisticas/gestantes")
def estatisticas_gestantes(session: DBSession):
    """Retorna estatísticas sobre as gestantes cadastradas."""
    total_gestantes = session.exec(select(Gestante)).all()
    total = len(total_gestantes)
    
    # Contar por estado civil
    estado_civil_counts = {}
    for gestante in total_gestantes:
        estado = gestante.estado_civil.value
        estado_civil_counts[estado] = estado_civil_counts.get(estado, 0) + 1
    
    # Contar por grupo sanguíneo
    grupo_sanguineo_counts = {}
    for gestante in total_gestantes:
        grupo = gestante.grupo_sanguineo.value
        grupo_sanguineo_counts[grupo] = grupo_sanguineo_counts.get(grupo, 0) + 1
    
    return {
        "total_gestantes": total,
        "por_estado_civil": estado_civil_counts,
        "por_grupo_sanguineo": grupo_sanguineo_counts
    }

@app.get("/estatisticas/partos")
def estatisticas_partos(session: DBSession):
    """Retorna estatísticas sobre os partos registrados."""
    total_partos = session.exec(select(Parto)).all()
    total = len(total_partos)
    
    # Contar por tipo de parto
    tipo_parto_counts = {}
    for parto in total_partos:
        tipo = parto.tipo_parto.value
        tipo_parto_counts[tipo] = tipo_parto_counts.get(tipo, 0) + 1
    
    # Contar por sexo do bebê
    sexo_bebe_counts = {}
    for parto in total_partos:
        sexo = parto.sexo_bebe.value
        sexo_bebe_counts[sexo] = sexo_bebe_counts.get(sexo, 0) + 1
    
    # Calcular peso médio dos bebês
    if total > 0:
        peso_medio = sum(parto.peso_bebe for parto in total_partos) / total
    else:
        peso_medio = 0
    
    return {
        "total_partos": total,
        "por_tipo_parto": tipo_parto_counts,
        "por_sexo_bebe": sexo_bebe_counts,
        "peso_medio_bebes_kg": round(peso_medio, 2)
    }

@app.get("/gestantes/{gestante_id}/resumo")
def resumo_gestante(gestante_id: uuid.UUID, session: DBSession):
    """Retorna um resumo completo dos dados de uma gestante."""
    gestante = session.get(Gestante, gestante_id)
    if not gestante:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Gestante não encontrada"
        )
    
    consultas = session.exec(
        select(ConsultaPrenatal).where(ConsultaPrenatal.id_gestante == gestante_id)
    ).all()
    
    exames = session.exec(
        select(Exame).where(Exame.id_gestante == gestante_id)
    ).all()
    
    parto = session.exec(
        select(Parto).where(Parto.id_gestante == gestante_id)
    ).first()
    
    # Calcular idade da gestante
    from datetime import datetime
    hoje = datetime.now().date()
    idade = hoje.year - gestante.data_nascimento.year
    if hoje.month < gestante.data_nascimento.month or (hoje.month == gestante.data_nascimento.month and hoje.day < gestante.data_nascimento.day):
        idade -= 1
    
    return {
        "gestante": {
            "id": gestante.id_gestante,
            "nome": gestante.nome,
            "idade": idade,
            "bi": gestante.bi,
            "telefone": gestante.telefone,
            "grupo_sanguineo": gestante.grupo_sanguineo.value,
            "estado_civil": gestante.estado_civil.value,
            "data_registo": gestante.data_registo
        },
        "total_consultas": len(consultas),
        "total_exames": len(exames),
        "tem_parto": parto is not None,
        "parto": parto,
        "ultima_consulta": consultas[-1] if consultas else None,
        "ultimo_exame": exames[-1] if exames else None
    }

@app.get("/profissionais/{profissional_id}/atendimentos")
def atendimentos_profissional(profissional_id: uuid.UUID, session: DBSession):
    """Retorna estatísticas de atendimentos de um profissional."""
    profissional = session.get(ProfissionalSaude, profissional_id)
    if not profissional:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profissional de saúde não encontrado"
        )
    
    consultas = session.exec(
        select(ConsultaPrenatal).where(ConsultaPrenatal.id_profissional == profissional_id)
    ).all()
    
    partos = session.exec(
        select(Parto).where(Parto.id_profissional == profissional_id)
    ).all()
    
    return {
        "profissional": {
            "id": profissional.id_profissional,
            "nome": profissional.nome,
            "especialidade": profissional.especialidade
        },
        "total_consultas": len(consultas),
        "total_partos": len(partos),
        "total_atendimentos": len(consultas) + len(partos)
    }

#### UTILITÁRIOS ####
@app.get("/health")
def health_check():
    """Endpoint de verificação de saúde da API."""
    return {"status": "healthy", "service": "maternidade-api", "timestamp": datetime.now()}

@app.get("/")
def root():
    """Endpoint raiz com informações sobre a API."""
    return {
        "message": "API de Gestão de Maternidade",
        "version": "1.0.0",
        "description": "Sistema para gerenciamento de dados de gestantes, consultas, exames e partos",
        "endpoints": {
            "gestantes": "/gestantes",
            "profissionais": "/profissionais",
            "consultas": "/consultas",
            "exames": "/exames",
            "partos": "/partos",
            "estatisticas": ["/estatisticas/gestantes", "/estatisticas/partos"],
            "relatorios": [
                "/relatorios/gestantes-sem-parto",
                "/relatorios/gestantes-com-exames-pendentes",
                "/relatorios/profissionais-mais-atendimentos"
            ],
            "filtros": [
                "/profissionais/especialidade/{especialidade}",
                "/consultas/profissional/{id}",
                "/partos/profissional/{id}",
                "/exames/tipo/{tipo}",
                "/partos/tipo/{tipo}",
                "/gestantes/estado-civil/{estado}",
                "/gestantes/grupo-sanguineo/{grupo}"
            ],
            "resumos": ["/gestantes/{id}/resumo", "/profissionais/{id}/atendimentos"],
            "documentacao": "/docs"
        }
    }