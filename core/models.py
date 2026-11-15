import uuid
from django.conf import settings
from django.db import models
from django.contrib.auth.models import User


class Grupo(models.Model):
    """RF-02: unidad organizacional (área, sede o departamento)."""
    nombre = models.CharField(max_length=100)

    def __str__(self):
        return self.nombre


class Perfil(models.Model):
    """Extiende al usuario de Django: rol implícito por grupo de Django, y grupo organizacional."""
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="perfil")
    grupo = models.ForeignKey(Grupo, null=True, blank=True, on_delete=models.SET_NULL)
    consentimiento_revocado = models.BooleanField(default=False)  # RNF-06

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class Consentimiento(models.Model):
    """RF-10: consentimiento informado a nivel organizacional, con trazabilidad."""
    organizacion = models.CharField(max_length=150)
    texto = models.TextField()
    fecha = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKey(User, null=True, on_delete=models.SET_NULL)

    def __str__(self):
        return f"{self.organizacion} ({self.fecha:%d/%m/%Y})"


class Campana(models.Model):
    ESTADOS = [("borrador", "Borrador"), ("ejecutada", "Ejecutada")]
    nombre = models.CharField(max_length=150)
    consentimiento = models.ForeignKey(Consentimiento, null=True, blank=True, on_delete=models.PROTECT)
    grupos = models.ManyToManyField(Grupo)
    asunto = models.CharField(max_length=200)
    remitente = models.CharField(max_length=150, default="Soporte TI <soporte@empresa-falsa.test>")
    cuerpo = models.TextField(help_text="Usa {nombre} y {enlace} dentro del texto.")
    estado = models.CharField(max_length=10, choices=ESTADOS, default="borrador")
    creada = models.DateTimeField(auto_now_add=True)
    ejecutada = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.nombre


class Simulacion(models.Model):
    """Un correo simulado enviado a un usuario. El token identifica sus eventos."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="simulaciones")
    campana = models.ForeignKey(Campana, on_delete=models.CASCADE, related_name="simulaciones")
    token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    enviada = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.campana} → {self.usuario}"

    def tipos_eventos(self):
        return set(self.eventos.values_list("tipo", flat=True))

    @property
    def fallida(self):
        return bool(self.tipos_eventos() & {"clic", "datos"})


class EventoComportamiento(models.Model):
    """RF-04: apertura, clic, ingreso de datos o reporte."""
    TIPOS = [("apertura", "Apertura"), ("clic", "Clic"), ("datos", "Ingreso de datos"), ("reporte", "Reporte")]
    simulacion = models.ForeignKey(Simulacion, on_delete=models.CASCADE, related_name="eventos")
    tipo = models.CharField(max_length=10, choices=TIPOS)
    fecha = models.DateTimeField(auto_now_add=True)


class Reforzamiento(models.Model):
    """RF-05: se asigna tras una simulación fallida; nota = % de aciertos de la evaluación."""
    simulacion = models.OneToOneField(Simulacion, on_delete=models.CASCADE, related_name="reforzamiento")
    nota = models.FloatField(null=True, blank=True)
    completado = models.DateTimeField(null=True, blank=True)


class ModeloML(models.Model):
    """RNF-07: cada modelo guarda su versión y AUC; solo uno está vigente."""
    version = models.PositiveIntegerField(unique=True)
    auc = models.FloatField()
    vigente = models.BooleanField(default=False)
    archivo = models.CharField(max_length=200)
    creado = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"v{self.version} (AUC {self.auc:.2f})"


class PuntajeRiesgo(models.Model):
    """RF-06: historial de puntajes (0-100) por usuario, ligado al modelo que lo calculó."""
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name="puntajes")
    valor = models.FloatField()
    modelo = models.ForeignKey(ModeloML, null=True, on_delete=models.SET_NULL)
    fecha = models.DateTimeField(auto_now_add=True)
