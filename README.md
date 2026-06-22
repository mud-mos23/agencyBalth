# Ets Balthazar - Gestion de transferts d'argent

Application web de gestion des transferts d'argent pour les agences. 
Permet d'enregistrer les operations de depot/retrait (Orange Money, Airtel Money, M-Pesa), 
de gerer les depenses, la comptabilite, et de generer des rapports.

## Fonctionnalites

- **Operations** - Creation, validation et suivi des transferts
- **Depenses** - Enregistrement et approbation
- **Comptabilite** - Ecritures automatiques, soldes par devise
- **Rapports** - Statistiques par periode et agence
- **Agences** - Gestion multi-agence
- **Utilisateurs** - 5 roles avec permissions distinctes
- **Commissions** - Configuration des baremes (pourcentage + fixe)

## Technologies

- Python / Flask
- SQLite / SQLAlchemy
- Bootstrap 5
- CSS personnalise (style Odoo-like)

## Installation

```bash
git clone https://github.com/mud-mos23/agencyBalth.git
cd agencyBalth
pip install -r requirements.txt
python app.py
```

Acces : http://localhost:5000

## Comptes par defaut

| Role | Identifiant | Mot de passe |
|------|-------------|--------------|
| Super Admin | admin | admin123 |
| Comptable | comptable | comptable123 |
| Guichetier | guichetier | guichetier123 |
| Secretaire | secretaire | secretaire123 |

## Documentation

Une documentation detaillee par poste est accessible dans l'application 
via le menu **Compte > Documentation**.
