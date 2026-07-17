"""
MASK.SOUND — API web + frontend estático.

Roda em :8501 (compatível com EasyPanel).
"""

from __future__ import annotations

import os
import sys
import tempfile
import traceback
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import (
    Cookie,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from api.sessions import create_session, destroy_session, get_user_id
from auth.db import PLANS, User, get_db  # noqa: F401 — PLANS used in /api/plans
from core.pipeline_v2 import OpcoesProcessamento, processar_midia
from ui.platforms import PLATFORMS
from utils.audio_io import carregar_audio
from utils.video_io import extrair_audio_do_video, ffmpeg_disponivel

WEB_DIR = os.path.join(ROOT, "web")
OUTPUT_DIR = os.path.join(ROOT, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)

app = FastAPI(title="GhostWave", version="3.0.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

COOKIE = "ms_session"


# ─── models ────────────────────────────────────────────────────────────────

class LoginIn(BaseModel):
    email: str
    password: str


class RegisterIn(BaseModel):
    name: str
    email: str
    password: str = Field(min_length=6)


class UserUpdateIn(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    plan: Optional[str] = None
    video_limit: Optional[int] = None
    videos_used: Optional[int] = None
    active: Optional[bool] = None
    notes: Optional[str] = None
    new_password: Optional[str] = None


# ─── deps ──────────────────────────────────────────────────────────────────

def current_user(ms_session: Optional[str] = Cookie(default=None, alias=COOKIE)) -> User:
    uid = get_user_id(ms_session)
    if not uid:
        raise HTTPException(401, "Não autenticado")
    user = get_db().get_by_id(uid)
    if not user or not user.active:
        raise HTTPException(401, "Sessão inválida")
    return user


def optional_user(
    ms_session: Optional[str] = Cookie(default=None, alias=COOKIE),
) -> Optional[User]:
    uid = get_user_id(ms_session)
    if not uid:
        return None
    return get_db().get_by_id(uid)


# ─── auth ──────────────────────────────────────────────────────────────────

@app.post("/api/auth/login")
def login(body: LoginIn, response: Response):
    user = get_db().authenticate(body.email, body.password)
    if not user:
        raise HTTPException(401, "E-mail ou senha incorretos")
    token = create_session(user.id)
    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="lax",
        max_age=60 * 60 * 24 * 7,
        path="/",
    )
    return {"ok": True, "user": user.to_dict()}


@app.post("/api/auth/register")
def register(body: RegisterIn):
    created = get_db().create_user(
        body.email, body.name, body.password, role="user", plan="free"
    )
    if not created:
        raise HTTPException(400, "E-mail já cadastrado ou dados inválidos")
    return {"ok": True, "message": "Conta criada"}


@app.post("/api/auth/logout")
def logout(response: Response, ms_session: Optional[str] = Cookie(default=None, alias=COOKIE)):
    destroy_session(ms_session)
    response.delete_cookie(COOKIE, path="/")
    return {"ok": True}


@app.get("/api/auth/me")
def me(user: User = Depends(current_user)):
    return {"user": user.to_dict()}


# ─── meta ──────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {
        "ok": True,
        "service": "ghostwave",
        "ffmpeg": ffmpeg_disponivel(),
    }


@app.get("/api/platforms")
def platforms():
    return {
        "platforms": [
            {
                "id": p["id"],
                "name": p["name"],
                "icon": p["icon"],
                "color": p["color"],
                "hint_key": p["hint_key"],
                "icon_url": f"https://cdn.simpleicons.org/{p['icon']}/2ECBFF",
            }
            for p in PLATFORMS
        ]
    }


# ─── account ───────────────────────────────────────────────────────────────

@app.post("/api/account/request-pro")
def request_pro(user: User = Depends(current_user)):
    note = (user.notes or "") + f"\n[pedido plano {datetime.utcnow().isoformat()}]"
    get_db().update_user(user.id, notes=note.strip())
    return {
        "ok": True,
        "message": "Pedido registrado. O admin ativa mensal/trimestral/anual após pagamento.",
    }


@app.get("/api/plans")
def list_plans_public():
    return {
        "plans": [
            p
            for p in PLANS.values()
            if p.get("active", True) and p["id"] != "pro"
        ]
    }


@app.get("/api/account/usage")
def usage(user: User = Depends(current_user)):
    return {"usage": get_db().usage_for_user(user.id)}


# ─── admin ─────────────────────────────────────────────────────────────────

@app.get("/api/admin/stats")
def admin_stats(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return get_db().stats()


@app.get("/api/admin/users")
def admin_users(user: User = Depends(current_user)):
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    return {"users": [u.to_dict() for u in get_db().list_users()]}


@app.patch("/api/admin/users/{user_id}")
def admin_update_user(
    user_id: int, body: UserUpdateIn, user: User = Depends(current_user)
):
    if user.role != "admin":
        raise HTTPException(403, "Admin only")
    updated = get_db().update_user(
        user_id,
        name=body.name,
        role=body.role,
        plan=body.plan,
        video_limit=body.video_limit,
        videos_used=body.videos_used,
        active=body.active,
        notes=body.notes,
        new_password=body.new_password,
    )
    if not updated:
        raise HTTPException(404, "Usuário não encontrado")
    return {"user": updated.to_dict()}


# ─── process ───────────────────────────────────────────────────────────────

@app.post("/api/process")
async def process_media(
    platform: str = Form("capcut"),
    file: UploadFile = File(...),
    white_file: Optional[UploadFile] = File(None),
    white_text: str = Form(""),
    opt_proteger: str = Form("1"),
    opt_metadados: str = Form("1"),
    opt_phase: str = Form("1"),
    opt_compress: str = Form("1"),
    decoy_db: float = Form(-40.0),
    cloak_mode: str = Form("auto"),
    black_text: str = Form(""),
    stt_blend: float = Form(0.4),
    user: User = Depends(current_user),
):
    """
    Processa mídia com as 4 funções principais + cloaker black/white.
    """
    fresh = get_db().get_by_id(user.id)
    if not fresh or not fresh.can_process:
        raise HTTPException(
            402,
            "Sem créditos. Assine o Pro (R$ 49,90) ou peça ao admin.",
        )

    raw = await file.read()
    if not raw:
        raise HTTPException(400, "Arquivo vazio")

    filename = file.filename or "upload.bin"
    ext = os.path.splitext(filename)[1].lower()
    is_video = ext in {".mp4", ".mov", ".mkv", ".webm", ".m4v", ".avi"}

    def _flag(v: str) -> bool:
        return str(v).lower() in ("1", "true", "yes", "on")

    tmp_dir = tempfile.mkdtemp(prefix="ms_")
    try:
        in_path = os.path.join(tmp_dir, f"in{ext or '.bin'}")
        with open(in_path, "wb") as f:
            f.write(raw)

        if is_video:
            if not ffmpeg_disponivel():
                raise HTTPException(500, "ffmpeg indisponível no servidor")
            y, sr, _vmeta = extrair_audio_do_video(in_path, sr_alvo=48000)
            video_path = in_path
        else:
            y, sr = carregar_audio(in_path, sr_alvo=48000)
            video_path = None

        # White copy (áudio enviado ou texto → sintético no pipeline)
        white_audio = None
        if white_file is not None:
            wr = await white_file.read()
            if wr:
                wext = os.path.splitext(white_file.filename or "w.wav")[1] or ".wav"
                wpath = os.path.join(tmp_dir, f"white{wext}")
                with open(wpath, "wb") as f:
                    f.write(wr)
                white_audio, _ = carregar_audio(wpath, sr_alvo=sr)

        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        base = f"ms_{user.id}_{ts}"
        mode = (cloak_mode or "auto").strip().lower().replace("-", "_")
        if mode in ("ads", "anti_analysis"):
            mode = "anti_analise"
        if mode not in ("auto", "natural", "redirect", "white_only", "anti_analise"):
            mode = "auto"
        db = float(decoy_db)
        if mode == "anti_analise":
            # white um degrau mais presente que o residual natural
            if db > -24.0 or db < -50.0:
                db = -30.0
            db = float(max(-36.0, min(-24.0, db)))
            anti_db = db
        else:
            if db > -30.0:
                db = -40.0
            if db < -50.0:
                db = -50.0
            anti_db = -30.0
        blend = float(max(0.2, min(0.55, float(stt_blend))))
        opt = OpcoesProcessamento(
            proteger_audio_ia=_flag(opt_proteger),
            limpar_metadados=_flag(opt_metadados) or mode == "anti_analise",
            phase_stereo=_flag(opt_phase) or mode == "anti_analise",
            comprimir_video=_flag(opt_compress) and is_video,
            usar_cloaker=_flag(opt_proteger),
            decoy_db=db,
            cloak_mode=mode,
            optimize_stt=(mode == "auto"),
            stt_blend=blend,
            black_scramble=0.2,
            white_text=(white_text or "").strip()
            or "Oferta especial. Confira as condicoes oficiais no site. Produto com garantia e suporte.",
            black_text_hint=(black_text or "").strip(),
            anti_ia_leve=False,
            platform=platform,
            anti_decoy_db=anti_db,
            micro_scramble=0.12 if mode == "anti_analise" else 0.0,
        )

        result = processar_midia(
            y,
            sr,
            audio_white=white_audio,
            caminho_video=video_path,
            out_dir=OUTPUT_DIR,
            basename=base,
            opcoes=opt,
        )

        get_db().consume_video(
            user.id,
            kind="video" if is_video else "audio",
            platform=platform,
            filename=filename,
        )
        fresh2 = get_db().get_by_id(user.id)

        out_wav = result["audio_protected"]
        orig_wav = result["audio_original"]
        out_mp4 = result.get("video")

        return {
            "ok": True,
            "files": {
                "protected_wav": f"/api/files/{os.path.basename(out_wav)}",
                "original_wav": f"/api/files/{os.path.basename(orig_wav)}",
                "protected_mp4": (
                    f"/api/files/{os.path.basename(out_mp4)}" if out_mp4 else None
                ),
            },
            "report": {
                "platform": platform,
                "pipeline": "v5_anti_analise",
                "cloak_mode": mode,
                "etapas": result.get("report", {}).get("etapas"),
                "opcoes": result.get("report", {}).get("opcoes"),
                "stt_preview": result.get("stt_preview")
                or result.get("report", {}).get("stt_preview"),
                "nota": (
                    "auto = loop Whisper até white vencer black no score. "
                    "anti_analise = black normal + white sob mascaramento + micro-scramble "
                    "(mira robô de ads; não garante aprovação). "
                    "white_only força white. natural = black limpa + watermark."
                ),
            },
            "stt_preview": result.get("stt_preview")
            or result.get("report", {}).get("stt_preview"),
            "user": fresh2.to_dict() if fresh2 else None,
        }
    except HTTPException:
        raise
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(500, f"Falha no processamento: {e}") from e
    finally:
        try:
            for name in os.listdir(tmp_dir):
                os.unlink(os.path.join(tmp_dir, name))
            os.rmdir(tmp_dir)
        except OSError:
            pass


@app.get("/api/files/{name}")
def get_file(name: str, user: User = Depends(current_user)):
    # só arquivos do usuário ou admin
    safe = os.path.basename(name)
    if ".." in safe or "/" in safe:
        raise HTTPException(400, "Nome inválido")
    path = os.path.join(OUTPUT_DIR, safe)
    if not os.path.isfile(path):
        raise HTTPException(404, "Arquivo não encontrado")
    if user.role != "admin" and f"ms_{user.id}_" not in safe:
        raise HTTPException(403, "Sem permissão")
    media = "audio/wav"
    if safe.endswith(".mp4"):
        media = "video/mp4"
    elif safe.endswith(".mp3"):
        media = "audio/mpeg"
    return FileResponse(path, media_type=media, filename=safe)


# ─── static SPA ────────────────────────────────────────────────────────────

@app.get("/")
def index():
    return FileResponse(os.path.join(WEB_DIR, "index.html"))


if os.path.isdir(WEB_DIR):
    app.mount("/static", StaticFiles(directory=os.path.join(WEB_DIR, "static")), name="static")

# assets (logo)
_assets = os.path.join(ROOT, "assets")
if os.path.isdir(_assets):
    app.mount("/assets", StaticFiles(directory=_assets), name="assets")
