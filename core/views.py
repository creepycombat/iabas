from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from . import services
from .models import Campana, Consentimiento, EventoComportamiento, Simulacion
from .refuerzo_contenido import PREGUNTAS, SENALES

# GIF transparente de 1x1 (pixel de apertura)
PIXEL = (b"GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff!\xf9\x04\x01\x00\x00\x00\x00,"
         b"\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;")


def es_admin(u):
    return u.is_authenticated and (u.is_staff or u.groups.filter(name="admin_seguridad").exists())


admin_requerido = user_passes_test(es_admin, login_url="/login/")


@login_required
def inicio(request):
    return redirect("panel" if es_admin(request.user) else "bandeja")


# ---------- Administrador de seguridad ----------
@admin_requerido
def panel(request):
    filas = []
    for c in Campana.objects.select_related("consentimiento").order_by("-creada"):
        n = c.simulaciones.count()
        ev = EventoComportamiento.objects.filter(simulacion__campana=c)
        filas.append({
            "c": c, "n": n,
            "destinatarios": services.destinatarios(c).count(),
            "clic": round(100 * ev.filter(tipo="clic").count() / n) if n else None,
            "reporte": round(100 * ev.filter(tipo="reporte").count() / n) if n else None,
        })
    return render(request, "core/panel.html", {"filas": filas})


@admin_requerido
@require_POST
def ejecutar_campana(request, pk):
    c = get_object_or_404(Campana, pk=pk)
    try:
        n = services.lanzar_campana(c)
        messages.success(request, f"Campaña ejecutada: {n} correos simulados enviados.")
    except services.ConsentimientoRequerido as e:
        messages.error(request, str(e))
    except services.CampanaInvalida as e:
        messages.warning(request, str(e))
    return redirect("panel")


@admin_requerido
@require_POST
def registrar_consentimiento(request, pk):
    c = get_object_or_404(Campana, pk=pk)
    if not request.POST.get("acepto"):
        messages.error(request, "Debes confirmar el consentimiento para registrarlo.")
        return redirect("panel")
    c.consentimiento = Consentimiento.objects.create(
        organizacion=request.POST.get("organizacion") or "Empresa Demo SpA",
        registrado_por=request.user,
        texto="La organización autoriza simulaciones de phishing con fines formativos, "
              "conforme a la Ley N.º 21.719, sin informar de forma anticipada su contenido.")
    c.save(update_fields=["consentimiento"])
    messages.success(request, "Consentimiento registrado. Ya puedes ejecutar la campaña.")
    return redirect("panel")


# ---------- Colaborador evaluado ----------
@login_required
def bandeja(request):
    sims = request.user.simulaciones.select_related("campana").order_by("-enviada")
    return render(request, "core/bandeja.html", {"sims": sims})


@login_required
def correo(request, token):
    sim = get_object_or_404(Simulacion, token=token, usuario=request.user)
    cuerpo = services.renderizar_correo(sim, request.build_absolute_uri("/").rstrip("/"))
    return render(request, "core/correo.html", {"sim": sim, "cuerpo": cuerpo})


@login_required
def privacidad(request):
    if request.method == "POST":
        services.revocar_consentimiento(request.user)
        messages.success(request, "Tu consentimiento fue revocado. No recibirás nuevas simulaciones.")
        return redirect("privacidad")
    return render(request, "core/privacidad.html")


# ---------- Tracking (públicas: se accede desde el correo, con el token) ----------
def _evento(token, tipo):
    try:
        return services.registrar_evento(token, tipo)
    except Simulacion.DoesNotExist:
        raise Http404


def pixel_apertura(request, token):
    _evento(token, "apertura")
    return HttpResponse(PIXEL, content_type="image/gif")


def clic(request, token):
    """Registra el clic y muestra un login falso. No se guarda ninguna credencial."""
    sim = _evento(token, "clic")
    if request.method == "POST":
        _evento(token, "datos")   # solo el evento: nunca se lee ni guarda la clave
        return redirect("refuerzo", token=token)
    return render(request, "core/login_falso.html", {"sim": sim})


def reportar(request, token):
    sim = _evento(token, "reporte")
    return render(request, "core/reporte_ok.html", {"sim": sim})


def refuerzo(request, token):
    sim = get_object_or_404(Simulacion, token=token)
    if not hasattr(sim, "reforzamiento"):
        raise Http404
    ref = sim.reforzamiento
    ctx = {"sim": sim, "ref": ref, "senales": SENALES, "preguntas": list(enumerate(PREGUNTAS))}
    if request.method == "POST" and not ref.completado:
        resultados, aciertos = [], 0
        for i, p in enumerate(PREGUNTAS):
            ok = request.POST.get(f"p{i}") == str(p["correcta"])
            aciertos += ok
            resultados.append({"p": p, "ok": ok, "elegida": request.POST.get(f"p{i}")})
        services.completar_reforzamiento(sim, aciertos, len(PREGUNTAS))
        ctx.update(resultados=resultados, aciertos=aciertos, total=len(PREGUNTAS))
    ctx["ref"] = sim.reforzamiento
    return render(request, "core/refuerzo.html", ctx)
