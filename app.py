import os
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, redirect, url_for, flash, request, jsonify, abort
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename

from config import Config
from models import db, User, Agency, OperationType, CommissionConfig, Operation, Expense, AccountingLog, VirtualStock, CashBalance, ClotureJournaliere, Excedent, CreancePartenaire, Dette
from forms import (LoginForm, AgencyForm, UserForm, OperationForm, CommissionForm, ExpenseForm, FilterForm, ClotureForm)

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Veuillez vous connecter pour acceder a cette page.'

OP_ICONS = {
    'Orange Money': 'orange_money.png',
    'Airtel Money': 'airtel_money.png',
    'M-Pesa': 'mpesa.png',
    'Pepete Mobile': 'pepele.webp',
    'Equity': 'equity.png',
}

@app.template_filter('op_icon')
def op_icon_filter(name):
    return url_for('static', filename=f'images/{OP_ICONS.get(name, "")}') if name in OP_ICONS else None

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.has_role(*roles):
                flash('Acces non autorise.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def inject_globals():
    agencies = Agency.query.filter_by(is_active=True).all() if current_user.is_authenticated else []
    return dict(agencies=agencies)

app.context_processor(inject_globals)

@app.route('/')
@login_required
def index():
    return redirect(url_for('dashboard'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            login_user(user)
            user.last_login = datetime.utcnow()
            db.session.commit()
            flash('Connecte avec succes.', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        flash("Nom d'utilisateur ou mot de passe incorrect.", 'danger')
    return render_template('auth/login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Deconnecte avec succes.', 'success')
    return redirect(url_for('login'))

@app.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    user = current_user
    if request.method == 'POST':
        user.full_name = request.form.get('full_name', user.full_name)
        user.email = request.form.get('email') or None
        user.phone = request.form.get('phone') or None
        password = request.form.get('password')
        if password:
            user.set_password(password)
        db.session.commit()
        flash('Profil mis a jour avec succes.', 'success')
        return redirect(url_for('profile'))
    return render_template('users/profile.html', user=user)

@app.route('/documentation')
@login_required
def documentation():
    return render_template('documentation.html')

@app.route('/dashboard')
@login_required
def dashboard():
    user = current_user
    query = Operation.query

    if user.role == 'guichetier':
        query = query.filter_by(guichetier_id=user.id)
    elif user.role != 'super_admin':
        query = query.filter_by(agency_id=user.agency_id)

    today = datetime.utcnow().date()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)

    operations_today = query.filter(db.func.date(Operation.created_at) == today).count()
    operations_week = query.filter(Operation.created_at >= week_ago).count()
    operations_month = query.filter(Operation.created_at >= month_ago).count()

    def filtered_base():
        q = Operation.query
        if user.role == 'guichetier':
            q = q.filter_by(guichetier_id=user.id)
        elif user.role != 'super_admin':
            q = q.filter_by(agency_id=user.agency_id)
        return q

    total_amount_usd_today = filtered_base().filter(
        db.func.date(Operation.created_at) == today, Operation.currency == 'USD'
    ).with_entities(db.func.sum(Operation.amount)).scalar() or 0

    total_amount_fc_today = filtered_base().filter(
        db.func.date(Operation.created_at) == today, Operation.currency == 'FC'
    ).with_entities(db.func.sum(Operation.amount)).scalar() or 0

    total_commission_usd_today = filtered_base().filter(
        db.func.date(Operation.created_at) == today, Operation.currency == 'USD'
    ).with_entities(db.func.sum(Operation.commission_total)).scalar() or 0

    total_commission_fc_today = filtered_base().filter(
        db.func.date(Operation.created_at) == today, Operation.currency == 'FC'
    ).with_entities(db.func.sum(Operation.commission_total)).scalar() or 0

    pending_ops = query.filter_by(status='pending').count()
    validated_ops = query.filter_by(status='validated').count()

    recent_ops = query.order_by(Operation.created_at.desc()).limit(10).all()

    return render_template('dashboard/index.html',
        operations_today=operations_today,
        operations_week=operations_week,
        operations_month=operations_month,
        total_amount_usd_today=total_amount_usd_today,
        total_amount_fc_today=total_amount_fc_today,
        total_commission_usd_today=total_commission_usd_today,
        total_commission_fc_today=total_commission_fc_today,
        pending_ops=pending_ops,
        validated_ops=validated_ops,
        recent_ops=recent_ops)

@app.route('/agences')
@login_required
@role_required('super_admin')
def list_agencies():
    agencies = Agency.query.all()
    return render_template('agences/list.html', agencies=agencies)

@app.route('/agences/ajouter', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def add_agency():
    form = AgencyForm()
    if form.validate_on_submit():
        agency = Agency(
            name=form.name.data,
            address=form.address.data,
            phone=form.phone.data,
            email=form.email.data
        )
        db.session.add(agency)
        db.session.commit()
        flash('Agence creee avec succes.', 'success')
        return redirect(url_for('list_agencies'))
    return render_template('agences/form.html', form=form, title='Ajouter une agence')

@app.route('/agences/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('super_admin')
def edit_agency(id):
    agency = Agency.query.get_or_404(id)
    form = AgencyForm(obj=agency)
    if form.validate_on_submit():
        agency.name = form.name.data
        agency.address = form.address.data
        agency.phone = form.phone.data
        agency.email = form.email.data
        db.session.commit()
        flash('Agence modifiee avec succes.', 'success')
        return redirect(url_for('list_agencies'))
    return render_template('agences/form.html', form=form, title="Modifier l'agence")

@app.route('/agences/supprimer/<int:id>')
@login_required
@role_required('super_admin')
def delete_agency(id):
    agency = Agency.query.get_or_404(id)
    agency.is_active = False
    db.session.commit()
    flash('Agence desactivee.', 'success')
    return redirect(url_for('list_agencies'))

@app.route('/utilisateurs')
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def list_users():
    if current_user.role == 'super_admin':
        users = User.query.all()
    else:
        users = User.query.filter_by(agency_id=current_user.agency_id).all()
    return render_template('users/list.html', users=users)

@app.route('/utilisateurs/ajouter', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def add_user():
    form = UserForm()
    if current_user.role in ('admin_agence', 'secretaire'):
        form.agency_id.data = current_user.agency_id
        form.agency_id.render_kw = {'disabled': True}

    agencies = Agency.query.filter_by(is_active=True).all()
    form.agency_id.choices = [(0, 'Aucune')] + [(a.id, a.name) for a in agencies]
    op_types = OperationType.query.filter_by(is_active=True).all()

    if form.validate_on_submit():
        user = User(
            username=form.username.data,
            full_name=form.full_name.data,
            email=form.email.data or None,
            phone=form.phone.data or None,
            role=form.role.data,
            agency_id=form.agency_id.data if form.agency_id.data != 0 else None
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.flush()

        if user.role == 'guichetier' and user.agency_id:
            for cur in ('USD', 'FC'):
                opening = form.cash_usd_opening.data if cur == 'USD' else form.cash_fc_opening.data
                cb = CashBalance(agency_id=user.agency_id, currency=cur, user_id=user.id, opening_balance=opening or 0.0, current_balance=opening or 0.0)
                db.session.add(cb)
            for ot in op_types:
                for cur in ('USD', 'FC'):
                    key = f'stock_{ot.id}_{"usd" if cur == "USD" else "fc"}'
                    opening = request.form.get(key, 0.0, type=float)
                    vs = VirtualStock(agency_id=user.agency_id, operation_type_id=ot.id, currency=cur, user_id=user.id, opening_balance=opening, current_balance=opening)
                    db.session.add(vs)

        db.session.commit()
        flash('Utilisateur cree avec succes.', 'success')
        return redirect(url_for('list_users'))
    return render_template('users/form.html', form=form, title='Ajouter un utilisateur', op_types=op_types, stock_balances={})

@app.route('/utilisateurs/modifier/<int:id>', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def edit_user(id):
    user = User.query.get_or_404(id)
    form = UserForm(obj=user)
    agencies = Agency.query.filter_by(is_active=True).all()
    form.agency_id.choices = [(0, 'Aucune')] + [(a.id, a.name) for a in agencies]
    op_types = OperationType.query.filter_by(is_active=True).all()

    if form.validate_on_submit():
        user.username = form.username.data
        user.full_name = form.full_name.data
        user.email = form.email.data or None
        user.phone = form.phone.data or None
        user.role = form.role.data
        user.agency_id = form.agency_id.data if form.agency_id.data != 0 else None
        if form.password.data:
            user.set_password(form.password.data)
        db.session.flush()

        if user.role == 'guichetier' and user.agency_id:
            for cur in ('USD', 'FC'):
                opening = form.cash_usd_opening.data if cur == 'USD' else form.cash_fc_opening.data
                cb = CashBalance.query.filter_by(user_id=user.id, currency=cur).first()
                if cb:
                    cb.opening_balance = opening or 0.0
                    cb.current_balance = opening or 0.0
                else:
                    cb = CashBalance(agency_id=user.agency_id, currency=cur, user_id=user.id, opening_balance=opening or 0.0, current_balance=opening or 0.0)
                    db.session.add(cb)
            for ot in op_types:
                for cur in ('USD', 'FC'):
                    key = f'stock_{ot.id}_{"usd" if cur == "USD" else "fc"}'
                    opening = request.form.get(key, 0.0, type=float)
                    vs = VirtualStock.query.filter_by(user_id=user.id, operation_type_id=ot.id, currency=cur).first()
                    if vs:
                        vs.opening_balance = opening
                        vs.current_balance = opening
                    else:
                        vs = VirtualStock(agency_id=user.agency_id, operation_type_id=ot.id, currency=cur, user_id=user.id, opening_balance=opening, current_balance=opening)
                        db.session.add(vs)

        db.session.commit()
        flash('Utilisateur modifie avec succes.', 'success')
        return redirect(url_for('list_users'))

    form.agency_id.data = user.agency_id or 0
    stock_balances = {}
    if user.role == 'guichetier':
        form.cash_usd_opening.data = CashBalance.query.filter_by(user_id=user.id, currency='USD').with_entities(CashBalance.opening_balance).scalar() or 0.0
        form.cash_fc_opening.data = CashBalance.query.filter_by(user_id=user.id, currency='FC').with_entities(CashBalance.opening_balance).scalar() or 0.0
        for vs in VirtualStock.query.filter_by(user_id=user.id).all():
            stock_balances[f'{vs.operation_type_id}_{vs.currency}'] = vs.opening_balance
    return render_template('users/form.html', form=form, title="Modifier l'utilisateur", op_types=op_types, stock_balances=stock_balances)

@app.route('/utilisateurs/supprimer/<int:id>')
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def delete_user(id):
    user = User.query.get_or_404(id)
    user.is_active = False
    db.session.commit()
    flash('Utilisateur desactive.', 'success')
    return redirect(url_for('list_users'))

@app.route('/operations')
@login_required
def list_operations():
    page = request.args.get('page', 1, type=int)
    form = FilterForm()
    agencies = Agency.query.filter_by(is_active=True).all()
    form.agency_id.choices = [(0, 'Toutes')] + [(a.id, a.name) for a in agencies]

    query = Operation.query
    if current_user.role == 'guichetier':
        query = query.filter_by(guichetier_id=current_user.id)
    elif current_user.role != 'super_admin':
        query = query.filter_by(agency_id=current_user.agency_id)

    status = request.args.get('status')
    agency_id = request.args.get('agency_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if status:
        query = query.filter_by(status=status)
    if agency_id:
        query = query.filter_by(agency_id=agency_id)
    if date_from:
        query = query.filter(Operation.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(Operation.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    operations = query.order_by(Operation.created_at.desc()).paginate(
        page=page, per_page=20, error_out=False)
    return render_template('operations/list.html', operations=operations, form=form)

@app.route('/operations/ajouter', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence', 'guichetier', 'secretaire')
def add_operation():
    form = OperationForm()
    op_types = OperationType.query.filter_by(is_active=True).all()
    form.operation_type_id.choices = [(t.id, t.name) for t in op_types]

    if form.validate_on_submit():
        op_type = OperationType.query.get(form.operation_type_id.data)
        commission = calc_commission(form.operation_type_id.data, form.direction.data, form.amount.data, form.currency.data)

        ref = f"TRF-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}-{current_user.id}"

        operation = Operation(
            reference=ref,
            agency_id=current_user.agency_id or 1,
            guichetier_id=current_user.id,
            operation_type_id=form.operation_type_id.data,
            direction=form.direction.data,
            client_name=form.client_name.data,
            client_phone=form.client_phone.data,
            currency=form.currency.data,
            amount=form.amount.data,
            commission_percentage=commission['percentage'],
            commission_fixed=commission['fixed'],
            commission_total=commission['total'],
            total_amount=form.amount.data + commission['total'],
            notes=form.notes.data,
            status='pending'
        )
        db.session.add(operation)
        db.session.commit()
        flash(f'Operation creee avec succes. Reference: {ref}', 'success')
        return redirect(url_for('list_operations'))
    return render_template('operations/form.html', form=form, title='Nouvelle operation')

def calc_commission(op_type_id, direction, amount, currency='USD'):
    configs = CommissionConfig.query.filter_by(
        operation_type_id=op_type_id,
        direction=direction,
        is_active=True
    ).all()

    pct = 0
    fixed = 0
    for cfg in configs:
        if cfg.min_amount and amount < cfg.min_amount:
            continue
        if cfg.max_amount and amount > cfg.max_amount:
            continue
        if cfg.percentage:
            pct = cfg.percentage
        if currency == 'FC' and cfg.fixed_amount_fc:
            fixed = cfg.fixed_amount_fc
        elif currency == 'USD' and cfg.fixed_amount:
            fixed = cfg.fixed_amount

    total = (amount * pct / 100) + fixed
    return {'percentage': pct, 'fixed': fixed, 'total': total}

@app.route('/operations/valider/<int:id>')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def validate_operation(id):
    op = Operation.query.get_or_404(id)
    if op.status != 'pending':
        flash('Cette operation a deja ete traitee.', 'warning')
        return redirect(url_for('list_operations'))

    op.status = 'validated'
    op.validated_by = current_user.id
    op.validated_at = datetime.utcnow()

    log = AccountingLog(
        agency_id=op.agency_id,
        operation_id=op.id,
        currency=op.currency,
        type='commission',
        direction='entree',
        amount=op.commission_total,
        description=f'Commission sur operation {op.reference}',
        created_by=current_user.id
    )
    db.session.add(log)

    log2 = AccountingLog(
        agency_id=op.agency_id,
        operation_id=op.id,
        currency=op.currency,
        type='transfert',
        direction='sortie' if op.direction == 'depot' else 'entree',
        amount=op.amount,
        description=f"{'Depot' if op.direction == 'depot' else 'Retrait'} - {op.reference}",
        created_by=current_user.id
    )
    db.session.add(log2)

    def update_stock(model, extra_filter, direction, amount):
        entry = model.query.filter_by(
            agency_id=op.agency_id, currency=op.currency, **extra_filter
        ).first()
        if not entry:
            entry = model(
                agency_id=op.agency_id, currency=op.currency,
                opening_balance=0.0, current_balance=0.0, **extra_filter
            )
            db.session.add(entry)
        if direction == 'depot':
            entry.current_balance += amount
        else:
            entry.current_balance -= amount

    stock_filters = {'operation_type_id': op.operation_type_id, 'user_id': None}
    cash_filters = {'user_id': None}
    update_stock(VirtualStock, stock_filters, op.direction, op.amount)
    update_stock(CashBalance, cash_filters, op.direction, op.amount)

    if op.guichetier_id:
        stock_filters['user_id'] = op.guichetier_id
        cash_filters['user_id'] = op.guichetier_id
        update_stock(VirtualStock, stock_filters, op.direction, op.amount)
        update_stock(CashBalance, cash_filters, op.direction, op.amount)

    db.session.commit()
    flash('Operation validee avec succes.', 'success')
    return redirect(url_for('list_operations'))

@app.route('/operations/rejeter/<int:id>')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def reject_operation(id):
    op = Operation.query.get_or_404(id)
    op.status = 'rejected'
    op.validated_by = current_user.id
    op.validated_at = datetime.utcnow()
    db.session.commit()
    flash('Operation rejetee.', 'warning')
    return redirect(url_for('list_operations'))

@app.route('/operations/details/<int:id>')
@login_required
def view_operation(id):
    op = Operation.query.get_or_404(id)
    return render_template('operations/details.html', op=op)

@app.route('/api/commission')
@login_required
def api_commission():
    op_type_id = request.args.get('operation_type_id', type=int)
    direction = request.args.get('direction')
    amount = request.args.get('amount', type=float)
    currency = request.args.get('currency', 'USD')
    if not all([op_type_id, direction, amount]):
        return jsonify({'percentage': 0, 'fixed': 0, 'total': 0})
    commission = calc_commission(op_type_id, direction, amount, currency)
    return jsonify(commission)

@app.route('/api/soldes-actuels')
@login_required
def api_soldes_actuels():
    agencies = Agency.query.filter_by(is_active=True).all() if current_user.role == 'super_admin' else [current_user.agency]
    data = {}
    for a in agencies:
        stocks = VirtualStock.query.filter_by(agency_id=a.id, user_id=None).all()
        cash = CashBalance.query.filter_by(agency_id=a.id, user_id=None).all()
        data[str(a.id)] = {
            'virtuel_usd': sum(s.current_balance for s in stocks if s.currency == 'USD'),
            'virtuel_cdf': sum(s.current_balance for s in stocks if s.currency == 'FC'),
            'cash_usd': sum(c.current_balance for c in cash if c.currency == 'USD'),
            'cash_cdf': sum(c.current_balance for c in cash if c.currency == 'FC'),
        }
    return jsonify(data)

@app.route('/commissions')
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def list_commissions():
    configs = CommissionConfig.query.all()
    return render_template('commissions/list.html', configs=configs)

@app.route('/commissions/ajouter', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def add_commission():
    form = CommissionForm()
    op_types = OperationType.query.filter_by(is_active=True).all()
    form.operation_type_id.choices = [(t.id, t.name) for t in op_types]

    if form.validate_on_submit():
        config = CommissionConfig(
            operation_type_id=form.operation_type_id.data,
            direction=form.direction.data,
            percentage=form.percentage.data or 0,
            fixed_amount=form.fixed_amount.data or 0,
            fixed_amount_fc=form.fixed_amount_fc.data or 0,
            min_amount=form.min_amount.data or 0,
            max_amount=form.max_amount.data or None
        )
        db.session.add(config)
        db.session.commit()
        flash('Commission ajoutee avec succes.', 'success')
        return redirect(url_for('list_commissions'))
    return render_template('commissions/form.html', form=form, title='Ajouter une commission')

@app.route('/commissions/supprimer/<int:id>')
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def delete_commission(id):
    config = CommissionConfig.query.get_or_404(id)
    config.is_active = False
    db.session.commit()
    flash('Commission desactivee.', 'success')
    return redirect(url_for('list_commissions'))

@app.route('/stocks-virtuels', methods=['GET', 'POST'])
@login_required
def virtual_stocks():
    if request.method == 'POST':
        if current_user.role not in ('super_admin', 'admin_agence'):
            flash('Action non autorisee.', 'danger')
            return redirect(url_for('virtual_stocks'))
        stock_id = request.form.get('stock_id', type=int)
        opening = request.form.get('opening_balance', type=float)
        stock = VirtualStock.query.get_or_404(stock_id)
        if current_user.role == 'super_admin' or stock.agency_id == current_user.agency_id:
            stock.opening_balance = opening
            stock.current_balance = opening
            db.session.commit()
            flash('Solde d ouverture mis a jour.', 'success')
        return redirect(url_for('virtual_stocks'))

    op_types = OperationType.query.filter_by(is_active=True).all()
    agencies = Agency.query.filter_by(is_active=True).all() if current_user.role == 'super_admin' else [current_user.agency]

    if current_user.role == 'guichetier':
        for ot in op_types:
            for cur in ('USD', 'FC'):
                existing = VirtualStock.query.filter_by(
                    user_id=current_user.id, operation_type_id=ot.id, currency=cur
                ).first()
                if not existing:
                    vs = VirtualStock(
                        agency_id=current_user.agency_id or 1,
                        operation_type_id=ot.id, currency=cur,
                        user_id=current_user.id,
                        opening_balance=0.0, current_balance=0.0
                    )
                    db.session.add(vs)
        db.session.commit()
        stocks = VirtualStock.query.filter_by(user_id=current_user.id).order_by(VirtualStock.operation_type_id, VirtualStock.currency).all()
        return render_template('virtual_stocks.html', stocks=stocks, op_types=op_types, is_guichetier=True, can_edit=False)
    else:
        for a in agencies:
            for ot in op_types:
                for cur in ('USD', 'FC'):
                    existing = VirtualStock.query.filter_by(
                        agency_id=a.id, operation_type_id=ot.id, currency=cur, user_id=None
                    ).first()
                    if not existing:
                        vs = VirtualStock(agency_id=a.id, operation_type_id=ot.id, currency=cur, user_id=None, opening_balance=0.0, current_balance=0.0)
                        db.session.add(vs)
                    for u in User.query.filter_by(agency_id=a.id, role='guichetier', is_active=True).all():
                        existing = VirtualStock.query.filter_by(
                            agency_id=a.id, operation_type_id=ot.id, currency=cur, user_id=u.id
                        ).first()
                        if not existing:
                            vs = VirtualStock(agency_id=a.id, operation_type_id=ot.id, currency=cur, user_id=u.id, opening_balance=0.0, current_balance=0.0)
                            db.session.add(vs)
        db.session.commit()

        agency_filter = {} if current_user.role == 'super_admin' else {'agency_id': current_user.agency_id}
        guichetiers = User.query.filter_by(role='guichetier', is_active=True, **agency_filter).all()
        stocks = VirtualStock.query.filter(**agency_filter).order_by(VirtualStock.agency_id, VirtualStock.user_id, VirtualStock.operation_type_id, VirtualStock.currency).all()
        return render_template('virtual_stocks.html', stocks=stocks, op_types=op_types, guichetiers=guichetiers, agencies=agencies, is_guichetier=False, can_edit=current_user.role in ('super_admin', 'admin_agence'))

@app.route('/cash-balance', methods=['GET', 'POST'])
@login_required
def cash_balance():
    if request.method == 'POST':
        if current_user.role not in ('super_admin', 'admin_agence'):
            flash('Action non autorisee.', 'danger')
            return redirect(url_for('cash_balance'))
        cash_id = request.form.get('cash_id', type=int)
        opening = request.form.get('opening_balance', type=float)
        cash = CashBalance.query.get_or_404(cash_id)
        if current_user.role == 'super_admin' or cash.agency_id == current_user.agency_id:
            cash.opening_balance = opening
            cash.current_balance = opening
            db.session.commit()
            flash('Solde de caisse mis a jour.', 'success')
        return redirect(url_for('cash_balance'))

    agencies = Agency.query.filter_by(is_active=True).all() if current_user.role == 'super_admin' else [current_user.agency]

    if current_user.role == 'guichetier':
        for cur in ('USD', 'FC'):
            existing = CashBalance.query.filter_by(user_id=current_user.id, currency=cur).first()
            if not existing:
                cb = CashBalance(agency_id=current_user.agency_id or 1, currency=cur, user_id=current_user.id, opening_balance=0.0, current_balance=0.0)
                db.session.add(cb)
        db.session.commit()
        balances = CashBalance.query.filter_by(user_id=current_user.id).order_by(CashBalance.currency).all()
        return render_template('cash_balance.html', balances=balances, is_guichetier=True, can_edit=False)
    else:
        for a in agencies:
            for cur in ('USD', 'FC'):
                existing = CashBalance.query.filter_by(agency_id=a.id, currency=cur, user_id=None).first()
                if not existing:
                    cb = CashBalance(agency_id=a.id, currency=cur, user_id=None, opening_balance=0.0, current_balance=0.0)
                    db.session.add(cb)
                for u in User.query.filter_by(agency_id=a.id, role='guichetier', is_active=True).all():
                    existing = CashBalance.query.filter_by(agency_id=a.id, currency=cur, user_id=u.id).first()
                    if not existing:
                        cb = CashBalance(agency_id=a.id, currency=cur, user_id=u.id, opening_balance=0.0, current_balance=0.0)
                        db.session.add(cb)
        db.session.commit()

        agency_filter = {} if current_user.role == 'super_admin' else {'agency_id': current_user.agency_id}
        guichetiers = User.query.filter_by(role='guichetier', is_active=True, **agency_filter).all()
        balances = CashBalance.query.filter(**agency_filter).order_by(CashBalance.agency_id, CashBalance.user_id, CashBalance.currency).all()
        return render_template('cash_balance.html', balances=balances, guichetiers=guichetiers, agencies=agencies, is_guichetier=False, can_edit=current_user.role in ('super_admin', 'admin_agence'))

@app.route('/comptabilite')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def accounting():
    form = FilterForm()
    agencies = Agency.query.filter_by(is_active=True).all()
    form.agency_id.choices = [(0, 'Toutes')] + [(a.id, a.name) for a in agencies]

    query = AccountingLog.query
    if current_user.role != 'super_admin':
        query = query.filter_by(agency_id=current_user.agency_id)

    agency_id = request.args.get('agency_id', type=int)
    date_from = request.args.get('date_from')
    date_to = request.args.get('date_to')

    if agency_id:
        query = query.filter_by(agency_id=agency_id)
    if date_from:
        query = query.filter(AccountingLog.created_at >= datetime.strptime(date_from, '%Y-%m-%d'))
    if date_to:
        query = query.filter(AccountingLog.created_at <= datetime.strptime(date_to, '%Y-%m-%d') + timedelta(days=1))

    logs = query.order_by(AccountingLog.created_at.desc()).all()

    total_entrees_usd = sum(l.amount for l in logs if l.direction == 'entree' and l.currency == 'USD')
    total_sorties_usd = sum(l.amount for l in logs if l.direction == 'sortie' and l.currency == 'USD')
    solde_usd = total_entrees_usd - total_sorties_usd
    total_entrees_fc = sum(l.amount for l in logs if l.direction == 'entree' and l.currency == 'FC')
    total_sorties_fc = sum(l.amount for l in logs if l.direction == 'sortie' and l.currency == 'FC')
    solde_fc = total_entrees_fc - total_sorties_fc

    commissions_usd = sum(l.amount for l in logs if l.type == 'commission' and l.direction == 'entree' and l.currency == 'USD')
    commissions_fc = sum(l.amount for l in logs if l.type == 'commission' and l.direction == 'entree' and l.currency == 'FC')
    transferts_total = sum(l.amount for l in logs if l.type == 'transfert')

    return render_template('comptabilite/index.html',
        logs=logs,
        total_entrees_usd=total_entrees_usd, total_sorties_usd=total_sorties_usd, solde_usd=solde_usd,
        total_entrees_fc=total_entrees_fc, total_sorties_fc=total_sorties_fc, solde_fc=solde_fc,
        commissions_usd=commissions_usd, commissions_fc=commissions_fc,
        transferts_total=transferts_total, form=form)

@app.route('/depenses')
@login_required
def list_expenses():
    query = Expense.query
    if current_user.role != 'super_admin':
        query = query.filter_by(agency_id=current_user.agency_id)

    expenses = query.order_by(Expense.created_at.desc()).all()
    total = sum(e.amount for e in expenses)
    return render_template('depenses/list.html', expenses=expenses, total=total)

@app.route('/depenses/ajouter', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence', 'secretaire')
def add_expense():
    form = ExpenseForm()
    if form.validate_on_submit():
        expense = Expense(
            agency_id=current_user.agency_id or 1,
            category=form.category.data,
            currency=form.currency.data,
            amount=form.amount.data,
            description=form.description.data,
            paid_by=current_user.id
        )
        db.session.add(expense)

        log = AccountingLog(
            agency_id=current_user.agency_id or 1,
            expense_id=expense.id,
            currency=form.currency.data,
            type='depense',
            direction='sortie',
            amount=form.amount.data,
            description=f'Depense: {form.category.data} - {form.description.data[:50]}',
            created_by=current_user.id
        )
        db.session.add(log)
        db.session.commit()
        flash('Depense enregistree.', 'success')
        return redirect(url_for('list_expenses'))
    return render_template('depenses/form.html', form=form, title='Nouvelle depense')

@app.route('/depenses/approuver/<int:id>')
@login_required
@role_required('super_admin', 'comptable', 'admin_agence', 'secretaire')
def approve_expense(id):
    expense = Expense.query.get_or_404(id)
    expense.approved_by = current_user.id
    db.session.commit()
    flash('Depense approuvee.', 'success')
    return redirect(url_for('list_expenses'))

@app.route('/rapports')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def reports():
    form = FilterForm()
    agencies = Agency.query.filter_by(is_active=True).all()
    form.agency_id.choices = [(0, 'Toutes')] + [(a.id, a.name) for a in agencies]

    agency_id = request.args.get('agency_id', type=int)
    period = request.args.get('period', 'month')

    today = datetime.utcnow().date()
    if period == 'week':
        start_date = today - timedelta(days=7)
    elif period == 'month':
        start_date = today - timedelta(days=30)
    elif period == 'quarter':
        start_date = today - timedelta(days=90)
    elif period == 'year':
        start_date = today - timedelta(days=365)
    else:
        start_date = today - timedelta(days=30)

    op_query = Operation.query.filter(Operation.created_at >= start_date)
    if agency_id:
        op_query = op_query.filter_by(agency_id=agency_id)

    total_operations = op_query.count()
    total_amount_usd = db.session.query(db.func.sum(Operation.amount)).filter(
        Operation.created_at >= start_date, Operation.currency == 'USD'
    ).scalar() or 0
    if agency_id:
        total_amount_usd = db.session.query(db.func.sum(Operation.amount)).filter(
            Operation.created_at >= start_date, Operation.currency == 'USD', Operation.agency_id == agency_id
        ).scalar() or 0

    total_amount_fc = db.session.query(db.func.sum(Operation.amount)).filter(
        Operation.created_at >= start_date, Operation.currency == 'FC'
    ).scalar() or 0
    if agency_id:
        total_amount_fc = db.session.query(db.func.sum(Operation.amount)).filter(
            Operation.created_at >= start_date, Operation.currency == 'FC', Operation.agency_id == agency_id
        ).scalar() or 0

    total_commission = db.session.query(db.func.sum(Operation.commission_total)).filter(
        Operation.created_at >= start_date
    ).scalar() or 0
    if agency_id:
        total_commission = db.session.query(db.func.sum(Operation.commission_total)).filter(
            Operation.created_at >= start_date, Operation.agency_id == agency_id
        ).scalar() or 0

    by_type = db.session.query(
        OperationType.name,
        db.func.count(Operation.id),
        db.func.sum(Operation.amount)
    ).join(OperationType).filter(Operation.id.in_([o.id for o in op_query.all()])).group_by(OperationType.name).all()

    by_agency = db.session.query(
        Agency.name,
        db.func.count(Operation.id),
        db.func.sum(Operation.amount)
    ).join(Agency).filter(Operation.id.in_([o.id for o in op_query.all()])).group_by(Agency.name).all()

    expense_usd = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.created_at >= start_date, Expense.currency == 'USD'
    ).scalar() or 0

    expense_fc = db.session.query(db.func.sum(Expense.amount)).filter(
        Expense.created_at >= start_date, Expense.currency == 'FC'
    ).scalar() or 0

    return render_template('rapports/index.html',
        period=period, total_operations=total_operations,
        total_amount_usd=total_amount_usd, total_amount_fc=total_amount_fc,
        total_commission=total_commission,
        by_type=by_type, by_agency=by_agency,
        expense_usd=expense_usd, expense_fc=expense_fc, form=form)

@app.route('/clotures')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def cloture_list():
    agency_filter = {} if current_user.role == 'super_admin' else {'agency_id': current_user.agency_id}
    clotures = ClotureJournaliere.query.filter_by(**agency_filter).order_by(ClotureJournaliere.date.desc()).all()
    return render_template('clotures/list.html', clotures=clotures)

@app.route('/cloture/nouvelle', methods=['GET', 'POST'])
@login_required
@role_required('super_admin', 'admin_agence')
def cloture_new():
    form = ClotureForm()
    agency = current_user.agency if current_user.agency else Agency.query.first()
    agencies = [agency] if current_user.role != 'super_admin' else Agency.query.filter_by(is_active=True).all()
    prev = ClotureJournaliere.query.filter_by(agency_id=agency.id, status='valide').order_by(ClotureJournaliere.date.desc()).first()

    if form.validate_on_submit():
        for a in agencies:
            excedents = []
            for cat, key in [('SWAPS', 'excedent_swaps'), ('Bureau de change', 'excedent_bureau'), ('Autres', 'excedent_autres')]:
                val = getattr(form, key).data or 0
                if val:
                    excedents.append(Excedent(categorie=cat, montant_cdf=val))
            total_exc = sum(e.montant_cdf for e in excedents)

            stocks = VirtualStock.query.filter_by(agency_id=a.id, user_id=None).all()
            virtuel_usd = sum(s.current_balance for s in stocks if s.currency == 'USD')
            virtuel_cdf = sum(s.current_balance for s in stocks if s.currency == 'FC')

            cash_balances = CashBalance.query.filter_by(agency_id=a.id, user_id=None).all()
            cash_usd = sum(c.current_balance for c in cash_balances if c.currency == 'USD')
            cash_cdf = sum(c.current_balance for c in cash_balances if c.currency == 'FC')

            total_actif_usd = virtuel_usd + cash_usd
            total_actif_cdf = virtuel_cdf + cash_cdf

            solde_initial_usd = form.solde_initial_usd.data or 0
            solde_initial_cdf = form.solde_initial_cdf.data or 0
            ajout_usd = form.ajout_initial_usd.data or 0
            ajout_cdf = form.ajout_initial_cdf.data or 0
            retrait_usd = form.retrait_initial_usd.data or 0
            retrait_cdf = form.retrait_initial_cdf.data or 0

            total_sin_usd = solde_initial_usd + ajout_usd - retrait_usd
            total_sin_cdf = solde_initial_cdf + ajout_cdf - retrait_cdf + total_exc

            cumule_usd = total_actif_usd - total_sin_usd
            cumule_cdf = total_actif_cdf - total_sin_cdf
            taux = form.taux_change.data or 0

            manque = cumule_cdf + (cumule_usd * taux)

            cloture = ClotureJournaliere(
                agency_id=a.id,
                date=form.date.data,
                taux_change=taux,
                solde_initial_usd=solde_initial_usd,
                solde_initial_cdf=solde_initial_cdf,
                ajout_initial_usd=ajout_usd,
                ajout_initial_cdf=ajout_cdf,
                retrait_initial_usd=retrait_usd,
                retrait_initial_cdf=retrait_cdf,
                total_excedent_cdf=total_exc,
                total_virtuel_usd=virtuel_usd,
                total_virtuel_cdf=virtuel_cdf,
                total_cash_usd=cash_usd,
                total_cash_cdf=cash_cdf,
                total_dettes_usd=0,
                total_dettes_cdf=0,
                total_actif_usd=total_actif_usd,
                total_actif_cdf=total_actif_cdf,
                cumule_usd=cumule_usd,
                cumule_cdf=cumule_cdf,
                manque=manque,
                notes=form.notes.data,
                created_by=current_user.id,
            )
            db.session.add(cloture)
            db.session.flush()
            for e in excedents:
                e.cloture_id = cloture.id
                db.session.add(e)
        db.session.commit()
        flash('Cloture creee avec succes.', 'success')
        return redirect(url_for('cloture_list'))
    return render_template('clotures/form.html', form=form, agencies=agencies, prev=prev)

@app.route('/cloture/<int:id>')
@login_required
@role_required('super_admin', 'admin_agence', 'comptable', 'secretaire')
def cloture_detail(id):
    cloture = ClotureJournaliere.query.get_or_404(id)
    if current_user.role != 'super_admin' and cloture.agency_id != current_user.agency_id:
        abort(403)
    return render_template('clotures/details.html', cloture=cloture)

@app.route('/cloture/<int:id>/valider', methods=['POST'])
@login_required
@role_required('super_admin', 'admin_agence')
def cloture_valider(id):
    cloture = ClotureJournaliere.query.get_or_404(id)
    if current_user.role != 'super_admin' and cloture.agency_id != current_user.agency_id:
        abort(403)
    cloture.status = 'valide'
    db.session.commit()
    flash('Cloture validee.', 'success')
    return redirect(url_for('cloture_detail', id=id))

@app.route('/cloture/<int:id>/supprimer', methods=['POST'])
@login_required
@role_required('super_admin', 'admin_agence')
def cloture_delete(id):
    cloture = ClotureJournaliere.query.get_or_404(id)
    if current_user.role != 'super_admin' and cloture.agency_id != current_user.agency_id:
        abort(403)
    Excedent.query.filter_by(cloture_id=id).delete()
    CreancePartenaire.query.filter_by(cloture_id=id).delete()
    Dette.query.filter_by(cloture_id=id).delete()
    db.session.delete(cloture)
    db.session.commit()
    flash('Cloture supprimee.', 'success')
    return redirect(url_for('cloture_list'))

def init_db():
    db.create_all()

    import sqlite3
    try:
        conn = sqlite3.connect('agence.db')
        c = conn.cursor()
        for table, col in [('virtual_stocks', 'user_id'), ('cash_balances', 'user_id')]:
            try:
                c.execute(f'ALTER TABLE {table} ADD COLUMN {col} INTEGER REFERENCES users(id)')
                conn.commit()
            except sqlite3.OperationalError:
                pass
        try:
            c.execute('ALTER TABLE commission_configs ADD COLUMN fixed_amount_fc FLOAT DEFAULT 0.0')
            conn.commit()
        except sqlite3.OperationalError:
            pass
        try:
            c.execute('ALTER TABLE clotures_journalieres ADD COLUMN guichetier_id INTEGER REFERENCES users(id)')
            conn.commit()
        except sqlite3.OperationalError:
            pass
        conn.close()
    except Exception:
        pass

    for name, desc in [
        ('Orange Money', 'Transfert via Orange Money'),
        ('Airtel Money', 'Transfert via Airtel Money'),
        ('M-Pesa', 'Transfert via M-Pesa'),
        ('Pepete Mobile', 'Transfert via Pepete Mobile'),
        ('Equity', 'Transfert via Equity'),
    ]:
        if not OperationType.query.filter_by(name=name).first():
            db.session.add(OperationType(name=name, description=desc))
    db.session.commit()

    if not CommissionConfig.query.first():
        for ot in OperationType.query.filter_by(is_active=True).all():
            for direction in ['depot', 'retrait']:
                cfg = CommissionConfig(
                    operation_type_id=ot.id,
                    direction=direction,
                    percentage=1.0,
                    fixed_amount=0.50,
                    min_amount=0,
                    is_active=True
                )
                db.session.add(cfg)
        db.session.commit()

    if not Agency.query.first():
        agency = Agency(name='Agence Principale', address='Centre Ville', phone='+123456789')
        db.session.add(agency)
        db.session.commit()

    if not User.query.first():
        admin = User(
            username='admin',
            full_name='Administrateur',
            email='admin@agence.com',
            role='super_admin'
        )
        admin.set_password('admin123')
        db.session.add(admin)

        agency = Agency.query.first()
        comptable = User(
            username='comptable',
            full_name='Comptable',
            email='comptable@agence.com',
            role='comptable',
            agency_id=agency.id
        )
        comptable.set_password('comptable123')
        db.session.add(comptable)

        guichetier = User(
            username='guichetier',
            full_name='Guichetier Principal',
            email='guichetier@agence.com',
            role='guichetier',
            agency_id=agency.id
        )
        guichetier.set_password('guichetier123')
        db.session.add(guichetier)

        secretaire = User(
            username='secretaire',
            full_name='Secretaire',
            email='secretaire@agence.com',
            role='secretaire',
            agency_id=agency.id
        )
        secretaire.set_password('secretaire123')
        db.session.add(secretaire)
        db.session.commit()

    if not CashBalance.query.first():
        agency = Agency.query.first()
        if agency:
            for cur in ('USD', 'FC'):
                cb = CashBalance(agency_id=agency.id, currency=cur, opening_balance=0.0, current_balance=0.0)
                db.session.add(cb)
            db.session.commit()

    if not VirtualStock.query.first():
        agency = Agency.query.first()
        if agency:
            for ot in OperationType.query.filter_by(is_active=True).all():
                for cur in ('USD', 'FC'):
                    vs = VirtualStock(
                        agency_id=agency.id,
                        operation_type_id=ot.id,
                        currency=cur,
                        opening_balance=0.0,
                        current_balance=0.0
                    )
                    db.session.add(vs)
            db.session.commit()

with app.app_context():
    init_db()

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
