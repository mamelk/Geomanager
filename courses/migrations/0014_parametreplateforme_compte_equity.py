from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('courses', '0013_parametreplateforme_prix_certificat_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='parametreplateforme',
            name='compte_equity',
            field=models.CharField(
                blank=True,
                default='',
                help_text="Numéro de compte Equity affiché comme moyen de paiement (virement bancaire)",
                max_length=60,
            ),
        ),
    ]
