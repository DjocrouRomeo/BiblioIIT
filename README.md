# BiblioIIT — Gestion de bibliothèque (application console)

Projet de la **Séance 4** — Institut Ivoirien de Technologie (IIT).
Application console en **Python**, architecture **MVC**, base de données **SQLite**, tests unitaires et pipeline CI.

## 1. Prérequis

- **Python 3.9 ou supérieur** (vérifier avec `python --version`)
- Aucune bibliothèque externe : tout repose sur la bibliothèque standard (`sqlite3`, `unittest`, `argparse`).

## 2. Exécuter le projet

Depuis le dossier `BiblioIIT/` :

```bash
python main.py
```

- Au **premier lancement**, la base `biblioiit.db` est créée et remplie avec des données de démonstration
  (7 livres, 3 adhérents `E2026-001` à `E2026-003`).
- Pour repartir de zéro : supprimer le fichier `biblioiit.db`.
- Pour utiliser un autre fichier de base : `python main.py --db autre.db`.

Dans PyCharm : ouvrir le dossier `BiblioIIT`, puis exécuter `main.py`.

## 3. Lancer les tests

```bash
python -m unittest discover -s tests -v
```

24 tests : règles métier, dépôt SQLite, service (contrôleur) et une session complète
de la vue qui **rejoue la session affichée sur la slide** (recherche « Kourouma », emprunt de `L002`,
refus du second emprunt).

## 4. Fonctionnalités (menu)

| N° | Option | Description |
|---|---|---|
| 1 | Rechercher un livre | par titre, auteur, mot-clé, catégorie ou code |
| 2 | Fiche d'un livre | disponibilité, exemplaires, réservations en attente |
| 3 | Emprunter | calcule automatiquement la date de retour prévue |
| 4 | Rendre | calcule le retard et l'amende, prévient le prochain réservataire |
| 5 | Prolonger | une seule fois, sous conditions |
| 6 | Réserver | file d'attente pour un livre déjà emprunté |
| 7 | Inscrire un adhérent | génère un matricule `E2026-00X` |
| 8 | Consulter un adhérent | emprunts en cours, historique, amendes |
| 9 | Retards et amendes | liste des emprunts en retard |
| 10 | Statistiques | livres les plus empruntés, taux de retard |
| 11 | Administration | ajouter / modifier / retirer un livre |
| 12 | Encaisser les amendes | remet le compteur d'amendes à zéro |
| 0 | Quitter | |

### Règles métier (fichier `app/models/regles.py`)

| Règle | Valeur |
|---|---|
| Durée de prêt | 14 jours |
| Quota | 3 livres simultanés par adhérent |
| Prolongation | 1 fois (+14 jours), impossible si en retard ou si le livre est réservé par un autre |
| Amende | 100 FCFA par jour de retard, plafonnée à 5 000 FCFA |
| Emprunt refusé si | inscription expirée (> 1 an), livre en retard non rendu, amende impayée, quota atteint |
| Réservation | file d'attente : seul le premier réservataire peut emprunter le livre rendu |
| Exemplaires | un livre (titre) peut avoir plusieurs exemplaires |

Toutes ces valeurs sont des constantes en tête de `regles.py` et se modifient en un seul endroit.

## 5. Architecture MVC

```
BiblioIIT/
├── main.py                      # point d'entrée : assemble M, C et V
├── app/
│   ├── models/                  # MODÈLE
│   │   ├── modeles.py           #   entités : Livre, Adherent, Emprunt, Reservation
│   │   ├── regles.py            #   règles métier pures (durée, quota, amende...)
│   │   ├── depot_sqlite.py      #   accès aux données SQLite (CRUD, requêtes)
│   │   └── donnees_demo.py      #   données de démonstration
│   ├── controllers/             # CONTRÔLEUR
│   │   └── service.py           #   BiblioService : emprunter, rendre, prolonger, réserver...
│   └── views/                   # VUE
│       └── console.py           #   VueConsole : menu, saisies, affichage
├── tests/                       # tests unitaires (un fichier par couche)
├── .github/workflows/ci.yml     # pipeline CI (tests à chaque push / PR)
└── README.md
```

| Couche | Rôle | Ce qu'elle ne fait JAMAIS |
|---|---|---|
| **Modèle** | données, règles métier, persistance SQLite | afficher, lire le clavier |
| **Contrôleur** (`service.py`) | applique les règles, orchestre le dépôt, lève `BiblioError` | `print()`, `input()`, SQL |
| **Vue** (`console.py`) | affiche le menu, lit les saisies, montre résultats et erreurs | règle métier, SQL |

Flux d'un emprunt : `console.py` lit le code livre et le matricule → `BiblioService.emprunter()`
→ `regles.peut_emprunter()` valide → `DepotSQLite.creer_emprunt()` enregistre → la vue affiche
« Emprunt enregistré. Retour prévu le JJ/MM/AAAA. ».

Correspondance avec les modules de la slide : `regles.py`, `modeles.py`, `depot_sqlite.py` (Modèle),
`service.py` (Contrôleur), `console.py` (Vue), `tests/`.

## 6. Exemple de session (démo)

```
=== BiblioIIT ===
Votre choix : 1
Mot-clé : Kourouma
  L002  Les Soleils des indépendances — Ahmadou Kourouma (1968) [1/1 dispo]
  L004  Allah n'est pas obligé — Ahmadou Kourouma (2000) [2/2 dispo]
Votre choix : 3
Code du livre : L002
Matricule : E2026-001
Emprunt enregistré. Retour prévu le <date du jour + 14 jours>.
Votre choix : 3
Code du livre : L002
Matricule : E2026-002
Impossible : Le livre « Les Soleils des indépendances » est déjà emprunté (vous pouvez le réserver).
```

## 7. Organisation d'équipe (Git)

| Module | Branche | Membre |
|---|---|---|
| `regles.py` | `feature/regles` | A |
| `modeles.py` | `feature/modeles` | B |
| `depot_sqlite.py` | `feature/base` | C |
| `service.py` | `feature/service` | D |
| `console.py` | `feature/menu` | E |
| `tests/` | — | chacun ses tests |

Livrable : dépôt partagé, au moins 5 commits par membre, une PR relue par une autre personne,
pipeline CI vert (`.github/workflows/ci.yml` exécute les tests à chaque push et PR).

## 8. Équipe

Noms des membres : _à compléter_
