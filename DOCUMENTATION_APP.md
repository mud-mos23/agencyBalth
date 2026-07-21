# Documentation Technique - Application Agence de Transfert

## 1. Présentation

Application web de gestion d'agence de transfert d'argent pour **ETS BALTA**.  
Permet de gérer les opérations (dépôts/retraits) sur les services de mobile money, les stocks virtuels, la caisse, et les clôtures journalières.

**Stack technique :** Flask + SQLite + SQLAlchemy + Jinja2 + Bootstrap Icons  
**Déploiement :** cPanel avec Passenger WSGI

---

## 2. Modèles de données (models.py)

### User
| Champ | Type | Description |
|---|---|---|
| id | Integer PK | |
| username | String(80) | Login |
| password_hash | String(256) | Mot de passe hashé |
| full_name | String(120) | Nom complet |
| email | String(120) | Nullable |
| phone | String(20) | Nullable |
| role | String(20) | super_admin / admin_agence / comptable / guichetier / secretaire |
| agency_id | FK→agencies | Nullable |
| is_active | Boolean | |
| last_login | DateTime | |
| created_at | DateTime | |

**Méthodes :** `set_password()`, `check_password()`, `has_role()`

### Agency
| Champ | Description |
|---|---|
| id, name, address, phone, email | Infos agence |
| is_active | Booléen |
| users | Relation → User |

### OperationType
Types d'opération : Orange Money, Airtel Money, M-Pesa, Pepete Mobile, Equity

### CommissionConfig
| Champ | Description |
|---|---|
| operation_type_id | FK→operation_types |
| direction | depot / retrait |
| percentage | % commission |
| fixed_amount | Montant fixe en USD |
| fixed_amount_fc | Montant fixe en FC |
| min_amount / max_amount | Bornes |

### Operation
| Champ | Description |
|---|---|
| reference | Unique, généré automatiquement |
| agency_id | FK |
| guichetier_id | FK→users (celui qui saisit) |
| operation_type_id | FK→operation_types |
| direction | depot / retrait |
| client_name, client_phone | Infos client |
| currency | USD / FC |
| amount | Montant |
| commission_* | Calculée automatiquement |
| total_amount | Amount + commission |
| status | pending / validated / rejected |
| validated_by, validated_at | Validation |

**Logique métier :**
- Dépôt : client donne espèces → reçoit mobile money  
  → Stock virtuel AUGMENTE, Caisse DIMINUE
- Retrait : client donne mobile money → reçoit espèces  
  → Stock virtuel DIMINUE, Caisse AUGMENTE

### Expense
Dépenses : loyer, électricité, eau, internet, fournitures, salaire, entretien, transport, autre

### AccountingLog
Journal comptable : enregistre toutes les opérations validées + dépenses

### VirtualStock
| Champ | Description |
|---|---|
| agency_id | FK |
| operation_type_id | FK |
| currency | USD / FC |
| user_id | Nullable → NULL = stock agence, ID = stock guichetier |
| opening_balance | Solde d'ouverture |
| current_balance | Solde courant |

**Logique :** Mis à jour automatiquement à la validation d'une opération

### CashBalance
Même structure que VirtualStock mais pour la caisse physique

### ClotureJournaliere
| Champ | Description |
|---|---|
| agency_id, guichetier_id, date | |
| taux_change | Taux USD→CDF |
| solde_initial_usd/cdf | Report jour précédent |
| ajout/retrait_initial_usd/cdf | Ajustements |
| total_excedent_cdf | SWAPS + Bureau + Autres |
| total_creance_usd/cdf | Créances partenaires |
| total_virtuel_usd/cdf | Somme tous opérateurs |
| total_cash_usd/cdf | Caisse |
| total_dettes_usd/cdf | Dettes |
| total_actif_usd/cdf | Virtuel + Cash + Dettes |
| cumule_usd/cdf | Actif - Initial |
| manque | Cumul CDF + (Cumul USD × Taux) |
| status | brouillon / valide |
| created_by, created_at | |

