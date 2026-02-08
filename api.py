import uuid
from typing import Annotated, Optional
from sqlmodel import Field, Session, SQLModel, create_engine, select
from fastapi import Depends, FastAPI, HTTPException, Query, status
from datetime import date, datetime
from enum import Enum

# Enums para tipos específicos
class TipoDesbloqueio(str, Enum):
    FRP = "FRP"
    ICLOUD = "iCloud"
    SENHA = "Senha"
    NETWORK = "Network"
    OUTRO = "Outro"

class StatusDesbloqueio(str, Enum):
    PENDENTE = "Pendente"
    EM_PROCESSO = "Em Processo"
    CONCLUIDO = "Concluído"
    CANCELADO = "Cancelado"

# Tabelas da base de dados
class Usuario(SQLModel, table=True):
    id_usuario: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    username: str = Field(index=True, unique=True, nullable=False)
    senha_hash: str = Field(nullable=False)
    email: Optional[str] = Field(default=None, unique=True)
    nome_completo: Optional[str] = Field(default=None)
    data_criacao: datetime = Field(default_factory=datetime.now)

class Cliente(SQLModel, table=True):
    id_cliente: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    nome: str = Field(nullable=False)
    telefone: str = Field(nullable=False)
    email: str = Field(unique=True, nullable=False)
    endereco: Optional[str] = Field(default=None)
    data_registro: datetime = Field(default_factory=datetime.now)

class Celular(SQLModel, table=True):
    id_celular: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    marca: str = Field(nullable=False)
    modelo: str = Field(nullable=False)
    imei: str = Field(nullable=False, unique=True)
    cliente_id: uuid.UUID = Field(foreign_key="cliente.id_cliente", nullable=False)
    data_registro: datetime = Field(default_factory=datetime.now)

class Desbloqueio(SQLModel, table=True):
    id_desbloqueio: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    tipo_desbloqueio: TipoDesbloqueio = Field(nullable=False)
    status: StatusDesbloqueio = Field(default=StatusDesbloqueio.PENDENTE)
    data_entrada: date = Field(nullable=False)
    data_saida: Optional[date] = Field(default=None)
    descricao_problema: Optional[str] = Field(default=None)
    observacoes: Optional[str] = Field(default=None)
    valor_cobrado: Optional[float] = Field(default=None)
    celular_id: uuid.UUID = Field(foreign_key="celular.id_celular", nullable=False)
    usuario_responsavel_id: Optional[uuid.UUID] = Field(foreign_key="usuario.id_usuario", default=None)
    data_criacao: datetime = Field(default_factory=datetime.now)

# Modelos para atualização (PATCH)
class UsuarioUpdate(SQLModel):
    username: Optional[str] = None
    email: Optional[str] = None
    nome_completo: Optional[str] = None

