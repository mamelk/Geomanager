from django.core.management.base import BaseCommand
from django.contrib.auth.models import User


class Command(BaseCommand):
    help = 'Vérifie et crée le superutilisateur Admin (Admin/Admin) — Formateur principal Delphin BAZIBUHE'

    def handle(self, *args, **options):
        username = 'Admin'
        password = 'Admin'
        email = 'admin@geomanager.cd'

        # Gérer aussi l'ancien compte minuscule
        old_user = User.objects.filter(username__iexact='admin').exclude(username=username).first()
        if old_user:
            old_user.username = username
            old_user.is_superuser = True
            old_user.is_staff = True
            old_user.set_password(password)
            old_user.first_name = 'Delphin'
            old_user.last_name = 'BAZIBUHE'
            old_user.save()
            self.stdout.write(
                self.style.SUCCESS(
                    f'Ancien compte renommé en "{username}" avec identité Delphin BAZIBUHE.'
                )
            )
            return

        if User.objects.filter(username=username).exists():
            user = User.objects.get(username=username)
            updated = False
            if not user.is_superuser:
                user.is_superuser = True
                user.is_staff = True
                updated = True
            if user.first_name != 'Delphin' or user.last_name != 'BAZIBUHE':
                user.first_name = 'Delphin'
                user.last_name = 'BAZIBUHE'
                updated = True
            if updated:
                user.save()
                self.stdout.write(
                    self.style.WARNING(
                        f'L\'utilisateur "{username}" mis à jour — Delphin BAZIBUHE.'
                    )
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Le superutilisateur "{username}" (Delphin BAZIBUHE) existe déjà.'
                    )
                )
        else:
            User.objects.create_superuser(
                username=username,
                email=email,
                password=password,
                first_name='Delphin',
                last_name='BAZIBUHE',
            )
            self.stdout.write(
                self.style.SUCCESS(
                    f'Superutilisateur "{username}" créé — Delphin BAZIBUHE. '
                    f'Connexion : {username} / {password}'
                )
            )