### Excedent, CreancePartenaire, Dette
Sous-éléments liés à une clôture (relation directe)

---

## 3. Routes principales (app.py)

### Authentification
| Route | Méthode | Rôles | Description |
|---|---|---|---|
| /login | GET/POST | - | Connexion |
| /logout | GET | tous | Déconnexion |
| /profile | GET | tous | Profil + last_login |

### Dashboard
| Route | Rôles | Description |
|---|---|---|
| / | tous | Tableau de bord : stats, soldes, dernières opérations |

### Opérations
| Route | Rôles | Description |
|---|---|---|
| /operations | tous | Liste filtrée (guichetier voit ses opérations) |
| /operations/ajouter | tous | Nouvelle opération |
| /operations/<id> | tous | Détail |
| /operations/<id>/valider | super_admin, admin_agence | Validation |
| /operations/<id>/supprimer | super_admin, admin_agence | Suppression |

### Stocks Virtuels
| Route | Rôles | Description |
|---|---|---|
| /virtual-stocks | tous | Voir stocks par agence/guichetier |
| /virtual-stocks/edit | super_admin, admin_agence | Modifier solde d'ouverture |

### Caisse
| Route | Rôles | Description |
|---|---|---|
| /cash-balance | tous | Voir caisse par agence/guichetier |
| POST | super_admin, admin_agence | Modifier solde d'ouverture |

### Commissions
| Route | Rôles |
|---|---|
| /commissions | super_admin, admin_agence, secretaire |
| /commissions/ajouter | super_admin, admin_agence, secretaire |
| /commissions/<id>/editer | super_admin, admin_agence, secretaire |

### Clôtures Journalières
| Route | Rôles | Description |
|---|---|---|
| /clotures | super_admin, admin_agence, comptable, secretaire | Liste |
| /cloture/nouvelle | super_admin, admin_agence | Formulaire complet |
| /cloture/rapide | super_admin, admin_agence | Auto (POST) |
| /cloture/<id> | Mêmes rôles | Détail (tableau) |
| /cloture/<id>/valider | super_admin, admin_agence | Valider |
| /cloture/<id>/supprimer | super_admin, admin_agence | Supprimer |
| /cloture/importer-excel | super_admin seulement | Importer depuis Excel (POST) |

### API
| Route | Description |
|---|---|
| /api/commission | Calcule commission (GET, params : operation_type_id, direction, amount, currency) |
| /api/soldes-actuels | Retourne soldes virtuels et cash actuels par agence |

### Autres
| Route | Rôles |
|---|---|
| /agences | super_admin, admin_agence, secretaire |
| /utilisateurs | super_admin, admin_agence, secretaire |
| /depenses | super_admin, admin_agence, secretaire |
| /comptabilite | super_admin, admin_agence, comptable, secretaire |
| /rapports | super_admin, admin_agence, comptable, secretaire |
| /documentation | super_admin, admin_agence, comptable, secretaire |

---

## 4. Règles métier

### Rôles et permissions
| Rôle | Opérations | Stocks/Caisse | Compta/Rapports | Admin | Clôtures |
|---|---|---|---|---|---|
| super_admin | CRUD+Tout | Modif+Edit | Oui | Oui | Oui |
| admin_agence | CRUD+Agence | Modif+Edit | Oui | Oui | Oui |
| comptable | Lecture | Lecture | Oui | Non | Oui |
| secretaire | Lecture | Lecture* | Oui | Oui** | Oui |
| guichetier | CRUD+Sienne | Lecture+Sienne | Non | Non | Non |

*\* secretaire ne peut PAS modifier les soldes d'ouverture*  
*\*\* secretaire peut gérer utilisateurs/agences/commissions*

### Validation d'opération
- **Dépôt validé :** VirtualStock.current_balance += amount, CashBalance.current_balance -= amount
- **Retrait validé :** VirtualStock.current_balance -= amount, CashBalance.current_balance += amount
- Seuls super_admin et admin_agence peuvent valider
- La validation crée une entrée dans AccountingLog

### Calcul commission
`commission = max(percent × amount, fixed_amount)` selon la devise