class ClienteUpdate(SQLModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[str] = None
    endereco: Optional[str] = None

class CelularUpdate(SQLModel):
    marca: Optional[str] = None
    modelo: Optional[str] = None
    imei: Optional[str] = None
    cliente_id: Optional[uuid.UUID] = None

class DesbloqueioUpdate(SQLModel):
    tipo_desbloqueio: Optional[TipoDesbloqueio] = None
    status: Optional[StatusDesbloqueio] = None
    data_saida: Optional[date] = None
    descricao_problema: Optional[str] = None
    observacoes: Optional[str] = None
    valor_cobrado: Optional[float] = None
    usuario_responsavel_id: Optional[uuid.UUID] = None

##### CONFIGURACAO DA BASE DE DADOS ####
db_file = "celulares.db"
url = f"sqlite:///{db_file}"
engine = create_engine(url, connect_args={"check_same_thread": False})

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session

DBSession = Annotated[Session, Depends(get_session)]
app = FastAPI(title="API de Desbloqueio de Celulares",
              description="API para gerenciamento de clientes, celulares e serviços de desbloqueio",
              version="1.0.0")

@app.on_event("startup")
def on_startup():
    create_db_and_tables()

#### USUARIO APIENDPOINTS ###
@app.post("/usuarios", response_model=Usuario, status_code=status.HTTP_201_CREATED)
def criar_usuario(usuario: Usuario, session: DBSession):
    """Cria um novo usuário no sistema."""
    # Verificar se username já existe
    existing = session.exec(
        select(Usuario).where(Usuario.username == usuario.username)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username já cadastrado"
        )
    
    # Verificar se email já existe (se fornecido)
    if usuario.email:
        existing_email = session.exec(
            select(Usuario).where(Usuario.email == usuario.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado"
            )
    
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

@app.get("/usuarios", response_model=list[Usuario])
def listar_usuarios(
    session: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Lista todos os usuários do sistema."""
    return session.exec(
        select(Usuario).offset(skip).limit(limit)
    ).all()

@app.get("/usuarios/{usuario_id}", response_model=Usuario)
def buscar_usuario(usuario_id: uuid.UUID, session: DBSession):
    """Busca um usuário pelo ID."""
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return usuario

@app.get("/usuarios/username/{username}", response_model=Usuario)
def buscar_usuario_por_username(username: str, session: DBSession):
    """Busca um usuário pelo username."""
    usuario = session.exec(
        select(Usuario).where(Usuario.username == username)
    ).first()
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    return usuario

@app.patch("/usuarios/{usuario_id}", response_model=Usuario)
def atualizar_usuario(
    usuario_id: uuid.UUID,
    dados: UsuarioUpdate,
    session: DBSession
):
    """Atualiza parcialmente os dados de um usuário."""
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar se novo username já existe
    if dados.username and dados.username != usuario.username:
        existing = session.exec(
            select(Usuario).where(Usuario.username == dados.username)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username já cadastrado para outro usuário"
            )
    
    # Verificar se novo email já existe
    if dados.email and dados.email != usuario.email:
        existing_email = session.exec(
            select(Usuario).where(Usuario.email == dados.email)
        ).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado para outro usuário"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(usuario, key, value)
    
    session.add(usuario)
    session.commit()
    session.refresh(usuario)
    return usuario

@app.delete("/usuarios/{usuario_id}")
def deletar_usuario(usuario_id: uuid.UUID, session: DBSession):
    """Remove um usuário do sistema."""
    usuario = session.get(Usuario, usuario_id)
    if not usuario:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuário não encontrado"
        )
    
    # Verificar se usuário tem desbloqueios associados
    desbloqueios = session.exec(
        select(Desbloqueio).where(Desbloqueio.usuario_responsavel_id == usuario_id)
    ).first()
    
    if desbloqueios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir usuário com desbloqueios associados"
        )
    
    session.delete(usuario)
    session.commit()
    return {"mensagem": "Usuário removido com sucesso"}

#### CLIENTE APIENDPOINTS ###
@app.post("/clientes", response_model=Cliente, status_code=status.HTTP_201_CREATED)
def criar_cliente(cliente: Cliente, session: DBSession):
    """Cria um novo cliente."""
    # Verificar se email já existe
    existing = session.exec(
        select(Cliente).where(Cliente.email == cliente.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email já cadastrado para outro cliente"
        )
    
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente

@app.get("/clientes", response_model=list[Cliente])
def listar_clientes(
    session: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
):
    """Lista todos os clientes."""
    return session.exec(
        select(Cliente).offset(skip).limit(limit)
    ).all()

@app.get("/clientes/{cliente_id}", response_model=Cliente)
def buscar_cliente(cliente_id: uuid.UUID, session: DBSession):
    """Busca um cliente pelo ID."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente

@app.get("/clientes/email/{email}", response_model=Cliente)
def buscar_cliente_por_email(email: str, session: DBSession):
    """Busca um cliente pelo email."""
    cliente = session.exec(
        select(Cliente).where(Cliente.email == email)
    ).first()
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    return cliente

@app.patch("/clientes/{cliente_id}", response_model=Cliente)
def atualizar_cliente(
    cliente_id: uuid.UUID,
    dados: ClienteUpdate,
    session: DBSession
):
    """Atualiza parcialmente os dados de um cliente."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Verificar se novo email já existe
    if dados.email and dados.email != cliente.email:
        existing = session.exec(
            select(Cliente).where(Cliente.email == dados.email)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email já cadastrado para outro cliente"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(cliente, key, value)
    
    session.add(cliente)
    session.commit()
    session.refresh(cliente)
    return cliente

@app.delete("/clientes/{cliente_id}")
def deletar_cliente(cliente_id: uuid.UUID, session: DBSession):
    """Remove um cliente do sistema."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Verificar se cliente tem celulares associados
    celulares = session.exec(
        select(Celular).where(Celular.cliente_id == cliente_id)
    ).first()
    
    if celulares:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir cliente com celulares registrados"
        )
    
    session.delete(cliente)
    session.commit()
    return {"mensagem": "Cliente removido com sucesso"}

#### CELULAR APIENDPOINTS ###
@app.post("/celulares", response_model=Celular, status_code=status.HTTP_201_CREATED)
def criar_celular(celular: Celular, session: DBSession):
    """Registra um novo celular."""
    # Verificar se IMEI já existe
    existing = session.exec(
        select(Celular).where(Celular.imei == celular.imei)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="IMEI já cadastrado para outro celular"
        )
    
    # Verificar se cliente existe
    cliente = session.get(Cliente, celular.cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    session.add(celular)
    session.commit()
    session.refresh(celular)
    return celular

@app.get("/celulares", response_model=list[Celular])
def listar_celulares(
    session: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    cliente_id: Optional[uuid.UUID] = None,
    marca: Optional[str] = None
):
    """Lista celulares com filtros opcionais."""
    query = select(Celular)
    
    if cliente_id:
        query = query.where(Celular.cliente_id == cliente_id)
    
    if marca:
        query = query.where(Celular.marca == marca)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/celulares/{celular_id}", response_model=Celular)
def buscar_celular(celular_id: uuid.UUID, session: DBSession):
    """Busca um celular pelo ID."""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    return celular

@app.get("/celulares/imei/{imei}", response_model=Celular)
def buscar_celular_por_imei(imei: str, session: DBSession):
    """Busca um celular pelo IMEI."""
    celular = session.exec(
        select(Celular).where(Celular.imei == imei)
    ).first()
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    return celular

@app.get("/clientes/{cliente_id}/celulares", response_model=list[Celular])
def celulares_por_cliente(
    session: DBSession,
    cliente_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100)
    
):
    """Lista todos os celulares de um cliente específico."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    return session.exec(
        select(Celular)
        .where(Celular.cliente_id == cliente_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.patch("/celulares/{celular_id}", response_model=Celular)
def atualizar_celular(
    celular_id: uuid.UUID,
    dados: CelularUpdate,
    session: DBSession
):
    """Atualiza parcialmente os dados de um celular."""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    
    # Verificar se novo IMEI já existe
    if dados.imei and dados.imei != celular.imei:
        existing = session.exec(
            select(Celular).where(Celular.imei == dados.imei)
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="IMEI já cadastrado para outro celular"
            )
    
    # Verificar se novo cliente existe (se estiver sendo atualizado)
    if dados.cliente_id and dados.cliente_id != celular.cliente_id:
        cliente = session.get(Cliente, dados.cliente_id)
        if not cliente:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Cliente não encontrado"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(celular, key, value)
    
    session.add(celular)
    session.commit()
    session.refresh(celular)
    return celular

@app.delete("/celulares/{celular_id}")
def deletar_celular(celular_id: uuid.UUID, session: DBSession):
    """Remove um celular do sistema."""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    
    # Verificar se celular tem desbloqueios associados
    desbloqueios = session.exec(
        select(Desbloqueio).where(Desbloqueio.celular_id == celular_id)
    ).first()
    
    if desbloqueios:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não é possível excluir celular com desbloqueios registrados"
        )
    
    session.delete(celular)
    session.commit()
    return {"mensagem": "Celular removido com sucesso"}

#### DESBLOQUEIO APIENDPOINTS ###
@app.post("/desbloqueios", response_model=Desbloqueio, status_code=status.HTTP_201_CREATED)
def criar_desbloqueio(desbloqueio: Desbloqueio, session: DBSession):
    """Registra um novo serviço de desbloqueio."""
    # Verificar se celular existe
    celular = session.get(Celular, desbloqueio.celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    
    # Verificar se usuário responsável existe (se fornecido)
    if desbloqueio.usuario_responsavel_id:
        usuario = session.get(Usuario, desbloqueio.usuario_responsavel_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário responsável não encontrado"
            )
    
    session.add(desbloqueio)
    session.commit()
    session.refresh(desbloqueio)
    return desbloqueio

@app.get("/desbloqueios", response_model=list[Desbloqueio])
def listar_desbloqueios(
    session: DBSession,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    status: Optional[StatusDesbloqueio] = None,
    tipo_desbloqueio: Optional[TipoDesbloqueio] = None,
    celular_id: Optional[uuid.UUID] = None
    
):
    """Lista serviços de desbloqueio com filtros opcionais."""
    query = select(Desbloqueio)
    
    if status:
        query = query.where(Desbloqueio.status == status)
    
    if tipo_desbloqueio:
        query = query.where(Desbloqueio.tipo_desbloqueio == tipo_desbloqueio)
    
    if celular_id:
        query = query.where(Desbloqueio.celular_id == celular_id)
    
    return session.exec(query.offset(skip).limit(limit)).all()

@app.get("/desbloqueios/{desbloqueio_id}", response_model=Desbloqueio)
def buscar_desbloqueio(desbloqueio_id: uuid.UUID, session: DBSession):
    """Busca um serviço de desbloqueio pelo ID."""
    desbloqueio = session.get(Desbloqueio, desbloqueio_id)
    if not desbloqueio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Desbloqueio não encontrado"
        )
    return desbloqueio

@app.get("/celulares/{celular_id}/desbloqueios", response_model=list[Desbloqueio])
def desbloqueios_por_celular(
    session: DBSession,
    celular_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    
):
    """Lista todos os desbloqueios de um celular específico."""
    celular = session.get(Celular, celular_id)
    if not celular:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Celular não encontrado"
        )
    
    return session.exec(
        select(Desbloqueio)
        .where(Desbloqueio.celular_id == celular_id)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/desbloqueios/status/{status}", response_model=list[Desbloqueio])
def desbloqueios_por_status(
    session: DBSession,
    status: StatusDesbloqueio,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    
):
    """Lista desbloqueios por status."""
    return session.exec(
        select(Desbloqueio)
        .where(Desbloqueio.status == status)
        .offset(skip)
        .limit(limit)
    ).all()

@app.get("/desbloqueios/tipo/{tipo}", response_model=list[Desbloqueio])
def desbloqueios_por_tipo(
    session: DBSession,
    tipo: TipoDesbloqueio,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
   
):
    """Lista desbloqueios por tipo."""
    return session.exec(
        select(Desbloqueio)
        .where(Desbloqueio.tipo_desbloqueio == tipo)
        .offset(skip)
        .limit(limit)
    ).all()

@app.patch("/desbloqueios/{desbloqueio_id}", response_model=Desbloqueio)
def atualizar_desbloqueio(
    desbloqueio_id: uuid.UUID,
    dados: DesbloqueioUpdate,
    session: DBSession
):
    """Atualiza parcialmente os dados de um serviço de desbloqueio."""
    desbloqueio = session.get(Desbloqueio, desbloqueio_id)
    if not desbloqueio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Desbloqueio não encontrado"
        )
    
    # Verificar se novo usuário responsável existe (se estiver sendo atualizado)
    if dados.usuario_responsavel_id:
        usuario = session.get(Usuario, dados.usuario_responsavel_id)
        if not usuario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário responsável não encontrado"
            )
    
    update_data = dados.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(desbloqueio, key, value)
    
    session.add(desbloqueio)
    session.commit()
    session.refresh(desbloqueio)
    return desbloqueio

@app.delete("/desbloqueios/{desbloqueio_id}")
def deletar_desbloqueio(desbloqueio_id: uuid.UUID, session: DBSession):
    """Remove um serviço de desbloqueio do sistema."""
    desbloqueio = session.get(Desbloqueio, desbloqueio_id)
    if not desbloqueio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Desbloqueio não encontrado"
        )
    
    session.delete(desbloqueio)
    session.commit()
    return {"mensagem": "Desbloqueio removido com sucesso"}

#### ENDPOINTS DE RELATÓRIOS ####
@app.get("/relatorios/desbloqueios-pendentes")
def desbloqueios_pendentes(session: DBSession):
    """Lista todos os desbloqueios com status pendente."""
    desbloqueios = session.exec(
        select(Desbloqueio)
        .where(Desbloqueio.status == StatusDesbloqueio.PENDENTE)
    ).all()
    
    return {
        "total_desbloqueios_pendentes": len(desbloqueios),
        "desbloqueios": desbloqueios
    }

@app.get("/relatorios/desbloqueios-periodo")
def desbloqueios_por_periodo(
    session: DBSession,
    data_inicio: date = Query(..., description="Data inicial (YYYY-MM-DD)"),
    data_fim: date = Query(..., description="Data final (YYYY-MM-DD)")
    
):
    """Lista desbloqueios realizados em um período específico."""
    if data_inicio > data_fim:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Data inicial não pode ser maior que data final"
        )
    
    desbloqueios = session.exec(
        select(Desbloqueio)
        .where(Desbloqueio.data_entrada >= data_inicio)
        .where(Desbloqueio.data_entrada <= data_fim)
    ).all()
    
    # Calcular estatísticas
    total = len(desbloqueios)
    total_concluidos = len([d for d in desbloqueios if d.status == StatusDesbloqueio.CONCLUIDO])
    total_pendentes = len([d for d in desbloqueios if d.status == StatusDesbloqueio.PENDENTE])
    valor_total = sum(d.valor_cobrado or 0 for d in desbloqueios if d.valor_cobrado)
    
    return {
        "periodo": {
            "data_inicio": data_inicio,
            "data_fim": data_fim
        },
        "total_desbloqueios": total,
        "total_concluidos": total_concluidos,
        "total_pendentes": total_pendentes,
        "valor_total_cobrado": round(valor_total, 2),
        "desbloqueios": desbloqueios
    }

@app.get("/relatorios/tipos-desbloqueio")
def estatisticas_tipos_desbloqueio(session: DBSession):
    """Estatísticas por tipo de desbloqueio."""
    desbloqueios = session.exec(select(Desbloqueio)).all()
    
    tipos_counts = {}
    for desbloqueio in desbloqueios:
        tipo = desbloqueio.tipo_desbloqueio.value
        tipos_counts[tipo] = tipos_counts.get(tipo, 0) + 1
    
    return {
        "total_desbloqueios": len(desbloqueios),
        "por_tipo": tipos_counts
    }

@app.get("/clientes/{cliente_id}/historico")
def historico_cliente(cliente_id: uuid.UUID, session: DBSession):
    """Retorna o histórico completo de um cliente."""
    cliente = session.get(Cliente, cliente_id)
    if not cliente:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cliente não encontrado"
        )
    
    # Buscar celulares do cliente
    celulares = session.exec(
        select(Celular).where(Celular.cliente_id == cliente_id)
    ).all()
    
    # Buscar desbloqueios de cada celular
    historico_desbloqueios = []
    for celular in celulares:
        desbloqueios_celular = session.exec(
            select(Desbloqueio).where(Desbloqueio.celular_id == celular.id_celular)
        ).all()
        
        for desbloqueio in desbloqueios_celular:
            historico_desbloqueios.append({
                "celular": {
                    "marca": celular.marca,
                    "modelo": celular.modelo,
                    "imei": celular.imei
                },
                "desbloqueio": desbloqueio
            })
    
    return {
        "cliente": cliente,
        "total_celulares": len(celulares),
        "total_desbloqueios": len(historico_desbloqueios),
        "historico": historico_desbloqueios
    }

#### ENDPOINTS DE ESTATÍSTICAS ####
@app.get("/estatisticas/gerais")
def estatisticas_gerais(session: DBSession):
    """Retorna estatísticas gerais do sistema."""
    total_clientes = len(session.exec(select(Cliente)).all())
    total_celulares = len(session.exec(select(Celular)).all())
    total_desbloqueios = len(session.exec(select(Desbloqueio)).all())
    
    desbloqueios = session.exec(select(Desbloqueio)).all()
    
    # Contar por status
    status_counts = {}
    for desbloqueio in desbloqueios:
        status = desbloqueio.status.value
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Calcular valor total cobrado
    valor_total = sum(d.valor_cobrado or 0 for d in desbloqueios if d.valor_cobrado)
    
    # Calcular média de tempo de conclusão
    tempos_conclusao = []
    for d in desbloqueios:
        if d.data_saida and d.status == StatusDesbloqueio.CONCLUIDO:
            dias = (d.data_saida - d.data_entrada).days
            if dias > 0:
                tempos_conclusao.append(dias)
    
    media_tempo = sum(tempos_conclusao) / len(tempos_conclusao) if tempos_conclusao else 0
    
    return {
        "total_clientes": total_clientes,
        "total_celulares": total_celulares,
        "total_desbloqueios": total_desbloqueios,
        "desbloqueios_por_status": status_counts,
        "valor_total_cobrado": round(valor_total, 2),
        "media_tempo_conclusao_dias": round(media_tempo, 2) if media_tempo > 0 else 0
    }

#### UTILITÁRIOS ####
@app.get("/health")
def health_check():
    """Endpoint de verificação de saúde da API."""
    return {"status": "healthy", "service": "celulares-api", "timestamp": datetime.now()}

@app.get("/")
def root():
    """Endpoint raiz com informações sobre a API."""
    return {
        "message": "API de Desbloqueio de Celulares",
        "version": "1.0.0",
        "description": "Sistema para gerenciamento de clientes, celulares e serviços de desbloqueio",
        "endpoints": {
            "usuarios": {
                "POST": "/usuarios",
                "GET": "/usuarios",
                "GET_ID": "/usuarios/{id}",
                "GET_USERNAME": "/usuarios/username/{username}",
                "PATCH": "/usuarios/{id}",
                "DELETE": "/usuarios/{id}"
            },
            "clientes": {
                "POST": "/clientes",
                "GET": "/clientes",
                "GET_ID": "/clientes/{id}",
                "GET_EMAIL": "/clientes/email/{email}",
                "PATCH": "/clientes/{id}",
                "DELETE": "/clientes/{id}"
            },
            "celulares": {
                "POST": "/celulares",
                "GET": "/celulares",
                "GET_ID": "/celulares/{id}",
                "GET_IMEI": "/celulares/imei/{imei}",
                "GET_CLIENTE": "/clientes/{id}/celulares",
                "PATCH": "/celulares/{id}",
                "DELETE": "/celulares/{id}"
            },
            "desbloqueios": {
                "POST": "/desbloqueios",
                "GET": "/desbloqueios",
                "GET_ID": "/desbloqueios/{id}",
                "GET_CELULAR": "/celulares/{id}/desbloqueios",
                "GET_STATUS": "/desbloqueios/status/{status}",
                "GET_TIPO": "/desbloqueios/tipo/{tipo}",
                "PATCH": "/desbloqueios/{id}",
                "DELETE": "/desbloqueios/{id}"
            },
            "relatorios": [
                "/relatorios/desbloqueios-pendentes",
                "/relatorios/desbloqueios-periodo",
                "/relatorios/tipos-desbloqueio",
                "/clientes/{id}/historico"
            ],
            "estatisticas": "/estatisticas/gerais",
            "health": "/health",
            "documentacao": "/docs"
        }
    }
