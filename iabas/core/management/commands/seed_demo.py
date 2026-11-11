"""Crea datos de demostración: grupos, usuarios, consentimiento y 5 campañas históricas."""
import random
from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.utils import timezone

from core import services
from core.models import *

NOMBRES = ["Camila", "Matías", "Valentina", "Benjamín", "Javiera", "Sebastián", "Constanza", "Felipe",
           "Fernanda", "Nicolás", "Catalina", "Diego", "Francisca", "Vicente", "Antonia", "Tomás",
           "Isidora", "Joaquín", "Daniela", "Cristóbal"]
APELLIDOS = ["González", "Muñoz", "Rojas", "Díaz", "Pérez", "Soto", "Contreras", "Silva", "Martínez",
             "Sepúlveda", "Morales", "Rodríguez", "López", "Fuentes", "Hernández"]
GRUPOS = ["Finanzas", "TI", "Ventas", "RRHH"]

PLANTILLAS = [
    ("Restablece tu contraseña", "Soporte TI <soporte@empresa-falsa.test>",
     "Hola {nombre},\n\nTu contraseña vence hoy. Para evitar el bloqueo de tu cuenta, restablécela aquí:\n{enlace}\n\nEquipo de Soporte TI"),
    ("Factura pendiente de pago", "Cobranzas <cobranzas@proveedor-falso.test>",
     "Estimado/a {nombre},\n\nAdjuntamos la factura N° 4821 con vencimiento mañana. Revísala en el siguiente enlace:\n{enlace}\n\nSaludos."),
    ("Nuevo beneficio para colaboradores", "RRHH <rrhh@empresa-falsa.test>",
     "Hola {nombre},\n\nYa está disponible tu bono de fin de año. Ingresa con tu cuenta para confirmarlo:\n{enlace}\n\nRecursos Humanos"),
    ("Alerta de inicio de sesión sospechoso", "Seguridad <seguridad@empresa-falsa.test>",
     "{nombre}, detectamos un acceso desde otro país. Si no fuiste tú, verifica tu cuenta:\n{enlace}"),
    ("Documento compartido contigo", "Gerencia <gerencia@empresa-falsa.test>",
     "Hola {nombre}, te compartí el informe trimestral. Ábrelo aquí:\n{enlace}"),
]


class Command(BaseCommand):
    help = "Carga datos de demostración (usa --reset para borrarlos antes)."

    def add_arguments(self, parser):
        parser.add_argument("--reset", action="store_true")
        parser.add_argument("--usuarios", type=int, default=60)

    def handle(self, *args, **o):
        if o["reset"]:
            User.objects.filter(is_superuser=False).delete()
            for m in (Campana, Consentimiento, Grupo, ModeloML):
                m.objects.all().delete()
        random.seed(42)
        g_admin, _ = Group.objects.get_or_create(name="admin_seguridad")
        g_colab, _ = Group.objects.get_or_create(name="colaborador")

        admin, creado = User.objects.get_or_create(username="admin", defaults=dict(
            first_name="Ana", last_name="Seguridad", is_staff=True, is_superuser=True))
        if creado:
            admin.set_password("admin1234"); admin.save()
        admin.groups.add(g_admin)
        Perfil.objects.get_or_create(user=admin)

        grupos = [Grupo.objects.get_or_create(nombre=n)[0] for n in GRUPOS]
        consent = Consentimiento.objects.create(
            organizacion="Empresa Demo SpA", registrado_por=admin,
            texto="La organización autoriza la ejecución de simulaciones de phishing con fines "
                  "formativos, conforme a la Ley N.º 21.719. El detalle de cada campaña no se "
                  "informa de forma anticipada, para preservar la validez de la medición.")

        # Usuarios, cada uno con una "susceptibilidad" latente que genera su comportamiento
        usuarios = []
        for i in range(o["usuarios"]):
            n, a = random.choice(NOMBRES), random.choice(APELLIDOS)
            u = User.objects.create_user(f"{n}.{a}{i}".lower().replace("í","i").replace("á","a")
                                         .replace("é","e").replace("ó","o").replace("ñ","n"),
                                         password="demo1234", first_name=n, last_name=a)
            u.groups.add(g_colab)
            Perfil.objects.create(user=u, grupo=grupos[i % len(grupos)])
            usuarios.append((u, random.betavariate(2, 3)))

        # 5 campañas históricas semanales (la última hace ~1 semana)
        ahora = timezone.now()
        for k, (asunto, rem, cuerpo) in enumerate(PLANTILLAS):
            fecha = ahora - timedelta(weeks=len(PLANTILLAS) - k)
            c = Campana.objects.create(nombre=f"Campaña {k+1}: {asunto}", consentimiento=consent,
                                       asunto=asunto, remitente=rem, cuerpo=cuerpo)
            c.grupos.set(grupos)
            services.lanzar_campana(c)
            Campana.objects.filter(pk=c.pk).update(creada=fecha, ejecutada=fecha)
            for sim in c.simulaciones.select_related("usuario"):
                s = dict((u.pk, v) for u, v in usuarios)[sim.usuario.pk]
                self._comportamiento(sim, s * (0.9 ** k), fecha)

        # Campañas para la demo en vivo
        demo = Campana.objects.create(nombre="Campaña 6 (demo en vivo)", consentimiento=consent,
                                      asunto="Actualiza tus datos de acceso", remitente=PLANTILLAS[0][1],
                                      cuerpo=PLANTILLAS[0][2])
        demo.grupos.set(grupos)
        sin = Campana.objects.create(nombre="Campaña sin consentimiento (prueba RF-10)",
                                     asunto="Prueba", cuerpo="Hola {nombre}, {enlace}")
        sin.grupos.set(grupos)
        self.stdout.write(self.style.SUCCESS(
            f"Listo: {len(usuarios)} usuarios, 5 campañas históricas, 2 campañas pendientes.\n"
            "Admin: admin / admin1234 · Colaboradores: <usuario> / demo1234"))

    def _comportamiento(self, sim, s, fecha):
        """Simula qué hizo el usuario; s = susceptibilidad efectiva (0-1)."""
        r = random.random
        eventos = []
        if r() < 0.85:
            eventos.append("apertura")
        if "apertura" in eventos and r() < s * 0.9:
            eventos.append("clic")
            if r() < 0.4:
                eventos.append("datos")
        elif "apertura" in eventos and r() < (1 - s) * 0.45:
            eventos.append("reporte")
        t = fecha
        for tipo in eventos:
            t += timedelta(minutes=random.randint(1, 240))
            EventoComportamiento.objects.create(simulacion=sim, tipo=tipo)
            EventoComportamiento.objects.filter(simulacion=sim, tipo=tipo).update(fecha=t)
        Simulacion.objects.filter(pk=sim.pk).update(enviada=fecha)
        if "clic" in eventos:
            ref = Reforzamiento.objects.create(simulacion=sim)
            if r() < 0.8:  # no todos completan el reforzamiento
                Reforzamiento.objects.filter(pk=ref.pk).update(
                    nota=round(min(100, max(30, random.gauss(75 - 20 * s, 12))), 1),
                    completado=t + timedelta(hours=random.randint(1, 48)))