### Clôture rapide
Prend les soldes actuels (VirtualStock + CashBalance) et les compare au solde initial (dernière clôture validée), calcule le cumul et le manque automatiquement.

---

## 5. Déploiement cPanel

### Structure
```
/home/daftooco/balthazar.daftoo.com/
├── app.py                  # Application Flask
├── models.py               # Modèles
├── forms.py                # Formulaires WTForms
├── config.py               # Configuration
├── passenger_wsgi.py       # Point d'entrée WSGI
├── agence.db               # Base SQLite (gitignorée)
├── import_excel.py         # Script d'import Excel
├── templates/              # Templates Jinja2
├── static/                 # Images, CSS
└── requirements.txt        # Dépendances
```

### Passenger WSGI (passenger_wsgi.py)
```python
import sys, os
sys.path.insert(0, os.path.dirname(__file__))
from app import app as application
```

### Après chaque git pull
1. Aller dans cPanel > Setup Python App
2. Cliquer **Restart**

### Dépendances
```
flask, flask-sqlalchemy, flask-login, flask-wtf, wtforms, openpyxl
```

---

## 6. Fichier Excel de clôture

Le fichier `CLOTURE SHOP AIRTEL - Copie (Enregistré automatiquement).xlsx` contient deux feuilles :

| Feuille | Guichetier | Clôtures |
|---|---|---|
| RIZIKI | Riziki | 565 |
| LUMIERE | Lumiere | 468 |

**Structure des colonnes Excel (feuille LUMIERE) :**
| Col | En-tête | Devises |
|---|---|---|
| A | DATTE | Date |
| B-C | SOLDE INITIAL | USD, CDF |
| D-E | AJOUT SUR INITIAL | USD, CDF |
| F-G | RETRAIT SUR L'INITIAL | USD, CDF |
| H-J | EXCEDENT | SWAPS, BUR ECHA, AUTRES (CDF) |
| K-L | CREANCE PARTENAIRES | USD, CDF |
| M-N | TOTAL S.IN ET EXC | USD, CDF (calculé) |
| O-P | VIRTUEL AIRTEL | USD, CDF |
| Q-R | VIRTUEL VODACOM | USD, CDF |
| S-T | VIRTUEL ORANGE | USD, CDF |
| U-V | VIRTUEL PEPELE | USD, CDF |
| W-X | CASH | USD, CDF |
| Y-Z | DETTES | USD, CDF |
| AA-AB | TOTAL CASH+VIRT+ DETTES | USD, CDF (calculé) |
| AC-AD | CUMULE | USD, CDF |
| AE-AF | VÉRIFICATION | TAUX, MANQUE |

### Import automatique
Au démarrage, si la table `clotures_journalieres` est vide et que le fichier Excel existe, l'app importe automatiquement les données.  
Chemin attendu sur cPanel : `/home/daftooco/balthazar.daftoo.com/CLOTURE SHOP AIRTEL - Copie (Enregistré automatiquement).xlsx`

---

## 7. Interface utilisateur

### Sidebar navigation
```
[Logo ETS BALTA]
▸ Dashboard
▸ Opérations
▸ Stocks virtuels
▸ Caisse / Liquidité
▸ Clôtures            ← Nouveau module
▸ Comptabilité
▸ Rapports
── Administration ──
▸ Agences
▸ Utilisateurs
▸ Commissions
── Compte ──
▸ Mon profil
▸ Documentation
▸ Déconnexion
```

### Pages clés

**Dashboard :** Stats globales (total opérations, commissions, soldes), dernières opérations avec logos opérateurs

**Opérations :** Tableau avec référence, client, montant, commission, statut, logos opérateurs

**Stocks virtuels :** Groupé par agence, puis sous-groupes guichetiers, cartes par opérateur avec logos

**Caisse :** Même structure que stocks

**Clôtures :** Tableau complet avec toutes les colonnes USD/CDF, cumul, manque. Bouton "Clôture rapide" pour générer automatiquement

---

## 8. Points à améliorer / modifier

*(Section à compléter par le client)*
