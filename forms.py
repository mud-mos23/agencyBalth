from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SelectField, FloatField, TextAreaField, DateField
from wtforms.validators import DataRequired, Length, Optional, NumberRange

class LoginForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired()])
    password = PasswordField("Mot de passe", validators=[DataRequired()])

class AgencyForm(FlaskForm):
    name = StringField("Nom de l'agence", validators=[DataRequired(), Length(max=120)])
    address = StringField("Adresse", validators=[Optional(), Length(max=255)])
    phone = StringField("Téléphone", validators=[Optional(), Length(max=20)])
    email = StringField("Email", validators=[Optional(), Length(max=120)])

class UserForm(FlaskForm):
    username = StringField("Nom d'utilisateur", validators=[DataRequired(), Length(max=80)])
    full_name = StringField("Nom complet", validators=[DataRequired(), Length(max=120)])
    email = StringField("Email", validators=[Optional(), Length(max=120)])
    phone = StringField("Téléphone", validators=[Optional(), Length(max=20)])
    password = PasswordField("Mot de passe", validators=[DataRequired(), Length(min=4)])
    role = SelectField("Rôle", choices=[
        ('super_admin', 'Super Admin'),
        ('admin_agence', 'Admin Agence'),
        ('comptable', 'Comptable'),
        ('guichetier', 'Guichetier'),
        ('secretaire', 'Secrétaire')
    ], validators=[DataRequired()])
    agency_id = SelectField("Agence", coerce=int, validators=[Optional()])
    cash_usd_opening = FloatField("Solde ouverture Caisse USD", validators=[Optional()])
    cash_fc_opening = FloatField("Solde ouverture Caisse FC", validators=[Optional()])

class OperationForm(FlaskForm):
    operation_type_id = SelectField("Type d'opération", coerce=int, validators=[DataRequired()])
    direction = SelectField("Opération", choices=[
        ('depot', 'Dépôt (espèces → mobile)'),
        ('retrait', 'Retrait (mobile → espèces)')
    ], validators=[DataRequired()])
    client_name = StringField("Nom du client", validators=[DataRequired(), Length(max=120)])
    client_phone = StringField("Téléphone du client", validators=[DataRequired(), Length(max=20)])
    currency = SelectField("Devise", choices=[('USD', '$ Dollar'), ('FC', 'FC Franc')], validators=[DataRequired()])
    amount = FloatField("Montant", validators=[DataRequired(), NumberRange(min=0.01)])
    notes = TextAreaField("Notes", validators=[Optional()])

class CommissionForm(FlaskForm):
    operation_type_id = SelectField("Type d'opération", coerce=int, validators=[DataRequired()])
    direction = SelectField("Opération", choices=[
        ('depot', 'Dépôt'),
        ('retrait', 'Retrait')
    ], validators=[DataRequired()])
    percentage = FloatField("Pourcentage (%)", validators=[Optional(), NumberRange(min=0)])
    fixed_amount = FloatField("Montant fixe (USD)", validators=[Optional(), NumberRange(min=0)])
    fixed_amount_fc = FloatField("Montant fixe (FC)", validators=[Optional(), NumberRange(min=0)])
    min_amount = FloatField("Montant minimum (USD)", validators=[Optional(), NumberRange(min=0)])
    max_amount = FloatField("Montant maximum (USD)", validators=[Optional(), NumberRange(min=0)])

class ExpenseForm(FlaskForm):
    category = SelectField("Catégorie", choices=[
        ('loyer', 'Loyer'),
        ('electricite', 'Électricité'),
        ('eau', 'Eau'),
        ('internet', 'Internet'),
        ('fournitures', 'Fournitures'),
        ('salaire', 'Salaire'),
        ('entretien', 'Entretien'),
        ('transport', 'Transport'),
        ('autre', 'Autre')
    ], validators=[DataRequired()])
    currency = SelectField("Devise", choices=[('USD', '$ Dollar'), ('FC', 'FC Franc')], validators=[DataRequired()])
    amount = FloatField("Montant", validators=[DataRequired(), NumberRange(min=0.01)])
    description = TextAreaField("Description", validators=[DataRequired()])

class FilterForm(FlaskForm):
    date_from = DateField("Date début", validators=[Optional()])
    date_to = DateField("Date fin", validators=[Optional()])
    agency_id = SelectField("Agence", coerce=int, validators=[Optional()])
    status = SelectField("Statut", choices=[
        ('', 'Tous'),
        ('pending', 'En attente'),
        ('validated', 'Validé'),
        ('rejected', 'Rejeté')
    ], validators=[Optional()])
