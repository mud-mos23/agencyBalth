from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    role = db.Column(db.String(20), nullable=False, default='guichetier')
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    last_login = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def has_role(self, *roles):
        return self.role in roles

class Agency(db.Model):
    __tablename__ = 'agencies'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    address = db.Column(db.String(255), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    email = db.Column(db.String(120), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    users = db.relationship('User', backref='agency', lazy='dynamic')

class OperationType(db.Model):
    __tablename__ = 'operation_types'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False, unique=True)
    description = db.Column(db.String(255), nullable=True)
    is_active = db.Column(db.Boolean, default=True)

class CommissionConfig(db.Model):
    __tablename__ = 'commission_configs'
    id = db.Column(db.Integer, primary_key=True)
    operation_type_id = db.Column(db.Integer, db.ForeignKey('operation_types.id'), nullable=False)
    direction = db.Column(db.String(20), nullable=False, default='depot')
    percentage = db.Column(db.Float, default=0.0)
    fixed_amount = db.Column(db.Float, default=0.0)
    fixed_amount_fc = db.Column(db.Float, default=0.0)
    min_amount = db.Column(db.Float, default=0.0)
    max_amount = db.Column(db.Float, nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    operation_type = db.relationship('OperationType')

class Operation(db.Model):
    __tablename__ = 'operations'
    id = db.Column(db.Integer, primary_key=True)
    reference = db.Column(db.String(50), unique=True, nullable=False)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    guichetier_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    operation_type_id = db.Column(db.Integer, db.ForeignKey('operation_types.id'), nullable=False)
    direction = db.Column(db.String(20), nullable=False, default='depot')
    client_name = db.Column(db.String(120), nullable=False)
    client_phone = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    amount = db.Column(db.Float, nullable=False)
    commission_percentage = db.Column(db.Float, default=0.0)
    commission_fixed = db.Column(db.Float, default=0.0)
    commission_total = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default='pending')
    validated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    validated_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    agency = db.relationship('Agency')
    guichetier = db.relationship('User', foreign_keys=[guichetier_id])
    validator = db.relationship('User', foreign_keys=[validated_by])
    operation_type = db.relationship('OperationType')

class Expense(db.Model):
    __tablename__ = 'expenses'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    category = db.Column(db.String(80), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    paid_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    receipt_path = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    agency = db.relationship('Agency')
    payer = db.relationship('User', foreign_keys=[paid_by])
    approver = db.relationship('User', foreign_keys=[approved_by])

class AccountingLog(db.Model):
    __tablename__ = 'accounting_logs'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    operation_id = db.Column(db.Integer, db.ForeignKey('operations.id'), nullable=True)
    expense_id = db.Column(db.Integer, db.ForeignKey('expenses.id'), nullable=True)
    type = db.Column(db.String(30), nullable=False)
    direction = db.Column(db.String(10), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    amount = db.Column(db.Float, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    agency = db.relationship('Agency')
    operation = db.relationship('Operation')
    expense = db.relationship('Expense')
    creator = db.relationship('User')

class VirtualStock(db.Model):
    __tablename__ = 'virtual_stocks'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    operation_type_id = db.Column(db.Integer, db.ForeignKey('operation_types.id'), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    opening_balance = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    agency = db.relationship('Agency')
    operation_type = db.relationship('OperationType')
    user = db.relationship('User')

class CashBalance(db.Model):
    __tablename__ = 'cash_balances'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    currency = db.Column(db.String(3), default="USD")
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    opening_balance = db.Column(db.Float, default=0.0)
    current_balance = db.Column(db.Float, default=0.0)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    agency = db.relationship('Agency')
    user = db.relationship('User')

class ClotureJournaliere(db.Model):
    __tablename__ = 'clotures_journalieres'
    id = db.Column(db.Integer, primary_key=True)
    agency_id = db.Column(db.Integer, db.ForeignKey('agencies.id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='brouillon')
    taux_change = db.Column(db.Float, default=0.0)
    solde_initial_usd = db.Column(db.Float, default=0.0)
    solde_initial_cdf = db.Column(db.Float, default=0.0)
    ajout_initial_usd = db.Column(db.Float, default=0.0)
    ajout_initial_cdf = db.Column(db.Float, default=0.0)
    retrait_initial_usd = db.Column(db.Float, default=0.0)
    retrait_initial_cdf = db.Column(db.Float, default=0.0)
    total_excedent_cdf = db.Column(db.Float, default=0.0)
    total_creance_usd = db.Column(db.Float, default=0.0)
    total_creance_cdf = db.Column(db.Float, default=0.0)
    total_virtuel_usd = db.Column(db.Float, default=0.0)
    total_virtuel_cdf = db.Column(db.Float, default=0.0)
    total_cash_usd = db.Column(db.Float, default=0.0)
    total_cash_cdf = db.Column(db.Float, default=0.0)
    total_dettes_usd = db.Column(db.Float, default=0.0)
    total_dettes_cdf = db.Column(db.Float, default=0.0)
    total_actif_usd = db.Column(db.Float, default=0.0)
    total_actif_cdf = db.Column(db.Float, default=0.0)
    cumule_usd = db.Column(db.Float, default=0.0)
    cumule_cdf = db.Column(db.Float, default=0.0)
    manque = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    agency = db.relationship('Agency')
    creator = db.relationship('User')

class Excedent(db.Model):
    __tablename__ = 'excedents'
    id = db.Column(db.Integer, primary_key=True)
    cloture_id = db.Column(db.Integer, db.ForeignKey('clotures_journalieres.id'), nullable=False)
    categorie = db.Column(db.String(50), nullable=False)
    montant_cdf = db.Column(db.Float, default=0.0)
    cloture = db.relationship('ClotureJournaliere', backref='excedents')

class CreancePartenaire(db.Model):
    __tablename__ = 'creances_partenaires'
    id = db.Column(db.Integer, primary_key=True)
    cloture_id = db.Column(db.Integer, db.ForeignKey('clotures_journalieres.id'), nullable=False)
    partenaire = db.Column(db.String(120), nullable=False)
    montant_usd = db.Column(db.Float, default=0.0)
    montant_cdf = db.Column(db.Float, default=0.0)
    cloture = db.relationship('ClotureJournaliere', backref='creances')

class Dette(db.Model):
    __tablename__ = 'dettes'
    id = db.Column(db.Integer, primary_key=True)
    cloture_id = db.Column(db.Integer, db.ForeignKey('clotures_journalieres.id'), nullable=False)
    creancier = db.Column(db.String(120), nullable=False)
    montant_usd = db.Column(db.Float, default=0.0)
    montant_cdf = db.Column(db.Float, default=0.0)
    cloture = db.relationship('ClotureJournaliere', backref='dettes')
